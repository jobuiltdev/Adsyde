import json
import uuid

from .base import VideoProvider
from .exceptions import (
    InvalidProviderResponseError,
    ProviderAcceptanceUnknownError,
    ProviderRejectedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .types import (
    GenerationRequest,
    ProviderCallback,
    ProviderCapabilities,
    ProviderModel,
    ProviderStatus,
    ResultDescriptor,
    StatusResult,
    SubmissionResult,
)


class MockVideoProvider(VideoProvider):
    key = "mock"
    capabilities = ProviderCapabilities(
        supports_text_to_video=True,
        supports_reference_images=False,
        max_reference_images=0,
        supports_cancel=True,
        supports_polling=True,
        supports_webhooks=True,
        supports_idempotency_key=True,
        supports_external_reference_lookup=True,
    )
    models = (
        ProviderModel(
            "mock-standard", "Standard", True, ("9:16", "1:1", "16:9"), (5, 8, 10, 15, 20)
        ),
        ProviderModel("mock-premium", "Premium", True, ("9:16", "1:1", "16:9"), (5, 10, 15, 20)),
    )

    def __init__(self, profile: str = "native"):
        if profile not in {"native", "external_reference", "neither"}:
            raise ValueError("Unknown mock capability profile.")
        self.profile = profile
        if profile != "native":
            self.capabilities = ProviderCapabilities(
                **{
                    **self.capabilities.__dict__,
                    "supports_idempotency_key": False,
                    "supports_external_reference_lookup": profile == "external_reference",
                }
            )

    def _job_id(self, key: str) -> str:
        return f"mock-{uuid.uuid5(uuid.NAMESPACE_URL, key)}"

    def submit_generation(self, request: GenerationRequest) -> SubmissionResult:
        job_id = self._job_id(request.idempotency_key)
        if request.scenario == "rejection":
            raise ProviderRejectedError("The request was rejected by provider policy.")
        if request.scenario == "persistent_503" or (
            request.scenario == "transient_503" and request.submission_attempt == 1
        ):
            raise ProviderUnavailableError("The provider is temporarily unavailable.")
        if request.scenario == "timeout_before_acceptance" and request.submission_attempt == 1:
            raise ProviderTimeoutError("The provider did not accept the request in time.")
        if request.scenario in {
            "uncertain_success",
            "uncertain_failure",
            "uncertain_unresolved",
        }:
            raise ProviderAcceptanceUnknownError(job_id)
        if request.scenario == "malformed_response":
            raise InvalidProviderResponseError("The provider returned an invalid response.")
        return SubmissionResult(provider_job_id=job_id, request_id=f"request-{job_id}")

    def get_status(self, job_id: str, *, scenario: str, poll_attempt: int) -> StatusResult:
        if not job_id.startswith("mock-"):
            raise InvalidProviderResponseError("The provider job identifier is invalid.")
        if scenario == "provider_failure":
            return StatusResult(
                ProviderStatus.FAILED,
                error_code="GENERATION_FAILED",
                error_detail="Generation failed at the provider.",
            )
        threshold = 4 if scenario == "slow" else 2
        if poll_attempt < threshold:
            return StatusResult(ProviderStatus.PROCESSING)
        return StatusResult(ProviderStatus.COMPLETED)

    def reconcile(
        self, external_reference: str, provider_job_id: str, *, scenario: str, attempt: int
    ) -> StatusResult:
        job_id = provider_job_id or self._job_id(external_reference)
        if self.profile == "neither" and not provider_job_id:
            return StatusResult(ProviderStatus.UNKNOWN)
        if scenario == "uncertain_unresolved":
            return StatusResult(ProviderStatus.UNKNOWN, provider_job_id=job_id)
        if attempt < 2:
            return StatusResult(ProviderStatus.PROCESSING, provider_job_id=job_id)
        if scenario == "uncertain_failure":
            return StatusResult(
                ProviderStatus.FAILED,
                error_code="GENERATION_FAILED",
                error_detail="Generation failed while provider state was reconciled.",
            )
        return StatusResult(ProviderStatus.COMPLETED)

    def cancel(self, job_id: str) -> bool:
        return job_id.startswith("mock-")

    def fetch_result(self, job_id: str) -> ResultDescriptor:
        from apps.generations.services import MOCK_VIDEO

        if not job_id.startswith("mock-"):
            raise InvalidProviderResponseError("The provider job identifier is invalid.")
        return ResultDescriptor(job_id, "video/mp4", len(MOCK_VIDEO), MOCK_VIDEO)

    def parse_callback(self, payload: bytes) -> ProviderCallback:
        try:
            data = json.loads(payload)
            values = (data["event_id"], data["provider_job_id"], data["event_type"])
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise InvalidProviderResponseError("The callback payload is invalid.") from exc
        if not all(isinstance(item, str) and item for item in values[:2]):
            raise InvalidProviderResponseError("The callback identifiers are invalid.")
        if values[2] not in {"completed", "failed", "processing"}:
            raise InvalidProviderResponseError("The callback event type is invalid.")
        return ProviderCallback(*values)
