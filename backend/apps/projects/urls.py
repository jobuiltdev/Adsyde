from django.urls import path

from .views import (
    AssetContentView,
    AssetDetailView,
    AssetListUploadView,
    ProjectDetailView,
    ProjectListCreateView,
)

urlpatterns = [
    path("projects/", ProjectListCreateView.as_view(), name="project-list"),
    path("projects/<uuid:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "projects/<uuid:project_id>/assets/",
        AssetListUploadView.as_view(),
        name="project-asset-list",
    ),
    path(
        "projects/<uuid:project_id>/assets/<uuid:asset_id>/",
        AssetDetailView.as_view(),
        name="project-asset-detail",
    ),
    path(
        "projects/<uuid:project_id>/assets/<uuid:asset_id>/content/",
        AssetContentView.as_view(),
        name="project-asset-content",
    ),
]
