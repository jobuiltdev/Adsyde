from rest_framework.exceptions import ValidationError

BLOCKED_TERMS = {
    "make a deepfake",
    "impersonate a real person",
    "sell illegal drugs",
    "build a weapon",
}


def validate_creative_text(values):
    combined = " ".join(value for value in values if value).lower()
    if any(term in combined for term in BLOCKED_TERMS):
        raise ValidationError("This request cannot be used for an ad plan.")
