from django.core.management.base import BaseCommand, CommandError

from apps.credits.services import audit_wallets


class Command(BaseCommand):
    help = "Report credit ledger and lifecycle inconsistencies without changing data."

    def handle(self, *args, **options):
        issues = audit_wallets()
        if issues:
            for issue in issues:
                self.stderr.write(issue)
            raise CommandError(f"Found {len(issues)} credit accounting issue(s).")
        self.stdout.write(self.style.SUCCESS("Credit accounting is consistent."))
