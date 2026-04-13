import uuid

from django.db import models


class Mission(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

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
