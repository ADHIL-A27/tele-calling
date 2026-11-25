from django import forms

from apps.leads.models import Campaign, LeadImportBatch, LeadSource

CLAY_INPUT_CLASS = "clay-input"


class LeadImportUploadForm(forms.Form):
    file = forms.FileField(
        label="Select CSV or Excel file",
        widget=forms.ClearableFileInput(attrs={"class": CLAY_INPUT_CLASS, "accept": ".csv,.xlsx"}),
    )
    lead_source = forms.ModelChoiceField(
        queryset=LeadSource.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
    )
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not (f.name.lower().endswith(".csv") or f.name.lower().endswith(".xlsx")):
            raise forms.ValidationError("Only .csv or .xlsx files are supported.")
        max_bytes = 15 * 1024 * 1024
        if f.size > max_bytes:
            raise forms.ValidationError("File is larger than 15 MB.")
        return f


class LeadFilterForm(forms.Form):
    q = forms.CharField(required=False)
    stage = forms.CharField(required=False)
    priority = forms.CharField(required=False)
    course = forms.CharField(required=False)
    owner = forms.CharField(required=False)
    unassigned_only = forms.BooleanField(required=False)
