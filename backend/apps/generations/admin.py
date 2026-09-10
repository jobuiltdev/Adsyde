from django.contrib import admin

from .models import Generation, ProviderEvent


@admin.register(Generation)
class GenerationAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "status", "provider_key", "model", "created_at")
    list_filter = ("status", "provider_key", "model")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProviderEvent)
class ProviderEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "generation", "provider_key", "event_type", "received_at")
    readonly_fields = ("received_at",)
