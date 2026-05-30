def unread_notifications(request):
    if request.user.is_authenticated:
        data = {
            "unread_notifications_count": request.user.notifications.filter(is_read=False).count()
        }
        if request.user.role in ["admin", "moderator"] or request.user.is_superuser:
            from moderation.models import UserReport

            data["open_reports_count"] = UserReport.objects.filter(status="new").count()
        else:
            data["open_reports_count"] = 0
        return data
    return {"unread_notifications_count": 0, "open_reports_count": 0}
