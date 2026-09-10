from django.urls import path

from .views import (
    PlanActionView,
    PlanDetailView,
    PlanGenerateView,
    PlanListCreateView,
    RevisionDetailView,
)

urlpatterns = [
    path(
        "projects/<uuid:project_id>/ad-plans/",
        PlanListCreateView.as_view(),
        name="ad-plan-list",
    ),
    path(
        "projects/<uuid:project_id>/ad-plans/<uuid:plan_id>/",
        PlanDetailView.as_view(),
        name="ad-plan-detail",
    ),
    path(
        "projects/<uuid:project_id>/ad-plans/<uuid:plan_id>/plan/",
        PlanActionView.as_view(),
        name="ad-plan-action",
    ),
    path(
        "projects/<uuid:project_id>/ad-plans/<uuid:plan_id>/revisions/<uuid:revision_id>/",
        RevisionDetailView.as_view(),
        name="ad-plan-revision",
    ),
    path(
        "projects/<uuid:project_id>/ad-plans/<uuid:plan_id>/revisions/<uuid:revision_id>/generate/",
        PlanGenerateView.as_view(),
        name="ad-plan-generate",
    ),
]
