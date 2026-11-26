from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.accounts.models import CustomUser, Role, TelecallerProfile
from apps.courses.models import College

CLAY_INPUT_CLASS = "clay-input"


class ClayAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": CLAY_INPUT_CLASS, "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": CLAY_INPUT_CLASS}))


class StaffUserCreationForm(UserCreationForm):
    """Create staff accounts for the application's single college."""

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
        )
        widgets = {
            "username": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "first_name": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "last_name": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": CLAY_INPUT_CLASS}),
            "phone_number": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.single_college = College.objects.filter(is_active=True).order_by("pk").first()
        self.fields["password1"].widget.attrs["class"] = CLAY_INPUT_CLASS
        self.fields["password2"].widget.attrs["class"] = CLAY_INPUT_CLASS

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = Role.TELECALLER
        user.college = self.single_college
        if commit:
            user.save()
            self.save_m2m()
            if user.role == Role.TELECALLER:
                TelecallerProfile.objects.get_or_create(user=user)
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
