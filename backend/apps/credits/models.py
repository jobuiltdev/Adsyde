import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class CreditTransactionType(models.TextChoices):
    PURCHASE = "purchase", "Purchase"
    PROMO = "promo", "Promotional credit"
    ADMIN_ADJUSTMENT = "admin_adjustment", "Administrative adjustment"
    GENERATION_RESERVATION = "generation_reservation", "Generation reservation"
    GENERATION_RELEASE = "generation_release", "Generation release"
    GENERATION_CHARGE = "generation_charge", "Video generation"
    REFUND = "refund", "Refund"


class ChargeStatus(models.TextChoices):
    RESERVED = "reserved", "Reserved"
    CHARGED = "charged", "Charged"
    RELEASED = "released", "Released"
    REFUNDED = "refunded", "Refunded"


class CreditWallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="credit_wallet"
    )
    balance = models.PositiveBigIntegerField(default=0)
    reserved_balance = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(balance__gte=0), name="credit_balance_nonnegative"),
            models.CheckConstraint(
                condition=Q(reserved_balance__gte=0), name="credit_reserved_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(reserved_balance__lte=F("balance")),
                name="credit_reserved_within_balance",
            ),
        ]

    def __str__(self):
        return str(self.id)

    @property
    def available_balance(self):
        return self.balance - self.reserved_balance


class GenerationCharge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generation = models.OneToOneField(
        "generations.Generation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_charge",
    )
    generation_id_snapshot = models.UUIDField(unique=True)
    wallet = models.ForeignKey(CreditWallet, on_delete=models.PROTECT, related_name="charges")
    quoted_credits = models.PositiveIntegerField()
    reserved_credits = models.PositiveIntegerField()
    charged_credits = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=ChargeStatus.choices)
    pricing_version = models.CharField(max_length=32)
    pricing_snapshot = models.JSONField(default=dict)
    reserved_at = models.DateTimeField()
    charged_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quoted_credits__gt=0), name="charge_quote_positive"),
            models.CheckConstraint(
                condition=Q(reserved_credits__gt=0), name="charge_reserved_positive"
            ),
            models.CheckConstraint(
                condition=Q(charged_credits__gte=0), name="charge_charged_nonnegative"
            ),
        ]

    def __str__(self):
        return str(self.generation_id_snapshot)


class CreditTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(CreditWallet, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=32, choices=CreditTransactionType.choices)
    balance_delta = models.BigIntegerField(default=0)
    reserved_delta = models.BigIntegerField(default=0)
    balance_after = models.PositiveBigIntegerField()
    reserved_after = models.PositiveBigIntegerField()
    reference = models.CharField(max_length=255, unique=True)
    reason = models.CharField(max_length=255)
    generation = models.ForeignKey(
        "generations.Generation", on_delete=models.SET_NULL, null=True, blank=True
    )
    generation_id_snapshot = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=("wallet", "-created_at"), name="credit_wallet_time_idx")]

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        if self.pk and CreditTransaction.objects.filter(pk=self.pk).exists():
            raise ValueError("Credit transactions are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Credit transactions are immutable.")
