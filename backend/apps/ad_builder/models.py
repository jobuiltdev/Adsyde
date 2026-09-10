import uuid

from django.conf import settings
from django.db import models

from apps.projects.models import Project


class PlanStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PLANNED = "planned", "Planned"
    GENERATED = "generated", "Generated"
    ARCHIVED = "archived", "Archived"


class Platform(models.TextChoices):
    TIKTOK = "tiktok", "TikTok"
    INSTAGRAM_REELS = "instagram_reels", "Instagram Reels"
    INSTAGRAM_FEED = "instagram_feed", "Instagram Feed"
    YOUTUBE_SHORTS = "youtube_shorts", "YouTube Shorts"
    YOUTUBE = "youtube", "YouTube"
    GENERAL_SOCIAL = "general_social", "General social"


class AssetRole(models.TextChoices):
    PRIMARY_PRODUCT = "primary_product", "Primary product"
    ADDITIONAL_PRODUCT = "additional_product", "Additional product"
    LOGO = "logo", "Logo"
    VISUAL_REFERENCE = "visual_reference", "Visual reference"


class AdPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ad_plans"
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="ad_plans")
    business_product = models.CharField(max_length=1000)
    offer_objective = models.CharField(max_length=1000, blank=True)
    audience = models.CharField(max_length=500, blank=True)
    style = models.CharField(max_length=32, default="premium")
    style_notes = models.CharField(max_length=500, blank=True)
    platform = models.CharField(
        max_length=32, choices=Platform.choices, default=Platform.INSTAGRAM_REELS
    )
    call_to_action = models.CharField(max_length=200, blank=True)
    selling_points = models.JSONField(default=list)
    model = models.CharField(max_length=64, default="mock-standard")
    aspect_ratio = models.CharField(max_length=8, default="9:16")
    duration_seconds = models.PositiveSmallIntegerField(default=10)
    status = models.CharField(max_length=16, choices=PlanStatus.choices, default=PlanStatus.DRAFT)
    planner_version = models.CharField(max_length=32, default="deterministic-v1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [models.Index(fields=("project", "-updated_at"), name="plan_project_time_idx")]

    def __str__(self):
        return self.business_product[:80]


class AdPlanAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(AdPlan, on_delete=models.CASCADE, related_name="selected_assets")
    asset = models.ForeignKey("assets.Asset", on_delete=models.SET_NULL, null=True, blank=True)
    asset_id_snapshot = models.UUIDField()
    filename_snapshot = models.CharField(max_length=255)
    category_snapshot = models.CharField(max_length=32)
    mime_type_snapshot = models.CharField(max_length=32)
    role = models.CharField(max_length=32, choices=AssetRole.choices)
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=("plan", "position"), name="plan_asset_position_unique"),
            models.UniqueConstraint(fields=("plan", "asset_id_snapshot"), name="plan_asset_unique"),
        ]

    def __str__(self):
        return self.filename_snapshot


class AdPlanRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(AdPlan, on_delete=models.CASCADE, related_name="revisions")
    number = models.PositiveSmallIntegerField()
    request_key = models.CharField(max_length=128)
    variant = models.CharField(max_length=32)
    template_version = models.CharField(max_length=32, default="prompt-template-v1")
    concept = models.TextField()
    hook = models.TextField()
    script_sections = models.JSONField(default=list)
    shots = models.JSONField(default=list)
    planner_prompt = models.TextField()
    reviewed_concept = models.TextField()
    reviewed_hook = models.TextField()
    reviewed_script_sections = models.JSONField(default=list)
    reviewed_shots = models.JSONField(default=list)
    reviewed_prompt = models.TextField()
    generation = models.OneToOneField(
        "generations.Generation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_plan_revision",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-number",)
        constraints = [
            models.UniqueConstraint(fields=("plan", "number"), name="plan_revision_number_unique"),
            models.UniqueConstraint(
                fields=("plan", "request_key"), name="plan_revision_request_unique"
            ),
        ]

    def __str__(self):
        return f"{self.plan_id}:{self.number}"


class GenerationReference(models.Model):
    generation = models.ForeignKey(
        "generations.Generation", on_delete=models.CASCADE, related_name="references"
    )
    asset = models.ForeignKey("assets.Asset", on_delete=models.SET_NULL, null=True, blank=True)
    asset_id_snapshot = models.UUIDField()
    filename_snapshot = models.CharField(max_length=255)
    category_snapshot = models.CharField(max_length=32)
    role = models.CharField(max_length=32, choices=AssetRole.choices)
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("position",)
        constraints = [
            models.UniqueConstraint(
                fields=("generation", "position"), name="generation_reference_position_unique"
            )
        ]

    def __str__(self):
        return f"{self.generation_id}:{self.position}"
