"""Aggregation helpers for dashboard KPIs and charts. Every number here is
computed from live SQLite data via the ORM -- nothing is hardcoded."""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.followups.models import FollowUp, FollowUpStatus
from apps.leads.models import LeadPriority, LeadStage, StudentLead
from apps.telecalling.models import CallAttempt, OutcomeCategory


def date_range_from_filter(request):
    filt = request.GET.get("range", "today")
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if filt == "yesterday":
        start = today_start - timedelta(days=1)
        end = today_start
    elif filt == "this_week":
        start = today_start - timedelta(days=today_start.weekday())
        end = now
    elif filt == "this_month":
        start = today_start.replace(day=1)
        end = now
    elif filt == "custom":
        start = request.GET.get("date_from") or today_start
        end = request.GET.get("date_to") or now
    else:
        start = today_start
        end = now
    return start, end, filt


def apply_common_filters(qs, request, date_field="created_at"):
    telecaller = request.GET.get("telecaller")
    course = request.GET.get("course")
    campaign = request.GET.get("campaign")
    if telecaller:
        qs = qs.filter(**{"current_owner_id" if hasattr(qs.model, "current_owner") else "telecaller_id": telecaller})
    if course and hasattr(qs.model, "interested_course"):
        qs = qs.filter(interested_course_id=course)
    if campaign and hasattr(qs.model, "campaign"):
        qs = qs.filter(campaign_id=campaign)
    return qs


def kpi_summary(request):
    leads = StudentLead.objects.filter(is_archived=False)
    leads = apply_common_filters(leads, request)

    today = timezone.now().date()
    calls_today = CallAttempt.objects.filter(call_date=today)
    pending_calls = leads.filter(current_owner__isnull=False).exclude(stage__in=["lost", "do_not_contact"]).count()

    return {
        "total_students": leads.count(),
        "total_uploaded_numbers": leads.count(),
        "assigned_leads": leads.filter(current_owner__isnull=False).count(),
        "unassigned_leads": leads.filter(current_owner__isnull=True).count(),
        "total_call_attempts": CallAttempt.objects.count(),
        "calls_completed_today": calls_today.count(),
        "pending_calls": pending_calls,
        "interested_students": leads.filter(
            stage__in=[LeadStage.INTERESTED, LeadStage.COUNSELING_SCHEDULED, LeadStage.COUNSELING_COMPLETED]
        ).count(),
        "not_interested": leads.filter(stage=LeadStage.NOT_INTERESTED).count(),
        "no_answer": CallAttempt.objects.filter(outcome__slug="no-answer").count(),
        "callback_requests": FollowUp.objects.filter(status=FollowUpStatus.PENDING).count(),
        "overdue_follow_ups": FollowUp.objects.filter(
            status=FollowUpStatus.PENDING, scheduled_at__lt=timezone.now()
        ).count(),
        "admission_enquiries": leads.filter(stage__in=[s for s in LeadStage if s not in (LeadStage.NEW,)]).count(),
        "counseling_scheduled": leads.filter(stage=LeadStage.COUNSELING_SCHEDULED).count(),
        "applications_submitted": leads.filter(stage=LeadStage.APPLICATION_SUBMITTED).count(),
        "confirmed_admissions": leads.filter(stage=LeadStage.ADMISSION_CONFIRMED).count(),
    }


def daily_calling_activity(days=14):
    today = timezone.now().date()
    labels, values = [], []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime("%d %b"))
        values.append(CallAttempt.objects.filter(call_date=day).count())
    return {"labels": labels, "values": values}


def weekly_performance(weeks=8):
    today = timezone.now().date()
    labels, values = [], []
    for i in range(weeks - 1, -1, -1):
        week_start = today - timedelta(days=today.weekday() + i * 7)
        week_end = week_start + timedelta(days=6)
        labels.append(week_start.strftime("%d %b"))
        values.append(CallAttempt.objects.filter(call_date__gte=week_start, call_date__lte=week_end).count())
    return {"labels": labels, "values": values}


def monthly_lead_conversion(months=6):
    today = timezone.now().date()
    labels, values = [], []
    for i in range(months - 1, -1, -1):
        month = (today.month - i - 1) % 12 + 1
        year = today.year + ((today.month - i - 1) // 12)
        count = StudentLead.objects.filter(
            stage=LeadStage.ENROLLED, updated_at__year=year, updated_at__month=month
        ).count()
        labels.append(f"{year}-{month:02d}")
        values.append(count)
    return {"labels": labels, "values": values}


def telecaller_comparison():
    from apps.accounts.models import CustomUser, Role

    telecallers = CustomUser.objects.filter(role=Role.TELECALLER, is_active_employee=True)
    labels, calls, conversions = [], [], []
    for t in telecallers:
        labels.append(t.get_full_name() or t.username)
        calls.append(CallAttempt.objects.filter(telecaller=t).count())
        conversions.append(StudentLead.objects.filter(current_owner=t, stage=LeadStage.ENROLLED).count())
    return {"labels": labels, "calls": calls, "conversions": conversions}


def interested_vs_not_interested():
    interested = StudentLead.objects.filter(stage=LeadStage.INTERESTED).count()
    not_interested = StudentLead.objects.filter(stage=LeadStage.NOT_INTERESTED).count()
    return {"labels": ["Interested", "Not Interested"], "values": [interested, not_interested]}


def course_wise_enquiries():
    from apps.courses.models import Course

    courses = Course.objects.filter(is_active=True).annotate(lead_count=Count("interested_leads"))
    return {"labels": [c.name for c in courses], "values": [c.lead_count for c in courses]}


def admission_funnel():
    from apps.admissions.views import PIPELINE_COLUMNS

    labels, values = [], []
    for stage, label in PIPELINE_COLUMNS:
        labels.append(label)
        values.append(StudentLead.objects.filter(stage=stage).count())
    return {"labels": labels, "values": values}


def follow_up_completion_rate():
    total = FollowUp.objects.count()
    completed = FollowUp.objects.filter(status=FollowUpStatus.COMPLETED).count()
    rate = round((completed / total) * 100, 1) if total else 0
    return {"total": total, "completed": completed, "rate": rate}
