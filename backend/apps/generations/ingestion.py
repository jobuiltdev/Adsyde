import ipaddress
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.providers.exceptions import ProviderResultFetchError
from apps.providers.types import ResultDescriptor


def validate_provider_url(locator: str, allowed_hosts: tuple[str, ...]) -> None:
    parsed = urlparse(locator)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ProviderResultFetchError("The provider result location is not permitted.")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if address and (address.is_private or address.is_loopback or address.is_link_local):
        raise ProviderResultFetchError("The provider result location is not permitted.")
    if parsed.hostname not in allowed_hosts:
        raise ProviderResultFetchError("The provider result host is not permitted.")


def ingest_result(generation, descriptor: ResultDescriptor):
    if generation.result_file:
        return generation
    if descriptor.locator:
        validate_provider_url(descriptor.locator, settings.PROVIDER_RESULT_ALLOWED_HOSTS)
        raise ProviderResultFetchError("External provider result fetching is not enabled.")
    if descriptor.content is None:
        raise ProviderResultFetchError("The provider result did not contain media.")
    size = len(descriptor.content)
    if descriptor.size is not None and descriptor.size != size:
        raise ProviderResultFetchError("The provider result size was inconsistent.")
    if size > settings.GENERATION_MAX_RESULT_BYTES:
        raise ProviderResultFetchError("The provider result exceeded the size limit.")
    if descriptor.mime_type not in settings.GENERATION_ALLOWED_RESULT_MIME_TYPES:
        raise ProviderResultFetchError("The provider result type is not permitted.")
    if descriptor.mime_type == "video/mp4" and descriptor.content[4:8] != b"ftyp":
        raise ProviderResultFetchError("The provider result media signature was invalid.")
    generation.result_file.save("result.mp4", ContentFile(descriptor.content), save=False)
    generation.result_mime_type = descriptor.mime_type
    generation.result_ingested_at = timezone.now()
    return generation
