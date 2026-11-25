from django import forms

from apps.dashboard.models import SystemSettings

CLAY_INPUT_CLASS = "clay-input"


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = [
            "college_name",
            "default_lead_retention_days",
            "overdue_follow_up_grace_hours",
            "enable_whatsapp_templates",
            "enable_email_notifications",
            "default_max_leads_per_telecaller",
        ]
        widgets = {
            "college_name": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "default_lead_retention_days": forms.NumberInput(attrs={"class": CLAY_INPUT_CLASS}),
            "overdue_follow_up_grace_hours": forms.NumberInput(attrs={"class": CLAY_INPUT_CLASS}),
            "default_max_leads_per_telecaller": forms.NumberInput(attrs={"class": CLAY_INPUT_CLASS}),
        }
