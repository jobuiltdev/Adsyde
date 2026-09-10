from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.assets.models import Asset
from apps.projects.models import Project

User = get_user_model()


@pytest.fixture(autouse=True)
def isolated_state(settings, tmp_path):
    cache.clear()
    settings.MEDIA_ROOT = tmp_path
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    original_rates = rates.copy()
    yield
    rates.clear()
    rates.update(original_rates)
    cache.clear()


def user(email):
    account = User.objects.create_user(email, "valid-test-password-72!")
    account.email_verified_at = timezone.now()
    account.save(update_fields=["email_verified_at"])
    return account


def client_for(account):
    client = APIClient()
    token = RefreshToken.for_user(account).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def image_upload(name="image.png", image_format="PNG", size=(4, 3), content_type=None):
    content = BytesIO()
    mode = "RGB" if image_format == "JPEG" else "RGBA"
    Image.new(mode, size, color="red").save(content, format=image_format)
    mime = (
        content_type
        or {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "GIF": "image/gif",
        }[image_format]
    )
    return SimpleUploadedFile(name, content.getvalue(), content_type=mime)


def upload(client, project, file=None, category="product_image"):
    return client.post(
        f"/api/v1/projects/{project.pk}/assets/",
        {"category": category, "file": file or image_upload()},
        format="multipart",
    )


@pytest.mark.django_db
def test_project_crud_assigns_owner_and_trims_fields():
    account = user("owner@example.com")
    client = client_for(account)
    rejected_owner = client.post(
        "/api/v1/projects/",
        {
            "name": "  September Sale  ",
            "business_name": "  Zara Fashion  ",
            "owner": str(user("other@example.com").pk),
        },
        format="json",
    )
    assert rejected_owner.status_code == 400
    created = client.post(
        "/api/v1/projects/",
        {"name": "  September Sale  ", "business_name": "  Zara Fashion  "},
        format="json",
    )
    assert created.status_code == 201
    project = Project.objects.get()
    assert project.owner == account
    assert project.name == "September Sale"
    assert project.business_name == "Zara Fashion"
    updated = client.patch(
        f"/api/v1/projects/{project.pk}/", {"brand_style": "  Premium  "}, format="json"
    )
    assert updated.status_code == 200
    assert updated.json()["brand_style"] == "Premium"
    assert client.delete(f"/api/v1/projects/{project.pk}/").status_code == 204
    assert not Project.objects.exists()


@pytest.mark.django_db
def test_projects_require_authentication_and_validate_input():
    assert APIClient().get("/api/v1/projects/").status_code == 401
    client = client_for(user("owner@example.com"))
    blank = client.post("/api/v1/projects/", {"name": "   "}, format="json")
    unknown = client.post(
        "/api/v1/projects/", {"name": "Valid", "unexpected": "value"}, format="json"
    )
    assert blank.status_code == unknown.status_code == 400
    assert set(blank.json()) == {"error"}


@pytest.mark.django_db
def test_project_queries_are_owner_scoped_and_ordered():
    owner = user("owner@example.com")
    other = user("other@example.com")
    older = Project.objects.create(owner=owner, name="Older")
    newer = Project.objects.create(owner=owner, name="Newer")
    foreign = Project.objects.create(owner=other, name="Private")
    client = client_for(owner)
    listed = client.get("/api/v1/projects/")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["results"]] == [str(newer.pk), str(older.pk)]
    assert client.get(f"/api/v1/projects/{older.pk}/").status_code == 200
    assert client.get(f"/api/v1/projects/{foreign.pk}/").status_code == 404
    assert (
        client.patch(
            f"/api/v1/projects/{foreign.pk}/", {"name": "Changed"}, format="json"
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/projects/{foreign.pk}/").status_code == 404


@pytest.mark.django_db
def test_project_database_rejects_empty_name():
    with pytest.raises(IntegrityError), transaction.atomic():
        Project.objects.create(owner=user("owner@example.com"), name="")


@pytest.mark.django_db
def test_project_create_throttle_is_distinct(settings):
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["project_create"] = "1/hour"
    client = client_for(user("owner@example.com"))
    assert client.post("/api/v1/projects/", {"name": "One"}, format="json").status_code == 201
    assert client.post("/api/v1/projects/", {"name": "Two"}, format="json").status_code == 429
    assert client.get("/api/v1/projects/").status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("image_format", "expected_mime"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_supported_image_uploads_use_verified_metadata(image_format, expected_mime):
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    response = upload(
        client_for(account),
        project,
        image_upload(f"claimed-{image_format}.txt", image_format, content_type="text/plain"),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["mime_type"] == expected_mime
    assert data["width"] == 4
    assert data["height"] == 3
    assert "file" not in data
    assert str(project.pk) in Asset.objects.get().file.name
    assert not Asset.objects.get().file.name.endswith(".txt")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "file",
    [
        SimpleUploadedFile("broken.jpg", b"not an image", content_type="image/jpeg"),
        SimpleUploadedFile(
            "active.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
            content_type="image/svg+xml",
        ),
        image_upload("animated.gif", "GIF"),
    ],
)
def test_malformed_svg_and_unsupported_images_are_rejected(file):
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    response = upload(client_for(account), project, file)
    assert response.status_code == 400
    assert not Asset.objects.exists()


@pytest.mark.django_db
def test_file_size_and_dimension_limits_are_enforced(settings):
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    client = client_for(account)
    settings.ASSET_MAX_FILE_SIZE = 10
    assert upload(client, project, image_upload()).status_code == 400
    settings.ASSET_MAX_FILE_SIZE = 10_000
    settings.ASSET_MAX_DIMENSION = 2
    assert upload(client, project, image_upload(size=(3, 2))).status_code == 400
    settings.ASSET_MAX_DIMENSION = 100
    settings.ASSET_MAX_PIXELS = 5
    assert upload(client, project, image_upload(size=(3, 2))).status_code == 400


@pytest.mark.django_db
def test_request_body_limit_rejects_before_upload_parsing(settings):
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    settings.REQUEST_MAX_BODY_SIZE = 100
    response = client_for(account).post(
        f"/api/v1/projects/{project.pk}/assets/",
        {"category": "product_image", "file": image_upload()},
        format="multipart",
        CONTENT_LENGTH="101",
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


@pytest.mark.django_db
def test_storage_key_and_original_filename_are_safe():
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    response = upload(client_for(account), project, image_upload("../../private.png"))
    assert response.status_code == 201
    asset = Asset.objects.get()
    assert asset.original_filename == "private.png"
    assert ".." not in asset.file.name
    assert asset.file.name.endswith(f"{asset.pk}.png")


@pytest.mark.django_db
def test_asset_access_is_private_and_owner_scoped():
    owner = user("owner@example.com")
    other = user("other@example.com")
    project = Project.objects.create(owner=owner, name="Images")
    asset = Asset.objects.create(
        project=project,
        category="logo",
        file=image_upload(),
        original_filename="image.png",
        mime_type="image/png",
        size=70,
        width=4,
        height=3,
    )
    detail = f"/api/v1/projects/{project.pk}/assets/{asset.pk}/"
    content = f"{detail}content/"
    assert APIClient().get(content).status_code == 401
    assert client_for(other).get(detail).status_code == 404
    assert client_for(other).get(content).status_code == 404
    response = client_for(owner).get(detail)
    assert response.status_code == 200
    assert "MEDIA_ROOT" not in str(response.json())
    assert client_for(owner).get(content).status_code == 200


@pytest.mark.django_db
def test_asset_lists_only_owned_project_and_foreign_operations_are_hidden():
    owner = user("owner@example.com")
    other = user("other@example.com")
    project = Project.objects.create(owner=owner, name="Images")
    asset = Asset.objects.create(
        project=project,
        category="reference_image",
        file=image_upload(),
        original_filename="image.png",
        mime_type="image/png",
        size=70,
        width=4,
        height=3,
    )
    other_client = client_for(other)
    assert other_client.get(f"/api/v1/projects/{project.pk}/assets/").status_code == 404
    assert upload(other_client, project).status_code == 404
    path = f"/api/v1/projects/{project.pk}/assets/{asset.pk}/"
    assert other_client.delete(path).status_code == 404


@pytest.mark.django_db
def test_asset_quota_and_upload_throttle(settings):
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    client = client_for(account)
    settings.ASSET_MAX_PER_PROJECT = 1
    assert upload(client, project).status_code == 201
    assert upload(client, project).status_code == 400
    settings.ASSET_MAX_PER_PROJECT = 30
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["asset_upload"] = "1/hour"
    cache.clear()
    second_project = Project.objects.create(owner=account, name="Other")
    assert upload(client, second_project).status_code == 201
    assert upload(client, second_project).status_code == 429


@pytest.mark.django_db(transaction=True)
def test_asset_and_project_deletion_clean_files(settings, tmp_path):
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    client = client_for(account)
    first = upload(client, project).json()
    first_asset = Asset.objects.get(pk=first["id"])
    first_path = tmp_path / first_asset.file.name
    assert first_path.exists()
    assert (
        client.delete(f"/api/v1/projects/{project.pk}/assets/{first_asset.pk}/").status_code == 204
    )
    assert not first_path.exists()
    second = upload(client, project).json()
    second_asset = Asset.objects.get(pk=second["id"])
    second_path = tmp_path / second_asset.file.name
    assert client.delete(f"/api/v1/projects/{project.pk}/").status_code == 204
    assert not second_path.exists()


@pytest.mark.django_db(transaction=True)
def test_deleting_asset_with_missing_file_is_safe(settings, tmp_path):
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    client = client_for(account)
    created = upload(client, project).json()
    asset = Asset.objects.get(pk=created["id"])
    (tmp_path / asset.file.name).unlink()
    response = client.delete(f"/api/v1/projects/{project.pk}/assets/{asset.pk}/")
    assert response.status_code == 204


@pytest.mark.django_db
def test_asset_database_constraints():
    project = Project.objects.create(owner=user("owner@example.com"), name="Images")
    with pytest.raises(IntegrityError), transaction.atomic():
        Asset.objects.create(
            project=project,
            category="invalid",
            file="safe.png",
            original_filename="safe.png",
            mime_type="image/png",
            size=1,
            width=1,
            height=1,
        )


@pytest.mark.django_db
def test_malformed_multipart_request_fails_safely():
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")
    response = client_for(account).post(
        f"/api/v1/projects/{project.pk}/assets/",
        {"category": "logo"},
        format="multipart",
    )
    assert response.status_code == 400
    assert set(response.json()) == {"error"}


@pytest.mark.django_db(transaction=True)
def test_database_failure_after_storage_write_cleans_orphan(monkeypatch, tmp_path):
    account = user("owner@example.com")
    project = Project.objects.create(owner=account, name="Images")

    def fail_after_file_save(instance, *args, **kwargs):
        instance.file.save(instance.file.name, instance.file.file, save=False)
        raise IntegrityError("forced database failure")

    monkeypatch.setattr(Asset, "save", fail_after_file_save)
    response = upload(client_for(account), project)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
