import os
import hmac
import hashlib
import time
from fastapi import HTTPException


WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


def verify_stripe_signature(payload: bytes, signature: str, tolerance: int = 300):
    """
    Minimal Stripe-signature validator.
    Compatible with Stripe’s "t=<timestamp>,v1=<signature>" format.
    """

    if not WEBHOOK_SECRET:
        raise HTTPException(500, "Stripe webhook secret not configured")

    try:
        # Parse Stripe header: "t=xxx,v1=xxx"
        items = dict(kv.split("=", 1) for kv in signature.split(","))
        ts = int(items.get("t", "0"))
        sig_provided = items.get("v1", "")

    except Exception:
        raise HTTPException(400, "Malformed Stripe signature header")

    # Timestamp tolerance
    if abs(time.time() - ts) > tolerance:
        raise HTTPException(400, "Stripe signature timestamp outside allowed tolerance")

    # Signed payload is "timestamp.payload"
    signed_payload = f"{ts}.".encode() + payload

    # Compute expected HMAC
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, sig_provided):
        raise HTTPException(400, "Stripe signature mismatch")

    return True
