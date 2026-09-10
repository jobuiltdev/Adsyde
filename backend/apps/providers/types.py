from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ProviderStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ProviderModel:
    key: str
    display_name: str
    enabled: bool
    supported_aspect_ratios: tuple[str, ...]
    supported_durations: tuple[int, ...]
    supports_reference_images: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    def public_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "display_name": self.display_name,
            "aspect_ratios": list(self.supported_aspect_ratios),
            "durations": list(self.supported_durations),
            "supports_reference_images": self.supports_reference_images,
        }


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_text_to_video: bool
    supports_reference_images: bool
    max_reference_images: int
    supports_cancel: bool
    supports_polling: bool
    supports_webhooks: bool
    supports_idempotency_key: bool
    supports_external_reference_lookup: bool


@dataclass(frozen=True)
class ReferenceInput:
    asset_id: str
    role: str = "reference"
    order: int = 0


@dataclass(frozen=True)
class GenerationRequest:
    external_reference: str
    prompt: str
    aspect_ratio: str
    duration_seconds: int
    model: str
    generation_id: str = ""
    references: tuple[ReferenceInput, ...] = ()
    callback_url: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    scenario: str = "success"
    submission_attempt: int = 1

    @property
    def idempotency_key(self) -> str:
        return self.external_reference


@dataclass(frozen=True)
class ResultDescriptor:
    provider_job_id: str
    mime_type: str
    size: int | None = None
    content: bytes | None = None
    locator: str | None = None
    duration_seconds: int | None = None


@dataclass(frozen=True)
class SubmissionResult:
    provider_job_id: str
    status: ProviderStatus = ProviderStatus.PROCESSING
    accepted: bool = True
    request_id: str = ""

    @property
    def job_id(self) -> str:
        return self.provider_job_id


@dataclass(frozen=True)
class StatusResult:
    status: ProviderStatus
    provider_job_id: str = ""
    progress: int | None = None
    result: ResultDescriptor | None = None
    error_code: str = ""
    error_detail: str = ""


@dataclass(frozen=True)
class ProviderCallback:
    event_id: str
    provider_job_id: str
    event_type: str
