from rest_framework import serializers

from .models import AdFinish, FinishRevision, RenderedAd


class FinishRevisionSerializer(serializers.ModelSerializer):
    output_id = serializers.UUIDField(source="output.id", read_only=True)

    class Meta:
        model = FinishRevision
        exclude = ("finish", "request_key")
        read_only_fields = ("id", "number", "created_at", "output_id")

    def validate_caption_segments(self, value):
        if len(value) > 100:
            raise serializers.ValidationError("Use no more than 100 caption segments.")
        previous_end = 0
        duration = self.context["duration_ms"]
        for segment in value:
            if not isinstance(segment, dict) or not {"order", "start_ms", "end_ms", "text"} <= set(
                segment
            ):
                raise serializers.ValidationError("Caption structure is invalid.")
            start, end, text = segment["start_ms"], segment["end_ms"], segment["text"]
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or start < previous_end
                or end <= start
                or end > duration
            ):
                raise serializers.ValidationError("Caption timing is invalid or overlapping.")
            if not isinstance(text, str) or not text.strip() or len(text) > 300:
                raise serializers.ValidationError("Caption text is invalid.")
            previous_end = end
        return value

    def validate_voice_script(self, value):
        if len(value) > 4000:
            raise serializers.ValidationError("Voice script is too long.")
        return value

    def validate_voice_key(self, value):
        if value not in {"neutral", "warm", "energetic"}:
            raise serializers.ValidationError("Voice preset is invalid.")
        return value

    def validate_music_key(self, value):
        if value not in {"none", "upbeat", "minimal", "elegant", "energetic"}:
            raise serializers.ValidationError("Music preset is invalid.")
        return value

    def validate_music_volume_percent(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Music volume must be between 0 and 100.")
        return value

    def validate_voice_speed_percent(self, value):
        if not 75 <= value <= 125:
            raise serializers.ValidationError("Voice speed must be between 75 and 125.")
        return value

    def validate_thumbnail_asset(self, value):
        if value and value.project_id != self.context["project_id"]:
            raise serializers.ValidationError("Thumbnail must belong to this project.")
        return value


class RenderedAdSerializer(serializers.ModelSerializer):
    class Meta:
        model = RenderedAd
        exclude = ("file",)


class AdFinishSerializer(serializers.ModelSerializer):
    revisions = FinishRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = AdFinish
        fields = (
            "id",
            "project_id",
            "source_generation_id",
            "source_plan_revision_id",
            "status",
            "revisions",
            "created_at",
            "updated_at",
        )
