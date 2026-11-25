from django.urls import path

from apps.courses import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="list"),
    path("create/", views.course_create, name="create"),
    path("<int:pk>/edit/", views.course_edit, name="edit"),
    path("<int:pk>/toggle-active/", views.course_toggle_active, name="toggle_active"),
]
