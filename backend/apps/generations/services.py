import logging

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.providers.registry import get_provider

from .models import Generation, GenerationStatus, ProviderEvent

logger = logging.getLogger(__name__)
TERMINAL_STATUSES = {
    GenerationStatus.COMPLETED,
    GenerationStatus.FAILED,
    GenerationStatus.CANCELLED,
}
ACTIVE_STATUSES = {
    GenerationStatus.DRAFT,
    GenerationStatus.QUEUED,
    GenerationStatus.SUBMITTED,
    GenerationStatus.PROCESSING,
    GenerationStatus.UNKNOWN,
}
ALLOWED_TRANSITIONS = {
    GenerationStatus.DRAFT: {GenerationStatus.QUEUED, GenerationStatus.CANCELLED},
    GenerationStatus.QUEUED: {
        GenerationStatus.SUBMITTED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.SUBMITTED: {
        GenerationStatus.PROCESSING,
        GenerationStatus.UNKNOWN,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.PROCESSING: {
        GenerationStatus.UNKNOWN,
        GenerationStatus.COMPLETED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.UNKNOWN: {
        GenerationStatus.PROCESSING,
        GenerationStatus.COMPLETED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.COMPLETED: set(),
    GenerationStatus.FAILED: set(),
    GenerationStatus.CANCELLED: set(),
}


class InvalidTransition(ValueError):
    pass


def transition_locked(generation, target, **fields):
    if generation.status == target:
        return generation
    if target not in ALLOWED_TRANSITIONS[generation.status]:
        raise InvalidTransition(f"Cannot transition from {generation.status} to {target}")
    now = timezone.now()
    generation.status = target
    if target == GenerationStatus.SUBMITTED and generation.submitted_at is None:
        generation.submitted_at = now
    if target == GenerationStatus.PROCESSING and generation.started_at is None:
        generation.started_at = now
    if target in TERMINAL_STATUSES and generation.completed_at is None:
        generation.completed_at = now
    for name, value in fields.items():
        setattr(generation, name, value)
    generation.save()
    logger.info(
        f"generation.{target}",
        extra={
            "event": f"generation.{target}",
            "generation_id": str(generation.pk),
            "project_id": str(generation.project_id),
            "provider": generation.provider_key,
        },
    )
    return generation


def transition_generation(generation_id, target, **fields):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        return transition_locked(generation, target, **fields)


def complete_generation(generation_id):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        if generation.status in TERMINAL_STATUSES:
            return generation
        if not generation.result_file:
            payload = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
            generation.result_file.save("result.mp4", ContentFile(payload), save=False)
            generation.result_mime_type = "video/mp4"
        return transition_locked(generation, GenerationStatus.COMPLETED)


def fail_generation(generation_id, code, detail):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        if generation.status in TERMINAL_STATUSES:
            return generation
        return transition_locked(
            generation, GenerationStatus.FAILED, error_code=code, error_detail=detail
        )


def process_provider_event(generation_id, provider_key, event_id, event_type):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        _, created = ProviderEvent.objects.get_or_create(
            provider_key=provider_key,
            event_id=event_id,
            defaults={"generation": generation, "event_type": event_type},
        )
        if not created or generation.status in TERMINAL_STATUSES:
            return generation
        if event_type == "completed":
            return complete_generation(generation.pk)
        if event_type == "failed":
            return transition_locked(
                generation,
                GenerationStatus.FAILED,
                error_code="GENERATION_FAILED",
                error_detail="Generation failed at the provider.",
            )
        return generation


def cancel_generation(generation):
    if generation.status == GenerationStatus.CANCELLED:
        return generation
    if generation.status in {GenerationStatus.COMPLETED, GenerationStatus.FAILED}:
        raise ValidationError("A terminal generation cannot be cancelled.")
    if generation.provider_job_id:
        provider = get_provider(generation.provider_key)
        if not provider.cancel(generation.provider_job_id):
            raise ValidationError("Cancellation could not be confirmed.")
    return transition_generation(generation.pk, GenerationStatus.CANCELLED)
