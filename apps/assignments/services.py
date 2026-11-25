"""Lead assignment engine: manual, bulk, equal distribution, round robin,
capacity-based, course-based assignment, and reassignment. All methods
funnel through `assign_leads`, which creates one AssignmentBatch and a
LeadAssignment row per lead inside a single atomic transaction, deactivating
any prior active assignment (preserving history) and updating the
denormalized StudentLead.current_owner pointer.
"""

from django.db import transaction
from django.utils import timezone

from apps.assignments.models import AssignmentBatch, AssignmentMethod, LeadAssignment
from apps.audit_logs.models import ActivityLog
from apps.leads.models import StudentLead
from apps.notifications.models import Notification, NotificationType


class AssignmentError(Exception):
    pass


def _deactivate_existing(lead):
    previous = LeadAssignment.objects.filter(lead=lead, is_active=True).first()
    if previous:
        previous.is_active = False
        previous.unassigned_at = timezone.now()
        previous.save(update_fields=["is_active", "unassigned_at"])
        return previous.telecaller
    return None


@transaction.atomic
def assign_leads(lead_ids, telecaller_map, method, assigned_by, notes=""):
    """telecaller_map: {lead_id: telecaller_user}. Creates the batch + rows,
    skipping leads that already have that exact active owner."""
    leads = {l.pk: l for l in StudentLead.objects.select_for_update().filter(pk__in=lead_ids)}
    batch = AssignmentBatch.objects.create(
        performed_by=assigned_by,
        method=method,
        lead_count=0,
        telecaller_count=len({t.pk for t in telecaller_map.values()}),
        notes=notes,
    )

    created = 0
    notify_map = {}
    for lead_id, telecaller in telecaller_map.items():
        lead = leads.get(lead_id)
        if not lead:
            continue
        existing_active = LeadAssignment.objects.filter(lead=lead, is_active=True).first()
        if existing_active and existing_active.telecaller_id == telecaller.pk:
            continue

        reassigned_from = _deactivate_existing(lead)

        LeadAssignment.objects.create(
            lead=lead,
            telecaller=telecaller,
            assigned_by=assigned_by,
            method=method,
            is_active=True,
            reassigned_from=reassigned_from,
            batch=batch,
            notes=notes,
        )
        lead.current_owner = telecaller
        lead.is_unassigned = False
        lead.save(update_fields=["current_owner", "is_unassigned", "updated_at"])
        created += 1
        notify_map.setdefault(telecaller.pk, {"user": telecaller, "count": 0})
        notify_map[telecaller.pk]["count"] += 1

        ActivityLog.log(
            assigned_by,
            "reassign_lead" if reassigned_from else "assign_lead",
            target=lead,
            description=f"{lead} assigned to {telecaller} via {method}",
        )

    batch.lead_count = created
    batch.save(update_fields=["lead_count"])

    for entry in notify_map.values():
        Notification.objects.create(
            recipient=entry["user"],
            notification_type=NotificationType.LEAD_ASSIGNED,
            title="New leads assigned to you",
            message=f"{entry['count']} new lead(s) have been assigned to you.",
            link="/calling/my-leads/",
        )

    return batch


def manual_assign(lead_ids, telecaller, assigned_by, notes=""):
    telecaller_map = {lid: telecaller for lid in lead_ids}
    return assign_leads(lead_ids, telecaller_map, AssignmentMethod.MANUAL, assigned_by, notes)


def bulk_assign(lead_ids, telecaller, assigned_by, notes=""):
    telecaller_map = {lid: telecaller for lid in lead_ids}
    return assign_leads(lead_ids, telecaller_map, AssignmentMethod.BULK, assigned_by, notes)


def equal_distribution_assign(lead_ids, telecallers, assigned_by, notes=""):
    if not telecallers:
        raise AssignmentError("Select at least one telecaller.")
    telecaller_map = {}
    for i, lead_id in enumerate(lead_ids):
        telecaller_map[lead_id] = telecallers[i % len(telecallers)]
    return assign_leads(lead_ids, telecaller_map, AssignmentMethod.EQUAL_DISTRIBUTION, assigned_by, notes)


def round_robin_assign(lead_ids, telecallers, assigned_by, notes=""):
    """Functionally identical distribution to equal_distribution (one at a
    time, cycling through callers) -- kept distinct so the audit trail
    records the method the admin explicitly chose."""
    if not telecallers:
        raise AssignmentError("Select at least one telecaller.")
    telecaller_map = {}
    for i, lead_id in enumerate(lead_ids):
        telecaller_map[lead_id] = telecallers[i % len(telecallers)]
    return assign_leads(lead_ids, telecaller_map, AssignmentMethod.ROUND_ROBIN, assigned_by, notes)


def capacity_based_assign(lead_ids, telecallers, assigned_by, notes=""):
    """Fill each telecaller up to their TelecallerProfile.max_active_leads
    before moving to the next, ordered by remaining capacity (most free
    capacity first)."""
    if not telecallers:
        raise AssignmentError("Select at least one telecaller.")

    capacities = []
    for t in telecallers:
        profile = getattr(t, "telecaller_profile", None)
        max_leads = profile.max_active_leads if profile else 200
        current_active = LeadAssignment.objects.filter(telecaller=t, is_active=True).count()
        remaining = max(max_leads - current_active, 0)
        capacities.append({"telecaller": t, "remaining": remaining})

    capacities.sort(key=lambda c: -c["remaining"])
    telecaller_map = {}
    idx = 0
    for lead_id in lead_ids:
        # find next caller with remaining capacity
        attempts = 0
        while capacities[idx % len(capacities)]["remaining"] <= 0 and attempts < len(capacities):
            idx += 1
            attempts += 1
        slot = capacities[idx % len(capacities)]
        if slot["remaining"] <= 0:
            break  # everyone is full
        telecaller_map[lead_id] = slot["telecaller"]
        slot["remaining"] -= 1
        idx += 1

    if not telecaller_map:
        raise AssignmentError("All selected telecallers are at full capacity.")
    return assign_leads(list(telecaller_map.keys()), telecaller_map, AssignmentMethod.CAPACITY_BASED, assigned_by, notes)


def course_based_assign(leads_by_course, assigned_by, notes=""):
    """leads_by_course: {course_id: (lead_ids, telecaller)} -- assigns each
    course's leads to the telecaller nominated for that course."""
    all_lead_ids = []
    telecaller_map = {}
    for course_id, (lead_ids, telecaller) in leads_by_course.items():
        for lid in lead_ids:
            telecaller_map[lid] = telecaller
            all_lead_ids.append(lid)
    return assign_leads(all_lead_ids, telecaller_map, AssignmentMethod.COURSE_BASED, assigned_by, notes)


def reassign_leads(lead_ids, new_telecaller, assigned_by, notes=""):
    telecaller_map = {lid: new_telecaller for lid in lead_ids}
    return assign_leads(lead_ids, telecaller_map, AssignmentMethod.REASSIGNMENT, assigned_by, notes)
