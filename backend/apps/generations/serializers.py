from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from apps.providers.registry import get_active_provider

from .models import AspectRatio, Generation


class GenerationCreateSerializer(serializers.Serializer):
    prompt = serializers.CharField(trim_whitespace=True)
    aspect_ratio = serializers.ChoiceField(choices=AspectRatio.choices)
    duration_seconds = serializers.IntegerField()
    model = serializers.CharField(max_length=64)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {field: ["Unknown field."] for field in sorted(unknown)}
            )
        return super().to_internal_value(data)

    def validate_prompt(self, value):
        if not value:
            raise serializers.ValidationError("Prompt cannot be empty.")
        if len(value) > settings.GENERATION_MAX_PROMPT_LENGTH:
            raise serializers.ValidationError("Prompt exceeds the configured length limit.")
        return value

    def validate_duration_seconds(self, value):
        if (
            not settings.GENERATION_MIN_DURATION_SECONDS
            <= value
            <= settings.GENERATION_MAX_DURATION_SECONDS
        ):
            raise serializers.ValidationError("Duration is outside the supported range.")
        return value

    def validate(self, attrs):
        provider = get_active_provider()
        model = next((item for item in provider.models if item.key == attrs["model"]), None)
        if model is None or not model.enabled:
            raise serializers.ValidationError({"model": ["The selected model is not supported."]})
        if attrs["aspect_ratio"] not in model.supported_aspect_ratios:
            raise serializers.ValidationError(
                {"aspect_ratio": ["The selected aspect ratio is not supported by this model."]}
            )
        if attrs["duration_seconds"] not in model.supported_durations:
            raise serializers.ValidationError(
                {"duration_seconds": ["The selected duration is not supported by this model."]}
            )
        return attrs


class GenerationSerializer(serializers.ModelSerializer):
    result_available = serializers.SerializerMethodField()
    result_url = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = (
            "id",
            "prompt",
            "status",
            "aspect_ratio",
            "duration_seconds",
            "provider_key",
            "model",
            "error_code",
            "error_detail",
            "result_available",
            "result_url",
            "submitted_at",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_result_available(self, obj):
        return bool(obj.result_file and obj.status == "completed")

    def get_result_url(self, obj):
        if not self.get_result_available(obj):
            return None
        path = reverse(
            "generation-result",
            kwargs={"project_id": obj.project_id, "generation_id": obj.pk},
        )
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path
