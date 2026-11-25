from django.urls import path

from apps.admissions import views

app_name = "admissions"

urlpatterns = [
    path("pipeline/", views.pipeline, name="pipeline"),
    path("pipeline/board/", views.pipeline_board_partial, name="pipeline_board"),
    path("pipeline/move/<int:pk>/", views.move_stage, name="move_stage"),
]
