import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

from apps.payments.exceptions import InvalidPaymentResponse, PaymentProviderUnavailable

from .base import InitializationResult, PaymentProvider, VerificationResult


class PaystackProvider(PaymentProvider):
    base_url = "https://api.paystack.co"

    def _request(self, path, *, payload=None, timeout):
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            self.base_url + path,
            data=body,
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            method="POST" if body else "GET",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                value = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise PaymentProviderUnavailable(
                "Payment provider is temporarily unavailable."
            ) from exc
        if not value.get("status") or not isinstance(value.get("data"), dict):
            raise InvalidPaymentResponse("Payment provider response was invalid.")
        return value["data"]

    def initialize(self, *, email, amount_minor, currency, reference, callback_url):
        data = self._request(
            "/transaction/initialize",
            payload={
                "email": email,
                "amount": amount_minor,
                "currency": currency,
                "reference": reference,
                "callback_url": callback_url,
                "metadata": {"payment_reference": reference},
            },
            timeout=settings.PAYSTACK_INITIALIZE_TIMEOUT_SECONDS,
        )
        try:
            return InitializationResult(
                data["authorization_url"], data["access_code"], data["reference"]
            )
        except KeyError as exc:
            raise InvalidPaymentResponse("Payment initialization response was invalid.") from exc

    def verify(self, reference):
        data = self._request(
            f"/transaction/verify/{quote(reference, safe='')}",
            timeout=settings.PAYSTACK_VERIFY_TIMEOUT_SECONDS,
        )
        try:
            return VerificationResult(
                data["reference"],
                data["status"],
                int(data["amount"]),
                data["currency"],
                data["customer"]["email"].lower(),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidPaymentResponse("Payment verification response was invalid.") from exc
