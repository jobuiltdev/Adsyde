from dataclasses import dataclass


@dataclass(frozen=True)
class RenderRequest:
    source: object
    duration_ms: int
    aspect_ratio: str


@dataclass(frozen=True)
class RenderResult:
    content: bytes
    mime_type: str
    duration_ms: int
    aspect_ratio: str


class FinishingRenderer:
    version = "local-copy-v1"

    def render(self, request):
        raise NotImplementedError


class LocalRenderer(FinishingRenderer):
    def render(self, request):
        content = request.source.read()
        if not content or len(content) > 100 * 1024 * 1024:
            raise ValueError("Source media is unavailable or invalid.")
        if content[4:8] != b"ftyp":
            raise ValueError("Source media is not a supported MP4 file.")
        return RenderResult(content, "video/mp4", request.duration_ms, request.aspect_ratio)
