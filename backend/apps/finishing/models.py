import uuid

from django.conf import settings
from django.db import models


class FinishStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    RENDERING = "rendering", "Rendering"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    ARCHIVED = "archived", "Archived"


class AdFinish(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.PROTECT, related_name="finishes"
    )
    source_generation = models.ForeignKey(
        "generations.Generation", on_delete=models.PROTECT, related_name="finishes"
    )
    source_plan_revision = models.ForeignKey(
        "ad_builder.AdPlanRevision", on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(
        max_length=16, choices=FinishStatus.choices, default=FinishStatus.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [models.Index(fields=("project", "-updated_at"), name="finish_project_time_idx")]

    def __str__(self):
        return str(self.id)


class FinishRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finish = models.ForeignKey(AdFinish, on_delete=models.CASCADE, related_name="revisions")
    number = models.PositiveSmallIntegerField()
    request_key = models.CharField(max_length=128)
    captions_enabled = models.BooleanField(default=True)
    caption_source = models.CharField(max_length=16, default="manual")
    caption_language = models.CharField(max_length=12, default="en")
    caption_style = models.CharField(max_length=16, default="clean")
    caption_position = models.CharField(max_length=16, default="bottom")
    caption_segments = models.JSONField(default=list)
    voiceover_enabled = models.BooleanField(default=False)
    voice_script = models.TextField(blank=True)
    voice_key = models.CharField(max_length=16, default="neutral")
    voice_speed_percent = models.PositiveSmallIntegerField(default=100)
    music_enabled = models.BooleanField(default=False)
    music_key = models.CharField(max_length=16, default="none")
    music_volume_percent = models.PositiveSmallIntegerField(default=20)
    fade_in_ms = models.PositiveIntegerField(default=300)
    fade_out_ms = models.PositiveIntegerField(default=300)
    watermark_enabled = models.BooleanField(default=False)
    thumbnail_asset = models.ForeignKey(
        "assets.Asset", on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-number",)
        constraints = [
            models.UniqueConstraint(
                fields=("finish", "number"), name="finish_revision_number_unique"
            ),
            models.UniqueConstraint(
                fields=("finish", "request_key"), name="finish_revision_request_unique"
            ),
        ]

    def __str__(self):
        return f"{self.finish_id}:{self.number}"


def rendered_output_path(instance, _filename):
    return f"projects/{instance.revision.finish.project_id}/finishes/{instance.id}/finished.mp4"


class RenderedAd(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.OneToOneField(FinishRevision, on_delete=models.PROTECT, related_name="output")
    file = models.FileField(upload_to=rendered_output_path, max_length=500)
    mime_type = models.CharField(max_length=32)
    size_bytes = models.PositiveBigIntegerField()
    duration_ms = models.PositiveIntegerField()
    aspect_ratio = models.CharField(max_length=8)
    render_version = models.CharField(max_length=32, default="local-copy-v1")
    captions_applied = models.BooleanField(default=False)
    voiceover_applied = models.BooleanField(default=False)
    music_applied = models.BooleanField(default=False)
    watermark_applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class RegenerationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    source_generation = models.ForeignKey(
        "generations.Generation", on_delete=models.PROTECT, related_name="regeneration_requests"
    )
    generation = models.OneToOneField(
        "generations.Generation", on_delete=models.PROTECT, related_name="regenerated_from_request"
    )
    request_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "source_generation", "request_key"),
                name="regeneration_request_unique",
            )
        ]

    def __str__(self):
        return str(self.id)
