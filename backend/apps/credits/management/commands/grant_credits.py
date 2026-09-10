import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.credits.services import grant_credits


class Command(BaseCommand):
    help = "Grant development credits through the immutable ledger."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("amount", type=int)
        parser.add_argument("--reason", required=True)
        parser.add_argument("--reference")

    def handle(self, *args, **options):
        if not settings.CREDIT_DEVELOPMENT_GRANTS_ENABLED:
            raise CommandError("Development credit grants are disabled.")
        if options["amount"] <= 0:
            raise CommandError("Amount must be a positive integer.")
        try:
            user = get_user_model().objects.get(email__iexact=options["email"].strip())
        except get_user_model().DoesNotExist as exc:
            raise CommandError("User does not exist.") from exc
        reference = options["reference"] or f"admin:{uuid.uuid4()}"
        try:
            entry = grant_credits(user, options["amount"], options["reason"], reference)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Granted {options['amount']} credits; balance is {entry.balance_after}."
            )
        )
