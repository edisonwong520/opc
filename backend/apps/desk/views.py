import json
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Mission
from .openclaw import (
    gateway_logs,
    gateway_status,
    model_status,
    serialize_mission,
    start_mission,
    usage_cost,
)


EXECUTIVE_TEAM = [
    {
        "id": "ceo",
        "name": "CEO",
        "title": "Chief Executive Agent",
        "mission": "Receive one executive command, make final tradeoffs, and produce a human-readable board brief.",
        "reportsTo": None,
        "status": "ready",
    },
    {
        "id": "coo",
        "name": "COO",
        "title": "Orchestration Lead",
        "mission": "Break goals into workstreams, set priorities, and coordinate cross-role handoffs.",
        "reportsTo": "ceo",
        "status": "ready",
    },
    {
        "id": "cto",
        "name": "CTO",
        "title": "Technical Strategy Agent",
        "mission": "Evaluate technical strategy, implementation plans, engineering risk, and delivery quality.",
        "reportsTo": "coo",
        "status": "ready",
    },
    {
        "id": "cfo",
        "name": "CFO",
        "title": "Budget & Cost Agent",
        "mission": "Estimate token/API cost, budget limits, and return on effort.",
        "reportsTo": "coo",
        "status": "ready",
    },
    {
        "id": "cmo",
        "name": "CMO",
        "title": "Market Intelligence Agent",
        "mission": "Assess market research, positioning, competitors, and growth channels.",
        "reportsTo": "coo",
        "status": "ready",
    },
    {
        "id": "sre",
        "name": "SRE",
        "title": "Reliability Agent",
        "mission": "Review deployment, monitoring, rollback, and operational safety boundaries.",
        "reportsTo": "cto",
        "status": "standby",
    },
]

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
    return JsonResponse(
        {
            "product": "CEO Desk",
            "positioning": "The CEO operating desk built exclusively for the OpenClaw ecosystem",
            "gateway": settings.OPENCLAW_GATEWAY_URL,
            "integration": "OpenClaw Gateway",
            "authMode": settings.OPENCLAW_GATEWAY_AUTH_MODE,
            "openclaw": {
                "health": health,
                "model": models,
            },
            "team": EXECUTIVE_TEAM,
            "pipeline": TASK_PIPELINE,
            "metrics": {
                "agentsReady": 5,
                "activeMissions": Mission.objects.filter(status__in=[Mission.Status.QUEUED, Mission.Status.RUNNING]).count(),
                "budgetUsedUsd": 0.0,
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

    session_id = str(payload.get("sessionId") or f"ceo-desk-{uuid.uuid4().hex[:10]}")
    mission = Mission.objects.create(
        command=command,
        session_id=session_id,
        agent_id=str(payload.get("agentId", "")),
    )
    start_mission(mission)
    return JsonResponse(serialize_mission(mission, include_events=True), status=201)


@require_GET
def list_missions(_request):
    missions = Mission.objects.prefetch_related("quality_gates")[:20]
    return JsonResponse({"missions": [serialize_mission(mission) for mission in missions]})


@require_http_methods(["GET"])
def mission_detail(_request, mission_id):
    mission = get_object_or_404(Mission.objects.prefetch_related("events", "quality_gates"), id=mission_id)
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
