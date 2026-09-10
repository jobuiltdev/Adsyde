import hashlib
import hmac
import time


def sign_payload(secret: str, timestamp: int, payload: bytes) -> str:
    digest = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + payload, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


def verify_signature(
    secret: str, timestamp_value: str, signature: str, payload: bytes, tolerance_seconds: int
) -> bool:
    if not secret:
        return False
    try:
        timestamp = int(timestamp_value)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - timestamp) > tolerance_seconds:
        return False
    return hmac.compare_digest(sign_payload(secret, timestamp, payload), signature)
