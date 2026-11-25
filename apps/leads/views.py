from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.permissions import can_access_lead, can_manage_leads, role_required
from apps.audit_logs.models import ActivityLog
from apps.courses.models import Course
from apps.leads import imports as import_lib
from apps.leads.forms import LeadImportUploadForm
from apps.leads.models import LeadImportBatch, LeadPriority, LeadStage, StudentLead


@login_required
def lead_list(request):
    leads = StudentLead.objects.select_related("interested_course", "current_owner").filter(is_archived=False)

    if request.user.role == Role.TELECALLER:
        leads = leads.filter(current_owner=request.user)

    q = request.GET.get("q", "").strip()
    if q:
        leads = leads.filter(
            Q(student_name__icontains=q)
            | Q(student_phone__icontains=q)
            | Q(parent_phone__icontains=q)
            | Q(email__icontains=q)
        )
    stage = request.GET.get("stage")
    if stage:
        leads = leads.filter(stage=stage)
    priority = request.GET.get("priority")
    if priority:
        leads = leads.filter(priority=priority)
    course_id = request.GET.get("course")
    if course_id:
        leads = leads.filter(interested_course_id=course_id)
    if request.GET.get("unassigned_only"):
        leads = leads.filter(current_owner__isnull=True)

    sort = request.GET.get("sort", "-created_at")
    if sort in {"-created_at", "created_at", "student_name", "-next_follow_up_at", "priority"}:
        leads = leads.order_by(sort)

    paginator = Paginator(leads, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "leads/list.html",
        {
            "page_obj": page_obj,
            "stages": LeadStage.choices,
            "priorities": LeadPriority.choices,
            "courses": Course.objects.filter(is_active=True),
            "total_count": leads.count(),
        },
    )


@login_required
def lead_detail(request, pk):
    lead = get_object_or_404(
        StudentLead.objects.select_related("interested_course", "current_owner", "academic_year", "campaign"),
        pk=pk,
    )
    if not can_access_lead(request.user, lead):
        raise PermissionDenied("You do not have access to this lead.")

    call_attempts = lead.call_attempts.select_related("telecaller", "outcome").all()
    follow_ups = lead.follow_ups.select_related("assigned_to").all()
    stage_history = lead.stage_history.select_related("changed_by").all()
    assignment_history = lead.assignment_history.select_related("telecaller", "assigned_by").all()

    tab = request.GET.get("tab", "overview")

    return render(
        request,
        "leads/detail.html",
        {
            "lead": lead,
            "call_attempts": call_attempts,
            "follow_ups": follow_ups,
            "stage_history": stage_history,
            "assignment_history": assignment_history,
            "tab": tab,
        },
    )


@login_required
@role_required(Role.ADMIN)
def import_start(request):
    if request.method == "POST":
        form = LeadImportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            batch = LeadImportBatch.objects.create(
                uploaded_by=request.user,
                original_filename=form.cleaned_data["file"].name,
                stored_file=form.cleaned_data["file"],
                lead_source=form.cleaned_data.get("lead_source"),
                campaign=form.cleaned_data.get("campaign"),
            )
            return redirect("leads:import_preview", batch_id=batch.pk)
    else:
        form = LeadImportUploadForm()
    recent_batches = LeadImportBatch.objects.select_related("uploaded_by")[:10]
    return render(request, "leads/import_start.html", {"form": form, "recent_batches": recent_batches})


@login_required
@role_required(Role.ADMIN)
def import_preview(request, batch_id):
    batch = get_object_or_404(LeadImportBatch, pk=batch_id)
    headers, raw_rows = import_lib.read_rows(batch.stored_file)

    if request.method == "POST":
        column_mapping = {header: request.POST.get(f"map_{i}", "") for i, header in enumerate(headers)}
        batch.column_mapping = column_mapping
        batch.save(update_fields=["column_mapping"])
        return redirect("leads:import_summary", batch_id=batch.pk)

    guessed_mapping = import_lib.guess_column_mapping(headers)
    columns = [
        {"index": i, "header": header, "guess": guessed_mapping.get(header, "")}
        for i, header in enumerate(headers)
    ]
    preview_rows = [[row.get(header, "") for header in headers] for row in raw_rows[:10]]

    return render(
        request,
        "leads/import_preview.html",
        {
            "batch": batch,
            "columns": columns,
            "preview_rows": preview_rows,
            "target_fields": import_lib.TARGET_FIELDS,
            "total_rows": len(raw_rows),
        },
    )


@login_required
@role_required(Role.ADMIN)
def import_summary(request, batch_id):
    batch = get_object_or_404(LeadImportBatch, pk=batch_id)
    headers, raw_rows = import_lib.read_rows(batch.stored_file)
    validated = import_lib.validate_rows(raw_rows, batch.column_mapping)
    summary = import_lib.summarize(validated)

    batch.total_rows = summary["total_rows"]
    batch.valid_rows = summary["valid_rows"]
    batch.invalid_rows = summary["invalid_rows"]
    batch.duplicate_rows = summary["duplicate_rows"]
    batch.new_leads_count = summary["new_leads_count"]
    batch.error_report = [
        {"row": i + 1, "errors": r["errors"]} for i, r in enumerate(validated) if r["errors"]
    ][:200]
    batch.status = LeadImportBatch.Status.PREVIEWED
    batch.save()

    if request.method == "POST":
        created = import_lib.commit_rows(
            validated,
            batch=batch,
            created_by=request.user,
            lead_source=batch.lead_source,
            campaign=batch.campaign,
        )
        batch.status = LeadImportBatch.Status.COMPLETED
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "completed_at"])
        ActivityLog.log(
            request.user, "import_leads", target=batch,
            description=f"Imported {created} new leads from {batch.original_filename}",
        )
        messages.success(request, f"Import complete: {created} new leads added.")
        return redirect("leads:import_report", batch_id=batch.pk)

    return render(request, "leads/import_summary.html", {"batch": batch, "summary": summary})


@login_required
@role_required(Role.ADMIN)
def import_report(request, batch_id):
    batch = get_object_or_404(LeadImportBatch, pk=batch_id)
    return render(request, "leads/import_report.html", {"batch": batch})
