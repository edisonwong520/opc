import django.db.models.deletion
from django.db import migrations, models


DEFAULT_TEMPLATES = [
    {
        "id": "ceo",
        "name": "CEO",
        "title": "Chief Executive Agent",
        "mission": "Receive one executive command, make final tradeoffs, and produce a human-readable board brief.",
        "reports_to": "",
        "status": "ready",
        "tools": ["board-brief", "decision-review"],
        "sort_order": 10,
    },
    {
        "id": "coo",
        "name": "COO",
        "title": "Orchestration Lead",
        "mission": "Break goals into workstreams, set priorities, and coordinate cross-role handoffs.",
        "reports_to": "ceo",
        "status": "ready",
        "tools": ["task-routing", "handoff"],
        "sort_order": 20,
    },
    {
        "id": "cto",
        "name": "CTO",
        "title": "Technical Strategy Agent",
        "mission": "Evaluate technical strategy, implementation plans, engineering risk, and delivery quality.",
        "reports_to": "coo",
        "status": "ready",
        "tools": ["architecture-review", "implementation-plan"],
        "sort_order": 30,
    },
    {
        "id": "cfo",
        "name": "CFO",
        "title": "Budget & Cost Agent",
        "mission": "Estimate token/API cost, budget limits, and return on effort.",
        "reports_to": "coo",
        "status": "ready",
        "tools": ["cost-estimate", "budget-control"],
        "sort_order": 40,
    },
    {
        "id": "cmo",
        "name": "CMO",
        "title": "Market Intelligence Agent",
        "mission": "Assess market research, positioning, competitors, and growth channels.",
        "reports_to": "coo",
        "status": "ready",
        "tools": ["market-research", "positioning"],
        "sort_order": 50,
    },
    {
        "id": "sre",
        "name": "SRE",
        "title": "Reliability Agent",
        "mission": "Review deployment, monitoring, rollback, and operational safety boundaries.",
        "reports_to": "cto",
        "status": "standby",
        "tools": ["reliability-review", "rollback-plan"],
        "sort_order": 60,
    },
]


def seed_templates(apps, _schema_editor):
    AgentTemplate = apps.get_model("desk", "AgentTemplate")
    for item in DEFAULT_TEMPLATES:
        AgentTemplate.objects.update_or_create(id=item["id"], defaults=item)


def remove_templates(apps, _schema_editor):
    AgentTemplate = apps.get_model("desk", "AgentTemplate")
    AgentTemplate.objects.filter(id__in=[item["id"] for item in DEFAULT_TEMPLATES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("desk", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentTemplate",
            fields=[
                ("id", models.CharField(max_length=40, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=80)),
                ("title", models.CharField(max_length=120)),
                ("mission", models.TextField()),
                ("reports_to", models.CharField(blank=True, max_length=40)),
                ("status", models.CharField(choices=[("ready", "Ready"), ("standby", "Standby"), ("disabled", "Disabled")], default="ready", max_length=20)),
                ("tools", models.JSONField(blank=True, default=list)),
                ("model_preference", models.CharField(blank=True, max_length=160)),
                ("budget_limit_usd", models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="BoardBrief",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("summary", models.TextField()),
                ("recommendations", models.JSONField(blank=True, default=list)),
                ("risks", models.JSONField(blank=True, default=list)),
                ("sources", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("mission", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="board_brief", to="desk.mission")),
            ],
        ),
        migrations.CreateModel(
            name="Workstream",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("owner", models.CharField(max_length=80)),
                ("title", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("skipped", "Skipped")], default="queued", max_length=20)),
                ("result", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("agent_template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workstreams", to="desk.agenttemplate")),
                ("mission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workstreams", to="desk.mission")),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.RunPython(seed_templates, remove_templates),
    ]
