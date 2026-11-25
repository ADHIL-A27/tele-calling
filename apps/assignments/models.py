from django.conf import settings
from django.db import models


class AssignmentMethod(models.TextChoices):
    MANUAL = "manual", "Manual"
    BULK = "bulk", "Bulk"
    EQUAL_DISTRIBUTION = "equal_distribution", "Equal Distribution"
    ROUND_ROBIN = "round_robin", "Round Robin"
    CAPACITY_BASED = "capacity_based", "Capacity Based"
    COURSE_BASED = "course_based", "Course Based"
    REASSIGNMENT = "reassignment", "Reassignment"


class LeadAssignment(models.Model):
    """One row per assignment event. Only one row per lead has is_active=True
    at any time, which represents the current owner. Reassigning a lead
    deactivates the previous row and creates a new one, preserving full history."""

    lead = models.ForeignKey(
        "leads.StudentLead", on_delete=models.CASCADE, related_name="assignment_history"
    )
    telecaller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_leads"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assignments_made"
    )
    method = models.CharField(max_length=25, choices=AssignmentMethod.choices, default=AssignmentMethod.MANUAL)
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    reassigned_from = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reassignments_lost",
    )
    batch = models.ForeignKey(
        "AssignmentBatch", null=True, blank=True, on_delete=models.SET_NULL, related_name="assignments"
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["lead", "is_active"]),
            models.Index(fields=["telecaller", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["lead"],
                condition=models.Q(is_active=True),
                name="unique_active_assignment_per_lead",
            )
        ]

    def __str__(self):
        return f"{self.lead} -> {self.telecaller} ({'active' if self.is_active else 'past'})"


class AssignmentBatch(models.Model):
    """Groups a set of LeadAssignment rows created together so the admin
    assignment screen can show/undo a single bulk operation."""

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assignment_batches"
    )
    method = models.CharField(max_length=25, choices=AssignmentMethod.choices)
    lead_count = models.PositiveIntegerField(default=0)
    telecaller_count = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch #{self.pk} ({self.get_method_display()}) - {self.lead_count} leads"
