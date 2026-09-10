class ProviderError(Exception):
    code = "GENERATION_FAILED"
    retryable = False
    uncertain = False


class ProviderInvalidRequestError(ProviderError):
    code = "PROVIDER_INVALID_REQUEST"


class ProviderRejectedError(ProviderError):
    code = "PROVIDER_REJECTED"


class ProviderUnsupportedOptionError(ProviderError):
    code = "PROVIDER_UNSUPPORTED_OPTION"


class ProviderConfigurationError(ProviderError):
    code = "PROVIDER_CONFIGURATION_ERROR"


class ProviderUnavailableError(ProviderError):
    code = "PROVIDER_UNAVAILABLE"
    retryable = True


class ProviderRateLimitedError(ProviderError):
    code = "PROVIDER_RATE_LIMITED"
    retryable = True


class ProviderNetworkError(ProviderError):
    code = "PROVIDER_NETWORK_ERROR"
    retryable = True


class ProviderTimeoutError(ProviderNetworkError):
    code = "PROVIDER_TIMEOUT"


class ProviderAcceptanceUnknownError(ProviderError):
    code = "UNKNOWN_PROVIDER_STATE"
    uncertain = True

    def __init__(self, job_id: str = ""):
        super().__init__("Provider acceptance could not be confirmed.")
        self.job_id = job_id


class InvalidProviderResponseError(ProviderError):
    code = "INVALID_PROVIDER_RESPONSE"


class ProviderUnknownJobError(ProviderError):
    code = "PROVIDER_UNKNOWN_JOB"


class ProviderGenerationError(ProviderError):
    code = "GENERATION_FAILED"


class ProviderCancellationError(ProviderError):
    code = "PROVIDER_CANCELLATION_FAILED"


class ProviderResultFetchError(ProviderError):
    code = "PROVIDER_RESULT_FETCH_FAILED"


class UnknownProviderError(ProviderError):
    code = "UNKNOWN_PROVIDER"
