from channels.generic.websocket import AsyncJsonWebsocketConsumer


class MissionLogConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.mission_id = self.scope["url_route"]["kwargs"]["mission_id"]
        self.group_name = f"mission_{self.mission_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def mission_event(self, event):
        await self.send_json(event["event"])
