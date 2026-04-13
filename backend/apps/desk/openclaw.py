import json
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from .models import AgentRun, AgentTemplate, ApprovalDecision, BoardBrief, Mission, MissionEvent, PricingProfile, QualityGate, Workstream


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in [
        "AI_BASE_URL",
        "AI_API_KEY",
        "AI_MODEL",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OPENCLAW_GATEWAY_TOKEN",
        "OPENCLAW_GATEWAY_PASSWORD",
    ]:
        value = getattr(settings, key, "")
        if value:
            env[key] = value
    return env


def _run_openclaw(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["openclaw", *args],
        cwd=str(settings.BASE_DIR.parent),
        env=_base_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def _json_from_output(output: str) -> dict[str, Any]:
    start = output.find("{")
    if start < 0:
        return {}
    try:
        return json.loads(output[start:])
    except json.JSONDecodeError:
        return {}


def gateway_status() -> dict[str, Any]:
    completed = _run_openclaw(["gateway", "status"], timeout=20)
    output = completed.stdout
    return {
        "ok": completed.returncode == 0 and "Runtime: running" in output,
        "rpcOk": "RPC probe: ok" in output,
        "pairingRequired": "pairing required" in output.lower(),
        "listening": "Listening: 127.0.0.1:7788" in output,
        "gatewayUrl": settings.OPENCLAW_GATEWAY_URL,
        "authMode": settings.OPENCLAW_GATEWAY_AUTH_MODE,
        "raw": output[-4000:],
    }


def model_status() -> dict[str, Any]:
    completed = _run_openclaw(["models", "status", "--json"], timeout=30)
    data = _json_from_output(completed.stdout)
    return {
        "ok": completed.returncode == 0 and bool(data.get("defaultModel")),
        "defaultModel": data.get("defaultModel", ""),
        "resolvedDefault": data.get("resolvedDefault", ""),
        "missingProvidersInUse": data.get("auth", {}).get("missingProvidersInUse", []),
    }


def dashboard_metrics(organization=None) -> dict[str, Any]:
    missions = Mission.objects.all()
    templates = AgentTemplate.objects.all()
    if organization:
        missions = missions.filter(organization=organization)
        templates = templates.filter(organization=organization)
    completed_missions = missions.filter(status__in=[Mission.Status.SUCCEEDED, Mission.Status.FAILED, Mission.Status.ABORTED]).count()
    succeeded_missions = missions.filter(status=Mission.Status.SUCCEEDED).count()
    return {
        "agentsReady": templates.filter(status=AgentTemplate.Status.READY).count(),
        "activeMissions": missions.filter(status__in=[Mission.Status.QUEUED, Mission.Status.RUNNING], archived_at__isnull=True).count(),
        "budgetUsedUsd": float(sum(mission.estimated_cost_usd for mission in missions.filter(archived_at__isnull=True))),
        "qualityGates": QualityGate.objects.filter(mission__in=missions).count(),
        "agentRuns": AgentRun.objects.filter(workstream__mission__in=missions).count(),
        "successRate": (succeeded_missions / completed_missions) if completed_missions else 0,
    }


def usage_cost(days: int = 30) -> dict[str, Any]:
    completed = _run_openclaw(["gateway", "usage-cost", "--json", "--days", str(days)], timeout=20)
    data = _json_from_output(completed.stdout)
    if completed.returncode != 0:
        return {"ok": False, "error": completed.stdout[-2000:]}
    return {"ok": True, "data": data}


def gateway_logs(limit: int = 100) -> list[dict[str, Any]]:
    completed = _run_openclaw(["logs", "--json", "--limit", str(limit)], timeout=20)
    entries: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        if not line.startswith("{"):
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def create_event(mission: Mission, message: str, *, level: str = "info", event_type: str = "log", payload: dict[str, Any] | None = None) -> MissionEvent:
    event = MissionEvent.objects.create(
        mission=mission,
        type=event_type,
        level=level,
        message=message,
        payload=payload or {},
    )
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"mission_{mission.id}",
            {
                "type": "mission.event",
                "event": serialize_event(event),
            },
        )
    return event


def serialize_event(event: MissionEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "type": event.type,
        "level": event.level,
        "message": event.message,
        "payload": event.payload,
        "createdAt": event.created_at.isoformat(),
    }


def serialize_gate(gate: QualityGate) -> dict[str, Any]:
    return {
        "id": gate.id,
        "name": gate.name,
        "status": gate.status,
        "details": gate.details,
        "updatedAt": gate.updated_at.isoformat(),
    }


def serialize_agent_template(template: AgentTemplate) -> dict[str, Any]:
    return {
        "id": template.id,
        "name": template.name,
        "title": template.title,
        "mission": template.mission,
        "reportsTo": template.reports_to or None,
        "status": template.status,
        "tools": template.tools,
        "modelPreference": template.model_preference,
        "budgetLimitUsd": str(template.budget_limit_usd),
    }


def serialize_agent_run(agent_run: AgentRun) -> dict[str, Any]:
    return {
        "id": agent_run.id,
        "sessionId": agent_run.session_id,
        "status": agent_run.status,
        "logs": agent_run.logs,
        "usage": {
            "input": agent_run.input_tokens,
            "output": agent_run.output_tokens,
            "estimatedCostUsd": str(agent_run.estimated_cost_usd),
        },
        "resultText": agent_run.result_text,
        "error": agent_run.error,
        "createdAt": agent_run.created_at.isoformat(),
        "startedAt": agent_run.started_at.isoformat() if agent_run.started_at else None,
        "finishedAt": agent_run.finished_at.isoformat() if agent_run.finished_at else None,
    }


def serialize_workstream(workstream: Workstream) -> dict[str, Any]:
    return {
        "id": workstream.id,
        "owner": workstream.owner,
        "title": workstream.title,
        "description": workstream.description,
        "status": workstream.status,
        "result": workstream.result,
        "agentTemplateId": workstream.agent_template_id,
        "agentRuns": [serialize_agent_run(agent_run) for agent_run in workstream.agent_runs.all()],
        "updatedAt": workstream.updated_at.isoformat(),
    }


def serialize_board_brief(brief: BoardBrief | None) -> dict[str, Any] | None:
    if not brief:
        return None
    return {
        "id": brief.id,
        "title": brief.title,
        "summary": brief.summary,
        "recommendations": brief.recommendations,
        "risks": brief.risks,
        "sources": brief.sources,
        "updatedAt": brief.updated_at.isoformat(),
    }


def serialize_approval_decision(decision: ApprovalDecision) -> dict[str, Any]:
    return {
        "id": decision.id,
        "decision": decision.decision,
        "reviewer": decision.reviewer,
        "notes": decision.notes,
        "createdAt": decision.created_at.isoformat(),
    }


def serialize_mission(mission: Mission, *, include_events: bool = False) -> dict[str, Any]:
    brief = getattr(mission, "board_brief", None)
    data = {
        "id": str(mission.id),
        "command": mission.command,
        "sessionId": mission.session_id,
        "agentId": mission.agent_id,
        "status": mission.status,
        "resultText": mission.result_text,
        "error": mission.error,
        "abortRequested": mission.abort_requested,
        "archivedAt": mission.archived_at.isoformat() if mission.archived_at else None,
        "usage": {
            "input": mission.input_tokens,
            "output": mission.output_tokens,
            "total": mission.total_tokens,
            "estimatedCostUsd": str(mission.estimated_cost_usd),
        },
        "qualityGates": [serialize_gate(gate) for gate in mission.quality_gates.all()],
        "workstreams": [serialize_workstream(workstream) for workstream in mission.workstreams.all()],
        "approvalDecisions": [serialize_approval_decision(decision) for decision in mission.approval_decisions.all()],
        "boardBrief": serialize_board_brief(brief),
        "createdAt": mission.created_at.isoformat(),
        "startedAt": mission.started_at.isoformat() if mission.started_at else None,
        "finishedAt": mission.finished_at.isoformat() if mission.finished_at else None,
    }
    if include_events:
        data["events"] = [serialize_event(event) for event in mission.events.all()]
    return data


def start_mission(mission: Mission) -> None:
    thread = threading.Thread(target=_run_mission, args=(str(mission.id),), daemon=True)
    thread.start()


def retry_workstream(workstream: Workstream) -> AgentRun:
    mission = workstream.mission
    if mission.status in [Mission.Status.QUEUED, Mission.Status.RUNNING]:
        raise ValueError("Running missions cannot retry individual workstreams.")

    context = _workstream_context(list(mission.workstreams.exclude(id=workstream.id)))
    workstream.status = Workstream.Status.QUEUED
    workstream.result = ""
    workstream.save(update_fields=["status", "result", "updated_at"])
    mission.status = Mission.Status.RUNNING
    mission.error = ""
    mission.abort_requested = False
    mission.finished_at = None
    mission.save(update_fields=["status", "error", "abort_requested", "finished_at"])

    agent_run = _run_agent_turn(workstream, context)
    mission = Mission.objects.get(id=mission.id)
    _aggregate_agent_usage(mission)
    workstreams = list(Workstream.objects.filter(mission=mission))
    mission.result_text = _workstream_context(workstreams)
    mission.raw_result = {
        "workstreams": [
            {
                "id": item.id,
                "owner": item.owner,
                "status": item.status,
                "result": item.result,
            }
            for item in workstreams
        ]
    }
    if any(item.status == Workstream.Status.FAILED for item in workstreams):
        mission.status = Mission.Status.FAILED
        mission.error = "One or more workstreams failed."
        _set_gate(mission, "agent-result", QualityGate.Status.FAILED, mission.error)
    else:
        mission.status = Mission.Status.SUCCEEDED
        mission.error = ""
        _set_gate(mission, "agent-result", QualityGate.Status.PASSED, "All OpenClaw workstream agents returned results.")
        _set_gate(mission, "founder-approval", QualityGate.Status.PENDING, "Awaiting founder review before follow-up execution.")
    _set_gate(mission, "cost-capture", QualityGate.Status.PASSED, f"{mission.total_tokens} total tokens captured; estimated cost ${mission.estimated_cost_usd}.")
    mission.finished_at = timezone.now()
    mission.save()
    if mission.status == Mission.Status.SUCCEEDED:
        _create_board_brief(mission, mission.result_text)
    create_event(mission, f"{workstream.owner} workstream retry finished.", event_type="status", payload=serialize_mission(mission))
    return agent_run


def _ensure_quality_gates(mission: Mission) -> None:
    for name in ["gateway-health", "model-provider", "agent-result", "cost-capture", "founder-approval"]:
        QualityGate.objects.get_or_create(mission=mission, name=name)


def _set_gate(mission: Mission, name: str, status: str, details: str = "") -> None:
    gate, _ = QualityGate.objects.get_or_create(mission=mission, name=name)
    gate.status = status
    gate.details = details
    gate.save(update_fields=["status", "details", "updated_at"])


def _ensure_workstreams(mission: Mission) -> None:
    definitions = [
        ("coo", "Mission decomposition", "Define workstreams, acceptance criteria, and reporting format."),
        ("cto", "Technical review", "Assess technical path, implementation risk, and engineering quality."),
        ("cfo", "Cost review", "Estimate token/API spend, budget risk, and return on effort."),
        ("cmo", "Market review", "Assess positioning, user value, and go-to-market implications."),
        ("sre", "Reliability review", "Check deployment, monitoring, rollback, and operational safety."),
    ]
    templates = {
        template.id: template
        for template in AgentTemplate.objects.filter(id__in=[item[0] for item in definitions], organization=mission.organization)
    }
    for index, (agent_id, title, description) in enumerate(definitions, start=1):
        template = templates.get(agent_id)
        Workstream.objects.get_or_create(
            mission=mission,
            owner=template.name if template else agent_id.upper(),
            title=title,
            defaults={
                "agent_template": template,
                "description": description,
                "sort_order": index * 10,
            },
        )


def _set_workstreams(mission: Mission, status: str, result: str = "") -> None:
    for workstream in mission.workstreams.all():
        workstream.status = status
        if result:
            workstream.result = result
        workstream.save(update_fields=["status", "result", "updated_at"])


def _model_key(model_preference: str = "") -> tuple[str, str]:
    fallback = f"opc/{settings.AI_MODEL}" if settings.AI_MODEL else ""
    model = (model_preference or "").strip() or fallback
    if "/" in model:
        provider, model_id = model.split("/", 1)
        return provider, model_id
    return "opc", model


def _estimate_cost(input_tokens: int, output_tokens: int, model_preference: str = "", organization=None) -> Decimal:
    provider, model_id = _model_key(model_preference)
    profile = None
    if model_id:
        profiles = PricingProfile.objects.filter(provider=provider, model_id=model_id, is_active=True)
        if organization:
            profiles = profiles.filter(organization=organization)
        profile = profiles.first()
    input_rate = profile.input_per_1k_usd if profile else Decimal(str(settings.OPC_COST_INPUT_PER_1K_USD or "0"))
    output_rate = profile.output_per_1k_usd if profile else Decimal(str(settings.OPC_COST_OUTPUT_PER_1K_USD or "0"))
    return ((Decimal(input_tokens) / Decimal(1000)) * input_rate) + ((Decimal(output_tokens) / Decimal(1000)) * output_rate)


def _result_text(data: dict[str, Any]) -> str:
    result_text = data.get("meta", {}).get("finalAssistantVisibleText", "")
    if result_text:
        return result_text
    payloads = data.get("payloads") or []
    return "\n".join(item.get("text", "") for item in payloads if item.get("text"))


def _usage(data: dict[str, Any]) -> dict[str, int]:
    raw = data.get("meta", {}).get("agentMeta", {}).get("usage", {})
    input_tokens = int(raw.get("input") or 0)
    output_tokens = int(raw.get("output") or 0)
    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": int(raw.get("total") or input_tokens + output_tokens),
    }


def _workstream_session_id(mission: Mission, workstream: Workstream) -> str:
    owner = (workstream.agent_template_id or workstream.owner or "agent").lower().replace(" ", "-")
    return f"{mission.session_id}-{owner}-{workstream.id}"


def _workstream_prompt(workstream: Workstream, context: str = "") -> str:
    mission = workstream.mission
    template = workstream.agent_template
    role = f"{workstream.owner} - {workstream.title}"
    role_mission = template.mission if template else workstream.description
    tools = ", ".join(template.tools) if template and template.tools else "none declared"
    parts = [
        f"You are the {role} in OPC.",
        f"Role mission: {role_mission}",
        f"Available role tools: {tools}",
        f"Founder command: {mission.command}",
        f"Workstream objective: {workstream.description}",
    ]
    if context:
        parts.append(f"Prior workstream context:\n{context}")
    parts.append("Return a concise executive workstream result with decisions, risks, and next actions.")
    return "\n\n".join(parts)


def _mission_cost_so_far(mission: Mission) -> Decimal:
    return sum((run.estimated_cost_usd for run in AgentRun.objects.filter(workstream__mission=mission)), Decimal("0"))


def _budget_limit(workstream: Workstream) -> Decimal:
    if not workstream.agent_template:
        return Decimal("0")
    return Decimal(str(workstream.agent_template.budget_limit_usd or "0"))


def _fail_workstream_for_budget(workstream: Workstream, budget_limit: Decimal, spent: Decimal) -> AgentRun:
    session_id = _workstream_session_id(workstream.mission, workstream)
    message = f"Budget exceeded before agent turn. Limit ${budget_limit}; mission spend ${spent}."
    agent_run = AgentRun.objects.create(
        workstream=workstream,
        session_id=session_id,
        status=AgentRun.Status.FAILED,
        error=message,
        finished_at=timezone.now(),
    )
    workstream.status = Workstream.Status.FAILED
    workstream.result = message
    workstream.save(update_fields=["status", "result", "updated_at"])
    create_event(
        workstream.mission,
        f"{workstream.owner} workstream blocked by budget limit.",
        level="warn",
        event_type="status",
        payload={"workstreamId": workstream.id, "agentRunId": agent_run.id, "budgetLimitUsd": str(budget_limit), "spentUsd": str(spent)},
    )
    return agent_run


def _run_agent_turn(workstream: Workstream, context: str = "") -> AgentRun:
    mission = workstream.mission
    if Mission.objects.filter(id=mission.id, abort_requested=True).exists():
        raise RuntimeError("Mission abort requested.")
    session_id = _workstream_session_id(mission, workstream)
    budget_limit = _budget_limit(workstream)
    spent = _mission_cost_so_far(mission)
    if budget_limit > 0 and spent >= budget_limit:
        return _fail_workstream_for_budget(workstream, budget_limit, spent)

    agent_run = AgentRun.objects.create(
        workstream=workstream,
        session_id=session_id,
        status=AgentRun.Status.RUNNING,
        started_at=timezone.now(),
    )
    workstream.status = Workstream.Status.RUNNING
    workstream.save(update_fields=["status", "updated_at"])
    create_event(
        mission,
        f"{workstream.owner} workstream dispatched to OpenClaw.",
        event_type="dispatch",
        payload={"workstreamId": workstream.id, "agentRunId": agent_run.id, "sessionId": session_id},
    )

    command = [
        "openclaw",
        "agent",
        "--session-id",
        session_id,
        "--message",
        _workstream_prompt(workstream, context),
        "--json",
        "--timeout",
        "600",
    ]
    process = subprocess.Popen(
        command,
        cwd=str(settings.BASE_DIR.parent),
        env=_base_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output_parts: list[str] = []
    logs: list[dict[str, Any]] = []
    assert process.stdout is not None
    for line in process.stdout:
        clean = line.rstrip()
        output_parts.append(line)
        if clean and not clean.startswith("{"):
            log_entry = {"level": "info", "message": clean, "createdAt": timezone.now().isoformat()}
            logs.append(log_entry)
            create_event(
                mission,
                f"{workstream.owner}: {clean}",
                level="info",
                payload={"workstreamId": workstream.id, "agentRunId": agent_run.id},
            )

    return_code = process.wait(timeout=660)
    output = "".join(output_parts)
    data = _json_from_output(output)
    usage = _usage(data)

    agent_run = AgentRun.objects.get(id=agent_run.id)
    workstream = Workstream.objects.select_related("mission").get(id=workstream.id)
    agent_run.logs = logs
    agent_run.raw_result = data or {"output": output[-8000:]}
    agent_run.input_tokens = usage["input"]
    agent_run.output_tokens = usage["output"]
    model_preference = workstream.agent_template.model_preference if workstream.agent_template else ""
    agent_run.estimated_cost_usd = _estimate_cost(usage["input"], usage["output"], model_preference, workstream.mission.organization)
    agent_run.finished_at = timezone.now()
    if return_code != 0:
        agent_run.status = AgentRun.Status.FAILED
        agent_run.error = output[-4000:]
        workstream.status = Workstream.Status.FAILED
        workstream.result = "OpenClaw agent execution failed."
    else:
        result_text = _result_text(data)
        agent_run.status = AgentRun.Status.SUCCEEDED
        agent_run.result_text = result_text
        workstream.status = Workstream.Status.SUCCEEDED
        workstream.result = result_text or "OpenClaw completed this workstream without a visible final response."

    agent_run.save()
    workstream.save(update_fields=["status", "result", "updated_at"])
    create_event(
        workstream.mission,
        f"{workstream.owner} workstream {workstream.status}.",
        event_type="status",
        payload={"workstreamId": workstream.id, "agentRunId": agent_run.id, "status": workstream.status},
    )
    return agent_run


def _run_workstream_id(workstream_id: int, context: str = "") -> AgentRun:
    close_old_connections()
    try:
        workstream = Workstream.objects.select_related("mission", "agent_template").get(id=workstream_id)
        return _run_agent_turn(workstream, context)
    finally:
        close_old_connections()


def _workstream_context(workstreams: list[Workstream]) -> str:
    lines = []
    for workstream in workstreams:
        if workstream.result:
            lines.append(f"{workstream.owner} ({workstream.title}): {workstream.result}")
    return "\n\n".join(lines)


def _aggregate_agent_usage(mission: Mission) -> None:
    runs = AgentRun.objects.filter(workstream__mission=mission)
    input_tokens = sum(run.input_tokens for run in runs)
    output_tokens = sum(run.output_tokens for run in runs)
    mission.input_tokens = input_tokens
    mission.output_tokens = output_tokens
    mission.total_tokens = input_tokens + output_tokens
    mission.estimated_cost_usd = sum((run.estimated_cost_usd for run in runs), Decimal("0"))


def _workstream_for_role(mission: Mission, role_id: str, title: str) -> Workstream:
    queryset = Workstream.objects.select_related("mission", "agent_template").filter(mission=mission, title=title)
    return queryset.filter(agent_template_id=role_id).first() or queryset.get()


def _create_board_brief(mission: Mission, result_text: str) -> BoardBrief:
    recommendations = []
    if result_text:
        recommendations.append("Review the OpenClaw result and approve the next concrete action.")
    if mission.total_tokens:
        recommendations.append("Use the captured token usage as the budget baseline for the next run.")
    return BoardBrief.objects.update_or_create(
        mission=mission,
        defaults={
            "title": f"Board Brief for {mission.session_id}",
            "summary": result_text or "OpenClaw completed the mission without a visible final response.",
            "recommendations": recommendations,
            "risks": [
                "Parallel workstreams depend on local OpenClaw agent execution and may need retry controls for production use.",
                "Gateway management RPCs may require pairing scope on this machine.",
            ],
            "sources": [
                {"type": "mission", "id": str(mission.id)},
                {"type": "openclaw-session", "id": mission.session_id},
            ],
        },
    )[0]


def _run_mission(mission_id: str) -> None:
    mission = Mission.objects.get(id=mission_id)
    _ensure_quality_gates(mission)
    _ensure_workstreams(mission)
    mission.status = Mission.Status.RUNNING
    mission.abort_requested = False
    mission.started_at = timezone.now()
    mission.save(update_fields=["status", "abort_requested", "started_at"])
    create_event(mission, "Mission accepted by OPC.", event_type="status")

    status = gateway_status()
    if status["ok"]:
        _set_gate(mission, "gateway-health", QualityGate.Status.PASSED, "OpenClaw Gateway service is running.")
    else:
        _set_gate(mission, "gateway-health", QualityGate.Status.FAILED, status["raw"][:1000])
        create_event(mission, "Gateway status check is degraded; OpenClaw CLI may fall back to embedded execution.", level="warn", payload=status)

    models = model_status()
    if models["ok"] and not models["missingProvidersInUse"]:
        _set_gate(mission, "model-provider", QualityGate.Status.PASSED, models["resolvedDefault"])
    else:
        _set_gate(mission, "model-provider", QualityGate.Status.FAILED, json.dumps(models, ensure_ascii=False))

    try:
        coo = _workstream_for_role(mission, "coo", "Mission decomposition")
        coo_run = _run_agent_turn(coo)
        coo = Workstream.objects.get(id=coo.id)
        if coo_run.status == AgentRun.Status.FAILED:
            raise RuntimeError(coo_run.error or "COO workstream failed.")
        if Mission.objects.filter(id=mission_id, abort_requested=True).exists():
            raise InterruptedError("Mission abort requested.")

        parallel_workstreams = list(
            Workstream.objects.select_related("mission", "agent_template").filter(
                mission=mission,
                title__in=["Technical review", "Cost review", "Market review"],
            )
        )
        parallel_context = _workstream_context([coo])
        with ThreadPoolExecutor(max_workers=max(len(parallel_workstreams), 1)) as executor:
            futures = [executor.submit(_run_workstream_id, workstream.id, parallel_context) for workstream in parallel_workstreams]
            for future in as_completed(futures):
                agent_run = future.result()
                if agent_run.status == AgentRun.Status.FAILED:
                    raise RuntimeError(agent_run.error or f"{agent_run.session_id} failed.")
        if Mission.objects.filter(id=mission_id, abort_requested=True).exists():
            raise InterruptedError("Mission abort requested.")

        completed_context = _workstream_context(list(Workstream.objects.filter(mission=mission).exclude(agent_template_id="sre")))
        sre = _workstream_for_role(mission, "sre", "Reliability review")
        sre_run = _run_agent_turn(sre, completed_context)
        if sre_run.status == AgentRun.Status.FAILED:
            raise RuntimeError(sre_run.error or "SRE workstream failed.")

        mission = Mission.objects.get(id=mission_id)
        mission.status = Mission.Status.SUCCEEDED
        mission.finished_at = timezone.now()
        workstreams = list(Workstream.objects.filter(mission=mission))
        mission.result_text = _workstream_context(workstreams)
        mission.raw_result = {
            "workstreams": [
                {
                    "id": workstream.id,
                    "owner": workstream.owner,
                    "status": workstream.status,
                    "result": workstream.result,
                }
                for workstream in workstreams
            ]
        }
        _aggregate_agent_usage(mission)
        _set_gate(mission, "agent-result", QualityGate.Status.PASSED, "All OpenClaw workstream agents returned results.")
        _set_gate(mission, "cost-capture", QualityGate.Status.PASSED, f"{mission.total_tokens} total tokens captured; estimated cost ${mission.estimated_cost_usd}.")
        _set_gate(mission, "founder-approval", QualityGate.Status.PENDING, "Awaiting founder review before follow-up execution.")
    except Exception as exc:
        mission = Mission.objects.get(id=mission_id)
        mission.status = Mission.Status.ABORTED if isinstance(exc, InterruptedError) or mission.abort_requested else Mission.Status.FAILED
        mission.error = str(exc)
        mission.finished_at = timezone.now()
        _aggregate_agent_usage(mission)
        _set_gate(mission, "agent-result", QualityGate.Status.FAILED, mission.error[:1000])
        for workstream in mission.workstreams.filter(status__in=[Workstream.Status.QUEUED, Workstream.Status.RUNNING]):
            workstream.status = Workstream.Status.FAILED
            workstream.result = "Skipped because mission orchestration failed."
            workstream.save(update_fields=["status", "result", "updated_at"])
    mission.save()
    if mission.status == Mission.Status.SUCCEEDED:
        _create_board_brief(mission, mission.result_text)
    create_event(mission, f"Mission {mission.status}.", event_type="status", payload=serialize_mission(mission))
