class PaymentProviderError(Exception):
    pass


class PaymentProviderUnavailable(PaymentProviderError):
    pass


class InvalidPaymentResponse(PaymentProviderError):
    pass
