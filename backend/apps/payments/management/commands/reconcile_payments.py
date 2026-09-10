from django.core.management.base import BaseCommand, CommandError

from apps.payments.models import Payment, PaymentStatus
from apps.payments.services import verify_payment


class Command(BaseCommand):
    help = "Verify pending payments through the configured provider."

    def add_arguments(self, parser):
        parser.add_argument("--reference")
        parser.add_argument("--pending", action="store_true")

    def handle(self, *args, **options):
        queryset = Payment.objects.all()
        if options["reference"]:
            queryset = queryset.filter(internal_reference=options["reference"])
        elif options["pending"]:
            queryset = queryset.filter(
                status__in=[
                    PaymentStatus.INITIALIZED,
                    PaymentStatus.PENDING,
                    PaymentStatus.VERIFICATION_REQUIRED,
                ]
            )
        else:
            raise CommandError("Use --pending or --reference.")
        count = 0
        for payment in queryset:
            verify_payment(payment.pk)
            count += 1
        self.stdout.write(f"Reconciled {count} payment(s).")
