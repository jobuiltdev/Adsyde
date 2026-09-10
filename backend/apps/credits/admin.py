from django.contrib import admin

from .models import CreditTransaction, CreditWallet, GenerationCharge


class ReadOnlyLedgerAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CreditWallet)
class CreditWalletAdmin(ReadOnlyLedgerAdmin):
    list_display = ("id", "user", "balance", "reserved_balance", "updated_at")


@admin.register(CreditTransaction)
class CreditTransactionAdmin(ReadOnlyLedgerAdmin):
    list_display = (
        "id",
        "wallet",
        "transaction_type",
        "balance_delta",
        "reserved_delta",
        "created_at",
    )


@admin.register(GenerationCharge)
class GenerationChargeAdmin(ReadOnlyLedgerAdmin):
    list_display = (
        "id",
        "generation_id_snapshot",
        "quoted_credits",
        "status",
        "reserved_at",
    )
