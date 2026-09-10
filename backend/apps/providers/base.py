from abc import ABC, abstractmethod

from .types import (
    GenerationRequest,
    ProviderCallback,
    ProviderCapabilities,
    ProviderModel,
    ResultDescriptor,
    StatusResult,
    SubmissionResult,
)


class VideoProvider(ABC):
    key: str
    capabilities: ProviderCapabilities
    models: tuple[ProviderModel, ...]

    @property
    def supported_models(self) -> frozenset[str]:
        return frozenset(model.key for model in self.models if model.enabled)

    @abstractmethod
    def submit_generation(self, request: GenerationRequest) -> SubmissionResult: ...

    @abstractmethod
    def get_status(self, job_id: str, *, scenario: str, poll_attempt: int) -> StatusResult: ...

    @abstractmethod
    def cancel(self, job_id: str) -> bool: ...

    @abstractmethod
    def reconcile(
        self, external_reference: str, provider_job_id: str, *, scenario: str, attempt: int
    ) -> StatusResult: ...

    @abstractmethod
    def fetch_result(self, job_id: str) -> ResultDescriptor: ...

    def parse_callback(self, payload: bytes) -> ProviderCallback:
        raise NotImplementedError

    def estimate_cost(self, request: GenerationRequest) -> int:
        return 0
