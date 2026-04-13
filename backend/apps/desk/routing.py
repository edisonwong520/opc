from django.urls import re_path

from .consumers import MissionLogConsumer

websocket_urlpatterns = [
    re_path(r"^ws/missions/(?P<mission_id>[0-9a-f-]+)/logs/$", MissionLogConsumer.as_asgi()),
]
