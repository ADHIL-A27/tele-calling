from django.contrib import admin

from apps.telecalling.models import CallAttempt, CallOutcome


@admin.register(CallOutcome)
class CallOutcomeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "requires_follow_up", "is_active", "display_order")
    list_editable = ("display_order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CallAttempt)
class CallAttemptAdmin(admin.ModelAdmin):
    list_display = ("lead", "telecaller", "outcome", "call_date", "call_time")
    list_filter = ("outcome", "call_date")
    search_fields = ("lead__student_name", "telecaller__username")
