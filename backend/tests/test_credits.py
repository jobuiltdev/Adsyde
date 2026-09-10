from concurrent.futures import ThreadPoolExecutor
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db import IntegrityError, close_old_connections, transaction

from apps.credits.exceptions import InsufficientCredits
from apps.credits.models import (
    ChargeStatus,
    CreditTransaction,
    CreditTransactionType,
    CreditWallet,
    GenerationCharge,
)
from apps.credits.pricing import PricingUnavailable, quote_generation
from apps.credits.services import (
    audit_wallets,
    charge_generation,
    get_or_create_wallet,
    grant_credits,
    release_generation,
    reserve_generation,
)
from apps.generations.models import GenerationStatus
from apps.generations.services import cancel_generation, fail_generation
from apps.generations.tasks import submit_generation_task
from tests.test_generations import auth_client, make_generation, make_user


@pytest.fixture
def empty_wallet(settings):
    settings.CREDIT_DEVELOPMENT_INITIAL_GRANT = 0
    user = make_user("credits@example.com")
    with transaction.atomic():
        wallet = get_or_create_wallet(user)
    return user, wallet


@pytest.mark.django_db
def test_wallet_creation_and_database_invariants(empty_wallet):
    user, wallet = empty_wallet
    assert wallet.balance == wallet.reserved_balance == wallet.available_balance == 0
    with pytest.raises(IntegrityError), transaction.atomic():
        CreditWallet.objects.create(user=user)
    wallet.reserved_balance = 1
    with pytest.raises(IntegrityError), transaction.atomic():
        wallet.save()


@pytest.mark.django_db
def test_grant_is_positive_ledger_backed_and_idempotent(empty_wallet):
    user, wallet = empty_wallet
    first = grant_credits(user, 500, "Local development", "admin:grant-one")
    second = grant_credits(user, 500, "Local development", "admin:grant-one")
    wallet.refresh_from_db()
    assert first.pk == second.pk
    assert wallet.balance == 500
    assert first.balance_delta == 500
    assert CreditTransaction.objects.count() == 1
    with pytest.raises(ValueError):
        grant_credits(user, 0, "Invalid", "admin:invalid")


@pytest.mark.django_db
def test_reserve_charge_and_release_are_idempotent(empty_wallet):
    user, wallet = empty_wallet
    grant_credits(user, 500, "Local development", "admin:fund")
    generation = make_generation(owner=user)
    charge = reserve_generation(generation)
    assert reserve_generation(generation).pk == charge.pk
    wallet.refresh_from_db()
    assert charge.quoted_credits == 96
    assert wallet.balance == 500
    assert wallet.reserved_balance == 96
    assert wallet.available_balance == 404
    charge_generation(generation.pk)
    charge_generation(generation.pk)
    wallet.refresh_from_db()
    charge.refresh_from_db()
    assert charge.status == ChargeStatus.CHARGED
    assert wallet.balance == 404
    assert wallet.reserved_balance == 0
    assert release_generation(generation.pk).status == ChargeStatus.CHARGED
    assert (
        CreditTransaction.objects.filter(
            transaction_type=CreditTransactionType.GENERATION_CHARGE
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_insufficient_and_exact_balance_reservations(empty_wallet):
    user, wallet = empty_wallet
    generation = make_generation(owner=user)
    grant_credits(user, 95, "Local", "admin:short")
    with pytest.raises(InsufficientCredits):
        reserve_generation(generation)
    assert not GenerationCharge.objects.exists()
    grant_credits(user, 1, "Local", "admin:exact")
    reserve_generation(generation)
    wallet.refresh_from_db()
    assert wallet.available_balance == 0


@pytest.mark.django_db
def test_failed_and_cancelled_generations_release_once(empty_wallet):
    user, wallet = empty_wallet
    grant_credits(user, 500, "Local", "admin:fund")
    failed = make_generation(owner=user, status=GenerationStatus.PROCESSING)
    reserve_generation(failed)
    fail_generation(failed.pk, "GENERATION_FAILED", "Failed safely.")
    fail_generation(failed.pk, "GENERATION_FAILED", "Repeated.")
    cancelled = make_generation(owner=user)
    reserve_generation(cancelled)
    cancel_generation(cancelled)
    wallet.refresh_from_db()
    assert wallet.balance == 500
    assert wallet.reserved_balance == 0
    assert GenerationCharge.objects.filter(status=ChargeStatus.RELEASED).count() == 2


@pytest.mark.django_db(transaction=True)
def test_unknown_keeps_reservation_and_unresolved_releases(settings, empty_wallet):
    user, wallet = empty_wallet
    grant_credits(user, 500, "Local", "admin:fund")
    settings.GENERATION_POLL_INTERVAL_SECONDS = 0
    settings.GENERATION_MAX_RECONCILIATION_ATTEMPTS = 2
    generation = make_generation(owner=user, scenario="uncertain_unresolved")
    reserve_generation(generation)
    submit_generation_task.delay(str(generation.pk))
    generation.refresh_from_db()
    wallet.refresh_from_db()
    assert generation.status == GenerationStatus.FAILED
    assert generation.error_code == "PROVIDER_STATE_UNRESOLVED"
    assert wallet.reserved_balance == 0
    assert generation.credit_charge.status == ChargeStatus.RELEASED


@pytest.mark.django_db
def test_pricing_snapshot_is_historical(settings, empty_wallet):
    user, _ = empty_wallet
    grant_credits(user, 500, "Local", "admin:fund")
    generation = make_generation(owner=user)
    charge = reserve_generation(generation)
    settings.CREDIT_GENERATION_RATES = {"mock-standard": 99}
    charge.refresh_from_db()
    assert charge.quoted_credits == 96
    assert charge.pricing_snapshot["credits_per_second"] == 12
    with pytest.raises(PricingUnavailable):
        quote_generation("missing", 8)


@pytest.mark.django_db
def test_wallet_and_history_apis_are_private(settings):
    settings.CREDIT_DEVELOPMENT_INITIAL_GRANT = 1000
    user = make_user("wallet-api@example.com")
    other = make_user("other-wallet@example.com")
    assert auth_client(user).get("/api/v1/credits/wallet/").json() == {
        "balance": 1000,
        "reserved": 0,
        "available": 1000,
    }
    history = auth_client(user).get("/api/v1/credits/transactions/").json()
    assert history["count"] == 1
    assert "wallet" not in history["results"][0]
    assert auth_client(other).get("/api/v1/credits/transactions/").json()["count"] == 1


@pytest.mark.django_db
def test_options_include_authoritative_prices_and_client_cannot_set_price():
    user = make_user("quote@example.com")
    options = auth_client(user).get("/api/v1/generation-options/").json()
    standard = next(item for item in options["models"] if item["key"] == "mock-standard")
    assert standard["credit_prices"]["10"] == 120
    generation = make_generation(owner=user)
    payload = {
        "prompt": "Valid advertisement",
        "aspect_ratio": "9:16",
        "duration_seconds": 10,
        "model": "mock-standard",
        "credit_cost": 1,
    }
    response = auth_client(user).post(
        f"/api/v1/projects/{generation.project_id}/generations/", payload, format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_insufficient_generation_does_not_queue(settings, empty_wallet):
    user, _ = empty_wallet
    generation = make_generation(owner=user)
    payload = {
        "prompt": "Valid advertisement",
        "aspect_ratio": "9:16",
        "duration_seconds": 10,
        "model": "mock-standard",
    }
    response = auth_client(user).post(
        f"/api/v1/projects/{generation.project_id}/generations/", payload, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_CREDITS"


@pytest.mark.django_db
def test_ledger_is_immutable_and_survives_project_deletion(empty_wallet):
    user, _ = empty_wallet
    grant_credits(user, 500, "Local", "admin:fund")
    generation = make_generation(owner=user)
    reserve_generation(generation)
    project = generation.project
    project.delete()
    charge = GenerationCharge.objects.get(generation_id_snapshot=generation.pk)
    entry = CreditTransaction.objects.get(reference=f"generation:{generation.pk}:reserve")
    assert charge.generation is None
    assert entry.generation is None
    assert entry.generation_id_snapshot == generation.pk
    entry.reason = "Changed"
    with pytest.raises(ValueError):
        entry.save()
    with pytest.raises(ValueError):
        entry.delete()


@pytest.mark.django_db
def test_ledger_failure_rolls_back_wallet(monkeypatch, empty_wallet):
    user, wallet = empty_wallet
    grant_credits(user, 500, "Local", "admin:fund")
    generation = make_generation(owner=user)
    monkeypatch.setattr("apps.credits.services._entry", lambda *args, **kwargs: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        reserve_generation(generation)
    wallet.refresh_from_db()
    assert wallet.reserved_balance == 0
    assert not GenerationCharge.objects.exists()


@pytest.mark.django_db
def test_audit_detects_wallet_and_terminal_charge_mismatches(empty_wallet):
    user, wallet = empty_wallet
    grant_credits(user, 500, "Local", "admin:fund")
    assert audit_wallets() == []
    CreditWallet.objects.filter(pk=wallet.pk).update(balance=499)
    assert any("stored=" in issue for issue in audit_wallets())


@pytest.mark.django_db
def test_management_commands_use_ledger(empty_wallet):
    user, _ = empty_wallet
    output = StringIO()
    call_command(
        "grant_credits",
        user.email,
        "250",
        reason="Local development",
        reference="admin:command",
        stdout=output,
    )
    assert "balance is 250" in output.getvalue()
    audit = StringIO()
    call_command("reconcile_credits", stdout=audit)
    assert "consistent" in audit.getvalue()
    with pytest.raises(CommandError):
        call_command("grant_credits", "missing@example.com", "1", reason="Missing")


@pytest.mark.django_db(transaction=True)
def test_postgresql_concurrent_reservations_cannot_overspend(empty_wallet):
    user, wallet = empty_wallet
    grant_credits(user, 150, "Local", "admin:fund")
    first = make_generation(owner=user)
    second = make_generation(owner=user)

    def attempt(generation_id):
        close_old_connections()
        from apps.generations.models import Generation

        try:
            reserve_generation(Generation.objects.get(pk=generation_id))
            return "reserved"
        except InsufficientCredits:
            return "insufficient"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (first.pk, second.pk)))
    wallet.refresh_from_db()
    assert sorted(results) == ["insufficient", "reserved"]
    assert wallet.balance == 150
    assert wallet.reserved_balance == 96
    assert wallet.available_balance == 54
