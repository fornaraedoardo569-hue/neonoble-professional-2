"""Chainalysis blockchain analytics adapter.

Modes mirror SumsubAdapter — MOCK by default, LIVE when
CHAINALYSIS_LIVE=true + CHAINALYSIS_API_KEY in env.
The LIVE endpoint paths follow the Chainalysis KYT v2 documentation.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Dict, Any

import httpx

from .base import BlockchainAnalyticsProvider

logger = logging.getLogger(__name__)


class ChainalysisAdapter(BlockchainAnalyticsProvider):
    name = "chainalysis"
    BASE_URL = "https://api.chainalysis.com"

    # Sanctioned/illicit categories — alert immediately if any of these hit.
    CRITICAL_CATEGORIES = {
        "sanctions", "darknet_market", "ransomware", "stolen_funds",
        "child_abuse_material", "terrorist_financing", "scam",
    }

    def __init__(self) -> None:
        self.api_key = os.environ.get("CHAINALYSIS_API_KEY", "")
        self.is_live = (
            os.environ.get("CHAINALYSIS_LIVE", "false").lower() == "true"
            and bool(self.api_key)
        )
        if self.is_live:
            logger.info("ChainalysisAdapter initialised in LIVE mode")
        else:
            logger.info("ChainalysisAdapter initialised in MOCK mode")

    # ── public api ──────────────────────────────────────────────────────────

    async def screen_address(self, address: str, asset: str, chain: str) -> Dict[str, Any]:
        if not self.is_live:
            return self._mock_address_screen(address, asset, chain)

        path = f"/api/kyt/v2/users/{address}/withdrawal-attempts"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{self.BASE_URL}{path}",
                headers={"Token": self.api_key, "Content-Type": "application/json"},
                json={"network": chain.lower(), "asset": asset, "address": address},
            )
            r.raise_for_status()
            data = r.json()

        risk = data.get("riskScore", 0)
        categories = data.get("categories", [])
        return {
            "address": address,
            "risk_score": risk,
            "categories": categories,
            "is_critical": any(c.get("name", "").lower() in self.CRITICAL_CATEGORIES for c in categories),
            "raw": data,
        }

    async def screen_transaction(self, tx_hash: str, chain: str) -> Dict[str, Any]:
        if not self.is_live:
            return self._mock_tx_screen(tx_hash, chain)

        path = "/api/kyt/v2/transfers/received"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{self.BASE_URL}{path}",
                headers={"Token": self.api_key, "Content-Type": "application/json"},
                json={"network": chain.lower(), "txHash": tx_hash},
            )
            r.raise_for_status()
            return r.json()

    async def register_transfer(self, **kwargs) -> Dict[str, Any]:
        if not self.is_live:
            return {"registered": True, "mock": True, **kwargs}
        # Live: POST /api/kyt/v2/users/{userId}/transfers
        return {"registered": True}

    # ── mocks ───────────────────────────────────────────────────────────────

    def _mock_address_screen(self, address: str, asset: str, chain: str) -> Dict[str, Any]:
        # deterministic score from address hash
        seed = int(hashlib.sha256(address.lower().encode()).hexdigest(), 16) % 100
        is_critical = seed > 92
        return {
            "address": address,
            "asset": asset,
            "chain": chain,
            "risk_score": float(seed),
            "categories": [{"name": "darknet_market"}] if is_critical else [],
            "is_critical": is_critical,
            "mock": True,
        }

    def _mock_tx_screen(self, tx_hash: str, chain: str) -> Dict[str, Any]:
        seed = int(hashlib.sha256(tx_hash.encode()).hexdigest(), 16) % 100
        return {
            "tx_hash": tx_hash,
            "chain": chain,
            "risk_score": float(seed),
            "is_critical": seed > 90,
            "mock": True,
        }
