import re

from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator


INDIAN_MOBILE_REGEX = re.compile(r"^[6-9]\d{9}$")

phone_validator = RegexValidator(
    regex=r"^\+?\d{7,15}$",
    message="Enter a valid phone number (7-15 digits, optional + prefix).",
)


def normalize_phone_number(raw_value: str) -> str:
    """Normalize a phone number: strip non-digits, keep leading + if present,
    collapse Indian numbers (+91 / 91 prefix) to a plain 10-digit form so
    duplicates with differing prefixes are detected correctly."""
    if not raw_value:
        return ""
    value = raw_value.strip()
    has_plus = value.startswith("+")
    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""
    if digits.startswith("91") and len(digits) == 12 and INDIAN_MOBILE_REGEX.match(digits[2:]):
        return digits[2:]
    if digits.startswith("0") and len(digits) == 11 and INDIAN_MOBILE_REGEX.match(digits[1:]):
        return digits[1:]
    if len(digits) == 10 and INDIAN_MOBILE_REGEX.match(digits):
        return digits
    # Preserve other international numbers as-is (with + if it was present)
    return f"+{digits}" if has_plus else digits


class LeadSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Campaign(models.Model):
    name = models.CharField(max_length=150)
    college = models.ForeignKey(
        "courses.College", null=True, blank=True, on_delete=models.SET_NULL, related_name="campaigns"
    )
    academic_session = models.ForeignKey(
        "courses.AcademicSession", null=True, blank=True, on_delete=models.SET_NULL, related_name="campaigns"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class LeadPriority(models.TextChoices):
    HOT = "hot", "Hot"
    WARM = "warm", "Warm"
    COLD = "cold", "Cold"


class LeadStage(models.TextChoices):
    NEW = "new", "New Lead"
    CONTACTED = "contacted", "Contacted"
    INTERESTED = "interested", "Interested"
    COUNSELING_SCHEDULED = "counseling_scheduled", "Counseling Scheduled"
    COUNSELING_COMPLETED = "counseling_completed", "Counseling Completed"
    APPLICATION_STARTED = "application_started", "Application Started"
    APPLICATION_SUBMITTED = "application_submitted", "Application Submitted"
    DOCUMENTS_VERIFIED = "documents_verified", "Documents Verified"
    ADMISSION_CONFIRMED = "admission_confirmed", "Admission Confirmed"
    ENROLLED = "enrolled", "Enrolled"
    LOST = "lost", "Lost"
    NOT_INTERESTED = "not_interested", "Not Interested"
    DEFERRED = "deferred", "Deferred"
    DO_NOT_CONTACT = "do_not_contact", "Do Not Contact"


ACTIVE_PIPELINE_STAGES = [
    LeadStage.NEW,
    LeadStage.CONTACTED,
    LeadStage.INTERESTED,
    LeadStage.COUNSELING_SCHEDULED,
    LeadStage.COUNSELING_COMPLETED,
    LeadStage.APPLICATION_STARTED,
    LeadStage.APPLICATION_SUBMITTED,
    LeadStage.DOCUMENTS_VERIFIED,
    LeadStage.ADMISSION_CONFIRMED,
    LeadStage.ENROLLED,
]

EXIT_STAGES = [LeadStage.LOST, LeadStage.NOT_INTERESTED, LeadStage.DEFERRED, LeadStage.DO_NOT_CONTACT]


class LeadImportBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PREVIEWED = "previewed", "Previewed"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="import_batches"
    )
    original_filename = models.CharField(max_length=255)
    stored_file = models.FileField(upload_to="imports/", blank=True, null=True)
    column_mapping = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    new_leads_count = models.PositiveIntegerField(default=0)
    error_report = models.JSONField(default=list, blank=True)
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="import_batches"
    )
    lead_source = models.ForeignKey(
        LeadSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="import_batches"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch #{self.pk} - {self.original_filename}"


class StudentLead(models.Model):
    student_name = models.CharField(max_length=150)
    student_phone = models.CharField(max_length=20, validators=[phone_validator])
    student_phone_normalized = models.CharField(max_length=20, db_index=True)
    parent_name = models.CharField(max_length=150, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    parent_phone_normalized = models.CharField(max_length=20, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    district = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, blank=True)
    qualification = models.CharField(max_length=150, blank=True)
    previous_school = models.CharField(max_length=200, blank=True)
    interested_course = models.ForeignKey(
        "courses.Course", null=True, blank=True, on_delete=models.SET_NULL, related_name="interested_leads"
    )
    lead_source = models.ForeignKey(
        LeadSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads"
    )
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads"
    )
    academic_year = models.ForeignKey(
        "courses.AcademicSession", null=True, blank=True, on_delete=models.SET_NULL, related_name="leads"
    )
    remarks = models.TextField(blank=True)

    stage = models.CharField(max_length=30, choices=LeadStage.choices, default=LeadStage.NEW)
    priority = models.CharField(max_length=10, choices=LeadPriority.choices, default=LeadPriority.WARM)

    current_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_leads",
        help_text="Denormalized pointer to the telecaller with the active assignment.",
    )
    is_unassigned = models.BooleanField(default=True, db_index=True)

    do_not_call = models.BooleanField(default=False)
    opted_out = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    import_batch = models.ForeignKey(
        LeadImportBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads"
    )

    last_call_at = models.DateTimeField(null=True, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_leads"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["stage"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["current_owner", "stage"]),
            models.Index(fields=["next_follow_up_at"]),
            models.Index(fields=["student_phone_normalized"]),
        ]

    def __str__(self):
        return f"{self.student_name} ({self.student_phone})"

    def save(self, *args, **kwargs):
        self.student_phone_normalized = normalize_phone_number(self.student_phone)
        if self.parent_phone:
            self.parent_phone_normalized = normalize_phone_number(self.parent_phone)
        self.is_unassigned = self.current_owner_id is None
        super().save(*args, **kwargs)

    @property
    def is_active_pipeline(self):
        return self.stage in ACTIVE_PIPELINE_STAGES


class LeadPhone(models.Model):
    """Secondary / alternate phone numbers for a lead, used for duplicate detection
    across student and parent numbers from different import batches."""

    class PhoneType(models.TextChoices):
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"
        ALTERNATE = "alternate", "Alternate"

    lead = models.ForeignKey(StudentLead, on_delete=models.CASCADE, related_name="phones")
    phone_number = models.CharField(max_length=20, validators=[phone_validator])
    phone_number_normalized = models.CharField(max_length=20, db_index=True)
    phone_type = models.CharField(max_length=15, choices=PhoneType.choices, default=PhoneType.ALTERNATE)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["phone_number_normalized"])]

    def __str__(self):
        return f"{self.phone_number} ({self.get_phone_type_display()})"

    def save(self, *args, **kwargs):
        self.phone_number_normalized = normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)
