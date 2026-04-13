from django.urls import path

from . import views

app_name = "desk"

urlpatterns = [
    path("briefing/", views.briefing, name="briefing"),
    path("commands/", views.create_command, name="create-command"),
]
