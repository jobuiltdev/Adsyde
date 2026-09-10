from .exceptions import UnknownProviderError
from .mock import MockVideoProvider

_PROVIDERS = {MockVideoProvider.key: MockVideoProvider()}


def get_provider(key: str):
    try:
        return _PROVIDERS[key]
    except KeyError as exc:
        raise UnknownProviderError("The configured provider is unavailable.") from exc
