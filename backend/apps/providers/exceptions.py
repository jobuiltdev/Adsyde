class ProviderError(Exception):
    code = "GENERATION_FAILED"
    retryable = False
    uncertain = False


class ProviderRejectedError(ProviderError):
    code = "PROVIDER_REJECTED"


class ProviderUnavailableError(ProviderError):
    code = "PROVIDER_UNAVAILABLE"
    retryable = True


class ProviderTimeoutError(ProviderError):
    code = "PROVIDER_TIMEOUT"
    retryable = True


class ProviderAcceptanceUnknownError(ProviderError):
    code = "UNKNOWN_PROVIDER_STATE"
    uncertain = True

    def __init__(self, job_id: str):
        super().__init__("Provider acceptance could not be confirmed.")
        self.job_id = job_id


class InvalidProviderResponseError(ProviderError):
    code = "INVALID_PROVIDER_RESPONSE"


class UnknownProviderError(ProviderError):
    code = "UNKNOWN_PROVIDER"
