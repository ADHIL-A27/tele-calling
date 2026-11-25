from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    """Generic audit trail entry. target_type/target_id let us point at any
    model (lead, assignment, application, user) without a hard FK coupling."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="activity_logs"
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.actor} {self.action} {self.target_type}:{self.target_id}"

    @classmethod
    def log(cls, actor, action, target=None, description="", metadata=None):
        target_type = target.__class__.__name__ if target is not None else ""
        target_id = getattr(target, "pk", None)
        return cls.objects.create(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
            metadata=metadata or {},
        )
