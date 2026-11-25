from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.permissions import can_access_lead, role_required
from apps.audit_logs.models import ActivityLog
from apps.courses.models import Course
from apps.followups.models import FollowUp, FollowUpPriority
from apps.leads.models import LeadPriority, LeadStage, StudentLead
from apps.notifications.models import Notification, NotificationType
from apps.telecalling.forms import CallLogForm
from apps.telecalling.models import CallAttempt, CallOutcome, OutcomeCategory

PRIORITY_ORDER = {LeadPriority.HOT: 0, LeadPriority.WARM: 1, LeadPriority.COLD: 2}


@login_required
@role_required(Role.TELECALLER)
def my_leads(request):
    leads = StudentLead.objects.filter(current_owner=request.user, is_archived=False).select_related(
        "interested_course"
    )

    q = request.GET.get("q", "").strip()
    if q:
        leads = leads.filter(student_name__icontains=q) | leads.filter(student_phone__icontains=q)
    stage = request.GET.get("stage")
    if stage:
        leads = leads.filter(stage=stage)
    course_id = request.GET.get("course")
    if course_id:
        leads = leads.filter(interested_course_id=course_id)

    sort = request.GET.get("sort", "priority")
    if sort == "priority":
        leads = sorted(leads, key=lambda l: PRIORITY_ORDER.get(l.priority, 1))
    else:
        leads = leads.order_by(sort if sort in {"-created_at", "created_at", "student_name"} else "-created_at")

    paginator = Paginator(leads, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "telecalling/my_leads.html",
        {"page_obj": page_obj, "stages": LeadStage.choices, "courses": Course.objects.filter(is_active=True)},
    )


def _next_lead_for(user, exclude_pk=None):
    base = StudentLead.objects.filter(current_owner=user, is_archived=False, do_not_call=False)
    if exclude_pk:
        base = base.exclude(pk=exclude_pk)

    overdue = base.filter(next_follow_up_at__lte=timezone.now(), next_follow_up_at__isnull=False).order_by(
        "next_follow_up_at"
    ).first()
    if overdue:
        return overdue

    never_called = base.filter(last_call_at__isnull=True).order_by("priority", "-created_at")
    for priority in (LeadPriority.HOT, LeadPriority.WARM, LeadPriority.COLD):
        lead = never_called.filter(priority=priority).first()
        if lead:
            return lead

    return base.order_by("last_call_at").first()


@login_required
@role_required(Role.TELECALLER)
def workspace(request):
    lead_id = request.GET.get("lead")
    lead = None
    if lead_id:
        lead = StudentLead.objects.filter(pk=lead_id, current_owner=request.user).first()
    if not lead:
        lead = _next_lead_for(request.user)

    form = CallLogForm()
    pending_count = StudentLead.objects.filter(
        current_owner=request.user, is_archived=False, do_not_call=False
    ).count()

    return render(
        request,
        "telecalling/workspace.html",
        {"lead": lead, "form": form, "pending_count": pending_count},
    )


@login_required
@role_required(Role.TELECALLER)
def log_call(request, pk):
    lead = get_object_or_404(StudentLead, pk=pk)
    if not can_access_lead(request.user, lead):
        raise PermissionDenied

    if request.method != "POST":
        return redirect("telecalling:workspace")

    form = CallLogForm(request.POST)
    if form.is_valid():
        now = timezone.now()
        outcome = form.cleaned_data["outcome"]
        call = CallAttempt.objects.create(
            lead=lead,
            telecaller=request.user,
            outcome=outcome,
            call_date=now.date(),
            call_time=now.time(),
            duration_seconds=form.cleaned_data.get("duration_seconds"),
            remarks=form.cleaned_data.get("remarks", ""),
            next_follow_up_at=form.cleaned_data.get("follow_up_at") if form.cleaned_data.get("schedule_follow_up") else None,
        )
        lead.last_call_at = now

        if outcome.category == OutcomeCategory.POSITIVE:
            lead.stage = LeadStage.INTERESTED
            lead.priority = LeadPriority.HOT if "very" in outcome.slug else lead.priority
        elif outcome.slug == "do-not-call":
            lead.do_not_call = True
            lead.stage = LeadStage.DO_NOT_CONTACT
        elif outcome.slug == "not-interested":
            lead.stage = LeadStage.NOT_INTERESTED
        elif outcome.slug == "already-joined-elsewhere":
            lead.stage = LeadStage.LOST
        elif lead.stage == LeadStage.NEW:
            lead.stage = LeadStage.CONTACTED

        course_text = form.cleaned_data.get("update_course_interest", "").strip()
        if course_text:
            course = Course.objects.filter(name__icontains=course_text).first()
            if course:
                lead.interested_course = course

        if form.cleaned_data.get("schedule_follow_up") and form.cleaned_data.get("follow_up_at"):
            lead.next_follow_up_at = form.cleaned_data["follow_up_at"]
            FollowUp.objects.create(
                lead=lead,
                assigned_to=request.user,
                created_by=request.user,
                scheduled_at=form.cleaned_data["follow_up_at"],
                reason=form.cleaned_data.get("follow_up_reason", "") or outcome.name,
                priority=FollowUpPriority.HIGH if lead.priority == LeadPriority.HOT else FollowUpPriority.MEDIUM,
                related_call=call,
            )

        lead.save()
        ActivityLog.log(request.user, "log_call", target=lead, description=f"Call outcome: {outcome.name}")

        if outcome.category == OutcomeCategory.POSITIVE:
            manager = getattr(getattr(request.user, "telecaller_profile", None), "manager", None)
            if manager:
                Notification.objects.create(
                    recipient=manager,
                    notification_type=NotificationType.NEW_INTERESTED_LEAD,
                    title="New interested lead",
                    message=f"{lead.student_name} marked interested by {request.user}.",
                    link=f"/leads/{lead.pk}/",
                )

        messages.success(request, f"Call logged: {outcome.name}")
    else:
        messages.error(request, "Please correct the errors in the call form.")

    return redirect(f"/calling/workspace/")


@login_required
@role_required(Role.TELECALLER)
def call_history(request):
    calls = CallAttempt.objects.filter(telecaller=request.user).select_related("lead", "outcome")
    paginator = Paginator(calls, 30)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "telecalling/history.html", {"page_obj": page_obj})


@login_required
@role_required(Role.TELECALLER)
def interested_students(request):
    leads = StudentLead.objects.filter(
        current_owner=request.user,
        stage__in=[LeadStage.INTERESTED, LeadStage.COUNSELING_SCHEDULED, LeadStage.COUNSELING_COMPLETED],
    ).select_related("interested_course")
    return render(request, "telecalling/interested.html", {"leads": leads})


@login_required
@role_required(Role.ADMIN)
def activity(request):
    calls = CallAttempt.objects.select_related("lead", "telecaller", "outcome").all()
    telecaller_id = request.GET.get("telecaller")
    if telecaller_id:
        calls = calls.filter(telecaller_id=telecaller_id)
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        calls = calls.filter(call_date__gte=date_from)
    if date_to:
        calls = calls.filter(call_date__lte=date_to)

    paginator = Paginator(calls, 40)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "telecalling/activity.html", {"page_obj": page_obj})
