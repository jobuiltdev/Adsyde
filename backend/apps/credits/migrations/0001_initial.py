import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("generations", "0002_provider_readiness"),
    ]
    operations = [
        migrations.CreateModel(
            name="CreditWallet",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("balance", models.PositiveBigIntegerField(default=0)),
                ("reserved_balance", models.PositiveBigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="credit_wallet", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=Q(("balance__gte", 0)), name="credit_balance_nonnegative"),
                    models.CheckConstraint(condition=Q(("reserved_balance__gte", 0)), name="credit_reserved_nonnegative"),
                    models.CheckConstraint(condition=Q(("reserved_balance__lte", F("balance"))), name="credit_reserved_within_balance"),
                ]
            },
        ),
        migrations.CreateModel(
            name="GenerationCharge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("generation_id_snapshot", models.UUIDField(unique=True)),
                ("quoted_credits", models.PositiveIntegerField()),
                ("reserved_credits", models.PositiveIntegerField()),
                ("charged_credits", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("reserved", "Reserved"), ("charged", "Charged"), ("released", "Released"), ("refunded", "Refunded")], max_length=16)),
                ("pricing_version", models.CharField(max_length=32)),
                ("pricing_snapshot", models.JSONField(default=dict)),
                ("reserved_at", models.DateTimeField()),
                ("charged_at", models.DateTimeField(blank=True, null=True)),
                ("released_at", models.DateTimeField(blank=True, null=True)),
                ("generation", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="credit_charge", to="generations.generation")),
                ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="charges", to="credits.creditwallet")),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=Q(("quoted_credits__gt", 0)), name="charge_quote_positive"),
                    models.CheckConstraint(condition=Q(("reserved_credits__gt", 0)), name="charge_reserved_positive"),
                    models.CheckConstraint(condition=Q(("charged_credits__gte", 0)), name="charge_charged_nonnegative"),
                ]
            },
        ),
        migrations.CreateModel(
            name="CreditTransaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("transaction_type", models.CharField(choices=[("purchase", "Purchase"), ("promo", "Promotional credit"), ("admin_adjustment", "Administrative adjustment"), ("generation_reservation", "Generation reservation"), ("generation_release", "Generation release"), ("generation_charge", "Video generation"), ("refund", "Refund")], max_length=32)),
                ("balance_delta", models.BigIntegerField(default=0)),
                ("reserved_delta", models.BigIntegerField(default=0)),
                ("balance_after", models.PositiveBigIntegerField()),
                ("reserved_after", models.PositiveBigIntegerField()),
                ("reference", models.CharField(max_length=255, unique=True)),
                ("reason", models.CharField(max_length=255)),
                ("generation_id_snapshot", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("generation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="generations.generation")),
                ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="credits.creditwallet")),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "indexes": [models.Index(fields=["wallet", "-created_at"], name="credit_wallet_time_idx")],
            },
        ),
    ]
