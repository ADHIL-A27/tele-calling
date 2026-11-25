from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.permissions import MANAGEMENT_ROLES, role_required
from apps.admissions.models import AdmissionApplication
from apps.courses.models import Course
from apps.followups.models import FollowUp
from apps.leads.models import StudentLead
from apps.reports.exporters import export_csv, export_xlsx
from apps.telecalling.models import CallAttempt

REPORT_TYPES = [
    ("all_leads", "All Student Leads"),
    ("assigned_leads", "Assigned Leads"),
    ("unassigned_leads", "Unassigned Leads"),
    ("daily_calls", "Daily Call Report"),
    ("employee_performance", "Employee Performance Report"),
    ("interested", "Interested Student List"),
    ("followups", "Follow-up Report"),
    ("admissions", "Admission Report"),
    ("course_wise", "Course-wise Enquiry Report"),
]


@login_required
@role_required(*MANAGEMENT_ROLES)
def index(request):
    return render(request, "reports/index.html", {"report_types": REPORT_TYPES})


def _lead_rows(qs):
    headers = ["Student Name", "Phone", "Parent Name", "Parent Phone", "Course", "Stage", "Priority", "Owner", "Created"]
    rows = [
        [
            l.student_name, l.student_phone, l.parent_name, l.parent_phone,
            str(l.interested_course or ""), l.get_stage_display(), l.get_priority_display(),
            str(l.current_owner or "Unassigned"), l.created_at.strftime("%Y-%m-%d"),
        ]
        for l in qs
    ]
    return headers, rows


@login_required
@role_required(*MANAGEMENT_ROLES)
def export_report(request, report_key):
    fmt = request.GET.get("format", "xlsx")
    exporter = export_xlsx if fmt == "xlsx" else export_csv
    stamp = timezone.now().strftime("%Y%m%d_%H%M")

    if report_key == "all_leads":
        headers, rows = _lead_rows(StudentLead.objects.filter(is_archived=False).select_related("interested_course", "current_owner"))
    elif report_key == "assigned_leads":
        headers, rows = _lead_rows(StudentLead.objects.filter(current_owner__isnull=False).select_related("interested_course", "current_owner"))
    elif report_key == "unassigned_leads":
        headers, rows = _lead_rows(StudentLead.objects.filter(current_owner__isnull=True))
    elif report_key == "interested":
        headers, rows = _lead_rows(
            StudentLead.objects.filter(stage__in=["interested", "counseling_scheduled", "counseling_completed"])
        )
    elif report_key == "daily_calls":
        headers = ["Date", "Time", "Telecaller", "Student", "Outcome", "Duration (s)", "Remarks"]
        calls = CallAttempt.objects.filter(call_date=timezone.now().date()).select_related("telecaller", "lead", "outcome")
        rows = [
            [c.call_date, c.call_time, str(c.telecaller), c.lead.student_name, str(c.outcome or ""), c.duration_seconds or "", c.remarks]
            for c in calls
        ]
    elif report_key == "employee_performance":
        from apps.accounts.models import CustomUser

        headers = ["Telecaller", "Total Calls", "Unique Leads", "Interested", "Admissions Confirmed"]
        rows = []
        for t in CustomUser.objects.filter(role=Role.TELECALLER):
            calls = CallAttempt.objects.filter(telecaller=t)
            rows.append(
                [
                    str(t),
                    calls.count(),
                    calls.values("lead_id").distinct().count(),
                    StudentLead.objects.filter(current_owner=t, stage="interested").count(),
                    StudentLead.objects.filter(current_owner=t, stage="admission_confirmed").count(),
                ]
            )
    elif report_key == "followups":
        headers = ["Student", "Assigned To", "Scheduled", "Reason", "Priority", "Status"]
        rows = [
            [f.lead.student_name, str(f.assigned_to), f.scheduled_at.strftime("%Y-%m-%d %H:%M"), f.reason, f.get_priority_display(), f.get_status_display()]
            for f in FollowUp.objects.select_related("lead", "assigned_to")
        ]
    elif report_key == "admissions":
        headers = ["Student", "Course", "Status", "Started", "Confirmed"]
        rows = [
            [a.lead.student_name, str(a.course or ""), a.get_status_display(), a.started_at.strftime("%Y-%m-%d"), a.confirmed_at.strftime("%Y-%m-%d") if a.confirmed_at else ""]
            for a in AdmissionApplication.objects.select_related("lead", "course")
        ]
    elif report_key == "course_wise":
        headers = ["Course", "Total Enquiries", "Interested", "Confirmed Admissions"]
        rows = [
            [
                c.name,
                StudentLead.objects.filter(interested_course=c).count(),
                StudentLead.objects.filter(interested_course=c, stage="interested").count(),
                StudentLead.objects.filter(interested_course=c, stage="admission_confirmed").count(),
            ]
            for c in Course.objects.filter(is_active=True)
        ]
    else:
        headers, rows = ["Error"], [["Unknown report type"]]

    return exporter(f"{report_key}_{stamp}", headers, rows)
