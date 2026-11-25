from django.conf import settings
from django.db import models
from django.utils import timezone


class FollowUpPriority(models.TextChoices):
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"


class FollowUpStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    RESCHEDULED = "rescheduled", "Rescheduled"
    CANCELLED = "cancelled", "Cancelled"


class FollowUp(models.Model):
    lead = models.ForeignKey("leads.StudentLead", on_delete=models.CASCADE, related_name="follow_ups")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follow_ups"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="follow_ups_created"
    )
    scheduled_at = models.DateTimeField(db_index=True)
    reason = models.CharField(max_length=255, blank=True)
    priority = models.CharField(max_length=10, choices=FollowUpPriority.choices, default=FollowUpPriority.MEDIUM)
    status = models.CharField(max_length=15, choices=FollowUpStatus.choices, default=FollowUpStatus.PENDING)
    related_call = models.ForeignKey(
        "telecalling.CallAttempt", null=True, blank=True, on_delete=models.SET_NULL, related_name="follow_ups"
    )
    reminder_sent = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    rescheduled_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reschedules"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["assigned_to", "status", "scheduled_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Follow-up for {self.lead} at {self.scheduled_at}"

    @property
    def is_overdue(self):
        return self.status == FollowUpStatus.PENDING and self.scheduled_at < timezone.now()
