from django.contrib import admin

from .models import Payment, PaymentEvent


class ReadOnlyPaymentAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnlyPaymentAdmin):
    list_display = (
        "internal_reference",
        "user",
        "package_key",
        "amount_minor",
        "status",
        "created_at",
    )
    list_filter = ("status", "package_key")
    search_fields = ("internal_reference", "provider_reference", "user__email")


@admin.register(PaymentEvent)
class PaymentEventAdmin(ReadOnlyPaymentAdmin):
    list_display = ("event_fingerprint", "event_type", "outcome", "received_at")
