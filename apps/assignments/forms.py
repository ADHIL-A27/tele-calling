from django import forms

from apps.accounts.models import CustomUser, Role
from apps.assignments.models import AssignmentMethod

CLAY_INPUT_CLASS = "clay-input"


class AssignmentForm(forms.Form):
    lead_ids = forms.CharField(widget=forms.HiddenInput())
    method = forms.ChoiceField(choices=AssignmentMethod.choices, widget=forms.Select(attrs={"class": CLAY_INPUT_CLASS}))
    telecallers = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(role=Role.TELECALLER, is_active_employee=True),
        widget=forms.SelectMultiple(attrs={"class": CLAY_INPUT_CLASS, "size": 8}),
    )
    single_telecaller = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role=Role.TELECALLER, is_active_employee=True),
        required=False,
        widget=forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
    )
    max_active_leads_override = forms.IntegerField(required=False, min_value=1)
    notes = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}))

    def clean_lead_ids(self):
        raw = self.cleaned_data["lead_ids"]
        try:
            return [int(x) for x in raw.split(",") if x.strip()]
        except ValueError:
            raise forms.ValidationError("Invalid lead selection.")
