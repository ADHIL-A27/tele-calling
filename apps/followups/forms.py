from django import forms

from apps.followups.models import FollowUpPriority

CLAY_INPUT_CLASS = "clay-input"


class RescheduleForm(forms.Form):
    scheduled_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"class": CLAY_INPUT_CLASS, "type": "datetime-local"})
    )
    reason = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}))


class CompleteFollowUpForm(forms.Form):
    completion_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": CLAY_INPUT_CLASS, "rows": 2}))
