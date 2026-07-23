"""
Webhook routes for external service callbacks.

Handles:
- Stripe payout webhooks
"""

from fastapi import APIRouter, Request, HTTPException, Header
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Service will be set by main app
payout_service = None


def set_payout_service(service):
    global payout_service
    payout_service = service


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """
    Handle Stripe webhook events.
    
    Events handled:
    - payout.paid: Payout completed successfully
    - payout.failed: Payout failed
    - payout.canceled: Payout was canceled
    """
    if not stripe_signature:
        logger.warning("Stripe webhook received without signature header")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    
    payload = await request.body()
    
    success, error = await payout_service.handle_webhook(payload, stripe_signature)
    
    if not success:
        logger.error(f"Stripe webhook processing failed: {error}")
        # Return 200 anyway to prevent Stripe from retrying
        # Log the error for investigation
        return {"status": "error", "message": error}
    
    return {"status": "success"}
