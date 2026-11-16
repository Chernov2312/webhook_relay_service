import hashlib
import hmac
import secrets


def generate_secret() -> str:
    return secrets.token_urlsafe(32)


def sign_payload(secret: str, body: bytes) -> str:
    """Return a SHA-256 HMAC in the ``sha256=<hex>`` wire format."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"
