from django.urls import path

from apps.reports import views

app_name = "reports"

urlpatterns = [
    path("", views.index, name="index"),
    path("export/<str:report_key>/", views.export_report, name="export"),
]
