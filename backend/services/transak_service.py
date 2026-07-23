"""
Transak integration service (staging).

This service is intentionally THIN: NeoNoble does not custody funds,
does not route trades, and does not hold private keys. Its only role is:

  1. Expose a public, read-only config to the frontend (api key + env).
  2. Decide whether the user's preferred token (NENO) is available on
     Transak staging or whether the UI should fall back to USDC on BSC.
  3. Log Transak widget events the frontend forwards back to us, for
     compliance/audit and customer support — never as a trade trigger.

Compliance pillars enforced at this layer:
  - User-initiated Only:  no backend endpoint *creates* a trade.
                          We only persist events emitted by the user's
                          own Transak widget session.
  - No Fund Intermediation: no payout, payment, custody or routing API.
  - Direct Delivery:        we never read or write the user's wallet
                          address from our DB into the widget params.
                          The frontend passes the user's connected
                          wallet directly to Transak.
"""

import os
import time
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# NENO BEP-20 contract (mainnet). Same value used by the blockchain listener.
NENO_CONTRACT_ADDRESS = "0xeF3F5C1892A8d7A3304E4A15959E124402d69974"

# Transak partner-API endpoints
TRANSAK_API_STG = "https://api-stg.transak.com"
TRANSAK_API_PROD = "https://api.transak.com"
TRANSAK_GATEWAY_STG = "https://api-gateway-stg.transak.com"
TRANSAK_GATEWAY_PROD = "https://api-gateway.transak.com"

# Refresh ~24h before expiry to avoid edge-of-window failures
ACCESS_TOKEN_REFRESH_BUFFER_SECONDS = 24 * 60 * 60

# Transak does NOT list NENO in its supported assets on staging today.
# Until Transak adds the NENO listing, the widget will fall back to USDC
# on BSC. This flag is environment-tunable so we can flip it the moment
# Transak whitelists the contract above.
SUPPORTS_NENO_DEFAULT = False


class TransakService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.events_collection = db.transak_events
        # Cached partner access token (JWT) — refreshed before expiry
        self._access_token: Optional[str] = None
        self._access_token_expires_at: int = 0

    def _is_production(self) -> bool:
        return os.environ.get("TRANSAK_ENVIRONMENT", "STAGING").upper() == "PRODUCTION"

    def _api_base(self) -> str:
        return TRANSAK_API_PROD if self._is_production() else TRANSAK_API_STG

    def _gateway_base(self) -> str:
        return TRANSAK_GATEWAY_PROD if self._is_production() else TRANSAK_GATEWAY_STG

    async def _ensure_access_token(self) -> str:
        """Return a valid Transak Partner Access Token, refreshing if needed."""
        now = int(time.time())
        if self._access_token and self._access_token_expires_at - now > ACCESS_TOKEN_REFRESH_BUFFER_SECONDS:
            return self._access_token

        api_key = os.environ.get("TRANSAK_API_KEY", "").strip()
        api_secret = os.environ.get("TRANSAK_API_SECRET", "").strip()
        if not api_key or not api_secret:
            raise RuntimeError("TRANSAK_API_KEY / TRANSAK_API_SECRET not configured")

        url = f"{self._api_base()}/partners/api/v2/refresh-token"
        headers = {
            "accept": "application/json",
            "api-secret": api_secret,
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, headers=headers, json={"apiKey": api_key})
            if r.status_code >= 400:
                logger.error(f"Transak refresh-token failed ({r.status_code}): {r.text[:300]}")
                r.raise_for_status()
            payload = r.json()

        token = (payload.get("data") or {}).get("accessToken")
        expires_at = (payload.get("data") or {}).get("expiresAt", 0)
        if not token:
            raise RuntimeError(f"Transak refresh-token returned no accessToken: {payload}")
        self._access_token = token
        self._access_token_expires_at = int(expires_at)
        logger.info(
            f"Transak partner access token refreshed (expires {datetime.fromtimestamp(self._access_token_expires_at, tz=timezone.utc).isoformat()})"
        )
        return token

    async def create_widget_url(self, widget_params: dict) -> dict:
        """Create a session-bound widgetUrl for the Transak widget.

        widget_params is a dict of Transak query parameters. apiKey and
        referrerDomain are injected by the backend (frontend cannot override
        them — anti-tamper).
        """
        access_token = await self._ensure_access_token()
        api_key = os.environ.get("TRANSAK_API_KEY", "").strip()
        # The frontend already auto-detects window.location.host, but we still
        # accept it as a parameter so the backend has the authoritative value
        # of what we sent to Transak (for audit + diagnostics).
        referrer_domain = (widget_params.get("referrerDomain") or "").strip()
        if not referrer_domain:
            referrer_domain = os.environ.get("TRANSAK_REFERRER_DOMAIN", "").strip()
        if not referrer_domain:
            raise RuntimeError("referrerDomain is required (env TRANSAK_REFERRER_DOMAIN or request body)")

        # Enforce server-controlled values
        enforced = dict(widget_params)
        enforced["apiKey"] = api_key
        enforced["referrerDomain"] = referrer_domain

        # NENO-on-BSC canonicalisation. If the caller targeted NENO, ensure:
        #   - network is bsc (Transak's BSC identifier)
        #   - the BEP-20 contract address is passed so Transak can bind the
        #     custom asset (they need this when the code is not on their
        #     global allow-list yet)
        #   - default fiat is EUR (unless caller overrode)
        code = (enforced.get("cryptoCurrencyCode") or "").upper()
        if code == "NENO":
            enforced["network"] = "bsc"
            enforced.setdefault("cryptoCurrencyAddress", NENO_CONTRACT_ADDRESS)
            enforced.setdefault("defaultFiatCurrency", "EUR")
            enforced.setdefault("fiatCurrency", "EUR")

        # Prune None / empty values so we send a clean payload to Transak
        enforced = {k: v for k, v in enforced.items() if v is not None and v != ""}

        url = f"{self._gateway_base()}/api/v2/auth/session"
        headers = {
            "access-token": access_token,
            "content-type": "application/json",
            "accept": "application/json",
        }
        body = {"widgetParams": enforced}
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, headers=headers, json=body)
            if r.status_code >= 400:
                logger.error(
                    f"Transak create-widget-url failed ({r.status_code}): {r.text[:500]}"
                )
                # Bubble up Transak's error for the UI
                try:
                    err = r.json()
                except Exception:
                    err = {"raw": r.text}
                # KYB-not-approved is a known state while Transak compliance reviews
                # our account — surface it cleanly instead of generic 502.
                err_text = str(err).lower()
                kyb_pending = (
                    "kyb" in err_text and "approved" in err_text
                ) or (
                    # Production widget-gateway returns this opaque error when the
                    # /partners/api/v2/refresh-token succeeded (so the API key+secret
                    # ARE valid) but the account is not yet provisioned for widget
                    # session creation — i.e. KYB still on hold upstream.
                    r.status_code == 401 and (
                        "errorcode': 1002" in err_text
                        or "errorcode': 1014" in err_text
                        or '"errorcode":1002' in err_text
                        or '"errorcode":1014' in err_text
                    )
                )
                if kyb_pending:
                    raise RuntimeError(
                        "TRANSAK_KYB_PENDING: API credentials are valid but the "
                        "Transak account is not yet provisioned for widget session "
                        "creation (KYB on hold). Reply to Rahul Das / email "
                        "support@transak.com to lift the on-hold status."
                    )
                raise RuntimeError(
                    f"Transak rejected widget session (HTTP {r.status_code}): {err}"
                )
            payload = r.json()

        widget_url = (payload.get("data") or {}).get("widgetUrl")
        if not widget_url:
            raise RuntimeError(f"Transak returned no widgetUrl: {payload}")
        logger.info(
            f"Transak widget URL created for referrer={referrer_domain} "
            f"crypto={enforced.get('cryptoCurrencyCode')}/{enforced.get('network')}"
        )
        return {
            "widget_url": widget_url,
            "referrer_domain_sent": referrer_domain,
            "expires_in_seconds": 300,  # per docs
        }

    async def initialize(self):
        await self.events_collection.create_index("wallet_address")
        await self.events_collection.create_index("event_type")
        await self.events_collection.create_index("order_id")
        await self.events_collection.create_index("created_at")

    def get_public_config(self) -> dict:
        """Public, read-only Transak config for the frontend."""
        supports_neno = (
            os.environ.get("TRANSAK_SUPPORTS_NENO", "")
            .strip()
            .lower()
            in ("1", "true", "yes")
        ) or SUPPORTS_NENO_DEFAULT

        # Curated catalogue of tokens we want to surface as quick-pick in the UI.
        # Any of them can be passed as cryptoCurrencyCode + network to Transak.
        # NENO is included only when supports_neno is true (after Transak
        # whitelists the contract); otherwise the UI hides it.
        catalogue = [
            {"code": "USDC", "network": "bsc",       "label": "USDC · BSC"},
            {"code": "USDT", "network": "bsc",       "label": "USDT · BSC"},
            {"code": "BNB",  "network": "bsc",       "label": "BNB · BSC"},
            {"code": "ETH",  "network": "ethereum",  "label": "ETH · Ethereum"},
            {"code": "USDC", "network": "ethereum",  "label": "USDC · Ethereum"},
            {"code": "USDC", "network": "polygon",   "label": "USDC · Polygon"},
            {"code": "MATIC","network": "polygon",   "label": "MATIC · Polygon"},
            {"code": "BTC",  "network": "mainnet",   "label": "BTC · Bitcoin"},
        ]
        if supports_neno:
            catalogue.insert(
                0,
                {"code": "NENO", "network": "bsc", "label": "NENO · BSC (native)"},
            )

        return {
            "api_key": os.environ.get("TRANSAK_API_KEY", ""),
            "environment": os.environ.get("TRANSAK_ENVIRONMENT", "STAGING"),
            "referrer_domain": os.environ.get("TRANSAK_REFERRER_DOMAIN", ""),
            "network": "bsc",
            "fiat_currency": os.environ.get("TRANSAK_DEFAULT_FIAT", "EUR"),
            "neno_contract": NENO_CONTRACT_ADDRESS,
            "supports_neno": supports_neno,
            # Token the UI should use until Transak lists NENO on staging
            "fallback_token": os.environ.get("TRANSAK_FALLBACK_TOKEN", "USDC"),
            # Token catalogue surfaced as quick-pick buttons in the UI
            "catalogue": catalogue,
            # Compliance attestation surfaced in the UI for the walkthrough
            "non_custodial": True,
            "compliance": {
                "user_initiated_only": True,
                "no_fund_intermediation": True,
                "direct_delivery": True,
            },
        }

    async def record_event(
        self,
        wallet_address: str,
        event_type: str,
        payload: dict,
        user_id: Optional[str] = None,
    ) -> str:
        """Persist a Transak widget event forwarded by the frontend."""
        order_id = None
        if isinstance(payload, dict):
            # Common Transak event payload shapes
            data = payload.get("status") or payload.get("data") or {}
            if isinstance(data, dict):
                order_id = data.get("id") or data.get("orderId")

        doc = {
            "user_id": user_id,
            "wallet_address": (wallet_address or "").lower(),
            "event_type": event_type,
            "order_id": order_id,
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await self.events_collection.insert_one(doc)
        logger.info(
            f"Transak event recorded: {event_type} for wallet "
            f"{wallet_address[:10] if wallet_address else 'n/a'}... "
            f"(order: {order_id or 'n/a'})"
        )
        return str(result.inserted_id)

    async def list_events_for_wallet(self, wallet_address: str, limit: int = 50) -> list:
        cursor = (
            self.events_collection
            .find({"wallet_address": wallet_address.lower()}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)
