import hashlib
import json
import logging
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.credits.services import record_purchase

from .catalog import get_package
from .exceptions import InvalidPaymentResponse, PaymentProviderUnavailable
from .models import Payment, PaymentEvent, PaymentStatus
from .providers.registry import get_payment_provider

logger = logging.getLogger(__name__)
FINAL_STATUSES = {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.REVIEW_REQUIRED}


def validate_checkout_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in settings.PAYSTACK_CHECKOUT_HOSTS:
        raise InvalidPaymentResponse("Payment checkout URL was invalid.")


@transaction.atomic
def initialize_payment(user, package_key, initialization_key):
    package = get_package(package_key)
    if not package:
        raise ValueError("The selected credit package is unavailable.")
    payment = (
        Payment.objects.select_for_update()
        .filter(user=user, initialization_key=initialization_key)
        .first()
    )
    if payment and payment.status not in {
        PaymentStatus.CREATED,
        PaymentStatus.VERIFICATION_REQUIRED,
    }:
        return payment
    if not payment:
        payment_id = uuid.uuid4()
        reference = f"adsyde_{payment_id.hex}"
        payment = Payment.objects.create(
            id=payment_id,
            user=user,
            internal_reference=reference,
            provider_reference=reference,
            initialization_key=initialization_key,
            package_key=package.key,
            package_name=package.name,
            currency=package.currency,
            amount_minor=package.amount_minor,
            credits=package.credits,
        )
    try:
        result = get_payment_provider().initialize(
            email=user.email,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            reference=payment.provider_reference,
            callback_url=f"{settings.PAYMENT_CALLBACK_URL}?payment_id={payment.pk}",
        )
        validate_checkout_url(result.authorization_url)
        if result.reference != payment.provider_reference:
            raise InvalidPaymentResponse("Payment reference did not match.")
    except PaymentProviderUnavailable:
        payment.status = PaymentStatus.VERIFICATION_REQUIRED
        payment.save(update_fields=["status", "updated_at"])
        return payment
    payment.authorization_url = result.authorization_url
    payment.access_code = result.access_code
    payment.status = PaymentStatus.INITIALIZED
    payment.initiated_at = timezone.now()
    payment.save(
        update_fields=[
            "authorization_url",
            "access_code",
            "status",
            "initiated_at",
            "updated_at",
        ]
    )
    return payment


@transaction.atomic
def verify_payment(payment_id):
    payment = Payment.objects.select_for_update().select_related("user").get(pk=payment_id)
    if payment.credited_at or payment.status == PaymentStatus.REVIEW_REQUIRED:
        return payment
    try:
        result = get_payment_provider().verify(payment.provider_reference)
    except (PaymentProviderUnavailable, KeyError):
        payment.status = PaymentStatus.VERIFICATION_REQUIRED
        payment.save(update_fields=["status", "updated_at"])
        return payment
    payment.verified_at = timezone.now()
    payment.provider_status = result.status[:32]
    mismatch = (
        result.reference != payment.provider_reference
        or result.amount_minor != payment.amount_minor
        or result.currency != payment.currency
        or result.customer_email.lower() != payment.user.email.lower()
    )
    if mismatch:
        payment.status = PaymentStatus.REVIEW_REQUIRED
    elif result.status == "success":
        record_purchase(payment.user, payment.credits, payment.pk)
        payment.status = PaymentStatus.SUCCEEDED
        payment.succeeded_at = timezone.now()
        payment.credited_at = payment.succeeded_at
    elif result.status in {"failed", "abandoned", "reversed"}:
        payment.status = PaymentStatus.FAILED
        payment.failed_at = timezone.now()
    else:
        payment.status = PaymentStatus.PENDING
    payment.save()
    return payment


def record_webhook(payload):
    fingerprint = hashlib.sha256(payload).hexdigest()
    try:
        data = json.loads(payload)
        event_type = data["event"]
        reference = data.get("data", {}).get("reference", "")
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError) as exc:
        raise InvalidPaymentResponse("Payment event payload was invalid.") from exc
    event, created = PaymentEvent.objects.get_or_create(
        event_fingerprint=fingerprint,
        defaults={
            "provider": "paystack",
            "event_type": str(event_type)[:64],
            "provider_reference": str(reference)[:100],
        },
    )
    if not created:
        return event
    payment = Payment.objects.filter(provider_reference=reference).first()
    event.payment = payment
    if event_type != "charge.success":
        event.outcome = "ignored"
    elif not payment:
        event.outcome = "unknown_reference"
    else:
        verify_payment(payment.pk)
        event.outcome = "processed"
    event.processed_at = timezone.now()
    event.save(update_fields=["payment", "outcome", "processed_at"])
    return event


def audit_payments():
    issues = []
    for payment in Payment.objects.select_related("user"):
        count = (
            payment.user.credit_wallet.transactions.filter(
                reference=f"payment:{payment.pk}:purchase"
            ).count()
            if hasattr(payment.user, "credit_wallet")
            else 0
        )
        if payment.status == PaymentStatus.SUCCEEDED and count != 1:
            issues.append(f"payment {payment.pk}: succeeded with {count} purchase entries")
        if payment.status == PaymentStatus.FAILED and count:
            issues.append(f"payment {payment.pk}: failed with a purchase entry")
        if bool(payment.credited_at) != (count == 1):
            issues.append(f"payment {payment.pk}: credited marker mismatch")
    return issues
