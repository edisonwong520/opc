import json
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import AgentTemplate, ApprovalDecision, Mission, QualityGate
from .openclaw import (
    gateway_logs,
    gateway_status,
    model_status,
    serialize_agent_template,
    serialize_mission,
    start_mission,
    usage_cost,
)


TASK_PIPELINE = [
    {"id": "intake", "label": "CEO Intake", "owner": "CEO", "state": "done"},
    {"id": "plan", "label": "COO Decomposition", "owner": "COO", "state": "active"},
    {"id": "parallel", "label": "Executive Parallel Work", "owner": "CTO/CFO/CMO", "state": "queued"},
    {"id": "quality", "label": "Quality Gate", "owner": "SRE", "state": "queued"},
    {"id": "report", "label": "Board Brief", "owner": "CEO", "state": "queued"},
]


@require_GET
def briefing(_request):
    health = gateway_status()
    models = model_status()
    team = [serialize_agent_template(template) for template in AgentTemplate.objects.all()]
    return JsonResponse(
        {
            "product": "OPC",
            "positioning": "The One Person Company operating desk built exclusively for the OpenClaw ecosystem",
            "gateway": settings.OPENCLAW_GATEWAY_URL,
            "integration": "OpenClaw Gateway",
            "authMode": settings.OPENCLAW_GATEWAY_AUTH_MODE,
            "openclaw": {
                "health": health,
                "model": models,
            },
            "team": team,
            "pipeline": TASK_PIPELINE,
            "metrics": {
                "agentsReady": AgentTemplate.objects.filter(status=AgentTemplate.Status.READY).count(),
                "activeMissions": Mission.objects.filter(status__in=[Mission.Status.QUEUED, Mission.Status.RUNNING]).count(),
                "budgetUsedUsd": float(sum(mission.estimated_cost_usd for mission in Mission.objects.all())),
                "qualityGates": 5,
            },
        }
    )


@csrf_exempt
@require_POST
def create_command(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    command = str(payload.get("command", "")).strip()
    if not command:
        return JsonResponse({"error": "`command` is required."}, status=400)

    session_id = str(payload.get("sessionId") or f"opc-{uuid.uuid4().hex[:10]}")
    mission = Mission.objects.create(
        command=command,
        session_id=session_id,
        agent_id=str(payload.get("agentId", "")),
    )
    start_mission(mission)
    return JsonResponse(serialize_mission(mission, include_events=True), status=201)


@require_GET
def list_missions(_request):
    missions = Mission.objects.prefetch_related("quality_gates", "workstreams").select_related("board_brief")[:20]
    return JsonResponse({"missions": [serialize_mission(mission) for mission in missions]})


@require_http_methods(["GET"])
def mission_detail(_request, mission_id):
    mission = get_object_or_404(Mission.objects.prefetch_related("events", "quality_gates", "workstreams").select_related("board_brief"), id=mission_id)
    return JsonResponse(serialize_mission(mission, include_events=True))


@require_GET
def openclaw_health(_request):
    return JsonResponse({"gateway": gateway_status(), "model": model_status()})


@require_GET
def openclaw_logs(request):
    limit = int(request.GET.get("limit", "100"))
    return JsonResponse({"logs": gateway_logs(limit=min(max(limit, 1), 500))})


@require_GET
def openclaw_cost(request):
    days = int(request.GET.get("days", "30"))
    return JsonResponse(usage_cost(days=min(max(days, 1), 90)))


@require_GET
def template_list(_request):
    templates = AgentTemplate.objects.all()
    return JsonResponse({"templates": [serialize_agent_template(t) for t in templates]})


@require_GET
def template_detail(_request, template_id):
    template = get_object_or_404(AgentTemplate, id=template_id)
    return JsonResponse(serialize_agent_template(template))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def template_create(request):
    if request.method == "GET":
        return template_list(request)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    template_id = str(payload.get("id", "")).strip()
    if not template_id:
        return JsonResponse({"error": "`id` is required."}, status=400)

    name = str(payload.get("name", "")).strip()
    if not name:
        return JsonResponse({"error": "`name` is required."}, status=400)

    template, created = AgentTemplate.objects.update_or_create(
        id=template_id,
        defaults={
            "name": name,
            "title": str(payload.get("title", "")),
            "mission": str(payload.get("mission", "")),
            "reports_to": str(payload.get("reportsTo", "")),
            "status": str(payload.get("status", AgentTemplate.Status.READY)),
            "tools": payload.get("tools", []),
            "model_preference": str(payload.get("modelPreference", "")),
            "budget_limit_usd": payload.get("budgetLimitUsd", 0),
            "sort_order": payload.get("sortOrder", 0),
        },
    )
    return JsonResponse(serialize_agent_template(template), status=201 if created else 200)


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def template_update(request, template_id):
    template = get_object_or_404(AgentTemplate, id=template_id)
    if request.method == "DELETE":
        template.delete()
        return JsonResponse({"deleted": template_id})
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    if "name" in payload:
        template.name = str(payload["name"])
    if "title" in payload:
        template.title = str(payload["title"])
    if "mission" in payload:
        template.mission = str(payload["mission"])
    if "reportsTo" in payload:
        template.reports_to = str(payload["reportsTo"])
    if "status" in payload:
        template.status = str(payload["status"])
    if "tools" in payload:
        template.tools = payload["tools"]
    if "modelPreference" in payload:
        template.model_preference = str(payload["modelPreference"])
    if "budgetLimitUsd" in payload:
        template.budget_limit_usd = payload["budgetLimitUsd"]
    if "sortOrder" in payload:
        template.sort_order = payload["sortOrder"]
    template.save()
    return JsonResponse(serialize_agent_template(template))


@csrf_exempt
@require_POST
def mission_approve(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    gate = mission.quality_gates.filter(name="founder-approval").first()
    if gate:
        gate.status = QualityGate.Status.PASSED
        gate.details = "Founder approved."
        gate.save(update_fields=["status", "details", "updated_at"])

    ApprovalDecision.objects.create(
        mission=mission,
        decision=ApprovalDecision.Decision.APPROVED,
        reviewer=str(payload.get("reviewer", "founder")),
        notes=str(payload.get("notes", "")),
    )
    return JsonResponse(serialize_mission(mission, include_events=True))


@csrf_exempt
@require_POST
def mission_reject(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    gate = mission.quality_gates.filter(name="founder-approval").first()
    if gate:
        gate.status = QualityGate.Status.FAILED
        gate.details = f"Founder rejected: {payload.get('notes', '')}"
        gate.save(update_fields=["status", "details", "updated_at"])

    ApprovalDecision.objects.create(
        mission=mission,
        decision=ApprovalDecision.Decision.REJECTED,
        reviewer=str(payload.get("reviewer", "founder")),
        notes=str(payload.get("notes", "")),
    )
    return JsonResponse(serialize_mission(mission, include_events=True))
