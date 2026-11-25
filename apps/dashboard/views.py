import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import CustomUser, Role
from apps.accounts.permissions import MANAGEMENT_ROLES, role_required
from apps.courses.models import Course
from apps.dashboard import services
from apps.dashboard.forms import SystemSettingsForm
from apps.dashboard.models import SystemSettings
from apps.followups.models import FollowUp, FollowUpStatus
from apps.leads.models import Campaign, LeadStage, StudentLead
from apps.telecalling.models import CallAttempt


@login_required
def home(request):
    if request.user.role == Role.TELECALLER:
        return redirect("telecalling:workspace")

    kpis = services.kpi_summary(request)
    charts = {
        "daily_calling": services.daily_calling_activity(),
        "weekly_performance": services.weekly_performance(),
        "monthly_conversion": services.monthly_lead_conversion(),
        "telecaller_comparison": services.telecaller_comparison(),
        "interested_split": services.interested_vs_not_interested(),
        "course_enquiries": services.course_wise_enquiries(),
        "admission_funnel": services.admission_funnel(),
    }
    follow_up_rate = services.follow_up_completion_rate()

    return render(
        request,
        "dashboard/home.html",
        {
            "kpis": kpis,
            "charts_json": json.dumps(charts),
            "follow_up_rate": follow_up_rate,
            "telecallers": CustomUser.objects.filter(role=Role.TELECALLER),
            "courses": Course.objects.filter(is_active=True),
            "campaigns": Campaign.objects.filter(is_active=True),
        },
    )


@login_required
@role_required(*MANAGEMENT_ROLES)
def performance(request):
    telecallers = CustomUser.objects.filter(role=Role.TELECALLER).select_related("telecaller_profile")
    rows = []
    for t in telecallers:
        calls = CallAttempt.objects.filter(telecaller=t)
        total_attempts = calls.count()
        unique_leads = calls.values("lead_id").distinct().count()
        answered = calls.exclude(outcome__slug__in=["not-called", "no-answer", "busy", "switched-off"]).count()
        no_answer = calls.filter(outcome__slug__in=["no-answer", "busy", "switched-off", "unreachable"]).count()
        interested = StudentLead.objects.filter(
            current_owner=t, stage__in=[LeadStage.INTERESTED, LeadStage.COUNSELING_SCHEDULED, LeadStage.COUNSELING_COMPLETED]
        ).count()
        not_interested = StudentLead.objects.filter(current_owner=t, stage=LeadStage.NOT_INTERESTED).count()
        callbacks_requested = FollowUp.objects.filter(assigned_to=t).count()
        callbacks_completed = FollowUp.objects.filter(assigned_to=t, status=FollowUpStatus.COMPLETED).count()
        overdue = FollowUp.objects.filter(assigned_to=t, status=FollowUpStatus.PENDING).count()
        admissions_confirmed = StudentLead.objects.filter(current_owner=t, stage=LeadStage.ADMISSION_CONFIRMED).count()
        conversion_pct = round((admissions_confirmed / unique_leads) * 100, 1) if unique_leads else 0

        rows.append(
            {
                "telecaller": t,
                "total_attempts": total_attempts,
                "unique_leads": unique_leads,
                "answered": answered,
                "no_answer": no_answer,
                "interested": interested,
                "not_interested": not_interested,
                "callbacks_requested": callbacks_requested,
                "callbacks_completed": callbacks_completed,
                "overdue": overdue,
                "admissions_confirmed": admissions_confirmed,
                "conversion_pct": conversion_pct,
            }
        )

    rows.sort(key=lambda r: -r["conversion_pct"])
    return render(request, "dashboard/performance.html", {"rows": rows})


@login_required
def my_performance(request):
    t = request.user
    calls = CallAttempt.objects.filter(telecaller=t)
    total_attempts = calls.count()
    unique_leads = calls.values("lead_id").distinct().count()
    interested = StudentLead.objects.filter(
        current_owner=t, stage__in=[LeadStage.INTERESTED, LeadStage.COUNSELING_SCHEDULED, LeadStage.COUNSELING_COMPLETED]
    ).count()
    admissions_confirmed = StudentLead.objects.filter(current_owner=t, stage=LeadStage.ADMISSION_CONFIRMED).count()
    weekly = services.weekly_performance(weeks=8)

    return render(
        request,
        "dashboard/my_performance.html",
        {
            "total_attempts": total_attempts,
            "unique_leads": unique_leads,
            "interested": interested,
            "admissions_confirmed": admissions_confirmed,
            "weekly_json": json.dumps(weekly),
        },
    )


@login_required
@role_required(Role.ADMIN)
def settings_view(request):
    settings_obj = SystemSettings.get_solo()
    if request.method == "POST":
        form = SystemSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated.")
            return redirect("dashboard:settings")
    else:
        form = SystemSettingsForm(instance=settings_obj)
    return render(request, "dashboard/settings.html", {"form": form})
