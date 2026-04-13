from django.urls import path

from . import views

app_name = "desk"

urlpatterns = [
    path("briefing/", views.briefing, name="briefing"),
    path("commands/", views.create_command, name="create-command"),
    path("missions/", views.list_missions, name="list-missions"),
    path("missions/<uuid:mission_id>/", views.mission_detail, name="mission-detail"),
    path("openclaw/health/", views.openclaw_health, name="openclaw-health"),
    path("openclaw/logs/", views.openclaw_logs, name="openclaw-logs"),
    path("openclaw/cost/", views.openclaw_cost, name="openclaw-cost"),
]
