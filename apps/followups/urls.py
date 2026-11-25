from django.urls import path

from apps.followups import views

app_name = "followups"

urlpatterns = [
    path("", views.followup_list, name="list"),
    path("<int:pk>/complete/", views.complete_followup, name="complete"),
    path("<int:pk>/reschedule/", views.reschedule_followup, name="reschedule"),
]
