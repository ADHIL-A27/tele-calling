from django.db import models


class SystemSettings(models.Model):
    """Singleton-style key/value store for CRM-wide configuration.
    Use SystemSettings.get_solo() to fetch the single row."""

    college_name = models.CharField(max_length=200, default="My College")
    default_lead_retention_days = models.PositiveIntegerField(
        default=730, help_text="Days to keep archived leads before deletion is permitted."
    )
    overdue_follow_up_grace_hours = models.PositiveIntegerField(default=1)
    enable_whatsapp_templates = models.BooleanField(default=False)
    enable_email_notifications = models.BooleanField(default=False)
    default_max_leads_per_telecaller = models.PositiveIntegerField(default=200)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
