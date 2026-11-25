from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.accounts.models import CustomUser, Role, TelecallerProfile

CLAY_INPUT_CLASS = "clay-input"


class ClayAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": CLAY_INPUT_CLASS, "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": CLAY_INPUT_CLASS}))


class StaffUserCreationForm(UserCreationForm):
    """Used by College Admin / Telecalling Manager to create telecaller
    and counselor accounts."""

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
            "college",
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
            "college": forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
            "branch": forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
            "reporting_manager": forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs["class"] = CLAY_INPUT_CLASS
        self.fields["password2"].widget.attrs["class"] = CLAY_INPUT_CLASS

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and user.role == Role.TELECALLER:
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
