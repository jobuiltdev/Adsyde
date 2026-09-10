from django.conf import settings

from .exceptions import UnknownProviderError
from .mock import MockVideoProvider

_PROVIDERS = {MockVideoProvider.key: MockVideoProvider()}


def get_provider(key: str):
    if key not in settings.GENERATION_ENABLED_PROVIDERS:
        raise UnknownProviderError("The configured provider is unavailable.")
    try:
        return _PROVIDERS[key]
    except KeyError as exc:
        raise UnknownProviderError("The configured provider is unavailable.") from exc


def get_active_provider():
    return get_provider(settings.GENERATION_PROVIDER)


def generation_options() -> dict:
    provider = get_active_provider()
    return {
        "provider": provider.key,
        "models": [model.public_dict() for model in provider.models if model.enabled],
    }
