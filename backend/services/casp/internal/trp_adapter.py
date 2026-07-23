"""In-house Travel Rule (TRP) adapter — replaces Notabene.

Speaks IVMS-101 (interVASP Messaging Standard) which is an open spec
maintained by the IVMS101.org joint working group (Joint Working Group on
interVASP Messaging Standards — INATBA / IDA / GDF). No vendor lock-in.

Outbound flow:
  1. Look up the beneficiary VASP in our internal `casp_vasp_directory`
     collection by wallet address (heuristic) or by an explicit override.
  2. Build an IVMS-101 payload.
  3. Sign with our private key (HMAC-SHA256 over the payload + timestamp).
  4. POST to the counterparty's TRP endpoint (recorded in the directory).

Inbound flow:
  * Other CASPs POST to /api/casp/trp/inbox (mounted by the casp router).
  * We verify the HMAC signature using the shared secret stored in the
    directory for that VASP, persist the message, and queue it for our
    MLRO to ACK/REJECT in the AML & Alerts panel.

This is exactly how Notabene/Sumsub-TRP/Veriscope work under the hood —
the only thing they add is a closed network of pre-onboarded VASPs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Optional, Dict, Any, List

import httpx

from ..base import TravelRuleProvider

logger = logging.getLogger(__name__)


class InternalTrpAdapter(TravelRuleProvider):
    name = "internal"
    is_live = True

    def __init__(self, db=None) -> None:
        self.db = db
        self.our_vasp_did = os.environ.get("NEONOBLE_VASP_DID", "did:web:neonoble-ramp.com")
        self.our_signing_secret = os.environ.get(
            "NEONOBLE_TRP_SIGNING_SECRET",
            "dev-only-trp-secret-rotate-in-prod",
        )
        logger.info("InternalTrpAdapter initialised — IVMS-101 over HTTPS, no third-party.")

    # ── public api ──────────────────────────────────────────────────────────

    async def identify_vasp(self, wallet_address: str, chain: str) -> Optional[Dict[str, Any]]:
        """Look up the beneficiary VASP in our internal directory.
        Returns None for self-hosted (unhosted) wallets — those are NOT
        covered by Travel Rule under MiCA, only required to be screened.
        """
        if self.db is None:
            return None
        addr = (wallet_address or "").lower()
        # Direct lookup
        doc = await self.db.casp_vasp_directory.find_one(
            {"$or": [
                {"known_addresses": addr},
                {"address_patterns": {"$regex": addr[:6], "$options": "i"}},
            ]},
            {"_id": 0},
        )
        if doc:
            return {"name": doc["name"], "did": doc["did"], "verified": doc.get("verified", True)}
        return None

    async def create_outgoing_transfer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        transfer_id = f"trp_{uuid.uuid4().hex[:14]}"
        ivms = self._build_ivms101(transfer_id, payload)
        # Persist locally
        if self.db is not None:
            await self.db.casp_trp_outbox.insert_one({
                "id": transfer_id,
                "payload": ivms,
                "status": "SUBMITTED",
                "created_at": time.time(),
            })
        # Try to deliver if the counterparty has a TRP endpoint
        ts = str(int(time.time()))
        body = json.dumps(ivms, sort_keys=True)
        sig = hmac.new(self.our_signing_secret.encode(), f"{ts}{body}".encode(), hashlib.sha256).hexdigest()

        counterparty_did = payload.get("beneficiary_vasp")
        endpoint = await self._endpoint_for(counterparty_did)
        delivered = False
        delivery_error = None
        if endpoint:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.post(endpoint, content=body, headers={
                        "Content-Type": "application/json",
                        "X-TRP-Originator-DID": self.our_vasp_did,
                        "X-TRP-Timestamp": ts,
                        "X-TRP-Signature": sig,
                    })
                    delivered = 200 <= r.status_code < 300
                    if not delivered:
                        delivery_error = f"HTTP {r.status_code}"
            except Exception as e:
                delivery_error = str(e)
                logger.warning(f"TRP delivery failed to {endpoint}: {e}")

        return {
            "transfer_id": transfer_id,
            "status": "ACCEPTED" if delivered else "PENDING",
            "counterparty_vasp": counterparty_did,
            "delivered": delivered,
            "delivery_error": delivery_error,
            "provider": "internal",
        }

    async def get_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        if self.db is None:
            return {"transfer_id": transfer_id, "status": "UNKNOWN", "provider": "internal"}
        doc = await self.db.casp_trp_outbox.find_one({"id": transfer_id}, {"_id": 0, "status": 1})
        return {"transfer_id": transfer_id, "status": doc["status"] if doc else "UNKNOWN", "provider": "internal"}

    async def list_inbox(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self.db is None:
            return []
        cur = self.db.casp_trp_inbox.find({}, {"_id": 0}).sort("received_at", -1).limit(limit)
        return await cur.to_list(length=limit)

    # ── internal-only helpers ───────────────────────────────────────────────

    async def _endpoint_for(self, did: Optional[str]) -> Optional[str]:
        if not did or self.db is None:
            return None
        doc = await self.db.casp_vasp_directory.find_one({"did": did}, {"_id": 0, "trp_endpoint": 1})
        return (doc or {}).get("trp_endpoint")

    def _build_ivms101(self, transfer_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Minimal IVMS-101 v1.0.1 payload."""
        return {
            "ivms101": "1.0.1",
            "transfer_id": transfer_id,
            "originator_vasp": {"did": self.our_vasp_did},
            "beneficiary_vasp": {"did": payload.get("beneficiary_vasp")},
            "originator": {
                "name": payload.get("originator", {}).get("name"),
                "address": payload.get("originator", {}).get("address"),
                "wallet_address": payload.get("originator", {}).get("wallet"),
                "national_identifier": payload.get("originator", {}).get("national_identifier"),
            },
            "beneficiary": {
                "name": payload.get("beneficiary", {}).get("name"),
                "wallet_address": payload.get("beneficiary", {}).get("wallet"),
            },
            "transfer": {
                "asset": payload.get("asset"),
                "amount": payload.get("amount"),
                "amount_eur": payload.get("amount_eur"),
                "chain": payload.get("chain"),
                "timestamp": int(time.time()),
            },
        }

    def verify_inbound_signature(self, body: bytes, ts: str, sig: str, peer_secret: str) -> bool:
        expected = hmac.new(peer_secret.encode(), f"{ts}{body.decode()}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
