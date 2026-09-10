import base64
import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.providers.registry import get_provider

from .models import Generation, GenerationStatus, ProviderEvent

logger = logging.getLogger(__name__)
MOCK_VIDEO = base64.b64decode(
    "AAAAJGZ0eXBpc29tAAACAGlzb21pc282aXNvMmF2YzFtcDQxAAAC6W1vb3YAAABsbXZoZAAAAAAA"
    "AAAAAAAAAAAAA+gAAAAAAAEAAAEAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAA"
    "AAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAHrdHJhawAAAFx0a2hkAAAA"
    "AwAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAQAA"
    "AAAAAAAAAAAAAAAAQAAAAACgAAAAWgAAAAABh21kaWEAAAAgbWRoZAAAAAAAAAAAAAAAAAAAMgAAAAAA"
    "VcQAAAAAAC1oZGxyAAAAAAAAAAB2aWRlAAAAAAAAAAAAAAAAVmlkZW9IYW5kbGVyAAAAATJtaW5m"
    "AAAAFHZtaGQAAAABAAAAAAAAAAAAAAAkZGluZgAAABxkcmVmAAAAAAAAAAEAAAAMdXJsIAAAAAEA"
    "AADyc3RibAAAAKZzdHNkAAAAAAAAAAEAAACWYXZjMQAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAACg"
    "AFoASAAAAEgAAAAAAAAAARVMYXZjNjAuMzEuMTAyIGxpYngyNjQAAAAAAAAAAAAAABj//wAAADBh"
    "dmNDAULAC//hABhnQsAL2go35MBEAAADAAQAAAMAyDxQqoABAAVozgOcgAAAABBwYXNwAAAAAQAA"
    "AAEAAAAQc3R0cwAAAAAAAAAAAAAAEHN0c2MAAAAAAAAAAAAAABRzdHN6AAAAAAAAAAAAAAAAAAAA"
    "EHN0Y28AAAAAAAAAAAAAAChtdmV4AAAAIHRyZXgAAAAAAAAAAQAAAAEAAAAAAAAAAAAAAAAAAABi"
    "dWR0YQAAAFptZXRhAAAAAAAAACFoZGxyAAAAAAAAAABtZGlyYXBwbAAAAAAAAAAAAAAAAC1pbHN0"
    "AAAAJal0b28AAAAdZGF0YQAAAAEAAAAATGF2ZjYwLjE2LjEwMAAAANRtb29mAAAAEG1maGQAAAAA"
    "AAAAAQAAALx0cmFmAAAAJHRmaGQAAAA5AAAAAQAAAAAAAAMNAAACAAAAAycBAQAAAAAAFHRmZHQB"
    "AAAAAAAAAAAAAAAAAAB8dHJ1bgAAAgUAAAAZAAAA3AIAAAAAAAMnAAAADQAAAB0AAAAmAAAAEgAA"
    "AA8AAABEAAAACgAAAAoAAAAKAAAACgAAACQAAAAKAAAACgAAAAoAAAAKAAAACgAAAAoAAAAKAAAA"
    "CgAAAAoAAAAKAAAACgAAAAoAAAAKAAAEsm1kYXQAAAJMBgX//0jcRem95tlIt5Ys2CDZI+7veDI2"
    "NCAtIGNvcmUgMTY0IHIzMTA4IC0gSC4yNjQvTVBFRy00IEFWQyBjb2RlYyAtIENvcHlsZWZ0IDIw"
    "MDMtMjAyMyAtIGh0dHA6Ly93d3cudmlkZW9sYW4ub3JnL3gyNjQuaHRtbCAtIG9wdGlvbnM6IGNh"
    "YmFjPTAgcmVmPTEgZGVibG9jaz0wOjA6MCBhbmFseXNpPTA6MCBtZT1kaWEgc3VibWU9MCBwc3k9"
    "MSBwc3lfcmQ9MS4wMDowLjAwIG1peGVkX3JlZj0wIG1lX3JhbmdlPTE2IGNocm9tYV9tZT0xIHRy"
    "ZWxsaXM9MCA4eDhkY3Q9MCBjcW09MCBkZWFkem9uZT0yMSwxMSBmYXN0X3Bza2lwPTEgY2hyb21h"
    "X3FwX29mZnNldD0wIHRocmVhZHM9MyBsb29rYWhlYWRfdGhyZWFkcz0xIHNsaWNlZF90aHJlYWRz"
    "PTAgbnI9MCBkZWNpbWF0ZT0xIGludGVybGFjZWQ9MCBibHVyYXlfY29tcGF0PTAgY29uc3RyYWlu"
    "ZWRfaW50cmE9MCBiZnJhbWVzPTAgd2VpZ2h0cD0wIGtleWludD0yNTAga2V5aW50X21pbj0yNSBz"
    "Y2VuZWN1dD0wIGludHJhX3JlZnJlc2g9MCByYz1jcmYgbWJ0cmVlPTAgY3JmPTQwLjAgcWNvbXA9"
    "MC42MCBxcG1pbj0wIHFwbWF4PTY5IHFwc3RlcD00IGlwX3JhdGlvPTEuNDAgYXE9MACAAAAA02WI"
    "hDoRigACAP44DJycnJycnJycnXXC2ABB8HZbCFpP/AjreeLhmcHhmQeGZKnDZpyipe2XTriZNbW1h"
    "dQAIj9V/X//wE+ZLXl6P09ddcLPfKZpDJD5ISQ+MdKa5lNczwzwtbW1tYWUB7Umf1hLD5YSwEVm"
    "DbuSt3JoTQT111ws4ACbTTALfbhSKJ/8DzK5+IJIq4IZ+mOEzppnUaamS1tbWF1AASbSTbAhaq2N"
    "+B5CuQ8hXPh5Cuc3yt3KFSk0NPrrrtdra2tra1111111111114AAAAAJQZogSgQ83dw5AAAAGUGa"
    "QHobwSdpqLGL5lELiFxC/F9praIMQVwAAAAiQZpgJobw3wi4zwVJljR4/Lw54aQuBeHnZeXq0V11"
    "L1jIXgAAAA5BmoAqgQ9YJeCTxfCF4AAAAAtBmqAugQ8tCpisOQAAAEBBmsAyhvP7jJKj8vXooNr+"
    "O3K259bcrbggLS4HRFuQ6ItyFdyS7heez7HGtKFCCqx229NOIXELiF+frts4l8LwAAAABkGa4DKB"
    "7AAAAAZBmwAygewAAAAGQZsgMoHsAAAABkGbQDKB7AAAACBBm2A2gl1SovEyryryryrxXEyryr2O"
    "VeXnr9DMZZQLwAAAAAZBm4A2gewAAAAGQZugNoHsAAAABkGbwDaB7AAAAAZBm+A2gewAAAAGQZoAN"
    "oHsAAAABkGaIDaB7AAAAAZBmkA2gewAAAAGQZpgNoHsAAAABkGagDaB7AAAAAZBmqA2gewAAAAGQZ"
    "rANoHsAAAABkGa4DaB7AAAAAZBmwA2gewAAABDbWZyYQAAACt0ZnJhAQAAAAAAAAEAAAAAAAAAAQ"
    "AAAAAAAAAAAAAAAAAAAw0BAQEAAAAQbWZybwAAAAAAAABD"
)
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
        generation.provider_accepted_at = now
    if target == GenerationStatus.PROCESSING and generation.started_at is None:
        generation.started_at = now
    if target == GenerationStatus.UNKNOWN and generation.unknown_since is None:
        generation.unknown_since = now
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
            from .ingestion import ingest_result

            descriptor = get_provider(generation.provider_key).fetch_result(
                generation.provider_job_id
            )
            ingest_result(generation, descriptor)
        return transition_locked(generation, GenerationStatus.COMPLETED)


def fail_generation(generation_id, code, detail):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        if generation.status in TERMINAL_STATUSES:
            return generation
        return transition_locked(
            generation, GenerationStatus.FAILED, error_code=code, error_detail=detail
        )


def process_provider_event(generation_id, provider_key, event_id, event_type, provider_job_id=""):
    with transaction.atomic():
        generation = Generation.objects.select_for_update().get(pk=generation_id)
        event, created = ProviderEvent.objects.get_or_create(
            provider_key=provider_key,
            event_id=event_id,
            defaults={
                "generation": generation,
                "event_type": event_type,
                "provider_job_id": provider_job_id,
            },
        )
        if not created:
            return generation
        if generation.status in TERMINAL_STATUSES:
            event.processed_at = timezone.now()
            event.processing_outcome = "terminal_ignored"
            event.save(update_fields=["processed_at", "processing_outcome"])
            return generation
        if event_type == "completed":
            result = complete_generation(generation.pk)
        elif event_type == "failed":
            result = transition_locked(
                generation,
                GenerationStatus.FAILED,
                error_code="GENERATION_FAILED",
                error_detail="Generation failed at the provider.",
            )
        elif event_type == "processing" and generation.status == GenerationStatus.UNKNOWN:
            result = transition_locked(generation, GenerationStatus.PROCESSING)
        else:
            result = generation
        event.processed_at = timezone.now()
        event.processing_outcome = "processed"
        event.save(update_fields=["processed_at", "processing_outcome"])
        return result


def cancel_generation(generation):
    if generation.status == GenerationStatus.CANCELLED:
        return generation
    if generation.status in {GenerationStatus.COMPLETED, GenerationStatus.FAILED}:
        raise ValidationError("A terminal generation cannot be cancelled.")
    now = timezone.now()
    Generation.objects.filter(pk=generation.pk).update(cancel_requested_at=now)
    if generation.provider_job_id:
        provider = get_provider(generation.provider_key)
        if not provider.capabilities.supports_cancel:
            raise ValidationError("The provider does not support cancellation.")
        if not provider.cancel(generation.provider_job_id):
            raise ValidationError("Cancellation could not be confirmed.")
        return transition_generation(
            generation.pk, GenerationStatus.CANCELLED, cancel_confirmed_at=timezone.now()
        )
    return transition_generation(generation.pk, GenerationStatus.CANCELLED)
