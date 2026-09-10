from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .catalog import PACKAGES
from .exceptions import InvalidPaymentResponse
from .models import Payment
from .serializers import PaymentInitializeSerializer, PaymentSerializer
from .services import initialize_payment, record_webhook, verify_payment
from .webhooks import valid_paystack_signature


def require_payments_enabled():
    if not settings.PAYMENTS_ENABLED:
        error = APIException("Credit purchases are not currently available.")
        error.status_code = 503
        error.default_code = "PAYMENTS_UNAVAILABLE"
        raise error


class PackageListView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment_packages"

    def get(self, request):
        require_payments_enabled()
        return Response([item.public_dict() for item in PACKAGES if item.enabled])


class PaymentInitializeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment_initialize"

    def post(self, request):
        require_payments_enabled()
        if not request.user.email_verified:
            raise PermissionDenied("Verify your email before purchasing credits.")
        key = request.headers.get("Idempotency-Key", "").strip()
        if not 8 <= len(key) <= 128:
            raise ValidationError({"idempotency_key": ["A valid Idempotency-Key is required."]})
        serializer = PaymentInitializeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = initialize_payment(request.user, serializer.validated_data["package"], key)
        except ValueError as exc:
            raise ValidationError({"package": [str(exc)]}) from exc
        data = PaymentSerializer(payment).data
        data["authorization_url"] = payment.authorization_url or None
        return Response(data, status=status.HTTP_201_CREATED)


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment_status"

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


class PaymentDetailView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment_status"

    def get_payment(self, request, payment_id):
        return get_object_or_404(Payment, pk=payment_id, user=request.user)

    def get(self, request, payment_id):
        return Response(PaymentSerializer(self.get_payment(request, payment_id)).data)


class PaymentVerifyView(PaymentDetailView):
    def post(self, request, payment_id):
        payment = self.get_payment(request, payment_id)
        return Response(PaymentSerializer(verify_payment(payment.pk)).data)


class PaystackWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment_webhook"

    def post(self, request):
        payload = request.body
        if not valid_paystack_signature(
            settings.PAYSTACK_SECRET_KEY,
            payload,
            request.headers.get("X-Paystack-Signature", ""),
        ):
            return Response({"detail": "Invalid payment signature."}, status=401)
        try:
            record_webhook(payload)
        except InvalidPaymentResponse:
            return Response({"detail": "Invalid payment event."}, status=400)
        return Response(status=204)
