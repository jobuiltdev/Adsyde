import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tokens import email_verification_token

User = get_user_model()
PASSWORD = "valid-test-password-72!"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()


def create_user(email="person@example.com", *, verified=True, password=PASSWORD):
    user = User.objects.create_user(email, password)
    if verified:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
    return user


def uid_for(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def token_from_email(message):
    return re.search(r"[?&]token=([^&\s]+)", message.body).group(1)


@pytest.mark.django_db
def test_registration_normalizes_email_hashes_password_and_sends_verification():
    response = APIClient().post(
        "/api/v1/auth/register/",
        {"email": "PERSON@Example.COM", "password": PASSWORD, "password_confirm": PASSWORD},
        format="json",
    )
    assert response.status_code == 201
    assert set(response.json()) == {"detail"}
    user = User.objects.get()
    assert user.email == "person@example.com"
    assert user.check_password(PASSWORD)
    assert not user.email_verified
    assert len(mail.outbox) == 1
    assert PASSWORD not in mail.outbox[0].body


@pytest.mark.django_db
def test_registration_rejects_duplicate_and_weak_password():
    create_user()
    duplicate = APIClient().post(
        "/api/v1/auth/register/",
        {"email": "PERSON@example.com", "password": PASSWORD, "password_confirm": PASSWORD},
        format="json",
    )
    weak = APIClient().post(
        "/api/v1/auth/register/",
        {"email": "new@example.com", "password": "password", "password_confirm": "password"},
        format="json",
    )
    assert duplicate.status_code == 400
    assert weak.status_code == 400
    assert "password" not in str(duplicate.json()).lower()


@pytest.mark.django_db
def test_email_verification_is_one_time():
    user = create_user(verified=False)
    token = email_verification_token.make_token(user)
    payload = {"uid": uid_for(user), "token": token}
    client = APIClient()
    assert client.post("/api/v1/auth/verify-email/", payload, format="json").status_code == 200
    user.refresh_from_db()
    assert user.email_verified
    assert client.post("/api/v1/auth/verify-email/", payload, format="json").status_code == 400


@pytest.mark.django_db
def test_invalid_and_expired_verification_tokens_fail(settings):
    user = create_user(verified=False)
    client = APIClient()
    assert (
        client.post(
            "/api/v1/auth/verify-email/",
            {"uid": uid_for(user), "token": "invalid"},
            format="json",
        ).status_code
        == 400
    )
    settings.EMAIL_VERIFICATION_TIMEOUT = -1
    token = email_verification_token.make_token(user)
    assert (
        client.post(
            "/api/v1/auth/verify-email/",
            {"uid": uid_for(user), "token": token},
            format="json",
        ).status_code
        == 400
    )


@pytest.mark.django_db
def test_verification_resend_is_enumeration_safe():
    create_user(verified=False)
    client = APIClient()
    known = client.post(
        "/api/v1/auth/verification/resend/", {"email": "PERSON@example.com"}, format="json"
    )
    assert len(mail.outbox) == 1
    unknown = client.post(
        "/api/v1/auth/verification/resend/", {"email": "unknown@example.com"}, format="json"
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_login_is_case_insensitive_and_requires_verification():
    create_user()
    success = APIClient().post(
        "/api/v1/auth/login/", {"email": "PERSON@EXAMPLE.COM", "password": PASSWORD}, format="json"
    )
    assert success.status_code == 200
    assert set(success.json()) == {"access", "refresh"}
    unverified = create_user("other@example.com", verified=False)
    failed = APIClient().post(
        "/api/v1/auth/login/", {"email": unverified.email, "password": PASSWORD}, format="json"
    )
    assert failed.status_code == 400


@pytest.mark.django_db
def test_login_unknown_and_wrong_password_have_same_response():
    create_user()
    client = APIClient()
    wrong = client.post(
        "/api/v1/auth/login/", {"email": "person@example.com", "password": "wrong"}, format="json"
    )
    unknown = client.post(
        "/api/v1/auth/login/", {"email": "unknown@example.com", "password": "wrong"}, format="json"
    )
    assert wrong.status_code == unknown.status_code == 400
    assert wrong.json() == unknown.json()


@pytest.mark.django_db
def test_access_token_authenticates_and_me_is_safe():
    user = create_user()
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    assert client.get("/api/v1/me/").status_code == 401
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    response = client.get("/api/v1/me/")
    assert response.status_code == 200
    assert set(response.json()) == {"id", "email", "email_verified", "date_joined"}


@pytest.mark.django_db
def test_refresh_rotates_and_old_token_cannot_be_replayed():
    user = create_user()
    old = str(RefreshToken.for_user(user))
    client = APIClient()
    response = client.post("/api/v1/auth/refresh/", {"refresh": old}, format="json")
    assert response.status_code == 200
    assert set(response.json()) == {"access", "refresh"}
    replay = client.post("/api/v1/auth/refresh/", {"refresh": old}, format="json")
    assert replay.status_code == 401
    assert "error" in replay.json()


@pytest.mark.django_db
def test_malformed_refresh_fails_with_error_envelope():
    response = APIClient().post("/api/v1/auth/refresh/", {"refresh": "not-a-token"}, format="json")
    assert response.status_code == 401
    assert set(response.json()) == {"error"}


@pytest.mark.django_db
def test_logout_blacklists_refresh_and_is_repeatable():
    user = create_user()
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    payload = {"refresh": str(refresh)}
    assert client.post("/api/v1/auth/logout/", payload, format="json").status_code == 204
    assert client.post("/api/v1/auth/logout/", payload, format="json").status_code == 204
    assert APIClient().post("/api/v1/auth/refresh/", payload, format="json").status_code == 401


@pytest.mark.django_db
def test_password_reset_request_is_enumeration_safe():
    create_user()
    client = APIClient()
    known = client.post(
        "/api/v1/auth/password-reset/", {"email": "person@example.com"}, format="json"
    )
    assert len(mail.outbox) == 1
    unknown = client.post(
        "/api/v1/auth/password-reset/", {"email": "unknown@example.com"}, format="json"
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_password_reset_is_one_time_and_revokes_refresh_tokens():
    user = create_user()
    refresh = str(RefreshToken.for_user(user))
    token = default_token_generator.make_token(user)
    payload = {
        "uid": uid_for(user),
        "token": token,
        "new_password": "new-valid-password-83!",
        "new_password_confirm": "new-valid-password-83!",
    }
    client = APIClient()
    assert (
        client.post("/api/v1/auth/password-reset/confirm/", payload, format="json").status_code
        == 200
    )
    user.refresh_from_db()
    assert user.check_password("new-valid-password-83!")
    assert not user.check_password(PASSWORD)
    assert (
        client.post("/api/v1/auth/password-reset/confirm/", payload, format="json").status_code
        == 400
    )
    assert (
        client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json").status_code == 401
    )


@pytest.mark.django_db
def test_password_reset_rejects_expired_token(settings):
    user = create_user()
    token = default_token_generator._make_token_with_timestamp(
        user,
        default_token_generator._num_seconds(default_token_generator._now() - timedelta(hours=2)),
        default_token_generator.secret,
    )
    settings.PASSWORD_RESET_TIMEOUT = 60
    response = APIClient().post(
        "/api/v1/auth/password-reset/confirm/",
        {
            "uid": uid_for(user),
            "token": token,
            "new_password": "new-valid-password-83!",
            "new_password_confirm": "new-valid-password-83!",
        },
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_account_password_change_requires_current_password_and_revokes_tokens():
    user = create_user()
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    payload = {
        "current_password": PASSWORD,
        "new_password": "changed-valid-password-94!",
        "new_password_confirm": "changed-valid-password-94!",
    }
    assert client.patch("/api/v1/me/", payload, format="json").status_code == 200
    assert (
        APIClient()
        .post("/api/v1/auth/refresh/", {"refresh": str(refresh)}, format="json")
        .status_code
        == 401
    )


@pytest.mark.django_db
def test_auth_throttle_scopes_are_independent(settings):
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    rates["auth_login"] = "1/min"
    rates["auth_password_reset"] = "1/min"
    client = APIClient()
    payload = {"email": "unknown@example.com", "password": "wrong"}
    assert client.post("/api/v1/auth/login/", payload, format="json").status_code == 400
    assert client.post("/api/v1/auth/login/", payload, format="json").status_code == 429
    reset = client.post(
        "/api/v1/auth/password-reset/", {"email": "unknown@example.com"}, format="json"
    )
    assert reset.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("scope", "path", "payload", "first_status"),
    [
        (
            "auth_register",
            "/api/v1/auth/register/",
            {"email": "new@example.com", "password": PASSWORD, "password_confirm": PASSWORD},
            201,
        ),
        (
            "auth_verify",
            "/api/v1/auth/verify-email/",
            {"uid": "invalid", "token": "invalid"},
            400,
        ),
        (
            "auth_verification_resend",
            "/api/v1/auth/verification/resend/",
            {"email": "unknown@example.com"},
            200,
        ),
        (
            "auth_refresh",
            "/api/v1/auth/refresh/",
            {"refresh": "invalid"},
            401,
        ),
        (
            "auth_password_reset_confirm",
            "/api/v1/auth/password-reset/confirm/",
            {"uid": "invalid", "token": "invalid"},
            400,
        ),
    ],
)
def test_public_auth_endpoints_use_their_own_throttle(settings, scope, path, payload, first_status):
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope] = "1/min"
    client = APIClient()
    assert client.post(path, payload, format="json").status_code == first_status
    assert client.post(path, payload, format="json").status_code == 429
