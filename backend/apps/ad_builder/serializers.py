from rest_framework import serializers

from apps.providers.registry import get_active_provider

from .models import AdPlan, AdPlanAsset, AdPlanRevision, AssetRole
from .safety import validate_creative_text


class AssetSelectionSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=AssetRole.choices)
    position = serializers.IntegerField(min_value=0, max_value=7)


class AdPlanWriteSerializer(serializers.ModelSerializer):
    selected_asset_inputs = AssetSelectionSerializer(many=True, required=False, write_only=True)
    selling_points = serializers.ListField(
        child=serializers.CharField(max_length=200), max_length=8, required=False
    )

    class Meta:
        model = AdPlan
        fields = (
            "business_product",
            "offer_objective",
            "audience",
            "style",
            "style_notes",
            "platform",
            "call_to_action",
            "selling_points",
            "model",
            "aspect_ratio",
            "duration_seconds",
            "selected_asset_inputs",
        )
        extra_kwargs = {
            "business_product": {"max_length": 1000},
            "offer_objective": {"max_length": 1000, "required": False},
            "audience": {"max_length": 500, "required": False},
            "style": {"max_length": 32},
        }

    def validate(self, attrs):
        validate_creative_text(
            [
                attrs.get("business_product", ""),
                attrs.get("offer_objective", ""),
                attrs.get("audience", ""),
                attrs.get("style_notes", ""),
                attrs.get("call_to_action", ""),
                *attrs.get("selling_points", []),
            ]
        )
        provider = get_active_provider()
        model_key = attrs.get("model", getattr(self.instance, "model", "mock-standard"))
        model = next(
            (item for item in provider.models if item.key == model_key and item.enabled), None
        )
        if not model:
            raise serializers.ValidationError({"model": ["The selected model is unavailable."]})
        ratio = attrs.get("aspect_ratio", getattr(self.instance, "aspect_ratio", "9:16"))
        duration = attrs.get("duration_seconds", getattr(self.instance, "duration_seconds", 10))
        if ratio not in model.supported_aspect_ratios:
            raise serializers.ValidationError({"aspect_ratio": ["Unsupported aspect ratio."]})
        if duration not in model.supported_durations:
            raise serializers.ValidationError({"duration_seconds": ["Unsupported duration."]})
        return attrs


class AdPlanAssetSerializer(serializers.ModelSerializer):
    asset_id = serializers.UUIDField(source="asset_id_snapshot")
    filename = serializers.CharField(source="filename_snapshot")
    category = serializers.CharField(source="category_snapshot")

    class Meta:
        model = AdPlanAsset
        fields = ("asset_id", "filename", "category", "role", "position")


class AdPlanRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdPlanRevision
        fields = (
            "id",
            "number",
            "variant",
            "template_version",
            "concept",
            "hook",
            "script_sections",
            "shots",
            "planner_prompt",
            "reviewed_concept",
            "reviewed_hook",
            "reviewed_script_sections",
            "reviewed_shots",
            "reviewed_prompt",
            "generation_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "number",
            "variant",
            "template_version",
            "concept",
            "hook",
            "script_sections",
            "shots",
            "planner_prompt",
            "generation_id",
            "created_at",
            "updated_at",
        )

    def validate_reviewed_shots(self, value):
        if len(value) > 8:
            raise serializers.ValidationError("Too many shots.")
        required = {"order", "start_ms", "duration_ms", "visual", "on_screen_text", "voiceover"}
        if any(not isinstance(shot, dict) or not required.issubset(shot) for shot in value):
            raise serializers.ValidationError("Shot plan structure is invalid.")
        return value


class AdPlanSerializer(serializers.ModelSerializer):
    selected_assets = AdPlanAssetSerializer(many=True, read_only=True)
    revisions = AdPlanRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = AdPlan
        fields = (
            "id",
            "project_id",
            "business_product",
            "offer_objective",
            "audience",
            "style",
            "style_notes",
            "platform",
            "call_to_action",
            "selling_points",
            "model",
            "aspect_ratio",
            "duration_seconds",
            "status",
            "planner_version",
            "selected_assets",
            "revisions",
            "created_at",
            "updated_at",
        )
