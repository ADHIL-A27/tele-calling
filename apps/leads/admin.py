from django.contrib import admin

from apps.leads.models import Campaign, LeadImportBatch, LeadPhone, LeadSource, StudentLead


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "college", "academic_session", "is_active")
    list_filter = ("college", "is_active")
    search_fields = ("name",)


@admin.register(LeadImportBatch)
class LeadImportBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "uploaded_by", "status", "total_rows", "new_leads_count", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at", "completed_at")


class LeadPhoneInline(admin.TabularInline):
    model = LeadPhone
    extra = 0


@admin.register(StudentLead)
class StudentLeadAdmin(admin.ModelAdmin):
    list_display = ("student_name", "student_phone", "stage", "priority", "current_owner", "created_at")
    list_filter = ("stage", "priority", "is_archived", "do_not_call")
    search_fields = ("student_name", "student_phone", "parent_phone", "email")
    inlines = [LeadPhoneInline]
    autocomplete_fields = ["interested_course", "current_owner", "lead_source", "campaign"]
