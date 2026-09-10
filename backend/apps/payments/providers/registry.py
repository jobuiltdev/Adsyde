from django.conf import settings

from .fake import FakePaymentProvider
from .paystack import PaystackProvider

_PROVIDERS = {"fake": FakePaymentProvider(), "paystack": PaystackProvider()}


def get_payment_provider():
    return _PROVIDERS[settings.PAYMENT_PROVIDER]
