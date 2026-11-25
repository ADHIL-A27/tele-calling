from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("performance/", views.performance, name="performance"),
    path("my-performance/", views.my_performance, name="my_performance"),
    path("settings/", views.settings_view, name="settings"),
]
