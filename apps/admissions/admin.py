from django.contrib import admin

from apps.admissions.models import AdmissionApplication, AdmissionStageHistory, CounselingAppointment


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = ("lead", "course", "status", "started_at", "confirmed_at")
    list_filter = ("status",)


@admin.register(AdmissionStageHistory)
class AdmissionStageHistoryAdmin(admin.ModelAdmin):
    list_display = ("lead", "from_stage", "to_stage", "changed_by", "changed_at")
    list_filter = ("to_stage",)


@admin.register(CounselingAppointment)
class CounselingAppointmentAdmin(admin.ModelAdmin):
    list_display = ("lead", "counselor", "scheduled_at", "status")
    list_filter = ("status",)
