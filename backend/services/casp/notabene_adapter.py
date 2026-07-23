"""Notabene Travel Rule adapter.

Supports the FATF Recommendation 16 obligation introduced by MiCAR & TFR
(Regulation EU 2023/1113): every crypto transfer >€1.000 between two VASPs
must include originator + beneficiary information.

Modes:
  - MOCK (default): pretends to identify a counterparty VASP from a heuristic
    on the wallet address. Stores transfers in-memory.
  - LIVE: hits https://api.notabene.id with NOTABENE_API_KEY.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from typing import Optional, Dict, Any, List

import httpx

from .base import TravelRuleProvider

logger = logging.getLogger(__name__)


# Well-known VASP wallets for demo purposes — in MOCK mode we use these to
# simulate counterparty identification.
KNOWN_VASPS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": ("Binance", "did:notabene:binance"),
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8": ("Coinbase", "did:notabene:coinbase"),
    "0x564286362092d8e7936f0549571a803b203aaced": ("Kraken", "did:notabene:kraken"),
}


class NotabeneAdapter(TravelRuleProvider):
    name = "notabene"
    BASE_URL = "https://api.notabene.id"

    def __init__(self) -> None:
        self.api_key = os.environ.get("NOTABENE_API_KEY", "")
        self.client_id = os.environ.get("NOTABENE_CLIENT_ID", "")
        self.vasp_did = os.environ.get("NOTABENE_VASP_DID", "did:notabene:neonoble")
        self.is_live = (
            os.environ.get("NOTABENE_LIVE", "false").lower() == "true"
            and bool(self.api_key)
        )
        if self.is_live:
            logger.info("NotabeneAdapter initialised in LIVE mode")
        else:
            logger.info("NotabeneAdapter initialised in MOCK mode")

    # ── public api ──────────────────────────────────────────────────────────

    async def identify_vasp(self, wallet_address: str, chain: str) -> Optional[Dict[str, Any]]:
        if not self.is_live:
            known = KNOWN_VASPS.get(wallet_address.lower())
            if known:
                return {"name": known[0], "did": known[1], "verified": True, "mock": True}
            seed = int(hashlib.sha256(wallet_address.lower().encode()).hexdigest(), 16) % 100
            if seed > 70:
                return {"name": "Unknown VASP", "did": None, "verified": False, "mock": True}
            return None  # likely self-hosted wallet

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.BASE_URL}/v1/tr/identify",
                params={"address": wallet_address, "chain": chain},
                headers=self._headers(),
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    async def create_outgoing_transfer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_live:
            transfer_id = f"mock_tr_{uuid.uuid4().hex[:12]}"
            return {
                "transfer_id": transfer_id,
                "status": "ACCEPTED",
                "counterparty_vasp": payload.get("beneficiary_vasp"),
                "mock": True,
            }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.BASE_URL}/v1/tr/transfers",
                headers=self._headers(),
                json={**payload, "originator_vasp_did": self.vasp_did},
            )
            r.raise_for_status()
            return r.json()

    async def get_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        if not self.is_live:
            return {"transfer_id": transfer_id, "status": "ACCEPTED", "mock": True}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{self.BASE_URL}/v1/tr/transfers/{transfer_id}", headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def list_inbox(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_live:
            return []
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.BASE_URL}/v1/tr/inbox",
                params={"limit": limit},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json().get("data", [])

    # ── helpers ─────────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "x-client-id": self.client_id,
            "Content-Type": "application/json",
        }
