from django.core.management.base import BaseCommand, CommandError

from apps.payments.services import audit_payments


class Command(BaseCommand):
    help = "Report payment and purchase-ledger inconsistencies without changing data."

    def handle(self, *args, **options):
        issues = audit_payments()
        if issues:
            for issue in issues:
                self.stderr.write(issue)
            raise CommandError(f"Found {len(issues)} payment issue(s).")
        self.stdout.write(self.style.SUCCESS("Payment accounting is consistent."))
