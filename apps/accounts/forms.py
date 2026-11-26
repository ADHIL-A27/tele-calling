from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.accounts.models import CustomUser, Role, TelecallerProfile
from apps.courses.models import Branch, College

CLAY_INPUT_CLASS = "clay-input"


class ClayAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": CLAY_INPUT_CLASS, "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": CLAY_INPUT_CLASS}))


class StaffUserCreationForm(UserCreationForm):
    """Create staff accounts for the application's single college."""

    employee_code = forms.CharField(required=False)
    team_name = forms.CharField(required=False)
    max_active_leads = forms.IntegerField(required=False, initial=200, min_value=1)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "branch",
            "reporting_manager",
        )
        widgets = {
            "username": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "first_name": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "last_name": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": CLAY_INPUT_CLASS}),
            "phone_number": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "role": forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
            "branch": forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
            "reporting_manager": forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.single_college = College.objects.filter(is_active=True).order_by("pk").first()
        self.fields["branch"].queryset = (
            Branch.objects.filter(college=self.single_college, is_active=True)
            if self.single_college
            else Branch.objects.none()
        )
        self.fields["password1"].widget.attrs["class"] = CLAY_INPUT_CLASS
        self.fields["password2"].widget.attrs["class"] = CLAY_INPUT_CLASS

    def save(self, commit=True):
        user = super().save(commit=False)
        user.college = self.single_college
        if commit:
            user.save()
            self.save_m2m()
            if user.role == Role.TELECALLER:
                TelecallerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "employee_code": self.cleaned_data.get("employee_code") or None,
                        "team_name": self.cleaned_data.get("team_name") or "",
                        "max_active_leads": self.cleaned_data.get("max_active_leads") or 200,
                    },
                )
            self._assign_group(user)
        return user

    @staticmethod
    def _assign_group(user):
        from django.contrib.auth.models import Group

        from apps.accounts.models import ROLE_GROUP_NAMES

        group_name = ROLE_GROUP_NAMES.get(user.role)
        if group_name:
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone_number")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "last_name": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": CLAY_INPUT_CLASS}),
            "phone_number": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
        }
