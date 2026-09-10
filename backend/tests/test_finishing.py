from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.credits.models import GenerationCharge
from apps.credits.services import grant_credits
from apps.finishing.captions import export_captions, timestamp
from apps.finishing.models import AdFinish, FinishRevision, RenderedAd
from apps.finishing.renderer import LocalRenderer, RenderRequest
from apps.generations.models import Generation, GenerationStatus
from apps.projects.models import Project


def user(email):
    account = User.objects.create_user(email, "valid-test-password-72!")
    account.email_verified_at = timezone.now()
    account.save(update_fields=["email_verified_at"])
    return account


def client_for(account):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(account).access_token}")
    return client


def generation_for(owner, *, status=GenerationStatus.COMPLETED, with_result=True):
    project = Project.objects.create(owner=owner, name="Launch")
    generation = Generation.objects.create(
        project=project,
        created_by=owner,
        prompt="Exact source prompt",
        model="mock-standard",
        aspect_ratio="9:16",
        duration_seconds=10,
        status=status,
        result_mime_type="video/mp4",
    )
    if with_result:
        generation.result_file.save("result.mp4", ContentFile(b"\x00\x00\x00\x18ftypisomfixture"))
    return generation


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def test_caption_timestamp_and_exports_are_standard():
    segments = [{"order": 1, "start_ms": 0, "end_ms": 2050, "text": "Hello <script>"}]
    assert timestamp(3_723_004) == "01:02:03,004"
    assert "00:00:00,000 --> 00:00:02,050" in export_captions(segments)
    assert export_captions(segments, vtt=True).startswith("WEBVTT")
    assert "Hello <script>" in export_captions(segments)


def test_local_renderer_validates_mp4_without_mutating_source():
    from io import BytesIO

    content = b"\x00\x00\x00\x18ftypisomfixture"
    source = BytesIO(content)
    result = LocalRenderer().render(RenderRequest(source, 10_000, "9:16"))
    assert result.content == content
    assert result.mime_type == "video/mp4"
    with pytest.raises(ValueError):
        LocalRenderer().render(RenderRequest(BytesIO(b"bad"), 10_000, "9:16"))


@pytest.mark.django_db
def test_finish_requires_completed_owned_available_generation():
    owner, stranger = user("owner@example.com"), user("other@example.com")
    pending = generation_for(owner, status=GenerationStatus.PROCESSING)
    client = client_for(owner)
    assert client.post(f"/api/v1/generations/{pending.pk}/finishes/").status_code == 400
    completed = generation_for(owner)
    assert (
        client_for(stranger).post(f"/api/v1/generations/{completed.pk}/finishes/").status_code
        == 404
    )


@pytest.mark.django_db
def test_create_edit_render_download_and_zero_cost():
    owner = user("owner@example.com")
    generation = generation_for(owner)
    client = client_for(owner)
    created = client.post(f"/api/v1/generations/{generation.pk}/finishes/")
    assert created.status_code == 201
    finish = created.json()
    segments = [{"order": 1, "start_ms": 0, "end_ms": 10_000, "text": "Shop now"}]
    updated = client.patch(
        f"/api/v1/finishes/{finish['id']}/",
        {
            "caption_segments": segments,
            "music_enabled": True,
            "music_key": "upbeat",
            "watermark_enabled": True,
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="finish-version-two",
    )
    assert updated.status_code == 200
    second = updated.json()
    assert second["number"] == 2
    rendered = client.post(f"/api/v1/finishes/{finish['id']}/revisions/{second['id']}/render/")
    assert rendered.status_code == 201
    output = rendered.json()
    assert output["size_bytes"] > 0
    assert output["watermark_applied"] is False
    assert client.get(f"/api/v1/finished-ads/{output['id']}/content/").status_code == 200
    assert (
        client.get(
            f"/api/v1/finishes/{finish['id']}/revisions/{second['id']}/captions/srt/"
        ).status_code
        == 200
    )
    assert not GenerationCharge.objects.exists()
    assert generation.result_file.read() == b"\x00\x00\x00\x18ftypisomfixture"


@pytest.mark.django_db
def test_render_and_revision_requests_are_idempotent():
    owner = user("owner@example.com")
    generation = generation_for(owner)
    client = client_for(owner)
    finish = client.post(f"/api/v1/generations/{generation.pk}/finishes/").json()
    url = f"/api/v1/finishes/{finish['id']}/"
    first = client.patch(url, {}, format="json", HTTP_IDEMPOTENCY_KEY="same-request")
    repeat = client.patch(url, {}, format="json", HTTP_IDEMPOTENCY_KEY="same-request")
    assert first.json()["id"] == repeat.json()["id"]
    render_url = f"/api/v1/finishes/{finish['id']}/revisions/{first.json()['id']}/render/"
    first_output = client.post(render_url)
    repeat_output = client.post(render_url)
    assert first_output.json()["id"] == repeat_output.json()["id"]
    assert RenderedAd.objects.count() == 1


@pytest.mark.django_db
def test_caption_voice_music_and_thumbnail_validation():
    owner = user("owner@example.com")
    generation = generation_for(owner)
    client = client_for(owner)
    finish = client.post(f"/api/v1/generations/{generation.pk}/finishes/").json()
    url = f"/api/v1/finishes/{finish['id']}/"
    invalid = client.patch(
        url,
        {
            "caption_segments": [{"order": 1, "start_ms": 9000, "end_ms": 11000, "text": "Late"}],
            "voice_key": "celebrity",
            "music_volume_percent": 101,
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="invalid-request",
    )
    assert invalid.status_code == 400
    assert FinishRevision.objects.filter(finish_id=finish["id"]).count() == 1


@pytest.mark.django_db
def test_private_output_and_subtitle_isolation():
    owner, stranger = user("owner@example.com"), user("other@example.com")
    generation = generation_for(owner)
    client = client_for(owner)
    finish = client.post(f"/api/v1/generations/{generation.pk}/finishes/").json()
    revision = finish["revisions"][0]
    output = client.post(
        f"/api/v1/finishes/{finish['id']}/revisions/{revision['id']}/render/"
    ).json()
    other = client_for(stranger)
    assert other.get(f"/api/v1/finishes/{finish['id']}/").status_code == 404
    assert (
        other.post(
            f"/api/v1/finishes/{finish['id']}/revisions/{revision['id']}/render/"
        ).status_code
        == 404
    )
    assert other.get(f"/api/v1/finished-ads/{output['id']}/content/").status_code == 404
    assert (
        other.get(
            f"/api/v1/finishes/{finish['id']}/revisions/{revision['id']}/captions/vtt/"
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_delete_draft_and_archive_completed_finish():
    owner = user("owner@example.com")
    generation = generation_for(owner)
    client = client_for(owner)
    draft = client.post(f"/api/v1/generations/{generation.pk}/finishes/").json()
    assert client.delete(f"/api/v1/finishes/{draft['id']}/").status_code == 204
    assert not AdFinish.objects.filter(pk=draft["id"]).exists()
    completed = client.post(f"/api/v1/generations/{generation.pk}/finishes/").json()
    revision = completed["revisions"][0]
    client.post(f"/api/v1/finishes/{completed['id']}/revisions/{revision['id']}/render/")
    assert client.delete(f"/api/v1/finishes/{completed['id']}/").status_code == 204
    assert AdFinish.objects.get(pk=completed["id"]).status == "archived"


@pytest.mark.django_db
def test_regenerate_is_exact_charged_and_idempotent(settings):
    settings.CREDIT_DEVELOPMENT_INITIAL_GRANT = 0
    owner = user("owner@example.com")
    source = generation_for(owner)
    grant_credits(owner, 500, "Test", "test:fund-regenerate")
    client = client_for(owner)
    url = f"/api/v1/generations/{source.pk}/regenerate/"
    with patch("apps.generations.tasks.submit_generation_task.delay"):
        first = client.post(url, HTTP_IDEMPOTENCY_KEY="regenerate-one")
        repeat = client.post(url, HTTP_IDEMPOTENCY_KEY="regenerate-one")
    assert first.status_code == repeat.status_code == 201
    assert first.json()["id"] == repeat.json()["id"]
    created = Generation.objects.get(pk=first.json()["id"])
    assert created.pk != source.pk
    assert created.prompt == source.prompt
    assert GenerationCharge.objects.filter(generation=created).count() == 1
    assert source.status == GenerationStatus.COMPLETED


@pytest.mark.django_db
def test_prompt_only_duplicate_copies_configuration_not_history():
    owner = user("owner@example.com")
    source = generation_for(owner)
    response = client_for(owner).post(f"/api/v1/generations/{source.pk}/duplicate/")
    assert response.status_code == 200
    assert response.json() == {
        "mode": "prompt",
        "prompt": source.prompt,
        "model": source.model,
        "aspect_ratio": source.aspect_ratio,
        "duration_seconds": source.duration_seconds,
    }
    assert Generation.objects.count() == 1
    assert not GenerationCharge.objects.exists()
