from dataclasses import dataclass

from django.conf import settings


class PricingUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class PriceQuote:
    credits: int
    version: str
    snapshot: dict


def quote_generation(model: str, duration_seconds: int) -> PriceQuote:
    rate = settings.CREDIT_GENERATION_RATES.get(model)
    if not isinstance(rate, int) or rate <= 0:
        raise PricingUnavailable("Pricing is unavailable for the selected model.")
    credits = rate * duration_seconds
    return PriceQuote(
        credits,
        settings.CREDIT_PRICING_VERSION,
        {
            "version": settings.CREDIT_PRICING_VERSION,
            "model": model,
            "duration_seconds": duration_seconds,
            "credits_per_second": rate,
            "quoted_credits": credits,
        },
    )
