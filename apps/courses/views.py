from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.permissions import role_required
from apps.accounts.models import Role
from apps.audit_logs.models import ActivityLog
from apps.courses.forms import CourseForm
from apps.courses.models import Course


@login_required
def course_list(request):
    courses = Course.objects.select_related("college", "academic_session").all()
    return render(request, "courses/list.html", {"courses": courses})


@login_required
@role_required(Role.ADMIN)
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            ActivityLog.log(request.user, "create_course", target=course, description=f"Created course {course}")
            messages.success(request, f"Course '{course.name}' created.")
            return redirect("courses:list")
    else:
        form = CourseForm()
    return render(request, "courses/form.html", {"form": form, "mode": "Create"})


@login_required
@role_required(Role.ADMIN)
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            ActivityLog.log(request.user, "update_course", target=course, description=f"Updated course {course}")
            messages.success(request, f"Course '{course.name}' updated.")
            return redirect("courses:list")
    else:
        form = CourseForm(instance=course)
    return render(request, "courses/form.html", {"form": form, "mode": "Edit", "course": course})


@login_required
@role_required(Role.ADMIN)
def course_toggle_active(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        course.is_active = not course.is_active
        course.save(update_fields=["is_active"])
        messages.success(request, f"Course '{course.name}' is now {'active' if course.is_active else 'inactive'}.")
    return redirect("courses:list")
