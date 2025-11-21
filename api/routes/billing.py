from fastapi import APIRouter, Request, Header, HTTPException
from api.utils.stripe_verify import verify_stripe_signature

router = APIRouter(prefix="/stripe", tags=["billing"])


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default=None, alias="Stripe-Signature")
):
    if not stripe_signature:
        raise HTTPException(400, "Missing Stripe-Signature header")

    payload = await request.body()

    # Validate signature
    verify_stripe_signature(payload, stripe_signature)

    # TODO: handle Stripe events here (invoice.paid, usage.reported, etc.)
    # For now, simply acknowledge.
    return {"ok": True}
