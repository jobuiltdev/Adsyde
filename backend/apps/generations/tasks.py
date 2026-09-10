import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction

from apps.providers.exceptions import ProviderAcceptanceUnknownError, ProviderError
from apps.providers.registry import get_provider
from apps.providers.types import GenerationRequest, ProviderStatus

from .models import Generation, GenerationStatus
from .services import (
    TERMINAL_STATUSES,
    complete_generation,
    fail_generation,
    transition_generation,
    transition_locked,
)

logger = logging.getLogger(__name__)


def request_for(generation):
    return GenerationRequest(
        idempotency_key=str(generation.idempotency_key),
        prompt=generation.prompt,
        aspect_ratio=generation.aspect_ratio,
        duration_seconds=generation.duration_seconds,
        model=generation.model,
        scenario=generation.mock_scenario,
        submission_attempt=generation.submission_attempts,
    )


@shared_task(bind=True)
def submit_generation_task(self, generation_id):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        if generation.status != GenerationStatus.QUEUED or generation.provider_job_id:
            return generation.status
        generation.submission_attempts += 1
        generation.save(update_fields=["submission_attempts", "updated_at"])
    try:
        provider = get_provider(generation.provider_key)
        result = provider.submit_generation(request_for(generation))
    except ProviderAcceptanceUnknownError as exc:
        with transaction.atomic():
            current = Generation.objects.select_for_update().get(pk=generation_id)
            if current.status == GenerationStatus.QUEUED:
                transition_locked(current, GenerationStatus.SUBMITTED, provider_job_id=exc.job_id)
                transition_locked(current, GenerationStatus.UNKNOWN)
                transaction.on_commit(
                    lambda: reconcile_generation_task.apply_async(
                        args=[str(current.pk)], countdown=settings.GENERATION_POLL_INTERVAL_SECONDS
                    )
                )
        return GenerationStatus.UNKNOWN
    except ProviderError as exc:
        if exc.retryable and generation.submission_attempts < settings.GENERATION_MAX_TASK_ATTEMPTS:
            raise self.retry(exc=exc, countdown=2 ** (generation.submission_attempts - 1)) from exc
        fail_generation(generation_id, exc.code, str(exc))
        return GenerationStatus.FAILED
    with transaction.atomic():
        current = Generation.objects.select_for_update().get(pk=generation_id)
        if current.status != GenerationStatus.QUEUED:
            return current.status
        transition_locked(current, GenerationStatus.SUBMITTED, provider_job_id=result.job_id)
        transaction.on_commit(
            lambda: poll_generation_task.apply_async(
                args=[str(current.pk)], countdown=settings.GENERATION_POLL_INTERVAL_SECONDS
            )
        )
    return GenerationStatus.SUBMITTED


@shared_task
def poll_generation_task(generation_id):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        if generation.status in TERMINAL_STATUSES or generation.status == GenerationStatus.UNKNOWN:
            return generation.status
        if generation.status not in {GenerationStatus.SUBMITTED, GenerationStatus.PROCESSING}:
            return generation.status
        generation.poll_attempts += 1
        generation.save(update_fields=["poll_attempts", "updated_at"])
    try:
        provider = get_provider(generation.provider_key)
        result = provider.get_status(
            generation.provider_job_id,
            scenario=generation.mock_scenario,
            poll_attempt=generation.poll_attempts,
        )
    except ProviderError as exc:
        fail_generation(generation_id, exc.code, str(exc))
        return GenerationStatus.FAILED
    if result.status == ProviderStatus.COMPLETED:
        complete_generation(generation_id)
        return GenerationStatus.COMPLETED
    if result.status == ProviderStatus.FAILED:
        fail_generation(generation_id, result.error_code, result.error_detail)
        return GenerationStatus.FAILED
    with transaction.atomic():
        current = Generation.objects.select_for_update().get(pk=generation_id)
        if current.status == GenerationStatus.SUBMITTED:
            transition_locked(current, GenerationStatus.PROCESSING)
        if current.status == GenerationStatus.PROCESSING:
            transaction.on_commit(
                lambda: poll_generation_task.apply_async(
                    args=[str(current.pk)], countdown=settings.GENERATION_POLL_INTERVAL_SECONDS
                )
            )
    return GenerationStatus.PROCESSING


@shared_task
def reconcile_generation_task(generation_id):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        if generation.status != GenerationStatus.UNKNOWN:
            return generation.status
        generation.reconciliation_attempts += 1
        generation.save(update_fields=["reconciliation_attempts", "updated_at"])
    try:
        provider = get_provider(generation.provider_key)
        result = provider.reconcile(
            generation.provider_job_id,
            scenario=generation.mock_scenario,
            attempt=generation.reconciliation_attempts,
        )
    except ProviderError as exc:
        fail_generation(generation_id, exc.code, str(exc))
        return GenerationStatus.FAILED
    if result.status == ProviderStatus.COMPLETED:
        complete_generation(generation_id)
        return GenerationStatus.COMPLETED
    if result.status == ProviderStatus.FAILED:
        fail_generation(generation_id, result.error_code, result.error_detail)
        return GenerationStatus.FAILED
    if generation.reconciliation_attempts >= settings.GENERATION_MAX_RECONCILIATION_ATTEMPTS:
        fail_generation(
            generation_id,
            "UNKNOWN_PROVIDER_STATE",
            "Provider state could not be reconciled.",
        )
        return GenerationStatus.FAILED
    transition_generation(generation_id, GenerationStatus.PROCESSING)
    transition_generation(generation_id, GenerationStatus.UNKNOWN)
    reconcile_generation_task.apply_async(
        args=[str(generation.pk)], countdown=settings.GENERATION_POLL_INTERVAL_SECONDS
    )
    return GenerationStatus.UNKNOWN
