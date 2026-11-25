from django.contrib import admin

from apps.audit_logs.models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "target_type", "target_id", "created_at")
    list_filter = ("action", "target_type")
    search_fields = ("actor__username", "description")
    readonly_fields = [f.name for f in ActivityLog._meta.fields]
