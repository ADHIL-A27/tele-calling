from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    LEAD_ASSIGNED = "lead_assigned", "New Numbers Assigned"
    FOLLOW_UP_REMINDER = "follow_up_reminder", "Follow-up Reminder"
    FOLLOW_UP_OVERDUE = "follow_up_overdue", "Follow-up Overdue"
    NEW_INTERESTED_LEAD = "new_interested_lead", "New Interested Lead"
    LEAD_REASSIGNED = "lead_reassigned", "Lead Reassigned"
    COUNSELING_SCHEDULED = "counseling_scheduled", "Counseling Scheduled"
    APPLICATION_SUBMITTED = "application_submitted", "Application Submitted"
    ADMISSION_CONFIRMED = "admission_confirmed", "Admission Confirmed"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"
