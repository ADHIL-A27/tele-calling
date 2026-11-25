from django.contrib import admin

from apps.dashboard.models import SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ("college_name", "updated_at")
