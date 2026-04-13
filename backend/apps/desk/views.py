import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST


EXECUTIVE_TEAM = [
    {
        "id": "ceo",
        "name": "CEO",
        "title": "Chief Executive Agent",
        "mission": "接收单一战略指令，做最终取舍，并生成面向人的汇总报告。",
        "reportsTo": None,
        "status": "ready",
    },
    {
        "id": "coo",
        "name": "COO",
        "title": "Orchestration Lead",
        "mission": "拆解任务、安排优先级、协调跨角色 handoff。",
        "reportsTo": "ceo",
        "status": "ready",
    },
    {
        "id": "cto",
        "name": "CTO",
        "title": "Technical Strategy Agent",
        "mission": "评估技术方案、实现计划、工程风险和交付质量。",
        "reportsTo": "coo",
        "status": "ready",
    },
    {
        "id": "cfo",
        "name": "CFO",
        "title": "Budget & Cost Agent",
        "mission": "估算 token/API 成本、预算上限和投入产出。",
        "reportsTo": "coo",
        "status": "ready",
    },
    {
        "id": "cmo",
        "name": "CMO",
        "title": "Market Intelligence Agent",
        "mission": "做市场研究、定位、竞品和增长渠道判断。",
        "reportsTo": "coo",
        "status": "ready",
    },
    {
        "id": "sre",
        "name": "SRE",
        "title": "Reliability Agent",
        "mission": "检查部署、监控、回滚和运行安全边界。",
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
    return JsonResponse(
        {
            "product": "CEO Desk",
            "positioning": "OpenClaw 生态专属的 CEO 管理桌面",
            "gateway": settings.OPENCLAW_GATEWAY_URL,
            "integration": "OpenClaw Gateway",
            "authMode": settings.OPENCLAW_GATEWAY_AUTH_MODE,
            "team": EXECUTIVE_TEAM,
            "pipeline": TASK_PIPELINE,
            "metrics": {
                "agentsReady": 5,
                "activeMissions": 1,
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

    return JsonResponse(
        {
            "id": "cmd-preview-001",
            "command": command,
            "status": "planned",
            "nextStep": "COO will split this command into executive workstreams.",
            "workstreams": [
                {"agent": "COO", "task": "拆解目标、定义验收标准和汇报格式。"},
                {"agent": "CTO", "task": "判断技术路径、依赖和工程风险。"},
                {"agent": "CFO", "task": "估算预算、token 成本和资源上限。"},
                {"agent": "CMO", "task": "补充市场定位、竞品和用户侧判断。"},
            ],
        },
        status=201,
    )
