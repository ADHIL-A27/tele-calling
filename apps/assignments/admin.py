from django.contrib import admin

from apps.assignments.models import AssignmentBatch, LeadAssignment


@admin.register(LeadAssignment)
class LeadAssignmentAdmin(admin.ModelAdmin):
    list_display = ("lead", "telecaller", "method", "is_active", "assigned_at")
    list_filter = ("method", "is_active")
    search_fields = ("lead__student_name", "telecaller__username")


@admin.register(AssignmentBatch)
class AssignmentBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "performed_by", "lead_count", "telecaller_count", "created_at")
    list_filter = ("method",)
