from dataclasses import dataclass


@dataclass(frozen=True)
class CreditPackage:
    key: str
    name: str
    credits: int
    amount_minor: int
    currency: str = "NGN"
    enabled: bool = True

    def public_dict(self):
        return {
            "key": self.key,
            "name": self.name,
            "credits": self.credits,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
        }


PACKAGES = (
    CreditPackage("starter", "Starter", 500, 500000),
    CreditPackage("growth", "Growth", 1200, 1000000),
    CreditPackage("creator", "Creator", 3000, 2000000),
)


def get_package(key):
    return next((item for item in PACKAGES if item.key == key and item.enabled), None)
