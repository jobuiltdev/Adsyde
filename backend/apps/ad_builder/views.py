from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.generations.serializers import GenerationSerializer
from apps.projects.models import Project

from .models import AdPlan, AdPlanRevision, PlanStatus
from .serializers import AdPlanRevisionSerializer, AdPlanSerializer, AdPlanWriteSerializer
from .services import create_revision, generate_from_revision, sync_assets


class PlanMixin:
    def project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_id"], owner=self.request.user)

    def plan(self):
        return get_object_or_404(
            AdPlan.objects.prefetch_related("selected_assets", "revisions"),
            pk=self.kwargs["plan_id"],
            project=self.project(),
            user=self.request.user,
        )


class PlanListCreateView(PlanMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ad_plan_create"

    def get(self, request, project_id):
        plans = AdPlan.objects.filter(project=self.project(), user=request.user)
        return Response(AdPlanSerializer(plans, many=True).data)

    def post(self, request, project_id):
        serializer = AdPlanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selections = serializer.validated_data.pop("selected_asset_inputs", [])
        with transaction.atomic():
            plan = serializer.save(project=self.project(), user=request.user)
            sync_assets(plan, selections)
        return Response(AdPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class PlanDetailView(PlanMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ad_plan_mutation"

    def get(self, request, project_id, plan_id):
        return Response(AdPlanSerializer(self.plan()).data)

    def patch(self, request, project_id, plan_id):
        plan = self.plan()
        serializer = AdPlanWriteSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        has_assets = "selected_asset_inputs" in serializer.validated_data
        selections = serializer.validated_data.pop("selected_asset_inputs", [])
        with transaction.atomic():
            plan = serializer.save()
            if has_assets:
                sync_assets(plan, selections)
        return Response(AdPlanSerializer(plan).data)

    def delete(self, request, project_id, plan_id):
        plan = self.plan()
        if plan.revisions.filter(generation__isnull=False).exists():
            plan.status = PlanStatus.ARCHIVED
            plan.save(update_fields=["status", "updated_at"])
        else:
            plan.delete()
        return Response(status=204)


class PlanActionView(PlanMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ad_plan_plan"

    def post(self, request, project_id, plan_id):
        key = request.headers.get("Idempotency-Key", "").strip()
        if not 8 <= len(key) <= 128:
            raise ValidationError({"idempotency_key": ["A valid Idempotency-Key is required."]})
        revision = create_revision(self.plan(), key)
        return Response(AdPlanRevisionSerializer(revision).data, status=201)


class RevisionDetailView(PlanMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ad_plan_mutation"

    def revision(self):
        return get_object_or_404(
            AdPlanRevision,
            pk=self.kwargs["revision_id"],
            plan=self.plan(),
        )

    def patch(self, request, **kwargs):
        revision = self.revision()
        serializer = AdPlanRevisionSerializer(revision, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PlanGenerateView(RevisionDetailView):
    throttle_scope = "ad_plan_generate"

    def post(self, request, **kwargs):
        generation = generate_from_revision(self.revision(), request.user)
        return Response(
            GenerationSerializer(generation, context={"request": request}).data,
            status=201,
        )
