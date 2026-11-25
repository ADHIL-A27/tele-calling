from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import CustomUser, TelecallerProfile


class TelecallerProfileInline(admin.StackedInline):
    model = TelecallerProfile
    fk_name = "user"
    can_delete = False
    extra = 0


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "get_full_name", "role", "college", "branch", "is_active_employee", "is_active")
    list_filter = ("role", "college", "branch", "is_active_employee", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    inlines = [TelecallerProfileInline]
    fieldsets = UserAdmin.fieldsets + (
        (
            "CRM Profile",
            {
                "fields": (
                    "role",
                    "phone_number",
                    "college",
                    "branch",
                    "reporting_manager",
                    "is_active_employee",
                    "date_joined_company",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("CRM Profile", {"fields": ("role", "phone_number", "college", "branch")}),
    )


@admin.register(TelecallerProfile)
class TelecallerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_code", "team_name", "manager", "max_active_leads", "is_accepting_leads")
    list_filter = ("is_accepting_leads", "team_name")
    search_fields = ("user__username", "employee_code", "team_name")
