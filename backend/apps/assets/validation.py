import re
import warnings

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

FORMAT_METADATA = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


def safe_original_filename(name: str) -> str:
    basename = name.replace("\\", "/").rsplit("/", 1)[-1]
    basename = re.sub(r"[\x00-\x1f\x7f]", "", basename).strip()
    if basename in {"", ".", ".."}:
        return "upload"
    return basename[:255]


def inspect_image(upload):
    if upload.size <= 0:
        raise serializers.ValidationError("The uploaded file is empty.")
    if upload.size > settings.ASSET_MAX_FILE_SIZE:
        raise serializers.ValidationError("The image exceeds the configured file-size limit.")
    try:
        upload.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                image_format = image.format
                width, height = image.size
                if image_format not in FORMAT_METADATA:
                    raise serializers.ValidationError(
                        "Supported image formats are JPEG, PNG, and WebP."
                    )
                if width > settings.ASSET_MAX_DIMENSION or height > settings.ASSET_MAX_DIMENSION:
                    raise serializers.ValidationError(
                        "The image dimensions exceed the configured limit."
                    )
                if width * height > settings.ASSET_MAX_PIXELS:
                    raise serializers.ValidationError(
                        "The image pixel count exceeds the configured limit."
                    )
                image.verify()
            upload.seek(0)
            with Image.open(upload) as image:
                image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise serializers.ValidationError("Upload a valid supported image.") from exc
    except Image.DecompressionBombWarning as exc:
        raise serializers.ValidationError("The image dimensions exceed the safety limit.") from exc
    finally:
        upload.seek(0)
    mime_type, extension = FORMAT_METADATA[image_format]
    return mime_type, extension, width, height
