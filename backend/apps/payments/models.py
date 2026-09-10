import uuid

from django.conf import settings
from django.db import models


class PaymentStatus(models.TextChoices):
    CREATED = "created", "Created"
    INITIALIZED = "initialized", "Initialized"
    PENDING = "pending", "Pending"
    VERIFICATION_REQUIRED = "verification_required", "Verification required"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    REVIEW_REQUIRED = "review_required", "Review required"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments"
    )
    provider = models.CharField(max_length=24, default="paystack")
    internal_reference = models.CharField(max_length=64, unique=True)
    provider_reference = models.CharField(max_length=100, unique=True)
    initialization_key = models.CharField(max_length=128)
    package_key = models.CharField(max_length=32)
    package_name = models.CharField(max_length=64)
    currency = models.CharField(max_length=3)
    amount_minor = models.PositiveBigIntegerField()
    credits = models.PositiveIntegerField()
    status = models.CharField(
        max_length=32, choices=PaymentStatus.choices, default=PaymentStatus.CREATED
    )
    provider_status = models.CharField(max_length=32, blank=True)
    authorization_url = models.URLField(max_length=500, blank=True)
    access_code = models.CharField(max_length=100, blank=True)
    initiated_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    succeeded_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "initialization_key"), name="payment_user_init_key_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(amount_minor__gt=0), name="payment_amount_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(credits__gt=0), name="payment_credits_positive"
            ),
            models.CheckConstraint(condition=models.Q(currency="NGN"), name="payment_currency_ngn"),
        ]
        indexes = [
            models.Index(fields=("user", "-created_at"), name="payment_user_time_idx"),
            models.Index(fields=("status",), name="payment_status_idx"),
        ]

    def __str__(self):
        return self.internal_reference


class PaymentEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=24)
    event_fingerprint = models.CharField(max_length=64, unique=True)
    event_type = models.CharField(max_length=64)
    provider_reference = models.CharField(max_length=100, blank=True)
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, null=True, blank=True, related_name="events"
    )
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return self.event_fingerprint
