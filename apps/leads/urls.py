from django.urls import path

from apps.leads import views

app_name = "leads"

urlpatterns = [
    path("", views.lead_list, name="list"),
    path("<int:pk>/", views.lead_detail, name="detail"),
    path("import/", views.import_start, name="import_start"),
    path("import/<int:batch_id>/preview/", views.import_preview, name="import_preview"),
    path("import/<int:batch_id>/summary/", views.import_summary, name="import_summary"),
    path("import/<int:batch_id>/report/", views.import_report, name="import_report"),
]
