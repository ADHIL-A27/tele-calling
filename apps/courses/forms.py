from django import forms

from apps.courses.models import Course

CLAY_INPUT_CLASS = "clay-input"


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "college",
            "name",
            "code",
            "description",
            "duration",
            "eligibility",
            "fee_details",
            "total_seats",
            "available_seats",
            "academic_session",
            "is_active",
        ]
        widgets = {
            "college": forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
            "name": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "code": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "description": forms.Textarea(attrs={"class": CLAY_INPUT_CLASS, "rows": 3}),
            "duration": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "eligibility": forms.Textarea(attrs={"class": CLAY_INPUT_CLASS, "rows": 2}),
            "fee_details": forms.TextInput(attrs={"class": CLAY_INPUT_CLASS}),
            "total_seats": forms.NumberInput(attrs={"class": CLAY_INPUT_CLASS}),
            "available_seats": forms.NumberInput(attrs={"class": CLAY_INPUT_CLASS}),
            "academic_session": forms.Select(attrs={"class": CLAY_INPUT_CLASS}),
        }
