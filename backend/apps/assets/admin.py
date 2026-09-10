from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "category", "mime_type", "size", "created_at")
    list_filter = ("category", "mime_type")
    readonly_fields = ("created_at",)
