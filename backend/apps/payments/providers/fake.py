from .base import InitializationResult, PaymentProvider, VerificationResult


class FakePaymentProvider(PaymentProvider):
    transactions = {}

    def initialize(self, *, email, amount_minor, currency, reference, callback_url):
        self.transactions.setdefault(
            reference,
            VerificationResult(reference, "pending", amount_minor, currency, email),
        )
        return InitializationResult(
            f"https://checkout.paystack.com/test-{reference}",
            f"test-{reference}",
            reference,
        )

    def verify(self, reference):
        return self.transactions[reference]

    @classmethod
    def set_result(cls, reference, *, status, amount_minor, currency, customer_email):
        cls.transactions[reference] = VerificationResult(
            reference, status, amount_minor, currency, customer_email
        )
