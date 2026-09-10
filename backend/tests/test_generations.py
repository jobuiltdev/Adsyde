from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.generations.models import Generation, GenerationStatus, ProviderEvent
from apps.generations.services import (
    InvalidTransition,
    cancel_generation,
    process_provider_event,
    transition_generation,
)
from apps.generations.tasks import submit_generation_task
from apps.projects.models import Project
from apps.providers.exceptions import ProviderRejectedError, UnknownProviderError
from apps.providers.registry import get_provider
from apps.providers.types import GenerationRequest
from config.celery import app as celery_app

User = get_user_model()


@pytest.fixture(autouse=True)
def isolated(settings, tmp_path):
    cache.clear()
    settings.MEDIA_ROOT = tmp_path
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False


def make_user(email):
    account = User.objects.create_user(email, "valid-test-password-72!")
    account.email_verified_at = timezone.now()
    account.save(update_fields=["email_verified_at"])
    return account


def auth_client(account):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(account).access_token}")
    return client


def make_generation(scenario="success", status=GenerationStatus.QUEUED, owner=None):
    owner = owner or make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Campaign")
    return Generation.objects.create(
        project=project,
        created_by=owner,
        prompt="Create a premium fashion advertisement.",
        model="mock-standard",
        aspect_ratio="9:16",
        duration_seconds=8,
        status=status,
        mock_scenario=scenario,
    )


@pytest.mark.django_db
def test_state_machine_sets_timestamps_and_protects_terminal_state():
    generation = make_generation()
    transition_generation(generation.pk, GenerationStatus.SUBMITTED, provider_job_id="mock-job")
    transition_generation(generation.pk, GenerationStatus.PROCESSING)
    transition_generation(generation.pk, GenerationStatus.COMPLETED)
    generation.refresh_from_db()
    assert generation.submitted_at
    assert generation.started_at
    assert generation.completed_at
    with pytest.raises(InvalidTransition):
        transition_generation(generation.pk, GenerationStatus.PROCESSING)


@pytest.mark.django_db
def test_generation_database_constraints():
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Campaign")
    with pytest.raises(IntegrityError), transaction.atomic():
        Generation.objects.create(
            project=project,
            created_by=owner,
            prompt="",
            model="mock-standard",
            aspect_ratio="4:3",
            duration_seconds=0,
            status="invalid",
        )


def test_provider_registry_contract_and_error():
    provider = get_provider("mock")
    request = GenerationRequest("key", "prompt", "9:16", 8, "mock-standard")
    assert provider.submit_generation(request).job_id.startswith("mock-")
    assert provider.estimate_cost(request) == 0
    with pytest.raises(UnknownProviderError):
        get_provider("missing")


def test_mock_provider_rejection_and_stable_idempotency_key():
    provider = get_provider("mock")
    request = GenerationRequest("same-key", "prompt", "9:16", 8, "mock-standard")
    assert provider.submit_generation(request) == provider.submit_generation(request)
    rejected = GenerationRequest(
        "rejected", "prompt", "9:16", 8, "mock-standard", scenario="rejection"
    )
    with pytest.raises(ProviderRejectedError):
        provider.submit_generation(rejected)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("success", GenerationStatus.COMPLETED),
        ("slow", GenerationStatus.COMPLETED),
        ("provider_failure", GenerationStatus.FAILED),
        ("rejection", GenerationStatus.FAILED),
        ("malformed_response", GenerationStatus.FAILED),
        ("transient_503", GenerationStatus.COMPLETED),
        ("persistent_503", GenerationStatus.FAILED),
        ("timeout_before_acceptance", GenerationStatus.COMPLETED),
        ("uncertain_success", GenerationStatus.COMPLETED),
        ("uncertain_failure", GenerationStatus.FAILED),
    ],
)
def test_task_orchestration_scenarios(settings, scenario, expected):
    settings.GENERATION_POLL_INTERVAL_SECONDS = 0
    generation = make_generation(scenario=scenario)
    submit_generation_task.delay(str(generation.pk))
    generation.refresh_from_db()
    assert generation.status == expected
    if scenario.startswith("uncertain"):
        assert generation.provider_job_id
        assert generation.reconciliation_attempts == 2
    if scenario == "persistent_503":
        assert generation.submission_attempts == settings.GENERATION_MAX_TASK_ATTEMPTS


@pytest.mark.django_db(transaction=True)
def test_duplicate_submission_and_polling_are_idempotent(settings):
    settings.GENERATION_POLL_INTERVAL_SECONDS = 0
    generation = make_generation()
    submit_generation_task.delay(str(generation.pk))
    generation.refresh_from_db()
    job_id = generation.provider_job_id
    attempts = generation.submission_attempts
    submit_generation_task.delay(str(generation.pk))
    generation.refresh_from_db()
    assert generation.status == GenerationStatus.COMPLETED
    assert generation.provider_job_id == job_id
    assert generation.submission_attempts == attempts


@pytest.mark.django_db
def test_duplicate_and_late_provider_events_preserve_terminal_state():
    generation = make_generation(status=GenerationStatus.PROCESSING)
    process_provider_event(generation.pk, "mock", "event-1", "failed")
    process_provider_event(generation.pk, "mock", "event-1", "failed")
    process_provider_event(generation.pk, "mock", "late-success", "completed")
    generation.refresh_from_db()
    assert generation.status == GenerationStatus.FAILED
    assert ProviderEvent.objects.count() == 2
    assert not generation.result_file


@pytest.mark.django_db
def test_generation_api_requires_authentication_and_enforces_ownership():
    owner = make_user("owner@example.com")
    other = make_user("other@example.com")
    project = Project.objects.create(owner=owner, name="Campaign")
    generation = make_generation(owner=owner)
    list_url = f"/api/v1/projects/{project.pk}/generations/"
    assert APIClient().get(list_url).status_code == 401
    assert auth_client(other).get(list_url).status_code == 404
    detail = f"/api/v1/projects/{generation.project_id}/generations/{generation.pk}/"
    assert auth_client(other).get(detail).status_code == 404


@pytest.mark.django_db
def test_generation_create_queues_only_after_commit(django_capture_on_commit_callbacks):
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Campaign")
    url = f"/api/v1/projects/{project.pk}/generations/"
    payload = {
        "prompt": "Create an elegant product advertisement.",
        "aspect_ratio": "16:9",
        "duration_seconds": 10,
        "model": "mock-standard",
    }
    with patch("apps.generations.tasks.submit_generation_task.delay") as delay:
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            response = auth_client(owner).post(url, payload, format="json")
        assert response.status_code == 201
        assert response.json()["status"] == GenerationStatus.QUEUED
        assert not delay.called
        assert len(callbacks) == 1
        callbacks[0]()
        delay.assert_called_once()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": "", "aspect_ratio": "9:16", "duration_seconds": 8, "model": "mock-standard"},
        {"prompt": "valid", "aspect_ratio": "4:3", "duration_seconds": 8, "model": "mock-standard"},
        {
            "prompt": "valid",
            "aspect_ratio": "9:16",
            "duration_seconds": 2,
            "model": "mock-standard",
        },
        {"prompt": "valid", "aspect_ratio": "9:16", "duration_seconds": 8, "model": "real-model"},
        {
            "prompt": "valid",
            "aspect_ratio": "9:16",
            "duration_seconds": 8,
            "model": "mock-standard",
            "created_by": "x",
        },
    ],
)
def test_generation_input_validation(payload):
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Campaign")
    response = auth_client(owner).post(
        f"/api/v1/projects/{project.pk}/generations/", payload, format="json"
    )
    assert response.status_code == 400
    assert set(response.json()) == {"error"}


@pytest.mark.django_db
def test_active_limit_and_submission_throttle(settings):
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Campaign")
    settings.GENERATION_MAX_ACTIVE_PER_USER = 1
    make_generation(owner=owner)
    payload = {
        "prompt": "valid",
        "aspect_ratio": "9:16",
        "duration_seconds": 8,
        "model": "mock-standard",
    }
    client = auth_client(owner)
    url = f"/api/v1/projects/{project.pk}/generations/"
    assert client.post(url, payload, format="json").status_code == 400
    settings.GENERATION_MAX_ACTIVE_PER_USER = 5
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["generation_submit"] = "1/hour"
    cache.clear()
    assert client.post(url, payload, format="json").status_code == 201
    assert client.post(url, payload, format="json").status_code == 429


@pytest.mark.django_db
def test_cancellation_rules_are_idempotent():
    generation = make_generation()
    cancel_generation(generation)
    generation.refresh_from_db()
    assert generation.status == GenerationStatus.CANCELLED
    assert cancel_generation(generation).status == GenerationStatus.CANCELLED
    completed = make_generation(status=GenerationStatus.COMPLETED, owner=generation.created_by)
    with pytest.raises(ValidationError):
        cancel_generation(completed)


@pytest.mark.django_db(transaction=True)
def test_completed_result_is_private_and_has_no_storage_path(settings):
    settings.GENERATION_POLL_INTERVAL_SECONDS = 0
    generation = make_generation()
    submit_generation_task.delay(str(generation.pk))
    generation.refresh_from_db()
    path = f"/api/v1/projects/{generation.project_id}/generations/{generation.pk}/result/"
    assert APIClient().get(path).status_code == 401
    response = auth_client(generation.created_by).get(path)
    assert response.status_code == 200
    detail = auth_client(generation.created_by).get(path.removesuffix("result/"))
    assert "result_file" not in detail.json()
