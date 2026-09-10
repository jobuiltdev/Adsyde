from django.urls import path

from .views import (
    GenerationCancelView,
    GenerationDetailView,
    GenerationListCreateView,
    GenerationOptionsView,
    GenerationResultView,
    MockProviderCallbackView,
)

urlpatterns = [
    path("generation-options/", GenerationOptionsView.as_view(), name="generation-options"),
    path(
        "provider-callbacks/mock/",
        MockProviderCallbackView.as_view(),
        name="mock-provider-callback",
    ),
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
