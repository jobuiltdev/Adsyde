from rest_framework import serializers

from .models import CreditTransaction, CreditWallet


class WalletSerializer(serializers.ModelSerializer):
    reserved = serializers.IntegerField(source="reserved_balance")
    available = serializers.IntegerField(source="available_balance")

    class Meta:
        model = CreditWallet
        fields = ("balance", "reserved", "available")


class CreditTransactionSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="transaction_type")
    amount = serializers.IntegerField(source="balance_delta")
    reserved_change = serializers.IntegerField(source="reserved_delta")
    generation_id = serializers.UUIDField(source="generation_id_snapshot", allow_null=True)

    class Meta:
        model = CreditTransaction
        fields = (
            "id",
            "type",
            "amount",
            "reserved_change",
            "reason",
            "generation_id",
            "created_at",
        )
