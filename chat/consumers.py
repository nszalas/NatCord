import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import Channel, Message, Notification, VoiceChannel


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated or not await self.can_access_channel():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        if self.user.is_blocked:
            return

        data = json.loads(text_data)
        content = data.get("message", "").strip()
        if not content:
            return

        await self.touch_last_seen()
        message = await self.save_message(content)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message.content,
                "username": self.user.username,
                "avatar_url": self.user.avatar.url if self.user.avatar else "",
                "message_id": message.id,
                "created_at": message.created_at.strftime("%Y-%m-%d %H:%M"),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @sync_to_async
    def can_access_channel(self):
        try:
            channel = Channel.objects.get(id=self.room_id)
        except Channel.DoesNotExist:
            return False

        if not channel.members.filter(id=self.user.id).exists():
            channel.members.add(self.user)
        return True

    @sync_to_async
    def save_message(self, content):
        channel = Channel.objects.get(id=self.room_id)
        message = Message.objects.create(channel=channel, author=self.user, content=content)
        Notification.objects.bulk_create([
            Notification(
                recipient=recipient,
                actor=self.user,
                message=message,
                text=f"New message from {self.user.username} in #{channel.name}",
            )
            for recipient in channel.members.exclude(id=self.user.id)
        ])
        return message

    @sync_to_async
    def touch_last_seen(self):
        self.user.last_seen = timezone.now()
        self.user.save(update_fields=["last_seen"])


class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.voice_channel_id = self.scope["url_route"]["kwargs"]["voice_channel_id"]
        self.room_group_name = f"voice_{self.voice_channel_id}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated or not await self.can_access_voice_channel():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.touch_last_seen()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "voice_signal",
                    "signal": {
                        "type": "user-left",
                        "sender": self.user.id,
                        "username": self.user.username,
                    },
                },
            )

    async def receive(self, text_data):
        if self.user.is_blocked:
            return

        data = json.loads(text_data)
        signal_type = data.get("type")

        if signal_type == "join":
            payload = {
                "type": "user-joined",
                "sender": self.user.id,
                "username": self.user.username,
            }
        elif signal_type == "leave":
            payload = {
                "type": "user-left",
                "sender": self.user.id,
                "username": self.user.username,
            }
        else:
            payload = data
            payload["sender"] = self.user.id
            payload["username"] = self.user.username

        await self.touch_last_seen()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "voice_signal",
                "signal": payload,
            },
        )

    async def voice_signal(self, event):
        await self.send(text_data=json.dumps(event["signal"]))

    @sync_to_async
    def can_access_voice_channel(self):
        try:
            voice_channel = VoiceChannel.objects.get(id=self.voice_channel_id)
        except VoiceChannel.DoesNotExist:
            return False

        if not voice_channel.members.filter(id=self.user.id).exists():
            voice_channel.members.add(self.user)
        return True

    @sync_to_async
    def touch_last_seen(self):
        self.user.last_seen = timezone.now()
        self.user.save(update_fields=["last_seen"])
