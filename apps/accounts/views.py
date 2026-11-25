from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from apps.accounts.forms import ClayAuthenticationForm, ProfileUpdateForm, StaffUserCreationForm
from apps.accounts.models import CustomUser, Role
from apps.accounts.permissions import can_assign_leads, role_required
from apps.audit_logs.models import ActivityLog


class ClayLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = ClayAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        ActivityLog.log(self.request.user, "login", description="User logged in.")
        return response


class ClayLogoutView(LogoutView):
    next_page = "accounts:login"


class ClayPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    success_url = reverse_lazy("accounts:password_reset_done")


@login_required
def profile(request, pk=None):
    user_obj = get_object_or_404(CustomUser, pk=pk) if pk else request.user
    if pk and user_obj != request.user and not can_assign_leads(request.user):
        user_obj = request.user
    if request.method == "POST" and user_obj == request.user:
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = ProfileUpdateForm(instance=user_obj)
    return render(request, "accounts/profile.html", {"profile_user": user_obj, "form": form})


@login_required
@role_required(Role.ADMIN)
def team_list(request):
    users = CustomUser.objects.select_related("telecaller_profile").exclude(pk=request.user.pk)
    roles = request.GET.get("role")
    if roles:
        users = users.filter(role=roles)
    return render(request, "accounts/team_list.html", {"users": users, "roles": Role.choices})


@login_required
@role_required(Role.ADMIN)
def team_create(request):
    if request.method == "POST":
        form = StaffUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ActivityLog.log(request.user, "create_user", target=user, description=f"Created user {user}")
            messages.success(request, f"User {user.username} created successfully.")
            return redirect("accounts:team_list")
    else:
        form = StaffUserCreationForm()
    return render(request, "accounts/team_form.html", {"form": form})


@login_required
@role_required(Role.ADMIN)
def team_toggle_active(request, pk):
    user_obj = get_object_or_404(CustomUser, pk=pk)
    if request.method == "POST":
        user_obj.is_active_employee = not user_obj.is_active_employee
        user_obj.is_active = user_obj.is_active_employee
        user_obj.save(update_fields=["is_active_employee", "is_active"])
        ActivityLog.log(
            request.user,
            "toggle_user_active",
            target=user_obj,
            description=f"Set {user_obj} active={user_obj.is_active_employee}",
        )
        messages.success(request, f"{user_obj.username} is now {'active' if user_obj.is_active else 'inactive'}.")
    return redirect("accounts:team_list")
