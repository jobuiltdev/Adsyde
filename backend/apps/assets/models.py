import uuid

from django.db import models
from django.db.models import Q

from apps.projects.models import Project


class AssetCategory(models.TextChoices):
    PRODUCT_IMAGE = "product_image", "Product image"
    LOGO = "logo", "Logo"
    REFERENCE_IMAGE = "reference_image", "Reference image"


EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def asset_upload_to(instance, _filename):
    extension = EXTENSIONS[instance.mime_type]
    return f"projects/{instance.project_id}/assets/{instance.id}.{extension}"


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="assets")
    category = models.CharField(max_length=32, choices=AssetCategory.choices)
    file = models.FileField(upload_to=asset_upload_to, max_length=500)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=32)
    size = models.PositiveBigIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(size__gt=0), name="asset_size_positive"),
            models.CheckConstraint(condition=Q(width__gt=0), name="asset_width_positive"),
            models.CheckConstraint(condition=Q(height__gt=0), name="asset_height_positive"),
            models.CheckConstraint(
                condition=Q(category__in=AssetCategory.values), name="asset_category_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.id}"
