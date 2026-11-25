from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.models import CustomUser, Role
from apps.accounts.permissions import role_required
from apps.assignments import services
from apps.assignments.models import AssignmentBatch, AssignmentMethod, LeadAssignment
from apps.courses.models import Course
from apps.leads.models import StudentLead

MANAGEMENT_ROLES = (Role.ADMIN,)


@login_required
@role_required(*MANAGEMENT_ROLES)
def workspace(request):
    leads = StudentLead.objects.filter(is_archived=False).select_related("current_owner", "interested_course")
    only_unassigned = request.GET.get("unassigned", "1") == "1"
    if only_unassigned:
        leads = leads.filter(current_owner__isnull=True)

    batch_id = request.GET.get("batch")
    if batch_id:
        leads = leads.filter(import_batch_id=batch_id)

    course_id = request.GET.get("course")
    if course_id:
        leads = leads.filter(interested_course_id=course_id)

    paginator = Paginator(leads.order_by("-created_at"), 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    telecallers = list(
        CustomUser.objects.filter(role=Role.TELECALLER, is_active_employee=True).select_related(
            "telecaller_profile"
        )
    )
    for t in telecallers:
        t.active_count = LeadAssignment.objects.filter(telecaller=t, is_active=True).count()

    return render(
        request,
        "assignments/workspace.html",
        {
            "page_obj": page_obj,
            "total_available": leads.count(),
            "telecallers": telecallers,
            "courses": Course.objects.filter(is_active=True),
            "methods": AssignmentMethod.choices,
            "only_unassigned": only_unassigned,
        },
    )


@login_required
@role_required(*MANAGEMENT_ROLES)
def assign_confirm(request):
    if request.method != "POST":
        return redirect("assignments:workspace")

    lead_ids = [int(x) for x in request.POST.get("lead_ids", "").split(",") if x.strip()]
    method = request.POST.get("method")
    notes = request.POST.get("notes", "")

    if not lead_ids:
        messages.error(request, "No leads selected.")
        return redirect("assignments:workspace")

    try:
        if method == AssignmentMethod.MANUAL or method == AssignmentMethod.BULK:
            telecaller_id = request.POST.get("single_telecaller")
            telecaller = get_object_or_404(CustomUser, pk=telecaller_id, role=Role.TELECALLER)
            batch = services.assign_leads(
                lead_ids, {lid: telecaller for lid in lead_ids}, method, request.user, notes
            )
        elif method == AssignmentMethod.EQUAL_DISTRIBUTION:
            telecallers = list(CustomUser.objects.filter(pk__in=request.POST.getlist("telecallers")))
            batch = services.equal_distribution_assign(lead_ids, telecallers, request.user, notes)
        elif method == AssignmentMethod.ROUND_ROBIN:
            telecallers = list(CustomUser.objects.filter(pk__in=request.POST.getlist("telecallers")))
            batch = services.round_robin_assign(lead_ids, telecallers, request.user, notes)
        elif method == AssignmentMethod.CAPACITY_BASED:
            telecallers = list(CustomUser.objects.filter(pk__in=request.POST.getlist("telecallers")))
            batch = services.capacity_based_assign(lead_ids, telecallers, request.user, notes)
        elif method == AssignmentMethod.REASSIGNMENT:
            telecaller_id = request.POST.get("single_telecaller")
            telecaller = get_object_or_404(CustomUser, pk=telecaller_id, role=Role.TELECALLER)
            batch = services.reassign_leads(lead_ids, telecaller, request.user, notes)
        else:
            messages.error(request, "Unsupported assignment method.")
            return redirect("assignments:workspace")
    except services.AssignmentError as exc:
        messages.error(request, str(exc))
        return redirect("assignments:workspace")

    messages.success(request, f"Assigned {batch.lead_count} lead(s) to {batch.telecaller_count} telecaller(s).")
    return redirect("assignments:history")


@login_required
@role_required(*MANAGEMENT_ROLES)
def course_based_assign_view(request):
    if request.method == "POST":
        course_ids = request.POST.getlist("course_id")
        leads_by_course = {}
        for course_id in course_ids:
            telecaller_id = request.POST.get(f"telecaller_for_{course_id}")
            if not telecaller_id:
                continue
            telecaller = get_object_or_404(CustomUser, pk=telecaller_id, role=Role.TELECALLER)
            lead_ids = list(
                StudentLead.objects.filter(
                    interested_course_id=course_id, current_owner__isnull=True, is_archived=False
                ).values_list("pk", flat=True)
            )
            if lead_ids:
                leads_by_course[course_id] = (lead_ids, telecaller)
        if leads_by_course:
            batch = services.course_based_assign(leads_by_course, request.user)
            messages.success(request, f"Assigned {batch.lead_count} lead(s) across {len(leads_by_course)} course(s).")
        else:
            messages.warning(request, "No unassigned leads found for the selected courses.")
        return redirect("assignments:history")

    courses = list(Course.objects.filter(is_active=True))
    for c in courses:
        c.unassigned_count = StudentLead.objects.filter(
            interested_course=c, current_owner__isnull=True, is_archived=False
        ).count()
    telecallers = CustomUser.objects.filter(role=Role.TELECALLER, is_active_employee=True)
    return render(
        request,
        "assignments/course_based.html",
        {"courses": courses, "telecallers": telecallers},
    )


@login_required
@role_required(*MANAGEMENT_ROLES)
def history(request):
    batches = AssignmentBatch.objects.select_related("performed_by").all()
    paginator = Paginator(batches, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "assignments/history.html", {"page_obj": page_obj})
