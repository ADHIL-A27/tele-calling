def unread_notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications": [], "unread_notification_count": 0}
    qs = request.user.notifications.filter(is_read=False)[:8]
    return {
        "unread_notifications": qs,
        "unread_notification_count": request.user.notifications.filter(is_read=False).count(),
    }
