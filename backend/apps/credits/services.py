import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .exceptions import InsufficientCredits
from .models import (
    ChargeStatus,
    CreditTransaction,
    CreditTransactionType,
    CreditWallet,
    GenerationCharge,
)
from .pricing import quote_generation

logger = logging.getLogger(__name__)


def _entry(
    wallet, transaction_type, balance_delta, reserved_delta, reference, reason, generation=None
):
    return CreditTransaction.objects.create(
        wallet=wallet,
        transaction_type=transaction_type,
        balance_delta=balance_delta,
        reserved_delta=reserved_delta,
        balance_after=wallet.balance,
        reserved_after=wallet.reserved_balance,
        reference=reference,
        reason=reason,
        generation=generation,
        generation_id_snapshot=generation.pk if generation else None,
    )


def get_or_create_wallet(user):
    wallet, created = CreditWallet.objects.select_for_update().get_or_create(user=user)
    initial = settings.CREDIT_DEVELOPMENT_INITIAL_GRANT if created else 0
    if initial:
        wallet.balance = initial
        wallet.save(update_fields=["balance", "updated_at"])
        _entry(
            wallet,
            CreditTransactionType.PROMO,
            initial,
            0,
            f"development-initial:{user.pk}",
            "Development credit",
        )
    return wallet


@transaction.atomic
def grant_credits(user, amount, reason, reference):
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise ValueError("Credit grant amount must be a positive integer.")
    if not reason.strip():
        raise ValueError("A grant reason is required.")
    existing = CreditTransaction.objects.filter(reference=reference).first()
    if existing:
        return existing
    wallet = get_or_create_wallet(user)
    wallet.balance += amount
    wallet.save(update_fields=["balance", "updated_at"])
    entry = _entry(
        wallet, CreditTransactionType.ADMIN_ADJUSTMENT, amount, 0, reference, reason.strip()
    )
    logger.info(
        "credits.granted",
        extra={"event": "credits.granted", "wallet_id": str(wallet.pk), "amount": amount},
    )
    return entry


@transaction.atomic
def record_purchase(user, amount, payment_id):
    reference = f"payment:{payment_id}:purchase"
    existing = CreditTransaction.objects.filter(reference=reference).first()
    if existing:
        return existing
    wallet = get_or_create_wallet(user)
    wallet.balance += amount
    wallet.save(update_fields=["balance", "updated_at"])
    return _entry(
        wallet,
        CreditTransactionType.PURCHASE,
        amount,
        0,
        reference,
        "Credit purchase",
    )


@transaction.atomic
def reserve_generation(generation):
    existing = (
        GenerationCharge.objects.select_for_update()
        .filter(generation_id_snapshot=generation.pk)
        .first()
    )
    if existing:
        return existing
    quote = quote_generation(generation.model, generation.duration_seconds)
    wallet = get_or_create_wallet(generation.created_by)
    if wallet.available_balance < quote.credits:
        raise InsufficientCredits(
            {
                "required": quote.credits,
                "available": wallet.available_balance,
                "shortfall": quote.credits - wallet.available_balance,
            }
        )
    wallet.reserved_balance += quote.credits
    wallet.save(update_fields=["reserved_balance", "updated_at"])
    now = timezone.now()
    charge = GenerationCharge.objects.create(
        generation=generation,
        generation_id_snapshot=generation.pk,
        wallet=wallet,
        quoted_credits=quote.credits,
        reserved_credits=quote.credits,
        status=ChargeStatus.RESERVED,
        pricing_version=quote.version,
        pricing_snapshot=quote.snapshot,
        reserved_at=now,
    )
    _entry(
        wallet,
        CreditTransactionType.GENERATION_RESERVATION,
        0,
        quote.credits,
        f"generation:{generation.pk}:reserve",
        "Video generation reserved",
        generation,
    )
    return charge


@transaction.atomic
def charge_generation(generation_id):
    charge = (
        GenerationCharge.objects.select_for_update()
        .filter(generation_id_snapshot=generation_id)
        .first()
    )
    if not charge or charge.status == ChargeStatus.CHARGED:
        return charge
    if charge.status != ChargeStatus.RESERVED:
        return charge
    wallet = CreditWallet.objects.select_for_update().get(pk=charge.wallet_id)
    wallet.balance -= charge.reserved_credits
    wallet.reserved_balance -= charge.reserved_credits
    wallet.save(update_fields=["balance", "reserved_balance", "updated_at"])
    charge.status = ChargeStatus.CHARGED
    charge.charged_credits = charge.reserved_credits
    charge.charged_at = timezone.now()
    charge.save(update_fields=["status", "charged_credits", "charged_at"])
    _entry(
        wallet,
        CreditTransactionType.GENERATION_CHARGE,
        -charge.charged_credits,
        -charge.reserved_credits,
        f"generation:{generation_id}:charge",
        "Video generation",
        charge.generation,
    )
    return charge


@transaction.atomic
def release_generation(generation_id):
    charge = (
        GenerationCharge.objects.select_for_update()
        .filter(generation_id_snapshot=generation_id)
        .first()
    )
    if not charge or charge.status == ChargeStatus.RELEASED:
        return charge
    if charge.status != ChargeStatus.RESERVED:
        return charge
    wallet = CreditWallet.objects.select_for_update().get(pk=charge.wallet_id)
    wallet.reserved_balance -= charge.reserved_credits
    wallet.save(update_fields=["reserved_balance", "updated_at"])
    charge.status = ChargeStatus.RELEASED
    charge.released_at = timezone.now()
    charge.save(update_fields=["status", "released_at"])
    _entry(
        wallet,
        CreditTransactionType.GENERATION_RELEASE,
        0,
        -charge.reserved_credits,
        f"generation:{generation_id}:release",
        "Generation reservation released",
        charge.generation,
    )
    return charge


def audit_wallets():
    issues = []
    for wallet in CreditWallet.objects.all():
        totals = wallet.transactions.aggregate(
            balance=Sum("balance_delta"), reserved=Sum("reserved_delta")
        )
        expected_balance = totals["balance"] or 0
        expected_reserved = totals["reserved"] or 0
        if wallet.balance != expected_balance or wallet.reserved_balance != expected_reserved:
            issues.append(
                f"wallet {wallet.pk}: stored={wallet.balance}/{wallet.reserved_balance} "
                f"ledger={expected_balance}/{expected_reserved}"
            )
    for charge in GenerationCharge.objects.filter(status=ChargeStatus.RESERVED).select_related(
        "generation"
    ):
        if charge.generation and charge.generation.status in {"completed", "failed", "cancelled"}:
            issues.append(
                f"charge {charge.pk}: reserved for terminal {charge.generation.status} generation"
            )
    return issues
