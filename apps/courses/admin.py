from django.contrib import admin

from apps.courses.models import AcademicSession, Branch, College, Course


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "phone_number", "email", "is_active")
    search_fields = ("name", "code")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "college", "code", "city", "is_active")
    list_filter = ("college", "is_active")


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current")
    list_filter = ("is_current",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "college", "academic_session", "total_seats", "available_seats", "is_active")
    list_filter = ("college", "academic_session", "is_active")
    search_fields = ("name", "code")
