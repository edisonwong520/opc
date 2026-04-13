import json
import os
import subprocess
import threading
from decimal import Decimal
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from .models import AgentTemplate, BoardBrief, Mission, MissionEvent, QualityGate, Workstream


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


def serialize_workstream(workstream: Workstream) -> dict[str, Any]:
    return {
        "id": workstream.id,
        "owner": workstream.owner,
        "title": workstream.title,
        "description": workstream.description,
        "status": workstream.status,
        "result": workstream.result,
        "agentTemplateId": workstream.agent_template_id,
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
        "usage": {
            "input": mission.input_tokens,
            "output": mission.output_tokens,
            "total": mission.total_tokens,
            "estimatedCostUsd": str(mission.estimated_cost_usd),
        },
        "qualityGates": [serialize_gate(gate) for gate in mission.quality_gates.all()],
        "workstreams": [serialize_workstream(workstream) for workstream in mission.workstreams.all()],
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
    templates = {template.id: template for template in AgentTemplate.objects.filter(id__in=[item[0] for item in definitions])}
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


def _estimate_cost(input_tokens: int, output_tokens: int) -> Decimal:
    input_rate = Decimal(str(settings.OPC_COST_INPUT_PER_1K_USD or "0"))
    output_rate = Decimal(str(settings.OPC_COST_OUTPUT_PER_1K_USD or "0"))
    return ((Decimal(input_tokens) / Decimal(1000)) * input_rate) + ((Decimal(output_tokens) / Decimal(1000)) * output_rate)


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
                "The current MVP runs one OpenClaw agent turn; multi-workstream execution is represented but not yet independently delegated.",
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
    mission.started_at = timezone.now()
    mission.save(update_fields=["status", "started_at"])
    create_event(mission, "Mission accepted by OPC.", event_type="status")
    _set_workstreams(mission, Workstream.Status.RUNNING)

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

    command = [
        "openclaw",
        "agent",
        "--session-id",
        mission.session_id,
        "--message",
        mission.command,
        "--json",
        "--timeout",
        "600",
    ]
    create_event(mission, "Dispatching command to OpenClaw agent.", event_type="dispatch", payload={"sessionId": mission.session_id})

    process = subprocess.Popen(
        command,
        cwd=str(settings.BASE_DIR.parent),
        env=_base_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output_parts: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        clean = line.rstrip()
        output_parts.append(line)
        if clean and not clean.startswith("{"):
            create_event(mission, clean, level="info")
    return_code = process.wait(timeout=660)
    output = "".join(output_parts)
    data = _json_from_output(output)

    mission = Mission.objects.get(id=mission_id)
    mission.raw_result = data or {"output": output[-8000:]}
    mission.finished_at = timezone.now()
    if return_code != 0:
        mission.status = Mission.Status.FAILED
        mission.error = output[-4000:]
        _set_gate(mission, "agent-result", QualityGate.Status.FAILED, mission.error[:1000])
        _set_workstreams(mission, Workstream.Status.FAILED, "OpenClaw agent execution failed.")
    else:
        mission.status = Mission.Status.SUCCEEDED
        result_text = data.get("meta", {}).get("finalAssistantVisibleText", "")
        if not result_text:
            payloads = data.get("payloads") or []
            result_text = "\n".join(item.get("text", "") for item in payloads if item.get("text"))
        mission.result_text = result_text
        usage = data.get("meta", {}).get("agentMeta", {}).get("usage", {})
        mission.input_tokens = int(usage.get("input") or 0)
        mission.output_tokens = int(usage.get("output") or 0)
        mission.total_tokens = int(usage.get("total") or 0)
        mission.estimated_cost_usd = _estimate_cost(mission.input_tokens, mission.output_tokens)
        _set_gate(mission, "agent-result", QualityGate.Status.PASSED, "OpenClaw returned a final assistant response.")
        _set_gate(mission, "cost-capture", QualityGate.Status.PASSED, f"{mission.total_tokens} total tokens captured; estimated cost ${mission.estimated_cost_usd}.")
        _set_gate(mission, "founder-approval", QualityGate.Status.PENDING, "Awaiting founder review before follow-up execution.")
        _set_workstreams(mission, Workstream.Status.SUCCEEDED, "Covered by the single-turn OpenClaw mission result.")
    mission.save()
    if mission.status == Mission.Status.SUCCEEDED:
        _create_board_brief(mission, mission.result_text)
    create_event(mission, f"Mission {mission.status}.", event_type="status", payload=serialize_mission(mission))
