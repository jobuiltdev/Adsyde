from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare
from django.utils.http import base36_to_int


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "apps.accounts.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.email}{user.email_verified_at}"

    def check_token(self, user, token):
        if not (user and token):
            return False
        try:
            ts_b36, _ = token.split("-")
            timestamp = base36_to_int(ts_b36)
        except (ValueError, TypeError):
            return False
        if not constant_time_compare(
            self._make_token_with_timestamp(user, timestamp, self.secret), token
        ):
            return False
        age = self._num_seconds(self._now()) - timestamp
        return age <= settings.EMAIL_VERIFICATION_TIMEOUT


email_verification_token = EmailVerificationTokenGenerator()
