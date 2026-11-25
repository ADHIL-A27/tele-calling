from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.notifications.models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user)[:100]
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def mark_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return redirect(n.link or "notifications:list")


@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")
