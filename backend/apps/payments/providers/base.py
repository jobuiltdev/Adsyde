from dataclasses import dataclass


@dataclass(frozen=True)
class InitializationResult:
    authorization_url: str
    access_code: str
    reference: str


@dataclass(frozen=True)
class VerificationResult:
    reference: str
    status: str
    amount_minor: int
    currency: str
    customer_email: str


class PaymentProvider:
    def initialize(self, *, email, amount_minor, currency, reference, callback_url):
        raise NotImplementedError

    def verify(self, reference):
        raise NotImplementedError
