import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=120)
    business_name = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=2000, blank=True)
    brand_style = models.CharField(max_length=500, blank=True)
    target_audience = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(condition=~Q(name=""), name="project_name_not_empty")]

    def __str__(self) -> str:
        return self.name
