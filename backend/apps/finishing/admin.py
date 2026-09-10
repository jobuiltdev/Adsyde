from django.contrib import admin

from .models import AdFinish, FinishRevision, RegenerationRequest, RenderedAd


@admin.register(AdFinish)
class AdFinishAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "source_generation", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "source_generation__id", "project__name")
    readonly_fields = (
        "user",
        "project",
        "source_generation",
        "source_plan_revision",
        "created_at",
        "updated_at",
    )


admin.site.register(FinishRevision)
admin.site.register(RenderedAd)
admin.site.register(RegenerationRequest)
