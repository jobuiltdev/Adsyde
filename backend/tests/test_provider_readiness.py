import json
import time
from dataclasses import replace

import pytest
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from apps.generations.ingestion import ingest_result, validate_provider_url
from apps.generations.models import GenerationStatus, ProviderEvent
from apps.generations.services import MOCK_VIDEO, process_provider_event
from apps.generations.tasks import submit_generation_task
from apps.providers.exceptions import (
    ProviderAcceptanceUnknownError,
    ProviderResultFetchError,
    ProviderUnavailableError,
)
from apps.providers.mock import MockVideoProvider
from apps.providers.policy import RetryDecision, RetryPolicy
from apps.providers.registry import generation_options, get_provider
from apps.providers.types import GenerationRequest, ProviderStatus, ResultDescriptor
from apps.providers.webhooks import sign_payload
from tests.test_generations import auth_client, make_generation, make_user


def provider_request(**changes):
    values = {
        "external_reference": "stable-reference",
        "generation_id": "generation-id",
        "prompt": "A concise advertisement.",
        "aspect_ratio": "9:16",
        "duration_seconds": 8,
        "model": "mock-standard",
    }
    values.update(changes)
    return GenerationRequest(**values)


def test_capability_catalog_is_normalized_and_contains_no_configuration():
    provider = get_provider("mock")
    assert provider.capabilities.supports_text_to_video
    assert provider.capabilities.supports_idempotency_key
    assert len(provider.supported_models) == len(provider.models)
    options = generation_options()
    assert options["provider"] == "mock"
    assert {item["key"] for item in options["models"]} == provider.supported_models
    assert "secret" not in json.dumps(options).lower()


@pytest.mark.django_db
def test_options_endpoint_is_authenticated_and_non_secret():
    assert APIClient().get("/api/v1/generation-options/").status_code == 401
    response = auth_client(make_user("options@example.com")).get("/api/v1/generation-options/")
    assert response.status_code == 200
    assert response.json()["models"][0]["aspect_ratios"]
    assert "secret" not in response.content.decode().lower()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value",
    [("aspect_ratio", "4:3"), ("duration_seconds", 6), ("model", "disabled-model")],
)
def test_server_rejects_unsupported_model_options(field, value):
    owner = make_user(f"{field}@example.com")
    generation = make_generation(owner=owner)
    payload = {
        "prompt": "A valid prompt.",
        "aspect_ratio": "9:16",
        "duration_seconds": 8,
        "model": "mock-standard",
        field: value,
    }
    response = auth_client(owner).post(
        f"/api/v1/projects/{generation.project_id}/generations/", payload, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("profile", "native", "lookup"),
    [
        ("native", True, True),
        ("external_reference", False, True),
        ("neither", False, False),
    ],
)
def test_mock_capability_profiles(profile, native, lookup):
    provider = MockVideoProvider(profile)
    assert provider.capabilities.supports_idempotency_key is native
    assert provider.capabilities.supports_external_reference_lookup is lookup
    first = provider.submit_generation(provider_request())
    second = provider.submit_generation(provider_request())
    assert first.provider_job_id == second.provider_job_id


def test_retry_policy_never_retries_ambiguous_submission():
    policy = RetryPolicy(3)
    capabilities = MockVideoProvider("neither").capabilities
    assert (
        policy.submission_decision(ProviderAcceptanceUnknownError(), 1, capabilities)
        == RetryDecision.RECONCILE
    )
    assert (
        policy.submission_decision(ProviderUnavailableError(), 1, capabilities)
        == RetryDecision.RETRY
    )
    assert (
        policy.submission_decision(ProviderUnavailableError(), 3, capabilities)
        == RetryDecision.FAIL
    )


def test_reconciliation_contract_profiles():
    request = provider_request()
    for profile in ("native", "external_reference"):
        provider = MockVideoProvider(profile)
        result = provider.reconcile(
            request.external_reference, "", scenario="uncertain_success", attempt=2
        )
        assert result.status == ProviderStatus.COMPLETED
    assert (
        MockVideoProvider("neither")
        .reconcile(request.external_reference, "", scenario="uncertain_success", attempt=2)
        .status
        == ProviderStatus.UNKNOWN
    )


@pytest.mark.django_db(transaction=True)
def test_unresolved_reconciliation_exhausts_explicitly(settings):
    settings.GENERATION_POLL_INTERVAL_SECONDS = 0
    settings.GENERATION_MAX_RECONCILIATION_ATTEMPTS = 2
    generation = make_generation(scenario="uncertain_unresolved")
    submit_generation_task.delay(str(generation.pk))
    generation.refresh_from_db()
    assert generation.status == GenerationStatus.FAILED
    assert generation.error_code == "PROVIDER_STATE_UNRESOLVED"
    assert generation.unknown_since
    assert generation.last_reconciled_at
    assert generation.reconciliation_attempts == 2


@pytest.mark.django_db
def test_result_ingestion_validates_and_is_idempotent(settings):
    generation = make_generation(status=GenerationStatus.PROCESSING)
    descriptor = ResultDescriptor("mock-job", "video/mp4", len(MOCK_VIDEO), MOCK_VIDEO)
    ingest_result(generation, descriptor)
    first_name = generation.result_file.name
    ingest_result(generation, descriptor)
    assert generation.result_file.name == first_name
    assert generation.result_ingested_at
    assert default_storage.exists(first_name)

    bad = replace(descriptor, content=b"not-video", size=9)
    other = make_generation(status=GenerationStatus.PROCESSING, owner=generation.created_by)
    with pytest.raises(ProviderResultFetchError):
        ingest_result(other, bad)
    settings.GENERATION_MAX_RESULT_BYTES = 4
    with pytest.raises(ProviderResultFetchError):
        ingest_result(other, descriptor)


@pytest.mark.parametrize(
    "url",
    [
        "http://media.example/result.mp4",
        "https://127.0.0.1/result.mp4",
        "https://user:pass@media.example/result.mp4",
        "https://unapproved.example/result.mp4",
    ],
)
def test_provider_result_url_boundary_rejects_unsafe_locations(url):
    with pytest.raises(ProviderResultFetchError):
        validate_provider_url(url, ("media.example",))


@pytest.mark.django_db
def test_signed_callback_replay_and_late_terminal_event(settings):
    settings.MOCK_PROVIDER_WEBHOOK_SECRET = "test-only-webhook-secret"
    generation = make_generation(status=GenerationStatus.PROCESSING)
    generation.provider_job_id = "mock-callback-job"
    generation.save(update_fields=["provider_job_id"])
    payload = json.dumps(
        {
            "event_id": "event-complete",
            "provider_job_id": generation.provider_job_id,
            "event_type": "completed",
        }
    ).encode()
    timestamp = int(time.time())
    signature = sign_payload(settings.MOCK_PROVIDER_WEBHOOK_SECRET, timestamp, payload)
    client = APIClient()
    for _ in range(2):
        response = client.post(
            "/api/v1/provider-callbacks/mock/",
            payload,
            content_type="application/json",
            HTTP_X_ADSYDE_TIMESTAMP=str(timestamp),
            HTTP_X_ADSYDE_SIGNATURE=signature,
        )
        assert response.status_code == 204
    generation.refresh_from_db()
    assert generation.status == GenerationStatus.COMPLETED
    assert ProviderEvent.objects.filter(event_id="event-complete").count() == 1

    process_provider_event(
        generation.pk, "mock", "late-failure", "failed", generation.provider_job_id
    )
    generation.refresh_from_db()
    assert generation.status == GenerationStatus.COMPLETED


@pytest.mark.django_db
def test_callback_rejects_invalid_stale_and_malformed_requests(settings):
    settings.MOCK_PROVIDER_WEBHOOK_SECRET = "test-only-webhook-secret"
    client = APIClient()
    assert (
        client.post(
            "/api/v1/provider-callbacks/mock/", b"{}", content_type="application/json"
        ).status_code
        == 401
    )
    stale = int(time.time()) - settings.PROVIDER_WEBHOOK_TOLERANCE_SECONDS - 1
    signature = sign_payload(settings.MOCK_PROVIDER_WEBHOOK_SECRET, stale, b"{}")
    assert (
        client.post(
            "/api/v1/provider-callbacks/mock/",
            b"{}",
            content_type="application/json",
            HTTP_X_ADSYDE_TIMESTAMP=str(stale),
            HTTP_X_ADSYDE_SIGNATURE=signature,
        ).status_code
        == 401
    )

    now = int(time.time())
    malformed = b"{}"
    signature = sign_payload(settings.MOCK_PROVIDER_WEBHOOK_SECRET, now, malformed)
    assert (
        client.post(
            "/api/v1/provider-callbacks/mock/",
            malformed,
            content_type="application/json",
            HTTP_X_ADSYDE_TIMESTAMP=str(now),
            HTTP_X_ADSYDE_SIGNATURE=signature,
        ).status_code
        == 400
    )
