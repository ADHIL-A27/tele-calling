from django import forms
from django.utils import timezone

from apps.telecalling.models import CallOutcome

CLAY_INPUT_CLASS = "clay-input"


class CallLogForm(forms.Form):
    outcome = forms.ModelChoiceField(
        queryset=CallOutcome.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
    )
    duration_seconds = forms.IntegerField(required=False, min_value=0, widget=forms.NumberInput(attrs={"class": CLAY_INPUT_CLASS}))
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": CLAY_INPUT_CLASS, "rows": 3}))
    schedule_follow_up = forms.BooleanField(required=False)
    follow_up_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"class": CLAY_INPUT_CLASS, "type": "datetime-local"}),
    )
    follow_up_reason = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}))
    update_course_interest = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("schedule_follow_up") and not cleaned.get("follow_up_at"):
            self.add_error("follow_up_at", "Pick a date/time for the callback.")
        return cleaned
