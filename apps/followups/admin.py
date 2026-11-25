from django.contrib import admin

from apps.followups.models import FollowUp


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ("lead", "assigned_to", "scheduled_at", "priority", "status")
    list_filter = ("status", "priority")
    search_fields = ("lead__student_name", "assigned_to__username")
