import hashlib
import hmac


def sign_paystack_payload(secret, payload):
    return hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()


def valid_paystack_signature(secret, payload, signature):
    if not secret or not signature:
        return False
    return hmac.compare_digest(sign_paystack_payload(secret, payload), signature)
