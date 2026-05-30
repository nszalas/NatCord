from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from users.decorators import admin_required, moderator_required

from .forms import ChannelForm, DirectMessageForm, MessageForm, VoiceChannelForm
from .models import (
    Channel,
    DirectConversation,
    DirectMessage,
    Message,
    MessageReaction,
    Notification,
    VoiceChannel,
)

User = get_user_model()


def home(request):
    if request.user.is_authenticated:
        return redirect("/channels/")
    return redirect("/login/")


@login_required
def channel_list(request):
    form = ChannelForm()
    voice_form = VoiceChannelForm(prefix="voice")
    channels = Channel.objects.order_by("name")
    voice_channels = VoiceChannel.objects.order_by("name")
    users = User.objects.exclude(id=request.user.id).order_by("username")

    if request.method == "POST":
        if request.user.role != "admin" and not request.user.is_superuser:
            messages.error(request, "Only an administrator can create channels.")
            return redirect("/channels/")

        if request.POST.get("form_type") == "voice":
            voice_form = VoiceChannelForm(request.POST, prefix="voice")
            if voice_form.is_valid():
                voice_channel = voice_form.save(commit=False)
                voice_channel.created_by = request.user
                voice_channel.save()
                voice_channel.members.add(request.user)
                messages.success(request, "Voice channel created.")
                return redirect("voice_channel_detail", voice_channel_id=voice_channel.id)
        else:
            form = ChannelForm(request.POST)
            if form.is_valid():
                channel = form.save(commit=False)
                channel.created_by = request.user
                channel.save()
                channel.members.add(request.user)
                messages.success(request, "Channel created.")
                return redirect("channel_detail", channel_id=channel.id)

    return render(request, "chat/channel_list.html", {
        "channels": channels,
        "voice_channels": voice_channels,
        "form": form,
        "voice_form": voice_form,
        "users": users,
    })


@login_required
def join_voice_channel(request, voice_channel_id):
    voice_channel = get_object_or_404(VoiceChannel, id=voice_channel_id)
    voice_channel.members.add(request.user)
    messages.success(request, "Joined voice channel.")
    return redirect("voice_channel_detail", voice_channel_id=voice_channel.id)


@login_required
def voice_channel_detail(request, voice_channel_id):
    voice_channel = get_object_or_404(VoiceChannel, id=voice_channel_id)
    if (
        request.user.role != "admin"
        and not request.user.is_superuser
        and not voice_channel.members.filter(id=request.user.id).exists()
    ):
        messages.error(request, "Join the voice channel first.")
        return redirect("/channels/")

    return render(request, "chat/voice_channel_detail.html", {
        "voice_channel": voice_channel,
        "channels": Channel.objects.order_by("name"),
        "voice_channels": VoiceChannel.objects.order_by("name"),
        "users": User.objects.exclude(id=request.user.id).order_by("username"),
        "channel_form": ChannelForm(),
        "voice_form": VoiceChannelForm(prefix="voice"),
    })


@login_required
@admin_required
def delete_voice_channel(request, voice_channel_id):
    voice_channel = get_object_or_404(VoiceChannel, id=voice_channel_id)
    voice_channel.delete()
    messages.success(request, "Voice channel deleted.")
    return redirect("/channels/")


@login_required
def join_channel(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    channel.members.add(request.user)
    messages.success(request, "Joined channel.")
    return redirect("channel_detail", channel_id=channel.id)


@login_required
def channel_detail(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    if not channel.members.filter(id=request.user.id).exists():
        channel.members.add(request.user)

    form = MessageForm()
    channel_form = ChannelForm()
    voice_form = VoiceChannelForm(prefix="voice")
    messages_qs = get_channel_messages_with_reactions(channel, request.user)
    channel_list_qs = Channel.objects.order_by("name")
    voice_channels = VoiceChannel.objects.order_by("name")
    users = User.objects.exclude(id=request.user.id).order_by("username")
    request.user.notifications.filter(message__channel=channel).update(is_read=True)

    if request.method == "POST":
        if request.user.is_blocked:
            messages.error(request, "A blocked user cannot send messages.")
            return redirect("channel_detail", channel_id=channel.id)

        form = MessageForm(request.POST, request.FILES)
        if form.is_valid() and any(form.cleaned_data.values()):
            message = form.save(commit=False)
            message.channel = channel
            message.author = request.user
            message.save()
            create_channel_notifications(message)
            return redirect("channel_detail", channel_id=channel.id)

    return render(request, "chat/channel_detail.html", {
        "channel": channel,
        "chat_messages": messages_qs,
        "channel_list": channel_list_qs,
        "channels": channel_list_qs,
        "voice_channels": voice_channels,
        "users": users,
        "channel_form": channel_form,
        "voice_form": voice_form,
        "form": form,
    })


@login_required
def channel_messages_latest(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    if not channel.members.filter(id=request.user.id).exists():
        channel.members.add(request.user)

    try:
        after_id = int(request.GET.get("after", 0))
    except ValueError:
        after_id = 0

    all_messages = get_channel_messages_with_reactions(channel, request.user)
    latest_id = all_messages.last().id if all_messages else 0

    return JsonResponse({
        "latest_id": latest_id,
        "html": render_to_string(
            "chat/channel_messages.html",
            {
                "chat_messages": all_messages,
                "user": request.user,
                "request": request,
            },
        ),
        "messages": [
            {
                "id": message.id,
                "username": message.author.username,
                "content": message.content,
                "created_at": message.created_at.strftime("%Y-%m-%d %H:%M"),
                "avatar_url": message.author.avatar.url if message.author.avatar else "",
                "is_online": message.author.is_online,
                "image_url": message.image.url if message.image else "",
                "audio_url": message.audio.url if message.audio else "",
                "can_delete": can_delete_message(request.user, message),
                "delete_url": f"/messages/delete/{message.id}/",
            }
            for message in all_messages.filter(id__gt=after_id)[:50]
        ]
    })


def get_channel_messages_with_reactions(channel, user):
    messages_qs = channel.messages.select_related("author").prefetch_related("reactions").order_by("created_at")
    for message in messages_qs:
        message.reaction_summary = []
        for emoji, label in MessageReaction.EMOJI_CHOICES:
            count = message.reactions.filter(emoji=emoji).count()
            reacted_by_user = message.reactions.filter(emoji=emoji, user=user).exists()
            message.reaction_summary.append({
                "emoji": emoji,
                "label": label,
                "count": count,
                "active": reacted_by_user,
            })
    return messages_qs


def can_delete_message(user, message):
    return user == message.author or user.role in ["admin", "moderator"] or user.is_superuser


def create_channel_notifications(message):
    recipients = message.channel.members.exclude(id=message.author.id)
    notifications = [
        Notification(
            recipient=recipient,
            actor=message.author,
            message=message,
            text=f"New message from {message.author.username} in #{message.channel.name}",
        )
        for recipient in recipients
    ]
    Notification.objects.bulk_create(notifications)


@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    channel_id = message.channel.id
    if not can_delete_message(request.user, message):
        messages.error(request, "You can delete only your own message.")
        return redirect("channel_detail", channel_id=channel_id)

    message.delete()
    messages.success(request, "Message deleted.")
    return redirect("channel_detail", channel_id=channel_id)


@login_required
def toggle_reaction(request, message_id, emoji):
    message = get_object_or_404(Message, id=message_id)
    if request.user.role != "admin" and not request.user.is_superuser and not message.channel.members.filter(id=request.user.id).exists():
        messages.error(request, "Join the channel first.")
        return redirect("/channels/")

    reaction, created = MessageReaction.objects.get_or_create(
        message=message,
        user=request.user,
        emoji=emoji,
    )
    if not created:
        reaction.delete()
    return redirect("channel_detail", channel_id=message.channel.id)


@login_required
@admin_required
def delete_channel(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    channel.delete()
    messages.success(request, "Channel deleted.")
    return redirect("/channels/")


def _get_or_create_direct_conversation(user_a, user_b):
    for conversation in DirectConversation.objects.filter(participants=user_a):
        if conversation.participants.filter(id=user_b.id).exists() and conversation.participants.count() == 2:
            return conversation

    conversation = DirectConversation.objects.create()
    conversation.participants.add(user_a, user_b)
    return conversation


@login_required
def direct_messages(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if other_user == request.user:
        return redirect("/channels/")

    conversation = _get_or_create_direct_conversation(request.user, other_user)
    form = DirectMessageForm()
    channel_form = ChannelForm()
    voice_form = VoiceChannelForm(prefix="voice")

    if request.method == "POST":
        if request.user.is_blocked:
            messages.error(request, "A blocked user cannot send messages.")
            return redirect("direct_messages", user_id=other_user.id)

        form = DirectMessageForm(request.POST, request.FILES)
        if form.is_valid() and any(form.cleaned_data.values()):
            direct_message = form.save(commit=False)
            direct_message.conversation = conversation
            direct_message.author = request.user
            direct_message.save()
            create_direct_notification(direct_message, other_user)
            return redirect("direct_messages", user_id=other_user.id)
    request.user.notifications.filter(direct_message__conversation=conversation).update(is_read=True)

    return render(request, "chat/direct_messages.html", {
        "conversation": conversation,
        "direct_messages": conversation.messages.select_related("author").order_by("created_at"),
        "other_user": other_user,
        "form": form,
        "channels": Channel.objects.order_by("name"),
        "voice_channels": VoiceChannel.objects.order_by("name"),
        "users": User.objects.exclude(id=request.user.id).order_by("username"),
        "channel_form": channel_form,
        "voice_form": voice_form,
    })


@login_required
def direct_messages_latest(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if other_user == request.user:
        return JsonResponse({"latest_id": 0, "html": "", "messages": []})

    conversation = _get_or_create_direct_conversation(request.user, other_user)
    messages_qs = conversation.messages.select_related("author").order_by("created_at")
    latest_id = messages_qs.last().id if messages_qs else 0

    try:
        after_id = int(request.GET.get("after", 0))
    except ValueError:
        after_id = 0

    return JsonResponse({
        "latest_id": latest_id,
        "html": render_to_string(
            "chat/direct_messages_list.html",
            {
                "direct_messages": messages_qs,
                "user": request.user,
                "request": request,
            },
        ),
        "messages": [
            {
                "id": message.id,
                "username": message.author.username,
                "content": message.content,
                "created_at": message.created_at.strftime("%Y-%m-%d %H:%M"),
                "avatar_url": message.author.avatar.url if message.author.avatar else "",
                "image_url": message.image.url if message.image else "",
                "audio_url": message.audio.url if message.audio else "",
            }
            for message in messages_qs.filter(id__gt=after_id)[:50]
        ],
    })


def create_direct_notification(direct_message, recipient):
    if recipient != direct_message.author:
        Notification.objects.create(
            recipient=recipient,
            actor=direct_message.author,
            direct_message=direct_message,
            text=f"New direct message from {direct_message.author.username}",
        )


@login_required
def delete_direct_message(request, message_id):
    message = get_object_or_404(DirectMessage, id=message_id)
    conversation = message.conversation
    other_user = conversation.participants.exclude(id=request.user.id).first()
    if not can_delete_message(request.user, message):
        messages.error(request, "You can delete only your own message.")
        return redirect("direct_messages", user_id=other_user.id if other_user else request.user.id)

    message.delete()
    messages.success(request, "Direct message deleted.")
    return redirect("direct_messages", user_id=other_user.id if other_user else request.user.id)


@login_required
def notifications_list(request):
    notifications = request.user.notifications.select_related("actor", "message", "direct_message")[:50]
    return render(request, "chat/notifications.html", {"notifications": notifications})


@login_required
def notifications_state(request):
    latest = request.user.notifications.filter(is_read=False).order_by("-created_at").first()
    return JsonResponse({
        "unread_count": request.user.notifications.filter(is_read=False).count(),
        "latest_id": latest.id if latest else 0,
        "latest_text": latest.text if latest else "",
    })


@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications")


@login_required
def search(request):
    query = request.GET.get("q", "").strip()
    channels = Channel.objects.none()
    users = User.objects.none()

    if query:
        channels = Channel.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).order_by("name")
        users = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id).order_by("username")

    return render(request, "chat/search.html", {
        "query": query,
        "channels": channels,
        "users": users,
    })
