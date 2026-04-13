from django.urls import path

from . import views

app_name = "desk"

urlpatterns = [
    path("briefing/", views.briefing, name="briefing"),
    path("commands/", views.create_command, name="create-command"),
    path("missions/", views.list_missions, name="list-missions"),
    path("missions/<uuid:mission_id>/", views.mission_detail, name="mission-detail"),
    path("missions/<uuid:mission_id>/approve/", views.mission_approve, name="mission-approve"),
    path("missions/<uuid:mission_id>/reject/", views.mission_reject, name="mission-reject"),
    path("openclaw/health/", views.openclaw_health, name="openclaw-health"),
    path("openclaw/logs/", views.openclaw_logs, name="openclaw-logs"),
    path("openclaw/cost/", views.openclaw_cost, name="openclaw-cost"),
    path("templates/", views.template_create, name="template-list-create"),
    path("templates/<str:template_id>/", views.template_update, name="template-detail-update"),
]
