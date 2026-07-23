"""
Transak integration routes (staging).

All endpoints are intentionally observational:
  GET  /api/transak/config         -> public widget config (api key + env)
  POST /api/transak/events         -> log a widget event from the user's
                                       own session (NOT a trade trigger)
  GET  /api/transak/events         -> read back the caller's events for
                                       the connected wallet
  POST /api/transak/webhook        -> server-to-server event hook from
                                       Transak with HMAC-SHA256 signature
                                       verification

There is NO endpoint that creates, routes, or settles a trade — the
Transak widget runs in the user's browser and settles directly to the
user's wallet. This is what "non-custodial + no fund intermediation"
means at the API layer.
"""

import hmac
import hashlib
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List

from middleware.auth import get_optional_user, get_current_user
from middleware.kyc_gate import require_kyc_approved
from services.transak_service import TransakService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transak", tags=["Transak"])

# Service is wired by main app
transak_service: Optional[TransakService] = None


def set_transak_service(service: TransakService):
    global transak_service
    transak_service = service


class TransakEventRequest(BaseModel):
    wallet_address: str = Field(..., description="User's connected wallet address")
    event_type: str = Field(..., description="Transak event name, e.g., TRANSAK_ORDER_SUCCESSFUL")
    payload: Dict[str, Any] = Field(default_factory=dict)


class TransakEventResponse(BaseModel):
    success: bool
    event_id: str


class CreateWidgetUrlRequest(BaseModel):
    productsAvailed: Optional[str] = None
    cryptoCurrencyCode: Optional[str] = None
    # BEP-20 / ERC-20 contract address for custom token (e.g., NENO on BSC).
    # Transak requires this when the token symbol alone is ambiguous or is a
    # custom asset the partner has whitelisted.
    cryptoCurrencyAddress: Optional[str] = None
    # Comma-separated list of allowed crypto currency codes. Used by SWAP flow
    # to restrict the source/destination selection to a curated subset.
    cryptoCurrencyList: Optional[str] = None
    network: Optional[str] = None
    walletAddress: Optional[str] = None
    disableWalletAddressForm: Optional[str] = None
    hideMenu: Optional[str] = None
    themeColor: Optional[str] = None
    defaultFiatCurrency: Optional[str] = None
    partnerCustomerId: Optional[str] = None
    fiatCurrency: Optional[str] = None
    fiatAmount: Optional[float] = None
    referrerDomain: Optional[str] = None


class CreateWidgetUrlResponse(BaseModel):
    widget_url: str
    referrer_domain_sent: str
    expires_in_seconds: int


@router.get("/config")
async def get_config():
    """Return the public, read-only Transak widget config."""
    if not transak_service:
        raise HTTPException(status_code=503, detail="Transak service not ready")
    config = transak_service.get_public_config()
    if not config.get("api_key"):
        raise HTTPException(
            status_code=503,
            detail="TRANSAK_API_KEY not configured on backend",
        )
    return config


@router.post("/widget-url", response_model=CreateWidgetUrlResponse)
async def create_widget_url(
    request: CreateWidgetUrlRequest,
    current_user: dict = Depends(require_kyc_approved),
):
    """Create a single-use Transak widget URL with embedded session token.

    Server-side KYC enforcement: the calling USER must have an APPROVED
    KYC record. ADMIN / DEVELOPER roles bypass for internal testing.

    The backend calls Transak's /partners/api/v2/refresh-token (using
    TRANSAK_API_SECRET) to obtain a partner access token, then calls
    /api/v2/auth/session with the requested widgetParams to obtain the
    final widgetUrl. The frontend opens that URL in a popup.

    apiKey + referrerDomain are server-controlled — the frontend can pass
    a hint but the backend enforces the canonical values from env / config.
    """
    if not transak_service:
        raise HTTPException(status_code=503, detail="Transak service not ready")
    params = {k: v for k, v in request.model_dump().items() if v is not None}
    try:
        result = await transak_service.create_widget_url(params)
    except RuntimeError as e:
        msg = str(e)
        # 409 Conflict — the upstream account is in a state that needs
        # external action (KYB approval). Frontend can show a clear banner.
        if msg.startswith("TRANSAK_KYB_PENDING"):
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=502, detail=msg)
    except Exception as e:
        logger.exception("Failed to create Transak widget URL")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    return CreateWidgetUrlResponse(**result)


@router.post("/events", response_model=TransakEventResponse)
async def log_event(
    request: TransakEventRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
):
    """Log a Transak widget event forwarded by the frontend."""
    if not transak_service:
        raise HTTPException(status_code=503, detail="Transak service not ready")
    if not request.wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address is required")

    event_id = await transak_service.record_event(
        wallet_address=request.wallet_address,
        event_type=request.event_type,
        payload=request.payload,
        user_id=current_user.get("user_id") if current_user else None,
    )
    return TransakEventResponse(success=True, event_id=event_id)


@router.get("/events")
async def list_events(
    wallet_address: str = Query(..., min_length=10, max_length=64),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Read back a wallet's recent Transak events for the demo / audit."""
    if not transak_service:
        raise HTTPException(status_code=503, detail="Transak service not ready")
    return await transak_service.list_events_for_wallet(wallet_address, limit=limit)


def _verify_transak_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify the HMAC-SHA256 signature Transak sends with each webhook.
    Header format (Transak): 'sha256=<hex>' or the raw hex value.
    Secret is the TRANSAK_API_SECRET issued in the partner dashboard.
    """
    secret = os.environ.get("TRANSAK_API_SECRET", "").strip()
    if not secret:
        logger.warning("TRANSAK_API_SECRET not set — webhook signature cannot be verified")
        return False
    if not signature_header:
        return False
    received = signature_header.strip()
    if received.lower().startswith("sha256="):
        received = received.split("=", 1)[1]
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(received.lower(), expected.lower())


@router.post("/webhook")
async def transak_webhook(request: Request):
    """Server-to-server event hook from Transak.

    - Verifies the HMAC-SHA256 signature using TRANSAK_API_SECRET.
    - Persists the (verified) event for audit.
    - Returns 200 even on signature failure to avoid leaking which
      requests come from Transak vs. probes — but logs the rejection.
    """
    if not transak_service:
        raise HTTPException(status_code=503, detail="Transak service not ready")

    raw = await request.body()
    signature = (
        request.headers.get("x-signature")
        or request.headers.get("transak-signature")
        or request.headers.get("x-transak-signature")
        or ""
    )
    verified = _verify_transak_signature(raw, signature)

    try:
        import json
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except Exception:
        payload = {"_raw": raw.decode("utf-8", errors="ignore")}

    event_type = payload.get("eventID") or payload.get("event_id") or "TRANSAK_WEBHOOK"
    data = payload.get("webhookData") or payload.get("data") or payload
    wallet_address = ""
    if isinstance(data, dict):
        wallet_address = (
            data.get("walletAddress")
            or data.get("wallet_address")
            or data.get("customerWalletAddress")
            or ""
        )

    enriched_payload = {
        **payload,
        "_verified": verified,
        "_source": "webhook",
    }
    await transak_service.record_event(
        wallet_address=wallet_address,
        event_type=event_type,
        payload=enriched_payload,
        user_id=None,
    )
    if not verified:
        logger.warning(
            f"Transak webhook signature verification FAILED for event {event_type}"
        )
        # We still return 200 to avoid acknowledging the probe.
    else:
        logger.info(f"Transak webhook verified: {event_type}")
    return {"received": True, "verified": verified}
