import uuid

from django.conf import settings
from django.db import models


def _generate_invitation_token() -> str:
    return uuid.uuid4().hex


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class FounderProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        FOUNDER = "founder", "Founder"
        OPERATOR = "operator", "Operator"
        VIEWER = "viewer", "Viewer"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="founder_profile")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="founders")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.FOUNDER)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user_id} {self.organization_id} {self.role}"


class AgentTemplate(models.Model):
    class Status(models.TextChoices):
        READY = "ready", "Ready"
        STANDBY = "standby", "Standby"
        DISABLED = "disabled", "Disabled"

    id = models.CharField(primary_key=True, max_length=40)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="agent_templates", null=True, blank=True)
    name = models.CharField(max_length=80)
    title = models.CharField(max_length=120)
    mission = models.TextField()
    reports_to = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.READY)
    tools = models.JSONField(default=list, blank=True)
    model_preference = models.CharField(max_length=160, blank=True)
    budget_limit_usd = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class PricingProfile(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="pricing_profiles", null=True, blank=True)
    provider = models.CharField(max_length=80)
    model_id = models.CharField(max_length=160)
    input_per_1k_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    output_per_1k_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "model_id"]
        unique_together = [("organization", "provider", "model_id")]

    def __str__(self) -> str:
        return f"{self.provider}/{self.model_id}"


class Mission(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        ABORTED = "aborted", "Aborted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="missions", null=True, blank=True)
    command = models.TextField()
    session_id = models.CharField(max_length=120, db_index=True)
    agent_id = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    result_text = models.TextField(blank=True)
    error = models.TextField(blank=True)
    raw_result = models.JSONField(default=dict, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    abort_requested = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.session_id} {self.status}"


class Workstream(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="workstreams")
    agent_template = models.ForeignKey(AgentTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="workstreams")
    owner = models.CharField(max_length=80)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    result = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.mission_id} {self.owner} {self.status}"


class AgentRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    workstream = models.ForeignKey(Workstream, on_delete=models.CASCADE, related_name="agent_runs")
    session_id = models.CharField(max_length=160, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    logs = models.JSONField(default=list, blank=True)
    raw_result = models.JSONField(default=dict, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    result_text = models.TextField(blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.session_id} {self.status}"


class MissionEvent(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="events")
    type = models.CharField(max_length=40, default="log")
    level = models.CharField(max_length=20, default="info")
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.mission_id} {self.type} {self.level}"


class QualityGate(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="quality_gates")
    name = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        unique_together = [("mission", "name")]

    def __str__(self) -> str:
        return f"{self.mission_id} {self.name} {self.status}"


class BoardBrief(models.Model):
    mission = models.OneToOneField(Mission, on_delete=models.CASCADE, related_name="board_brief")
    title = models.CharField(max_length=180)
    summary = models.TextField()
    recommendations = models.JSONField(default=list, blank=True)
    risks = models.JSONField(default=list, blank=True)
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title


class ApprovalDecision(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="approval_decisions")
    decision = models.CharField(max_length=20, choices=Decision.choices)
    reviewer = models.CharField(max_length=120, default="founder")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.mission_id} {self.decision}"


class AuditLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True)
    actor = models.CharField(max_length=120, default="founder")
    action = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=120)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.actor} {self.action} {self.entity_type}:{self.entity_id}"


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=64, unique=True, default=_generate_invitation_token)
    email = models.EmailField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invitations")
    role = models.CharField(max_length=20, choices=FounderProfile.Role.choices, default=FounderProfile.Role.OPERATOR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.email} ({self.status})"
