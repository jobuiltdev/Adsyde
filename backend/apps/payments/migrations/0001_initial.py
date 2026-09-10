import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(default="paystack", max_length=24)),
                ("internal_reference", models.CharField(max_length=64, unique=True)),
                ("provider_reference", models.CharField(max_length=100, unique=True)),
                ("initialization_key", models.CharField(max_length=128)),
                ("package_key", models.CharField(max_length=32)),
                ("package_name", models.CharField(max_length=64)),
                ("currency", models.CharField(max_length=3)),
                ("amount_minor", models.PositiveBigIntegerField()),
                ("credits", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("created", "Created"), ("initialized", "Initialized"), ("pending", "Pending"), ("verification_required", "Verification required"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("review_required", "Review required")], default="created", max_length=32)),
                ("provider_status", models.CharField(blank=True, max_length=32)),
                ("authorization_url", models.URLField(blank=True, max_length=500)),
                ("access_code", models.CharField(blank=True, max_length=100)),
                ("initiated_at", models.DateTimeField(blank=True, null=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("succeeded_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("credited_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "indexes": [models.Index(fields=["user", "-created_at"], name="payment_user_time_idx"), models.Index(fields=["status"], name="payment_status_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "initialization_key"), name="payment_user_init_key_unique"),
                    models.CheckConstraint(condition=models.Q(("amount_minor__gt", 0)), name="payment_amount_positive"),
                    models.CheckConstraint(condition=models.Q(("credits__gt", 0)), name="payment_credits_positive"),
                    models.CheckConstraint(condition=models.Q(("currency", "NGN")), name="payment_currency_ngn"),
                ],
            },
        ),
        migrations.CreateModel(
            name="PaymentEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(max_length=24)),
                ("event_fingerprint", models.CharField(max_length=64, unique=True)),
                ("event_type", models.CharField(max_length=64)),
                ("provider_reference", models.CharField(blank=True, max_length=100)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("outcome", models.CharField(blank=True, max_length=32)),
                ("payment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="events", to="payments.payment")),
            ],
        ),
    ]
