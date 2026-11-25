from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    TELECALLER = "telecaller", "Telecaller"


ROLE_GROUP_NAMES = {
    Role.ADMIN: "Admin",
    Role.TELECALLER: "Telecaller",
}


class CustomUser(AbstractUser):
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.TELECALLER)
    phone_number = models.CharField(max_length=20, blank=True)
    college = models.ForeignKey(
        "courses.College", null=True, blank=True, on_delete=models.SET_NULL, related_name="users"
    )
    branch = models.ForeignKey(
        "courses.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="users"
    )
    is_active_employee = models.BooleanField(default=True)
    date_joined_company = models.DateField(null=True, blank=True)
    reporting_manager = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="team_members"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["is_active_employee"]),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_telecaller(self):
        return self.role == Role.TELECALLER

    def get_absolute_url(self):
        return reverse("accounts:profile", args=[self.pk])


class TelecallerProfile(models.Model):
    """Extended profile for users whose role is telecaller."""

    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="telecaller_profile"
    )
    employee_code = models.CharField(max_length=32, unique=True, blank=True, null=True)
    team_name = models.CharField(max_length=100, blank=True)
    manager = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_telecallers"
    )
    max_active_leads = models.PositiveIntegerField(default=200)
    is_accepting_leads = models.BooleanField(default=True)
    shift_start = models.TimeField(null=True, blank=True)
    shift_end = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["is_accepting_leads"])]

    def __str__(self):
        return f"Profile: {self.user}"

    @property
    def active_lead_count(self):
        from apps.assignments.models import LeadAssignment

        return LeadAssignment.objects.filter(telecaller=self.user, is_active=True).count()
