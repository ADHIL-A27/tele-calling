from django.urls import path

from apps.assignments import views

app_name = "assignments"

urlpatterns = [
    path("", views.workspace, name="workspace"),
    path("confirm/", views.assign_confirm, name="assign_confirm"),
    path("course-based/", views.course_based_assign_view, name="course_based"),
    path("history/", views.history, name="history"),
]
