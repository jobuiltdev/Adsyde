from django.urls import reverse
from rest_framework import serializers

from .models import Asset
from .validation import inspect_image, safe_original_filename


class AssetSerializer(serializers.ModelSerializer):
    access_url = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = (
            "id",
            "category",
            "original_filename",
            "mime_type",
            "size",
            "width",
            "height",
            "created_at",
            "access_url",
        )
        read_only_fields = fields

    def get_access_url(self, obj):
        request = self.context.get("request")
        path = reverse(
            "project-asset-content", kwargs={"project_id": obj.project_id, "asset_id": obj.pk}
        )
        return request.build_absolute_uri(path) if request else path


class AssetUploadSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=Asset._meta.get_field("category").choices)
    file = serializers.FileField()

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {field: ["Unknown field."] for field in sorted(unknown)}
            )
        return super().to_internal_value(data)

    def validate_file(self, value):
        mime_type, extension, width, height = inspect_image(value)
        value._asset_metadata = {
            "mime_type": mime_type,
            "extension": extension,
            "width": width,
            "height": height,
            "size": value.size,
            "original_filename": safe_original_filename(value.name),
        }
        return value
