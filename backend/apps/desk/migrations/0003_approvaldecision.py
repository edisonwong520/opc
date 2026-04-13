from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("desk", "0002_templates_workstreams_boardbrief"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApprovalDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision", models.CharField(choices=[("approved", "Approved"), ("rejected", "Rejected")], max_length=20)),
                ("reviewer", models.CharField(default="founder", max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_decisions", to="desk.mission")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
