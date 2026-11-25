from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("leads/", include("apps.leads.urls")),
    path("assignments/", include("apps.assignments.urls")),
    path("calling/", include("apps.telecalling.urls")),
    path("followups/", include("apps.followups.urls")),
    path("admissions/", include("apps.admissions.urls")),
    path("courses/", include("apps.courses.urls")),
    path("reports/", include("apps.reports.urls")),
    path("notifications/", include("apps.notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
