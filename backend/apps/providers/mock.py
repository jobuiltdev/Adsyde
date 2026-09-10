import uuid

from .base import VideoProvider
from .exceptions import (
    InvalidProviderResponseError,
    ProviderAcceptanceUnknownError,
    ProviderRejectedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .types import GenerationRequest, ProviderStatus, StatusResult, SubmissionResult


class MockVideoProvider(VideoProvider):
    key = "mock"
    supported_models = frozenset({"mock-standard", "mock-premium"})

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
        if request.scenario in {"uncertain_success", "uncertain_failure"}:
            raise ProviderAcceptanceUnknownError(job_id)
        if request.scenario == "malformed_response":
            raise InvalidProviderResponseError("The provider returned an invalid response.")
        return SubmissionResult(job_id=job_id)

    def get_status(self, job_id: str, *, scenario: str, poll_attempt: int) -> StatusResult:
        if not job_id.startswith("mock-"):
            raise InvalidProviderResponseError("The provider job identifier is invalid.")
        if scenario == "provider_failure":
            return StatusResult(
                ProviderStatus.FAILED, "GENERATION_FAILED", "Generation failed at the provider."
            )
        threshold = 4 if scenario == "slow" else 2
        if poll_attempt < threshold:
            return StatusResult(ProviderStatus.PROCESSING)
        return StatusResult(ProviderStatus.COMPLETED)

    def reconcile(self, job_id: str, *, scenario: str, attempt: int) -> StatusResult:
        if attempt < 2:
            return StatusResult(ProviderStatus.PROCESSING)
        if scenario == "uncertain_failure":
            return StatusResult(
                ProviderStatus.FAILED,
                "GENERATION_FAILED",
                "Generation failed while provider state was reconciled.",
            )
        return StatusResult(ProviderStatus.COMPLETED)

    def cancel(self, job_id: str) -> bool:
        return job_id.startswith("mock-")
