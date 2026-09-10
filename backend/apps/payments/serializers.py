from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "internal_reference",
            "package_key",
            "package_name",
            "currency",
            "amount_minor",
            "credits",
            "status",
            "initiated_at",
            "verified_at",
            "succeeded_at",
            "credited_at",
            "created_at",
        )
        read_only_fields = fields


class PaymentInitializeSerializer(serializers.Serializer):
    package = serializers.CharField(max_length=32)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {field: ["Unknown field."] for field in sorted(unknown)}
            )
        return super().to_internal_value(data)
