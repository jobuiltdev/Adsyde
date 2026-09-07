from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def send_verification_email(user) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    url = f"{settings.FRONTEND_BASE_URL}/verify-email?uid={uid}&token={token}"
    send_mail(
        "Verify your Adsyde email",
        f"Verify your email address to activate your Adsyde account:\n\n{url}\n",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def send_password_reset_email(user, token_generator) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)
    url = f"{settings.FRONTEND_BASE_URL}/reset-password?uid={uid}&token={token}"
    send_mail(
        "Reset your Adsyde password",
        f"Use this link to reset your Adsyde password:\n\n{url}\n",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
