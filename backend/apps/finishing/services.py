import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.credits.exceptions import InvalidPricingOption
from apps.credits.pricing import PricingUnavailable
from apps.credits.services import reserve_generation
from apps.generations.models import Generation, GenerationStatus
from apps.generations.services import ACTIVE_STATUSES
from apps.providers.registry import get_active_provider

from .captions import defaults_from_generation
from .models import AdFinish, FinishRevision, FinishStatus, RegenerationRequest, RenderedAd
from .renderer import LocalRenderer, RenderRequest

logger = logging.getLogger(__name__)


def validate_source(generation):
    if generation.status != "completed" or not generation.result_file:
        raise ValidationError({"generation": ["A completed generation result is required."]})
    try:
        generation.result_file.open("rb").close()
    except FileNotFoundError as exc:
        raise ValidationError({"generation": ["The source result is unavailable."]}) from exc


@transaction.atomic
def create_finish(generation, user):
    validate_source(generation)
    source_revision = getattr(generation, "source_plan_revision", None)
    finish = AdFinish.objects.create(
        user=user,
        project=generation.project,
        source_generation=generation,
        source_plan_revision=source_revision,
    )
    voice_script = (
        "\n".join(section["text"] for section in source_revision.reviewed_script_sections)
        if source_revision
        else ""
    )
    FinishRevision.objects.create(
        finish=finish,
        number=1,
        request_key="initial",
        caption_source="guided" if source_revision else "manual",
        caption_segments=defaults_from_generation(generation),
        voice_script=voice_script,
    )
    return finish


@transaction.atomic
def create_revision(finish, request_key, values):
    existing = FinishRevision.objects.filter(finish=finish, request_key=request_key).first()
    if existing:
        return existing
    finish = AdFinish.objects.select_for_update().get(pk=finish.pk)
    current = finish.revisions.first()
    fields = {
        field.name: getattr(current, field.name)
        for field in FinishRevision._meta.fields
        if field.name not in {"id", "finish", "number", "request_key", "created_at"}
    }
    fields.update(values)
    return FinishRevision.objects.create(
        finish=finish,
        number=finish.revisions.count() + 1,
        request_key=request_key,
        **fields,
    )


@transaction.atomic
def render_revision(revision):
    revision = (
        FinishRevision.objects.select_for_update()
        .select_related("finish__source_generation")
        .get(pk=revision.pk)
    )
    if hasattr(revision, "output"):
        return revision.output
    generation = revision.finish.source_generation
    validate_source(generation)
    revision.finish.status = FinishStatus.RENDERING
    revision.finish.save(update_fields=["status", "updated_at"])
    try:
        with generation.result_file.open("rb") as source:
            result = LocalRenderer().render(
                RenderRequest(source, generation.duration_seconds * 1000, generation.aspect_ratio)
            )
        output = RenderedAd(
            revision=revision,
            mime_type=result.mime_type,
            size_bytes=len(result.content),
            duration_ms=result.duration_ms,
            aspect_ratio=result.aspect_ratio,
        )
        output.file.save("finished.mp4", ContentFile(result.content), save=False)
        output.save()
        revision.finish.status = FinishStatus.COMPLETED
        revision.finish.save(update_fields=["status", "updated_at"])
        logger.info(
            "finish.rendered",
            extra={
                "event": "finish.rendered",
                "finish_id": str(revision.finish_id),
                "render_id": str(output.pk),
                "generation_id": str(generation.pk),
                "output_size": output.size_bytes,
            },
        )
        return output
    except Exception:
        revision.finish.status = FinishStatus.FAILED
        revision.finish.save(update_fields=["status", "updated_at"])
        raise


@transaction.atomic
def regenerate(source, user, request_key):
    existing = (
        RegenerationRequest.objects.filter(
            source_generation=source, user=user, request_key=request_key
        )
        .select_related("generation")
        .first()
    )
    if existing:
        return existing.generation
    get_user_model().objects.select_for_update().get(pk=user.pk)
    source = Generation.objects.select_for_update().get(pk=source.pk)
    if (
        Generation.objects.filter(created_by=user, status__in=ACTIVE_STATUSES).count()
        >= settings.GENERATION_MAX_ACTIVE_PER_USER
    ):
        raise ValidationError({"generation": ["The active generation limit has been reached."]})
    generation = Generation.objects.create(
        project=source.project,
        created_by=user,
        prompt=source.prompt,
        provider_key=get_active_provider().key,
        model=source.model,
        aspect_ratio=source.aspect_ratio,
        duration_seconds=source.duration_seconds,
        status=GenerationStatus.QUEUED,
    )
    try:
        reserve_generation(generation)
    except PricingUnavailable as exc:
        raise InvalidPricingOption from exc
    RegenerationRequest.objects.create(
        user=user,
        source_generation=source,
        generation=generation,
        request_key=request_key,
    )
    from apps.generations.tasks import submit_generation_task

    transaction.on_commit(lambda: submit_generation_task.delay(str(generation.pk)))
    return generation
