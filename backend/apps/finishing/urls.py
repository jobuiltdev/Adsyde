from django.urls import path

from .views import (
    CaptionDownloadView,
    DuplicateGenerationView,
    FinishDetailView,
    GenerationFinishListCreateView,
    OutputContentView,
    RegenerateView,
    RenderView,
)

urlpatterns = [
    path("generations/<uuid:generation_id>/regenerate/", RegenerateView.as_view()),
    path("generations/<uuid:generation_id>/duplicate/", DuplicateGenerationView.as_view()),
    path("generations/<uuid:generation_id>/finishes/", GenerationFinishListCreateView.as_view()),
    path("finishes/<uuid:finish_id>/", FinishDetailView.as_view()),
    path("finishes/<uuid:finish_id>/revisions/<uuid:revision_id>/render/", RenderView.as_view()),
    path(
        "finishes/<uuid:finish_id>/revisions/<uuid:revision_id>/captions/<str:caption_format>/",
        CaptionDownloadView.as_view(),
    ),
    path("finished-ads/<uuid:output_id>/content/", OutputContentView.as_view()),
]
