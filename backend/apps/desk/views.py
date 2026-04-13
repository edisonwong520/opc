import json
import uuid

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import AgentTemplate, ApprovalDecision, AuditLog, FounderProfile, Invitation, Mission, Organization, QualityGate, Workstream
from .openclaw import (
    dashboard_metrics,
    gateway_logs,
    gateway_status,
    model_status,
    serialize_agent_template,
    serialize_mission,
    retry_workstream,
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


def _json_payload(request) -> tuple[dict, JsonResponse | None]:
    try:
        return json.loads(request.body.decode("utf-8") or "{}"), None
    except json.JSONDecodeError:
        return {}, JsonResponse({"error": "Invalid JSON body."}, status=400)


def _rate_limit(key: str, max_requests: int = 10, window_seconds: int = 60) -> JsonResponse | None:
    """Simple cache-based rate limiting. Returns error response if limit exceeded."""
    count = cache.get(key, 0)
    if count >= max_requests:
        return JsonResponse({"error": "Too many requests. Please try again later."}, status=429)
    cache.set(key, count + 1, window_seconds)
    return None


def _rate_limit_key(request, action: str) -> str:
    """Generate rate limit key based on IP and action."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown"))
    return f"ratelimit:{action}:{ip}"


def _organization_for_request(request) -> Organization:
    if request.user.is_authenticated:
        profile = FounderProfile.objects.select_related("organization").filter(user=request.user).first()
        if profile:
            return profile.organization
    organization, _ = Organization.objects.get_or_create(slug="default", defaults={"name": "Default OPC"})
    return organization


def _profile_for_request(request) -> FounderProfile | None:
    if not request.user.is_authenticated:
        return None
    return FounderProfile.objects.select_related("organization").filter(user=request.user).first()


def _role_for_request(request) -> str:
    if not request.user.is_authenticated:
        return "anonymous"
    if request.user.is_superuser:
        return FounderProfile.Role.ADMIN
    profile = _profile_for_request(request)
    return profile.role if profile else FounderProfile.Role.VIEWER


def _auth_error(request) -> JsonResponse | None:
    if settings.OPC_REQUIRE_AUTH and not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    return None


def _role_error(request, allowed: set[str]) -> JsonResponse | None:
    auth_error = _auth_error(request)
    if auth_error:
        return auth_error
    if not settings.OPC_REQUIRE_AUTH and not request.user.is_authenticated:
        return None
    if _role_for_request(request) not in allowed:
        return JsonResponse({"error": "Insufficient role permission."}, status=403)
    return None


READ_ROLES = {FounderProfile.Role.ADMIN, FounderProfile.Role.FOUNDER, FounderProfile.Role.OPERATOR, FounderProfile.Role.VIEWER}
OPERATE_ROLES = {FounderProfile.Role.ADMIN, FounderProfile.Role.FOUNDER, FounderProfile.Role.OPERATOR}
FOUNDER_ROLES = {FounderProfile.Role.ADMIN, FounderProfile.Role.FOUNDER}


def _serialize_session(request) -> dict:
    organization = _organization_for_request(request)
    return {
        "authenticated": request.user.is_authenticated,
        "username": request.user.username if request.user.is_authenticated else "",
        "role": _role_for_request(request),
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug,
        },
    }


def _audit(request, action: str, entity_type: str, entity_id: str, metadata: dict | None = None) -> None:
    actor = request.user.username if request.user.is_authenticated else "founder"
    AuditLog.objects.create(
        organization=_organization_for_request(request),
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
    )


@require_GET
@ensure_csrf_cookie
def auth_me(request):
    """Returns session info and ensures CSRF cookie is set."""
    return JsonResponse(_serialize_session(request))


@csrf_exempt
@require_POST
def auth_login(request):
    """Login endpoint - exempted because CSRF cookie may not be set yet."""
    rate_error = _rate_limit(_rate_limit_key(request, "login"), max_requests=5, window_seconds=60)
    if rate_error:
        return rate_error

    payload, error = _json_payload(request)
    if error:
        return error
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return JsonResponse({"error": "`username` and `password` are required."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid credentials."}, status=401)

    login(request, user)
    organization = _organization_for_request(request)
    FounderProfile.objects.get_or_create(user=user, defaults={"organization": organization, "role": FounderProfile.Role.FOUNDER})
    _audit(request, "auth.login", "User", str(user.id))
    return JsonResponse(_serialize_session(request))


@require_POST
def auth_logout(request):
    """Logout endpoint - requires CSRF protection since user is authenticated."""
    user_id = str(request.user.id) if request.user.is_authenticated else ""
    _audit(request, "auth.logout", "User", user_id or "anonymous")
    logout(request)
    return JsonResponse(_serialize_session(request))


@csrf_exempt
@require_POST
def auth_bootstrap(request):
    """Bootstrap endpoint - exempted because no users exist yet."""
    rate_error = _rate_limit(_rate_limit_key(request, "bootstrap"), max_requests=3, window_seconds=300)
    if rate_error:
        return rate_error

    if User.objects.exists():
        return JsonResponse({"error": "Bootstrap is only available before the first user exists."}, status=409)
    payload, error = _json_payload(request)
    if error:
        return error
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    organization_name = str(payload.get("organizationName", "Default OPC")).strip() or "Default OPC"
    if not username or not password:
        return JsonResponse({"error": "`username` and `password` are required."}, status=400)

    if len(password) < 8:
        return JsonResponse({"error": "Password must be at least 8 characters."}, status=400)

    user = User.objects.create_user(username=username, password=password)
    organization, _ = Organization.objects.get_or_create(slug="default", defaults={"name": organization_name})
    FounderProfile.objects.create(user=user, organization=organization, role=FounderProfile.Role.ADMIN)
    login(request, user)
    _audit(request, "auth.bootstrap", "User", str(user.id), {"organizationId": str(organization.id)})
    return JsonResponse(_serialize_session(request), status=201)


@require_GET
def briefing(request):
    error = _role_error(request, READ_ROLES)
    if error:
        return error
    organization = _organization_for_request(request)
    health = gateway_status()
    models = model_status()
    team = [serialize_agent_template(template) for template in AgentTemplate.objects.filter(organization=organization)]
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
            "metrics": dashboard_metrics(organization),
        }
    )


@require_POST
def create_command(request):
    error = _role_error(request, OPERATE_ROLES)
    if error:
        return error
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    command = str(payload.get("command", "")).strip()
    if not command:
        return JsonResponse({"error": "`command` is required."}, status=400)

    organization = _organization_for_request(request)
    session_id = str(payload.get("sessionId") or f"opc-{uuid.uuid4().hex[:10]}")
    mission = Mission.objects.create(
        organization=organization,
        command=command,
        session_id=session_id,
        agent_id=str(payload.get("agentId", "")),
    )
    start_mission(mission)
    return JsonResponse(serialize_mission(mission, include_events=True), status=201)


@require_GET
def list_missions(request):
    error = _role_error(request, READ_ROLES)
    if error:
        return error
    organization = _organization_for_request(request)
    missions = Mission.objects.filter(organization=organization)
    if request.GET.get("includeArchived") != "true":
        missions = missions.filter(archived_at__isnull=True)
    status = request.GET.get("status", "").strip()
    if status:
        missions = missions.filter(status=status)
    search = request.GET.get("search", "").strip()
    if search:
        missions = missions.filter(command__icontains=search)
    missions = missions.prefetch_related("quality_gates", "workstreams__agent_runs").select_related("board_brief")[:50]
    return JsonResponse({"missions": [serialize_mission(mission) for mission in missions]})


@require_http_methods(["GET"])
def mission_detail(_request, mission_id):
    error = _role_error(_request, READ_ROLES)
    if error:
        return error
    organization = _organization_for_request(_request)
    mission = get_object_or_404(
        Mission.objects.prefetch_related("events", "quality_gates", "workstreams__agent_runs").select_related("board_brief"),
        id=mission_id,
        organization=organization,
    )
    return JsonResponse(serialize_mission(mission, include_events=True))


@require_GET
def openclaw_health(_request):
    return JsonResponse({"gateway": gateway_status(), "model": model_status()})


@require_GET
def openclaw_logs(request):
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    limit = int(request.GET.get("limit", "100"))
    return JsonResponse({"logs": gateway_logs(limit=min(max(limit, 1), 500))})


@require_GET
def openclaw_cost(request):
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    days = int(request.GET.get("days", "30"))
    return JsonResponse(usage_cost(days=min(max(days, 1), 90)))


@require_GET
def audit_logs(request):
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    organization = _organization_for_request(request)
    limit = min(max(int(request.GET.get("limit", "50")), 1), 200)
    action = request.GET.get("action", "").strip()
    logs = AuditLog.objects.filter(organization=organization)
    if action:
        logs = logs.filter(action=action)
    return JsonResponse(
        {
            "logs": [
                {
                    "id": log.id,
                    "actor": log.actor,
                    "action": log.action,
                    "entityType": log.entity_type,
                    "entityId": log.entity_id,
                    "metadata": log.metadata,
                    "createdAt": log.created_at.isoformat(),
                }
                for log in logs[:limit]
            ]
        }
    )


@require_GET
def template_list(_request):
    error = _role_error(_request, READ_ROLES)
    if error:
        return error
    organization = _organization_for_request(_request)
    templates = AgentTemplate.objects.filter(organization=organization)
    return JsonResponse({"templates": [serialize_agent_template(t) for t in templates]})


@require_GET
def template_detail(_request, template_id):
    error = _role_error(_request, READ_ROLES)
    if error:
        return error
    organization = _organization_for_request(_request)
    template = get_object_or_404(AgentTemplate, id=template_id, organization=organization)
    return JsonResponse(serialize_agent_template(template))


@require_http_methods(["GET", "POST"])
def template_create(request):
    if request.method == "GET":
        return template_list(request)
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    template_id = str(payload.get("id", "")).strip().lower()
    if not template_id:
        return JsonResponse({"error": "`id` is required."}, status=400)

    name = str(payload.get("name", "")).strip()
    if not name:
        return JsonResponse({"error": "`name` is required."}, status=400)

    template, created = AgentTemplate.objects.update_or_create(
        id=template_id,
        organization=_organization_for_request(request),
        defaults={
            "name": name,
            "title": str(payload.get("title", "")),
            "mission": str(payload.get("mission", "")),
            "reports_to": str(payload.get("reportsTo", "")),
            "status": str(payload.get("status", AgentTemplate.Status.READY)),
            "tools": _coerce_tools(payload.get("tools", [])),
            "model_preference": str(payload.get("modelPreference", "")),
            "budget_limit_usd": payload.get("budgetLimitUsd", 0),
            "sort_order": payload.get("sortOrder", 0),
        },
    )
    _audit(request, "template.created" if created else "template.updated", "AgentTemplate", template.id)
    return JsonResponse(serialize_agent_template(template), status=201 if created else 200)


@require_http_methods(["GET", "POST", "DELETE"])
def template_update(request, template_id):
    if request.method == "GET":
        return template_detail(request, template_id)

    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    template = get_object_or_404(AgentTemplate, id=template_id, organization=_organization_for_request(request))
    if request.method == "DELETE":
        template.delete()
        _audit(request, "template.deleted", "AgentTemplate", template_id)
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
        template.tools = _coerce_tools(payload["tools"])
    if "modelPreference" in payload:
        template.model_preference = str(payload["modelPreference"])
    if "budgetLimitUsd" in payload:
        template.budget_limit_usd = payload["budgetLimitUsd"]
    if "sortOrder" in payload:
        template.sort_order = payload["sortOrder"]
    template.save()
    _audit(request, "template.updated", "AgentTemplate", template.id)
    return JsonResponse(serialize_agent_template(template))


def _coerce_tools(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


@require_POST
def mission_approve(request, mission_id):
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    mission = get_object_or_404(Mission, id=mission_id)
    if mission.organization_id != _organization_for_request(request).id:
        return JsonResponse({"error": "Mission not found."}, status=404)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    gate = mission.quality_gates.filter(name="founder-approval").first()
    if gate:
        gate.status = QualityGate.Status.PASSED
        gate.details = "Founder approved."
        gate.save(update_fields=["status", "details", "updated_at"])

    decision = ApprovalDecision.objects.create(
        mission=mission,
        decision=ApprovalDecision.Decision.APPROVED,
        reviewer=str(payload.get("reviewer", "founder")),
        notes=str(payload.get("notes", "")),
    )
    _audit(request, "mission.approved", "Mission", str(mission.id), {"decisionId": decision.id})
    return JsonResponse(serialize_mission(mission, include_events=True))


@require_POST
def mission_reject(request, mission_id):
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    mission = get_object_or_404(Mission, id=mission_id)
    if mission.organization_id != _organization_for_request(request).id:
        return JsonResponse({"error": "Mission not found."}, status=404)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    gate = mission.quality_gates.filter(name="founder-approval").first()
    if gate:
        gate.status = QualityGate.Status.FAILED
        gate.details = f"Founder rejected: {payload.get('notes', '')}"
        gate.save(update_fields=["status", "details", "updated_at"])

    decision = ApprovalDecision.objects.create(
        mission=mission,
        decision=ApprovalDecision.Decision.REJECTED,
        reviewer=str(payload.get("reviewer", "founder")),
        notes=str(payload.get("notes", "")),
    )
    _audit(request, "mission.rejected", "Mission", str(mission.id), {"decisionId": decision.id})
    return JsonResponse(serialize_mission(mission, include_events=True))


@require_POST
def mission_retry(request, mission_id):
    error = _role_error(request, OPERATE_ROLES)
    if error:
        return error
    mission = get_object_or_404(Mission, id=mission_id, organization=_organization_for_request(request))
    if mission.status not in [Mission.Status.FAILED, Mission.Status.ABORTED]:
        return JsonResponse({"error": "Only failed or aborted missions can be retried."}, status=409)

    mission.status = Mission.Status.QUEUED
    mission.error = ""
    mission.abort_requested = False
    mission.finished_at = None
    mission.archived_at = None
    mission.save(update_fields=["status", "error", "abort_requested", "finished_at", "archived_at"])
    for workstream in mission.workstreams.filter(status__in=[Mission.Status.FAILED, "skipped", "running", "queued"]):
        workstream.status = "queued"
        workstream.result = ""
        workstream.save(update_fields=["status", "result", "updated_at"])
    _audit(request, "mission.retried", "Mission", str(mission.id))
    start_mission(mission)
    return JsonResponse(serialize_mission(mission, include_events=True))


@require_POST
def mission_abort(request, mission_id):
    error = _role_error(request, OPERATE_ROLES)
    if error:
        return error
    mission = get_object_or_404(Mission, id=mission_id, organization=_organization_for_request(request))
    if mission.status not in [Mission.Status.QUEUED, Mission.Status.RUNNING]:
        return JsonResponse({"error": "Only queued or running missions can be aborted."}, status=409)

    mission.abort_requested = True
    mission.status = Mission.Status.ABORTED
    mission.finished_at = timezone.now()
    mission.save(update_fields=["abort_requested", "status", "finished_at"])
    _audit(request, "mission.aborted", "Mission", str(mission.id))
    return JsonResponse(serialize_mission(mission, include_events=True))


@require_POST
def mission_archive(request, mission_id):
    error = _role_error(request, OPERATE_ROLES)
    if error:
        return error
    mission = get_object_or_404(Mission, id=mission_id, organization=_organization_for_request(request))
    if mission.status in [Mission.Status.QUEUED, Mission.Status.RUNNING]:
        return JsonResponse({"error": "Running missions cannot be archived."}, status=409)

    mission.archived_at = timezone.now()
    mission.save(update_fields=["archived_at"])
    _audit(request, "mission.archived", "Mission", str(mission.id))
    return JsonResponse(serialize_mission(mission, include_events=True))


@require_POST
def workstream_retry(request, mission_id, workstream_id):
    error = _role_error(request, OPERATE_ROLES)
    if error:
        return error
    workstream = get_object_or_404(
        Workstream.objects.select_related("mission", "agent_template"),
        id=workstream_id,
        mission_id=mission_id,
        mission__organization=_organization_for_request(request),
    )
    if workstream.status != Workstream.Status.FAILED:
        return JsonResponse({"error": "Only failed workstreams can be retried."}, status=409)
    try:
        retry_workstream(workstream)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    _audit(request, "workstream.retried", "Workstream", str(workstream.id), {"missionId": str(mission_id)})
    mission = get_object_or_404(
        Mission.objects.prefetch_related("events", "quality_gates", "workstreams__agent_runs").select_related("board_brief"),
        id=mission_id,
        organization=_organization_for_request(request),
    )
    return JsonResponse(serialize_mission(mission, include_events=True))


@require_GET
def mission_export(request, mission_id):
    error = _role_error(request, READ_ROLES)
    if error:
        return error
    mission = get_object_or_404(
        Mission.objects.prefetch_related("quality_gates", "workstreams__agent_runs").select_related("board_brief"),
        id=mission_id,
        organization=_organization_for_request(request),
    )
    lines = [
        f"# OPC Mission {mission.session_id}",
        "",
        f"- Status: {mission.status}",
        f"- Created: {mission.created_at.isoformat()}",
        f"- Finished: {mission.finished_at.isoformat() if mission.finished_at else ''}",
        f"- Tokens: {mission.total_tokens}",
        f"- Estimated Cost USD: {mission.estimated_cost_usd}",
        "",
        "## Founder Command",
        "",
        mission.command,
        "",
        "## Board Brief",
        "",
        mission.board_brief.summary if hasattr(mission, "board_brief") else mission.result_text,
        "",
        "## Workstreams",
    ]
    for workstream in mission.workstreams.all():
        lines.extend(["", f"### {workstream.owner}: {workstream.title}", "", f"Status: {workstream.status}", "", workstream.result or workstream.description])
    lines.extend(["", "## Quality Gates"])
    for gate in mission.quality_gates.all():
        lines.extend(["", f"- {gate.name}: {gate.status} - {gate.details}"])
    response = HttpResponse("\n".join(lines), content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="opc-mission-{mission.session_id}.md"'
    return response


def _serialize_invitation(invitation: Invitation) -> dict:
    return {
        "id": str(invitation.id),
        "email": invitation.email,
        "role": invitation.role,
        "status": invitation.status,
        "expiresAt": invitation.expires_at.isoformat(),
        "createdAt": invitation.created_at.isoformat(),
        "invitedBy": invitation.invited_by.username,
    }


@require_GET
def invitation_list(request):
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    organization = _organization_for_request(request)
    invitations = Invitation.objects.filter(organization=organization, status=Invitation.Status.PENDING)
    return JsonResponse({"invitations": [_serialize_invitation(inv) for inv in invitations]})


@require_POST
def invitation_create(request):
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    payload, err = _json_payload(request)
    if err:
        return err

    email = str(payload.get("email", "")).strip().lower()
    if not email:
        return JsonResponse({"error": "`email` is required."}, status=400)

    role = str(payload.get("role", FounderProfile.Role.OPERATOR))
    if role not in FounderProfile.Role.values:
        return JsonResponse({"error": f"Invalid role: {role}."}, status=400)

    organization = _organization_for_request(request)
    expires_days = int(payload.get("expiresInDays", 7))
    expires_at = timezone.now() + timezone.timedelta(days=max(1, min(expires_days, 30)))

    invitation = Invitation.objects.create(
        email=email,
        organization=organization,
        invited_by=request.user,
        role=role,
        expires_at=expires_at,
    )
    _audit(request, "invitation.created", "Invitation", str(invitation.id), {"email": email, "role": role})
    return JsonResponse(_serialize_invitation(invitation), status=201)


@csrf_exempt
@require_POST
def invitation_accept(request, token: str):
    """Accept invitation endpoint - exempted because user may not be authenticated yet."""
    rate_error = _rate_limit(_rate_limit_key(request, "invitation_accept"), max_requests=5, window_seconds=60)
    if rate_error:
        return rate_error

    try:
        invitation = Invitation.objects.get(token=token, status=Invitation.Status.PENDING)
    except Invitation.DoesNotExist:
        return JsonResponse({"error": "Invalid or expired invitation token."}, status=404)

    if invitation.expires_at < timezone.now():
        invitation.status = Invitation.Status.REVOKED
        invitation.save(update_fields=["status"])
        return JsonResponse({"error": "Invitation has expired."}, status=410)

    payload, err = _json_payload(request)
    if err:
        return err

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return JsonResponse({"error": "`username` and `password` are required."}, status=400)

    if len(password) < 8:
        return JsonResponse({"error": "Password must be at least 8 characters."}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already taken."}, status=409)

    user = User.objects.create_user(username=username, password=password)
    FounderProfile.objects.create(user=user, organization=invitation.organization, role=invitation.role)
    invitation.status = Invitation.Status.ACCEPTED
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["status", "accepted_at"])
    login(request, user)
    _audit(request, "invitation.accepted", "Invitation", str(invitation.id), {"userId": str(user.id), "username": username})
    return JsonResponse(_serialize_session(request), status=201)


@require_http_methods(["DELETE"])
def invitation_revoke(request, invitation_id: str):
    error = _role_error(request, FOUNDER_ROLES)
    if error:
        return error
    organization = _organization_for_request(request)
    try:
        invitation = Invitation.objects.get(id=invitation_id, organization=organization)
    except (Invitation.DoesNotExist, ValueError):
        return JsonResponse({"error": "Invitation not found."}, status=404)

    if invitation.status != Invitation.Status.PENDING:
        return JsonResponse({"error": "Only pending invitations can be revoked."}, status=409)

    invitation.status = Invitation.Status.REVOKED
    invitation.save(update_fields=["status"])
    _audit(request, "invitation.revoked", "Invitation", str(invitation.id))
    return JsonResponse({"revoked": str(invitation.id)})
