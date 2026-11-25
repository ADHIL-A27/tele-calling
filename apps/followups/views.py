from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.permissions import MANAGEMENT_ROLES
from apps.followups.forms import CompleteFollowUpForm, RescheduleForm
from apps.followups.models import FollowUp, FollowUpStatus


@login_required
def followup_list(request):
    qs = FollowUp.objects.select_related("lead", "assigned_to")
    if request.user.role not in MANAGEMENT_ROLES:
        qs = qs.filter(assigned_to=request.user)
    elif request.GET.get("assigned_to"):
        qs = qs.filter(assigned_to_id=request.GET["assigned_to"])

    now = timezone.now()
    today_end = now.replace(hour=23, minute=59, second=59)
    tomorrow_start = today_end + timedelta(seconds=1)
    tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59)

    category = request.GET.get("category", "today")
    pending = qs.filter(status=FollowUpStatus.PENDING)

    if category == "today":
        items = pending.filter(scheduled_at__gte=now.replace(hour=0, minute=0, second=0), scheduled_at__lte=today_end)
    elif category == "tomorrow":
        items = pending.filter(scheduled_at__gte=tomorrow_start, scheduled_at__lte=tomorrow_end)
    elif category == "upcoming":
        items = pending.filter(scheduled_at__gt=tomorrow_end)
    elif category == "overdue":
        items = pending.filter(scheduled_at__lt=now)
    elif category == "completed":
        items = qs.filter(status=FollowUpStatus.COMPLETED)
    else:
        items = pending

    items = items.order_by("scheduled_at")

    counts = {
        "today": pending.filter(scheduled_at__gte=now.replace(hour=0, minute=0, second=0), scheduled_at__lte=today_end).count(),
        "tomorrow": pending.filter(scheduled_at__gte=tomorrow_start, scheduled_at__lte=tomorrow_end).count(),
        "upcoming": pending.filter(scheduled_at__gt=tomorrow_end).count(),
        "overdue": pending.filter(scheduled_at__lt=now).count(),
        "completed": qs.filter(status=FollowUpStatus.COMPLETED).count(),
    }

    return render(
        request,
        "followups/list.html",
        {"items": items, "category": category, "counts": counts},
    )


@login_required
def complete_followup(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.role not in MANAGEMENT_ROLES and followup.assigned_to != request.user:
        messages.error(request, "You cannot update this follow-up.")
        return redirect("followups:list")

    if request.method == "POST":
        form = CompleteFollowUpForm(request.POST)
        if form.is_valid():
            followup.status = FollowUpStatus.COMPLETED
            followup.completed_at = timezone.now()
            followup.completion_notes = form.cleaned_data.get("completion_notes", "")
            followup.save()
            messages.success(request, "Follow-up marked completed.")
    return redirect("followups:list")


@login_required
def reschedule_followup(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.role not in MANAGEMENT_ROLES and followup.assigned_to != request.user:
        messages.error(request, "You cannot reschedule this follow-up.")
        return redirect("followups:list")

    if request.method == "POST":
        form = RescheduleForm(request.POST)
        if form.is_valid():
            new_followup = FollowUp.objects.create(
                lead=followup.lead,
                assigned_to=followup.assigned_to,
                created_by=request.user,
                scheduled_at=form.cleaned_data["scheduled_at"],
                reason=form.cleaned_data.get("reason") or followup.reason,
                priority=followup.priority,
                rescheduled_from=followup,
            )
            followup.status = FollowUpStatus.RESCHEDULED
            followup.save(update_fields=["status"])
            followup.lead.next_follow_up_at = new_followup.scheduled_at
            followup.lead.save(update_fields=["next_follow_up_at"])
            messages.success(request, "Follow-up rescheduled.")
    return redirect("followups:list")
