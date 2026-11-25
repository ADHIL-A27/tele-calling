from django.conf import settings
from django.db import models


class OutcomeCategory(models.TextChoices):
    POSITIVE = "positive", "Positive"
    NEUTRAL = "neutral", "Neutral"
    NEGATIVE = "negative", "Negative"
    FOLLOW_UP = "follow_up", "Needs Follow-up"


class CallOutcome(models.Model):
    """Admin-manageable list of call status / outcome options."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    category = models.CharField(max_length=15, choices=OutcomeCategory.choices, default=OutcomeCategory.NEUTRAL)
    requires_follow_up = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


DEFAULT_CALL_OUTCOMES = [
    ("Not Called", "not-called", OutcomeCategory.NEUTRAL, False),
    ("Connected", "connected", OutcomeCategory.NEUTRAL, False),
    ("Interested", "interested", OutcomeCategory.POSITIVE, True),
    ("Very Interested", "very-interested", OutcomeCategory.POSITIVE, True),
    ("Not Interested", "not-interested", OutcomeCategory.NEGATIVE, False),
    ("No Answer", "no-answer", OutcomeCategory.NEUTRAL, True),
    ("Busy", "busy", OutcomeCategory.NEUTRAL, True),
    ("Switched Off", "switched-off", OutcomeCategory.NEUTRAL, True),
    ("Unreachable", "unreachable", OutcomeCategory.NEUTRAL, True),
    ("Wrong Number", "wrong-number", OutcomeCategory.NEGATIVE, False),
    ("Callback Requested", "callback-requested", OutcomeCategory.FOLLOW_UP, True),
    ("Parent Contact Required", "parent-contact-required", OutcomeCategory.FOLLOW_UP, True),
    ("Course Details Requested", "course-details-requested", OutcomeCategory.FOLLOW_UP, True),
    ("Already Joined Elsewhere", "already-joined-elsewhere", OutcomeCategory.NEGATIVE, False),
    ("Admission in Progress", "admission-in-progress", OutcomeCategory.POSITIVE, True),
    ("Do Not Call", "do-not-call", OutcomeCategory.NEGATIVE, False),
]


class CallAttempt(models.Model):
    lead = models.ForeignKey("leads.StudentLead", on_delete=models.CASCADE, related_name="call_attempts")
    telecaller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="call_attempts"
    )
    outcome = models.ForeignKey(
        CallOutcome, null=True, blank=True, on_delete=models.SET_NULL, related_name="call_attempts"
    )
    call_date = models.DateField()
    call_time = models.TimeField()
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "-created_at"]),
            models.Index(fields=["telecaller", "call_date"]),
            models.Index(fields=["outcome"]),
        ]

    def __str__(self):
        return f"Call to {self.lead} by {self.telecaller} on {self.call_date}"
