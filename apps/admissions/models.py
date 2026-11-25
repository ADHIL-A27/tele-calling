from django.conf import settings
from django.db import models

from apps.leads.models import LeadStage


class ApplicationStatus(models.TextChoices):
    STARTED = "started", "Started"
    SUBMITTED = "submitted", "Submitted"
    DOCUMENTS_VERIFIED = "documents_verified", "Documents Verified"
    CONFIRMED = "confirmed", "Confirmed"
    ENROLLED = "enrolled", "Enrolled"
    REJECTED = "rejected", "Rejected"


class AdmissionApplication(models.Model):
    lead = models.OneToOneField(
        "leads.StudentLead", on_delete=models.CASCADE, related_name="admission_application"
    )
    course = models.ForeignKey(
        "courses.Course", null=True, blank=True, on_delete=models.SET_NULL, related_name="applications"
    )
    status = models.CharField(max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.STARTED)
    application_number = models.CharField(max_length=40, blank=True, unique=False)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    documents_verified_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    enrolled_at = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="handled_applications"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Application for {self.lead} ({self.get_status_display()})"


class AdmissionStageHistory(models.Model):
    lead = models.ForeignKey(
        "leads.StudentLead", on_delete=models.CASCADE, related_name="stage_history"
    )
    from_stage = models.CharField(max_length=30, choices=LeadStage.choices, blank=True)
    to_stage = models.CharField(max_length=30, choices=LeadStage.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="stage_changes"
    )
    notes = models.CharField(max_length=255, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [models.Index(fields=["lead", "-changed_at"])]

    def __str__(self):
        return f"{self.lead} : {self.from_stage} -> {self.to_stage}"


class CounselingAppointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No Show"
        CANCELLED = "cancelled", "Cancelled"
        RESCHEDULED = "rescheduled", "Rescheduled"

    lead = models.ForeignKey(
        "leads.StudentLead", on_delete=models.CASCADE, related_name="counseling_appointments"
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="counseling_appointments"
    )
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    outcome_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]
        indexes = [models.Index(fields=["counselor", "status", "scheduled_at"])]

    def __str__(self):
        return f"Counseling: {self.lead} on {self.scheduled_at}"
