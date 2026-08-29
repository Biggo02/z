def notification_context(request):
    if not request.user.is_authenticated:
        return {'notification_unread_count': 0}
    return {'notification_unread_count': request.user.notifications.filter(is_read=False).count()}
