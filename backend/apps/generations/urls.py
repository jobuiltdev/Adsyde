from django.urls import path

from .views import (
    GenerationCancelView,
    GenerationDetailView,
    GenerationListCreateView,
    GenerationResultView,
)

urlpatterns = [
    path(
        "projects/<uuid:project_id>/generations/",
        GenerationListCreateView.as_view(),
        name="generation-list",
    ),
    path(
        "projects/<uuid:project_id>/generations/<uuid:generation_id>/",
        GenerationDetailView.as_view(),
        name="generation-detail",
    ),
    path(
        "projects/<uuid:project_id>/generations/<uuid:generation_id>/cancel/",
        GenerationCancelView.as_view(),
        name="generation-cancel",
    ),
    path(
        "projects/<uuid:project_id>/generations/<uuid:generation_id>/result/",
        GenerationResultView.as_view(),
        name="generation-result",
    ),
]
