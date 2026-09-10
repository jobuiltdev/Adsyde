from dataclasses import dataclass
from enum import StrEnum


class ProviderStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class GenerationRequest:
    idempotency_key: str
    prompt: str
    aspect_ratio: str
    duration_seconds: int
    model: str
    scenario: str = "success"
    submission_attempt: int = 1


@dataclass(frozen=True)
class SubmissionResult:
    job_id: str


@dataclass(frozen=True)
class StatusResult:
    status: ProviderStatus
    error_code: str = ""
    error_detail: str = ""
