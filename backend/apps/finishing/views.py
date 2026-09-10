from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.ad_builder.models import AdPlan, AdPlanAsset, PlanStatus
from apps.generations.models import Generation
from apps.generations.serializers import GenerationSerializer

from .captions import export_captions
from .models import AdFinish, FinishRevision, FinishStatus, RenderedAd
from .serializers import AdFinishSerializer, FinishRevisionSerializer, RenderedAdSerializer
from .services import create_finish, create_revision, regenerate, render_revision


class FinishMixin:
    def finish(self):
        return get_object_or_404(
            AdFinish.objects.prefetch_related("revisions"),
            pk=self.kwargs["finish_id"],
            user=self.request.user,
            project__owner=self.request.user,
        )

    def revision(self):
        return get_object_or_404(
            FinishRevision.objects.select_related("finish", "finish__source_generation"),
            pk=self.kwargs["revision_id"],
            finish=self.finish(),
        )


class GenerationFinishListCreateView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "finish_create"

    def generation(self):
        return get_object_or_404(
            Generation.objects.select_related("project"),
            pk=self.kwargs["generation_id"],
            project__owner=self.request.user,
            created_by=self.request.user,
        )

    def get(self, request, generation_id):
        finishes = AdFinish.objects.filter(source_generation=self.generation(), user=request.user)
        return Response(AdFinishSerializer(finishes, many=True).data)

    def post(self, request, generation_id):
        finish = create_finish(self.generation(), request.user)
        return Response(AdFinishSerializer(finish).data, status=status.HTTP_201_CREATED)


class FinishDetailView(FinishMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "finish_mutation"

    def get(self, request, finish_id):
        return Response(AdFinishSerializer(self.finish()).data)

    def patch(self, request, finish_id):
        finish = self.finish()
        current = finish.revisions.first()
        serializer = FinishRevisionSerializer(
            current,
            data=request.data,
            partial=True,
            context={
                "duration_ms": finish.source_generation.duration_seconds * 1000,
                "project_id": finish.project_id,
            },
        )
        serializer.is_valid(raise_exception=True)
        key = request.headers.get("Idempotency-Key", "").strip()
        if not 8 <= len(key) <= 128:
            raise ValidationError({"idempotency_key": ["A valid Idempotency-Key is required."]})
        revision = create_revision(finish, key, serializer.validated_data)
        return Response(FinishRevisionSerializer(revision).data)

    def delete(self, request, finish_id):
        finish = self.finish()
        if finish.revisions.filter(output__isnull=False).exists():
            finish.status = FinishStatus.ARCHIVED
            finish.save(update_fields=["status", "updated_at"])
        else:
            finish.delete()
        return Response(status=204)


class RenderView(FinishMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "finish_render"

    def post(self, request, **kwargs):
        try:
            output = render_revision(self.revision())
        except ValueError as exc:
            raise ValidationError({"render": [str(exc)]}) from exc
        return Response(RenderedAdSerializer(output).data, status=201)


class OutputContentView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "finish_download"

    def get(self, request, output_id):
        output = get_object_or_404(
            RenderedAd.objects.select_related("revision__finish__project"),
            pk=output_id,
            revision__finish__user=request.user,
        )
        try:
            source = output.file.open("rb")
        except FileNotFoundError as exc:
            raise Http404 from exc
        response = FileResponse(source, content_type=output.mime_type)
        response["Content-Disposition"] = f'attachment; filename="adsyde-finished-{output.pk}.mp4"'
        return response


class CaptionDownloadView(FinishMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "finish_download"

    def get(self, request, caption_format, **kwargs):
        revision = self.revision()
        if caption_format not in {"srt", "vtt"}:
            raise Http404
        content = export_captions(revision.caption_segments, vtt=caption_format == "vtt")
        response = HttpResponse(
            content,
            content_type="text/vtt" if caption_format == "vtt" else "application/x-subrip",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="adsyde-captions-{revision.pk}.{caption_format}"'
        )
        return response


class GenerationActionMixin:
    def generation(self):
        return get_object_or_404(
            Generation.objects.select_related("project"),
            pk=self.kwargs["generation_id"],
            project__owner=self.request.user,
            created_by=self.request.user,
        )


class RegenerateView(GenerationActionMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "generation_submit"

    def post(self, request, generation_id):
        key = request.headers.get("Idempotency-Key", "").strip()
        if not 8 <= len(key) <= 128:
            raise ValidationError({"idempotency_key": ["A valid Idempotency-Key is required."]})
        generation = regenerate(self.generation(), request.user, key)
        return Response(
            GenerationSerializer(generation, context={"request": request}).data, status=201
        )


class DuplicateGenerationView(GenerationActionMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "finish_mutation"

    def post(self, request, generation_id):
        source = self.generation()
        source_revision = getattr(source, "source_plan_revision", None)
        if not source_revision:
            return Response(
                {
                    "mode": "prompt",
                    "prompt": source.prompt,
                    "model": source.model,
                    "aspect_ratio": source.aspect_ratio,
                    "duration_seconds": source.duration_seconds,
                }
            )
        original = source_revision.plan
        copied = AdPlan.objects.create(
            user=request.user,
            project=original.project,
            business_product=original.business_product,
            offer_objective=original.offer_objective,
            audience=original.audience,
            style=original.style,
            style_notes=original.style_notes,
            platform=original.platform,
            call_to_action=original.call_to_action,
            selling_points=original.selling_points,
            model=original.model,
            aspect_ratio=original.aspect_ratio,
            duration_seconds=original.duration_seconds,
            status=PlanStatus.DRAFT,
        )
        AdPlanAsset.objects.bulk_create(
            [
                AdPlanAsset(
                    plan=copied,
                    asset=item.asset,
                    asset_id_snapshot=item.asset_id_snapshot,
                    filename_snapshot=item.filename_snapshot,
                    category_snapshot=item.category_snapshot,
                    mime_type_snapshot=item.mime_type_snapshot,
                    role=item.role,
                    position=item.position,
                )
                for item in original.selected_assets.all()
            ]
        )
        return Response(
            {"mode": "guided", "plan_id": str(copied.pk), "project_id": str(copied.project_id)},
            status=201,
        )
