from abc import ABC, abstractmethod

from .types import GenerationRequest, StatusResult, SubmissionResult


class VideoProvider(ABC):
    key: str
    supported_models: frozenset[str]

    @abstractmethod
    def submit_generation(self, request: GenerationRequest) -> SubmissionResult:
        raise NotImplementedError

    @abstractmethod
    def get_status(self, job_id: str, *, scenario: str, poll_attempt: int) -> StatusResult:
        raise NotImplementedError

    @abstractmethod
    def cancel(self, job_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def reconcile(self, job_id: str, *, scenario: str, attempt: int) -> StatusResult:
        raise NotImplementedError

    def estimate_cost(self, request: GenerationRequest) -> int:
        return 0
