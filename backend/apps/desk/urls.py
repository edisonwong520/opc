from django.urls import path

from . import views

app_name = "desk"

urlpatterns = [
    path("auth/me/", views.auth_me, name="auth-me"),
    path("auth/login/", views.auth_login, name="auth-login"),
    path("auth/logout/", views.auth_logout, name="auth-logout"),
    path("auth/bootstrap/", views.auth_bootstrap, name="auth-bootstrap"),
    path("audit-logs/", views.audit_logs, name="audit-logs"),
    path("briefing/", views.briefing, name="briefing"),
    path("commands/", views.create_command, name="create-command"),
    path("missions/", views.list_missions, name="list-missions"),
    path("missions/<uuid:mission_id>/", views.mission_detail, name="mission-detail"),
    path("missions/<uuid:mission_id>/approve/", views.mission_approve, name="mission-approve"),
    path("missions/<uuid:mission_id>/reject/", views.mission_reject, name="mission-reject"),
    path("missions/<uuid:mission_id>/retry/", views.mission_retry, name="mission-retry"),
    path("missions/<uuid:mission_id>/abort/", views.mission_abort, name="mission-abort"),
    path("missions/<uuid:mission_id>/archive/", views.mission_archive, name="mission-archive"),
    path("missions/<uuid:mission_id>/export/", views.mission_export, name="mission-export"),
    path("missions/<uuid:mission_id>/workstreams/<int:workstream_id>/retry/", views.workstream_retry, name="workstream-retry"),
    path("openclaw/health/", views.openclaw_health, name="openclaw-health"),
    path("openclaw/logs/", views.openclaw_logs, name="openclaw-logs"),
    path("openclaw/cost/", views.openclaw_cost, name="openclaw-cost"),
    path("templates/", views.template_create, name="template-list-create"),
    path("templates/<str:template_id>/", views.template_update, name="template-detail-update"),
    path("invitations/", views.invitation_list, name="invitation-list"),
    path("invitations/create/", views.invitation_create, name="invitation-create"),
    path("invitations/<str:token>/accept/", views.invitation_accept, name="invitation-accept"),
    path("invitations/<uuid:invitation_id>/revoke/", views.invitation_revoke, name="invitation-revoke"),
]
