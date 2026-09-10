import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone

from apps.credits.models import CreditTransaction, CreditTransactionType
from apps.credits.services import get_or_create_wallet
from apps.payments.models import Payment, PaymentEvent, PaymentStatus
from apps.payments.providers.fake import FakePaymentProvider
from apps.payments.services import audit_payments, initialize_payment, verify_payment
from apps.payments.webhooks import sign_paystack_payload
from tests.test_generations import auth_client, make_user


@pytest.fixture(autouse=True)
def payment_settings(settings):
    settings.PAYMENTS_ENABLED = True
    settings.PAYMENT_PROVIDER = "fake"
    settings.PAYSTACK_SECRET_KEY = "test-signing-secret"
    FakePaymentProvider.transactions.clear()


def initialize(user, key="request-key-123"):
    return initialize_payment(user, "starter", key)


@pytest.mark.django_db
def test_package_catalog_is_ngn_integer_and_non_secret():
    response = auth_client(make_user("packages@example.com")).get("/api/v1/payments/packages/")
    assert response.status_code == 200
    assert all(
        item["currency"] == "NGN" and isinstance(item["amount_minor"], int)
        for item in response.json()
    )
    assert "secret" not in response.content.decode().lower()


@pytest.mark.django_db
def test_initialization_snapshots_package_and_is_idempotent():
    user = make_user("initialize@example.com")
    first = initialize(user)
    second = initialize(user)
    assert first.pk == second.pk
    assert Payment.objects.count() == 1
    assert first.amount_minor == 500000
    assert first.credits == 500
    assert first.currency == "NGN"
    assert first.authorization_url.startswith("https://checkout.paystack.com/")
    assert user.email not in first.internal_reference


@pytest.mark.django_db
def test_initialization_api_requires_verified_email_and_authoritative_input():
    verified = make_user("verified-pay@example.com")
    client = auth_client(verified)
    response = client.post(
        "/api/v1/payments/initialize/",
        {"package": "starter"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="browser-request-123",
    )
    assert response.status_code == 201
    assert response.json()["amount_minor"] == 500000
    assert "access_code" not in response.json()
    manipulated = client.post(
        "/api/v1/payments/initialize/",
        {"package": "starter", "amount_minor": 1, "credits": 999999},
        format="json",
        HTTP_IDEMPOTENCY_KEY="browser-request-456",
    )
    assert manipulated.status_code == 400
    unverified = make_user("unverified-pay@example.com")
    unverified.email_verified_at = None
    unverified.save(update_fields=["email_verified_at"])
    assert (
        auth_client(unverified)
        .post(
            "/api/v1/payments/initialize/",
            {"package": "starter"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="browser-request-789",
        )
        .status_code
        == 403
    )


@pytest.mark.django_db
def test_successful_verification_credits_purchase_once():
    user = make_user("success-pay@example.com")
    payment = initialize(user)
    wallet = get_or_create_wallet(user)
    opening = wallet.balance
    FakePaymentProvider.set_result(
        payment.provider_reference,
        status="success",
        amount_minor=payment.amount_minor,
        currency="NGN",
        customer_email=user.email,
    )
    verify_payment(payment.pk)
    verify_payment(payment.pk)
    wallet.refresh_from_db()
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.credited_at
    assert wallet.balance == opening + 500
    assert (
        CreditTransaction.objects.filter(transaction_type=CreditTransactionType.PURCHASE).count()
        == 1
    )
    assert audit_payments() == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "change",
    [
        {"amount_minor": 499999},
        {"currency": "USD"},
        {"customer_email": "mismatch@example.com"},
    ],
)
def test_verification_mismatch_never_credits(change):
    user = make_user(f"mismatch-{next(iter(change))}@example.com")
    payment = initialize(user)
    values = {
        "status": "success",
        "amount_minor": payment.amount_minor,
        "currency": "NGN",
        "customer_email": user.email,
        **change,
    }
    FakePaymentProvider.set_result(payment.provider_reference, **values)
    verify_payment(payment.pk)
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.REVIEW_REQUIRED
    assert not CreditTransaction.objects.filter(transaction_type="purchase").exists()


@pytest.mark.django_db
def test_failed_and_pending_payments_do_not_credit():
    user = make_user("failed-pay@example.com")
    failed = initialize(user, "failed-request")
    FakePaymentProvider.set_result(
        failed.provider_reference,
        status="failed",
        amount_minor=failed.amount_minor,
        currency="NGN",
        customer_email=user.email,
    )
    assert verify_payment(failed.pk).status == PaymentStatus.FAILED
    pending = initialize(user, "pending-request")
    assert verify_payment(pending.pk).status == PaymentStatus.PENDING
    assert not CreditTransaction.objects.filter(transaction_type="purchase").exists()


@pytest.mark.django_db
def test_payment_ownership_is_enforced():
    owner = make_user("payment-owner@example.com")
    other = make_user("payment-other@example.com")
    payment = initialize(owner)
    assert auth_client(other).get(f"/api/v1/payments/{payment.pk}/").status_code == 404
    assert auth_client(other).post(f"/api/v1/payments/{payment.pk}/verify/").status_code == 404
    assert auth_client(owner).get("/api/v1/payments/").json()["count"] == 1
    assert auth_client(other).get("/api/v1/payments/").json()["count"] == 0


@pytest.mark.django_db
def test_signed_webhook_is_raw_body_verified_and_deduplicated():
    user = make_user("webhook-pay@example.com")
    payment = initialize(user)
    FakePaymentProvider.set_result(
        payment.provider_reference,
        status="success",
        amount_minor=payment.amount_minor,
        currency="NGN",
        customer_email=user.email,
    )
    payload = json.dumps(
        {"event": "charge.success", "data": {"reference": payment.provider_reference}}
    ).encode()
    signature = sign_paystack_payload("test-signing-secret", payload)
    client = auth_client(user)
    for _ in range(2):
        assert (
            client.post(
                "/api/v1/payments/webhooks/paystack/",
                payload,
                content_type="application/json",
                HTTP_X_PAYSTACK_SIGNATURE=signature,
            ).status_code
            == 204
        )
    assert PaymentEvent.objects.count() == 1
    assert CreditTransaction.objects.filter(transaction_type="purchase").count() == 1
    assert (
        client.post(
            "/api/v1/payments/webhooks/paystack/",
            payload + b" ",
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        ).status_code
        == 401
    )


@pytest.mark.django_db
def test_webhook_malformed_unsupported_and_unknown_reference():
    client = auth_client(make_user("events@example.com"))
    malformed = b"{}"
    assert (
        client.post(
            "/api/v1/payments/webhooks/paystack/",
            malformed,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sign_paystack_payload("test-signing-secret", malformed),
        ).status_code
        == 400
    )
    for payload in (
        {"event": "transfer.success", "data": {"reference": "unknown"}},
        {"event": "charge.success", "data": {"reference": "unknown"}},
    ):
        body = json.dumps(payload).encode()
        assert (
            client.post(
                "/api/v1/payments/webhooks/paystack/",
                body,
                content_type="application/json",
                HTTP_X_PAYSTACK_SIGNATURE=sign_paystack_payload("test-signing-secret", body),
            ).status_code
            == 204
        )
    assert {event.outcome for event in PaymentEvent.objects.all()} == {
        "ignored",
        "unknown_reference",
    }


@pytest.mark.django_db(transaction=True)
def test_concurrent_verification_credits_once():
    user = make_user("concurrent-pay@example.com")
    payment = initialize(user)
    FakePaymentProvider.set_result(
        payment.provider_reference,
        status="success",
        amount_minor=payment.amount_minor,
        currency="NGN",
        customer_email=user.email,
    )

    def run(_):
        close_old_connections()
        try:
            verify_payment(payment.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, range(2)))
    assert CreditTransaction.objects.filter(transaction_type="purchase").count() == 1


@pytest.mark.django_db
def test_payment_audit_finds_succeeded_without_purchase():
    user = make_user("audit-pay@example.com")
    payment = initialize(user)
    payment.status = PaymentStatus.SUCCEEDED
    payment.succeeded_at = timezone.now()
    payment.save(update_fields=["status", "succeeded_at"])
    assert any("succeeded" in issue for issue in audit_payments())
