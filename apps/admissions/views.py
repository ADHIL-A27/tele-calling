from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from apps.accounts.models import Role
from apps.accounts.permissions import MANAGEMENT_ROLES
from apps.admissions.models import AdmissionStageHistory
from apps.audit_logs.models import ActivityLog
from apps.leads.models import LeadStage, StudentLead
from apps.notifications.models import Notification, NotificationType

PIPELINE_COLUMNS = [
    (LeadStage.NEW, "New Lead"),
    (LeadStage.CONTACTED, "Contacted"),
    (LeadStage.INTERESTED, "Interested"),
    (LeadStage.COUNSELING_SCHEDULED, "Counseling Scheduled"),
    (LeadStage.COUNSELING_COMPLETED, "Counseling Completed"),
    (LeadStage.APPLICATION_STARTED, "Application Started"),
    (LeadStage.APPLICATION_SUBMITTED, "Application Submitted"),
    (LeadStage.DOCUMENTS_VERIFIED, "Documents Verified"),
    (LeadStage.ADMISSION_CONFIRMED, "Admission Confirmed"),
    (LeadStage.ENROLLED, "Enrolled"),
]


def _can_move_stage(user):
    return user.role in MANAGEMENT_ROLES


def _board_context(request):
    leads = StudentLead.objects.filter(is_archived=False).select_related("interested_course", "current_owner")
    if request.user.role == Role.TELECALLER:
        leads = leads.filter(current_owner=request.user)

    columns = []
    for stage, label in PIPELINE_COLUMNS:
        columns.append({"stage": stage, "label": label, "leads": leads.filter(stage=stage)})
    return {"columns": columns, "can_move": _can_move_stage(request.user)}


@login_required
def pipeline(request):
    return render(request, "admissions/pipeline.html", _board_context(request))


@login_required
def pipeline_board_partial(request):
    return render(request, "admissions/_kanban_board.html", _board_context(request))


@login_required
def move_stage(request, pk):
    if not _can_move_stage(request.user):
        raise PermissionDenied("You are not authorized to move admission stages.")

    lead = get_object_or_404(StudentLead, pk=pk)
    new_stage = request.POST.get("stage")
    valid_stages = {s.value for s in LeadStage}
    if request.method == "POST" and new_stage in valid_stages and new_stage != lead.stage:
        old_stage = lead.stage
        lead.stage = new_stage
        lead.save(update_fields=["stage", "updated_at"])

        AdmissionStageHistory.objects.create(
            lead=lead, from_stage=old_stage, to_stage=new_stage, changed_by=request.user
        )
        ActivityLog.log(request.user, "move_stage", target=lead, description=f"{old_stage} -> {new_stage}")

        if lead.current_owner and new_stage == LeadStage.APPLICATION_SUBMITTED:
            Notification.objects.create(
                recipient=lead.current_owner,
                notification_type=NotificationType.APPLICATION_SUBMITTED,
                title="Application submitted",
                message=f"{lead.student_name}'s application has been submitted.",
                link=f"/leads/{lead.pk}/",
            )
        elif lead.current_owner and new_stage == LeadStage.ADMISSION_CONFIRMED:
            Notification.objects.create(
                recipient=lead.current_owner,
                notification_type=NotificationType.ADMISSION_CONFIRMED,
                title="Admission confirmed!",
                message=f"{lead.student_name}'s admission has been confirmed.",
                link=f"/leads/{lead.pk}/",
            )

    return render(request, "admissions/_kanban_board.html", _board_context(request))
