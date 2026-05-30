from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from users.decorators import moderator_required
from chat.forms import ChannelForm, VoiceChannelForm
from chat.models import Channel, VoiceChannel

from .forms import UserReportForm, UserReportStatusForm
from .models import UserReport

User = get_user_model()


@login_required
def report_user(request, user_id):
    reported_user = get_object_or_404(User, id=user_id)
    if reported_user == request.user:
        messages.error(request, "You cannot report your own account.")
        return redirect("/channels/")

    form = UserReportForm()
    if request.method == "POST":
        form = UserReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = reported_user
            report.save()
            messages.success(request, "Report submitted to moderation.")
            return redirect("/channels/")

    return render(request, "moderation/report_user.html", {
        "form": form,
        "reported_user": reported_user,
        "channels": Channel.objects.order_by("name"),
        "voice_channels": VoiceChannel.objects.order_by("name"),
        "users": User.objects.exclude(id=request.user.id).order_by("username"),
        "channel_form": ChannelForm(),
        "voice_form": VoiceChannelForm(prefix="voice"),
    })


@login_required
@moderator_required
def report_list(request):
    reports = UserReport.objects.select_related("reporter", "reported_user")
    return render(request, "moderation/report_list.html", {"reports": reports})


@login_required
@moderator_required
def report_state(request):
    latest = UserReport.objects.filter(status="new").order_by("-created_at").first()
    return JsonResponse({
        "open_count": UserReport.objects.filter(status="new").count(),
        "latest_id": latest.id if latest else 0,
        "latest_text": (
            f"New report: {latest.reported_user.username}"
            if latest else ""
        ),
    })


@login_required
@moderator_required
def update_report_status(request, report_id):
    report = get_object_or_404(UserReport, id=report_id)
    if request.method == "POST":
        form = UserReportStatusForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, "Report status has been updated.")
    return redirect("/reports/")
