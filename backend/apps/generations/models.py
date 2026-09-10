import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.projects.models import Project


class GenerationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    QUEUED = "queued", "Queued"
    SUBMITTED = "submitted", "Submitted"
    PROCESSING = "processing", "Processing"
    UNKNOWN = "unknown", "Awaiting reconciliation"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class AspectRatio(models.TextChoices):
    PORTRAIT = "9:16", "9:16"
    SQUARE = "1:1", "1:1"
    LANDSCAPE = "16:9", "16:9"


def generation_result_path(instance, _filename):
    return f"projects/{instance.project_id}/generations/{instance.id}/result.mp4"


class Generation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="generations")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="generations"
    )
    prompt = models.TextField()
    provider_key = models.CharField(max_length=32, default="mock", editable=False)
    provider_job_id = models.CharField(max_length=255, blank=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    model = models.CharField(max_length=64)
    aspect_ratio = models.CharField(max_length=8, choices=AspectRatio.choices)
    duration_seconds = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=16, choices=GenerationStatus.choices, default=GenerationStatus.DRAFT
    )
    result_file = models.FileField(upload_to=generation_result_path, blank=True, max_length=500)
    result_mime_type = models.CharField(max_length=32, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_detail = models.CharField(max_length=255, blank=True)
    submission_attempts = models.PositiveSmallIntegerField(default=0)
    poll_attempts = models.PositiveSmallIntegerField(default=0)
    reconciliation_attempts = models.PositiveSmallIntegerField(default=0)
    mock_scenario = models.CharField(max_length=32, default="success", editable=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=~Q(prompt=""), name="generation_prompt_not_empty"),
            models.CheckConstraint(
                condition=Q(aspect_ratio__in=AspectRatio.values), name="generation_aspect_valid"
            ),
            models.CheckConstraint(
                condition=Q(duration_seconds__gt=0), name="generation_duration_positive"
            ),
            models.CheckConstraint(
                condition=Q(status__in=GenerationStatus.values), name="generation_status_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.id}"


class ProviderEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generation = models.ForeignKey(Generation, on_delete=models.CASCADE, related_name="events")
    provider_key = models.CharField(max_length=32)
    event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=32)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider_key", "event_id"), name="provider_event_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider_key}:{self.event_id}"
