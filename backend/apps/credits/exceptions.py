from rest_framework.exceptions import APIException


class InsufficientCredits(APIException):
    status_code = 409
    default_code = "INSUFFICIENT_CREDITS"
    default_detail = "There are not enough available credits for this generation."


class InvalidPricingOption(APIException):
    status_code = 400
    default_code = "INVALID_PRICING_OPTION"
    default_detail = "Pricing is unavailable for the selected generation options."
