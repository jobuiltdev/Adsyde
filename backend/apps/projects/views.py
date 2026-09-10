import logging

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.assets.models import Asset
from apps.assets.serializers import AssetSerializer, AssetUploadSerializer

from .models import Project
from .serializers import ProjectSerializer

logger = logging.getLogger(__name__)


def log_event(event, request, project=None, asset=None, outcome="success"):
    logger.info(
        event,
        extra={
            "event": event,
            "outcome": outcome,
            "account_id": str(request.user.pk),
            "project_id": str(project.pk) if project else None,
            "asset_id": str(asset.pk) if asset else None,
        },
    )


class OwnedProjectMixin:
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)


class ProjectListCreateView(OwnedProjectMixin, generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    throttle_classes = [ScopedRateThrottle]

    def get_throttles(self):
        self.throttle_scope = "project_create" if self.request.method == "POST" else None
        return super().get_throttles() if self.throttle_scope else []

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        log_event("project.created", self.request, project=project)


class ProjectDetailView(OwnedProjectMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "project_mutation"

    def get_throttles(self):
        if self.request.method in {"GET", "HEAD", "OPTIONS"}:
            return []
        return super().get_throttles()

    def perform_destroy(self, instance):
        if instance.ad_plans.filter(revisions__generation__isnull=False).exists():
            raise ValidationError(
                {"project": ["Projects with generated ad history cannot be deleted."]}
            )
        project_id = instance.pk
        instance.delete()
        logger.info(
            "project.deleted",
            extra={
                "event": "project.deleted",
                "outcome": "success",
                "account_id": str(self.request.user.pk),
                "project_id": str(project_id),
            },
        )


class OwnedProjectAssetMixin:
    def get_project(self, *, lock=False):
        queryset = Project.objects.filter(owner=self.request.user)
        if lock:
            queryset = queryset.select_for_update()
        return get_object_or_404(queryset, pk=self.kwargs["project_id"])

    def get_asset(self):
        return get_object_or_404(
            Asset.objects.select_related("project"),
            pk=self.kwargs["asset_id"],
            project__owner=self.request.user,
            project_id=self.kwargs["project_id"],
        )


class AssetListUploadView(OwnedProjectAssetMixin, generics.ListAPIView):
    serializer_class = AssetSerializer
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]

    def get_queryset(self):
        project = self.get_project()
        return Asset.objects.filter(project=project)

    def get_throttles(self):
        self.throttle_scope = "asset_upload" if self.request.method == "POST" else None
        return super().get_throttles() if self.throttle_scope else []

    def post(self, request, *args, **kwargs):
        serializer = AssetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        metadata = upload._asset_metadata
        asset = None
        try:
            with transaction.atomic():
                project = self.get_project(lock=True)
                if project.assets.count() >= settings.ASSET_MAX_PER_PROJECT:
                    raise ValidationError({"file": ["This project has reached its asset limit."]})
                asset = Asset(
                    project=project,
                    category=serializer.validated_data["category"],
                    file=upload,
                    original_filename=metadata["original_filename"],
                    mime_type=metadata["mime_type"],
                    size=metadata["size"],
                    width=metadata["width"],
                    height=metadata["height"],
                )
                asset.save()
        except Exception:
            if asset is not None and asset.file.name:
                asset.file.storage.delete(asset.file.name)
            log_event("asset.upload_rejected", request, outcome="rejected")
            raise
        log_event("asset.uploaded", request, project=project, asset=asset)
        return Response(
            AssetSerializer(asset, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AssetDetailView(OwnedProjectAssetMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "asset_delete"

    def get_throttles(self):
        return super().get_throttles() if self.request.method == "DELETE" else []

    def get(self, request, *args, **kwargs):
        return Response(AssetSerializer(self.get_asset(), context={"request": request}).data)

    def delete(self, request, *args, **kwargs):
        asset = self.get_asset()
        project = asset.project
        asset_id = asset.pk
        asset.delete()
        logger.info(
            "asset.deleted",
            extra={
                "event": "asset.deleted",
                "outcome": "success",
                "account_id": str(request.user.pk),
                "project_id": str(project.pk),
                "asset_id": str(asset_id),
            },
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetContentView(OwnedProjectAssetMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "asset_access"

    def get(self, request, *args, **kwargs):
        asset = self.get_asset()
        try:
            source = asset.file.open("rb")
        except FileNotFoundError as exc:
            raise Http404 from exc
        return FileResponse(source, content_type=asset.mime_type)
