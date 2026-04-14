import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from opc_server.logger import app_logger
from .models import FounderProfile, Organization
from .openclaw import dashboard_metrics


class MissionLogConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if settings.OPC_REQUIRE_AUTH and not self.scope.get("user"):
            app_logger.warning("WebSocket connection rejected: no user in scope")
            await self.close()
            return
        user = self.scope.get("user")
        if settings.OPC_REQUIRE_AUTH and (not user or not user.is_authenticated):
            app_logger.warning("WebSocket connection rejected: user not authenticated")
            await self.close()
            return
        self.mission_id = self.scope["url_route"]["kwargs"]["mission_id"]
        self.group_name = f"mission_{self.mission_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        app_logger.debug(f"WebSocket connected to mission {self.mission_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        app_logger.debug(f"WebSocket disconnected from mission {self.mission_id}: code={close_code}")

    async def mission_event(self, event):
        await self.send_json(event["event"])


class MetricsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if settings.OPC_REQUIRE_AUTH and not self.scope.get("user"):
            app_logger.warning("Metrics WebSocket rejected: no user in scope")
            await self.close()
            return
        user = self.scope.get("user")
        if settings.OPC_REQUIRE_AUTH and (not user or not user.is_authenticated):
            app_logger.warning("Metrics WebSocket rejected: user not authenticated")
            await self.close()
            return
        self.keep_streaming = True
        self.organization = await self._get_organization()
        await self.accept()
        app_logger.debug(f"Metrics WebSocket connected for organization {self.organization.slug}")
        self.metrics_task = asyncio.create_task(self.stream_metrics())

    @database_sync_to_async
    def _get_organization(self) -> Organization:
        user = self.scope.get("user")
        if user and user.is_authenticated:
            profile = FounderProfile.objects.select_related("organization").filter(user=user).first()
            if profile:
                return profile.organization
        organization, _ = Organization.objects.get_or_create(slug="default", defaults={"name": "Default OPC"})
        return organization

    async def disconnect(self, close_code):
        self.keep_streaming = False
        if hasattr(self, "metrics_task"):
            self.metrics_task.cancel()

    async def stream_metrics(self):
        while self.keep_streaming:
            metrics = await database_sync_to_async(dashboard_metrics)(self.organization)
            await self.send_json({"type": "metrics", "metrics": metrics})
            await asyncio.sleep(30)
