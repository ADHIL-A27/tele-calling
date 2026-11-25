from django.urls import path

from apps.telecalling import views

app_name = "telecalling"

urlpatterns = [
    path("my-leads/", views.my_leads, name="my_leads"),
    path("workspace/", views.workspace, name="workspace"),
    path("log-call/<int:pk>/", views.log_call, name="log_call"),
    path("history/", views.call_history, name="history"),
    path("interested/", views.interested_students, name="interested"),
    path("activity/", views.activity, name="activity"),
]
