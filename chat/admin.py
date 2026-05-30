from django.contrib import admin
from .models import (
    Channel,
    DirectConversation,
    DirectMessage,
    Message,
    MessageReaction,
    Notification,
    VoiceChannel,
)

admin.site.register(Channel)
admin.site.register(VoiceChannel)
admin.site.register(Message)
admin.site.register(DirectConversation)
admin.site.register(DirectMessage)
admin.site.register(MessageReaction)
admin.site.register(Notification)
