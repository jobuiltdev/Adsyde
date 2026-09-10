import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.projects.models import Project

from .models import Generation
from .serializers import GenerationCreateSerializer, GenerationSerializer
from .services import ACTIVE_STATUSES, cancel_generation

logger = logging.getLogger(__name__)


class GenerationOwnershipMixin:
    def get_project(self, *, lock=False):
        queryset = Project.objects.filter(owner=self.request.user)
        if lock:
            queryset = queryset.select_for_update()
        return get_object_or_404(queryset, pk=self.kwargs["project_id"])

    def get_generation(self):
        return get_object_or_404(
            Generation.objects.select_related("project"),
            pk=self.kwargs["generation_id"],
            project_id=self.kwargs["project_id"],
            project__owner=self.request.user,
        )


class GenerationListCreateView(GenerationOwnershipMixin, generics.ListAPIView):
    serializer_class = GenerationSerializer
    throttle_classes = [ScopedRateThrottle]

    def get_queryset(self):
        return Generation.objects.filter(project=self.get_project())

    def get_throttles(self):
        self.throttle_scope = (
            "generation_submit" if self.request.method == "POST" else "generation_status"
        )
        return super().get_throttles()

    def post(self, request, *args, **kwargs):
        serializer = GenerationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        User = get_user_model()
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            project = self.get_project(lock=True)
            active_count = Generation.objects.filter(
                created_by=request.user, status__in=ACTIVE_STATUSES
            ).count()
            if active_count >= settings.GENERATION_MAX_ACTIVE_PER_USER:
                raise ValidationError(
                    {"generation": ["The active generation limit has been reached."]}
                )
            generation = Generation.objects.create(
                project=project,
                created_by=request.user,
                provider_key="mock",
                status="queued",
                **serializer.validated_data,
            )
            logger.info(
                "generation.created",
                extra={
                    "event": "generation.created",
                    "generation_id": str(generation.pk),
                    "project_id": str(project.pk),
                    "account_id": str(request.user.pk),
                    "provider": generation.provider_key,
                    "prompt_length": len(generation.prompt),
                },
            )
            from .tasks import submit_generation_task

            transaction.on_commit(lambda: submit_generation_task.delay(str(generation.pk)))
        return Response(
            GenerationSerializer(generation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class GenerationDetailView(GenerationOwnershipMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "generation_status"

    def get(self, request, *args, **kwargs):
        generation = self.get_generation()
        return Response(GenerationSerializer(generation, context={"request": request}).data)


class GenerationCancelView(GenerationOwnershipMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "generation_cancel"

    def post(self, request, *args, **kwargs):
        generation = cancel_generation(self.get_generation())
        return Response(GenerationSerializer(generation, context={"request": request}).data)


class GenerationResultView(GenerationOwnershipMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "generation_status"

    def get(self, request, *args, **kwargs):
        generation = self.get_generation()
        if generation.status != "completed" or not generation.result_file:
            raise Http404
        try:
            source = generation.result_file.open("rb")
        except FileNotFoundError as exc:
            raise Http404 from exc
        return FileResponse(source, content_type=generation.result_mime_type)
