import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .emails import send_password_reset_email, send_verification_email
from .serializers import (
    AccountUpdateSerializer,
    EmailSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    TokenInputSerializer,
    TokenPairSerializer,
    UserSerializer,
    VerificationSerializer,
    user_from_uid,
)
from .services import revoke_refresh_tokens
from .tokens import email_verification_token

logger = logging.getLogger(__name__)
User = get_user_model()


def audit(event: str, outcome: str, user=None) -> None:
    logger.info(
        event,
        extra={"event": event, "outcome": outcome, "account_id": str(user.pk) if user else None},
    )


class PublicScopedView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]


class RegisterView(PublicScopedView):
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = serializer.save()
                send_verification_email(user)
        except IntegrityError as exc:
            raise ValidationError(
                {"email": ["An account with this email already exists."]}
            ) from exc
        audit("auth.registration", "success", user)
        return Response(
            {"detail": "Registration accepted. Check your email to verify your account."},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(PublicScopedView):
    throttle_scope = "auth_verify"

    def post(self, request):
        serializer = VerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        user = user_from_uid(serializer.validated_data["uid"])
        if user is None:
            return Response(
                {
                    "error": {
                        "code": "invalid_token",
                        "detail": "The verification link is invalid or has expired.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            if not email_verification_token.check_token(user, token):
                return Response(
                    {
                        "error": {
                            "code": "invalid_token",
                            "detail": "The verification link is invalid or has expired.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
        audit("auth.email_verified", "success", user)
        return Response({"detail": "Email verified."})


class VerificationResendView(PublicScopedView):
    throttle_scope = "auth_verification_resend"

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is not None and user.is_active and not user.email_verified:
            send_verification_email(user)
        return Response({"detail": "If verification is available, an email has been sent."})


class LoginView(PublicScopedView):
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            supplied_email = request.data.get("email")
            user = None
            if isinstance(supplied_email, str):
                user = User.objects.filter(email__iexact=supplied_email.strip()).first()
            audit("auth.login", "failure", user)
            raise ValidationError(serializer.errors)
        user = serializer.validated_data["user"]
        audit("auth.login", "success", user)
        return Response(TokenPairSerializer.for_user(user))


class RefreshView(TokenRefreshView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_refresh"


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_logout"

    def post(self, request):
        serializer = TokenInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token["user_id"]) != str(request.user.pk):
                raise TokenError("Token does not belong to this account")
            token.blacklist()
        except TokenError:
            pass
        audit("auth.logout", "success", request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "account_update"

    def get_throttles(self):
        if self.request.method == "GET":
            return []
        return super().get_throttles()

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = AccountUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            request.user.set_password(serializer.validated_data["new_password"])
            request.user.save(update_fields=["password"])
            revoke_refresh_tokens(request.user)
        audit("auth.password_changed", "success", request.user)
        return Response({"detail": "Password updated. Sign in again on all devices."})


class PasswordResetView(PublicScopedView):
    throttle_scope = "auth_password_reset"

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is not None and user.is_active:
            send_password_reset_email(user, default_token_generator)
        return Response(
            {"detail": "If the account is eligible, a password reset email has been sent."}
        )


class PasswordResetConfirmView(PublicScopedView):
    throttle_scope = "auth_password_reset_confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            if not default_token_generator.check_token(user, serializer.validated_data["token"]):
                raise ValidationError("The reset link is invalid or has expired.")
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password"])
            revoke_refresh_tokens(user)
        audit("auth.password_reset", "success", user)
        return Response({"detail": "Password reset complete. Sign in again on all devices."})
