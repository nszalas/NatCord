from django.db import models
from users.models import User

class Channel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    members = models.ManyToManyField(User, related_name='channels', blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_channels',
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.name


class VoiceChannel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(User, related_name='voice_channels', blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_voice_channels',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Message(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='messages/images/', blank=True, null=True)
    audio = models.FileField(upload_to='messages/audio/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author} - {self.channel}"


class MessageReaction(models.Model):
    EMOJI_CHOICES = (
        ("👍", "Like"),
        ("❤️", "Love"),
        ("😂", "Laugh"),
        ("😮", "Wow"),
        ("😢", "Sad"),
    )

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    emoji = models.CharField(max_length=10, choices=EMOJI_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'emoji')

    def __str__(self):
        return f"{self.user} {self.emoji} {self.message_id}"


class DirectConversation(models.Model):
    participants = models.ManyToManyField(User, related_name='direct_conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return ", ".join(self.participants.values_list("username", flat=True))


class DirectMessage(models.Model):
    conversation = models.ForeignKey(
        DirectConversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='dm/images/', blank=True, null=True)
    audio = models.FileField(upload_to='dm/audio/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author} - DM {self.conversation_id}"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, blank=True, null=True)
    direct_message = models.ForeignKey(DirectMessage, on_delete=models.CASCADE, blank=True, null=True)
    text = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.text
