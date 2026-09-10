from dataclasses import dataclass
from enum import StrEnum

from .exceptions import ProviderError
from .types import ProviderCapabilities


class RetryDecision(StrEnum):
    RETRY = "retry"
    RECONCILE = "reconcile"
    FAIL = "fail"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int

    def submission_decision(
        self, error: ProviderError, attempts: int, capabilities: ProviderCapabilities
    ) -> RetryDecision:
        if error.uncertain:
            return RetryDecision.RECONCILE
        if error.retryable and attempts < self.max_attempts:
            return RetryDecision.RETRY
        return RetryDecision.FAIL
