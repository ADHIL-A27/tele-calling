from django.db import models
from django.core.validators import MinValueValidator


class College(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Branch(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    city = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("college", "code")
        ordering = ["college", "name"]

    def __str__(self):
        return f"{self.name} ({self.college.code})"


class AcademicSession(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="e.g. 2025-2026")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_current:
            AcademicSession.objects.exclude(pk=self.pk).update(is_current=False)


class Course(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name="courses")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    duration = models.CharField(max_length=50, blank=True, help_text="e.g. 3 Years")
    eligibility = models.TextField(blank=True)
    fee_details = models.CharField(max_length=200, blank=True)
    total_seats = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    available_seats = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    academic_session = models.ForeignKey(
        AcademicSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="courses"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("college", "code")
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return f"{self.name} ({self.code})"
