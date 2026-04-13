import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Mission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("command", models.TextField()),
                ("session_id", models.CharField(db_index=True, max_length=120)),
                ("agent_id", models.CharField(blank=True, max_length=80)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed")], db_index=True, default="queued", max_length=20)),
                ("result_text", models.TextField(blank=True)),
                ("error", models.TextField(blank=True)),
                ("raw_result", models.JSONField(blank=True, default=dict)),
                ("input_tokens", models.PositiveIntegerField(default=0)),
                ("output_tokens", models.PositiveIntegerField(default=0)),
                ("total_tokens", models.PositiveIntegerField(default=0)),
                ("estimated_cost_usd", models.DecimalField(decimal_places=6, default=0, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MissionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(default="log", max_length=40)),
                ("level", models.CharField(default="info", max_length=20)),
                ("message", models.TextField()),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="desk.mission")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.CreateModel(
            name="QualityGate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("passed", "Passed"), ("failed", "Failed")], default="pending", max_length=20)),
                ("details", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("mission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quality_gates", to="desk.mission")),
            ],
            options={"ordering": ["created_at", "id"], "unique_together": {("mission", "name")}},
        ),
    ]
