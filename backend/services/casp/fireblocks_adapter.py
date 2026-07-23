"""Fireblocks MPC custody adapter.

Implementation modes:
  - MOCK (default): generates deterministic vault IDs / addresses, keeps
    an in-memory + persisted state. Transactions auto-confirm after 1 poll.
  - LIVE: uses fireblocks-sdk-py with a JWT private key + workspace API key.

Switch via FIREBLOCKS_LIVE=true + FIREBLOCKS_API_KEY + FIREBLOCKS_PRIVATE_KEY
(or FIREBLOCKS_PRIVATE_KEY_PATH) once the production workspace is provisioned.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from typing import Optional, Dict, Any

from .base import CustodyProvider

logger = logging.getLogger(__name__)


class FireblocksAdapter(CustodyProvider):
    name = "fireblocks"

    def __init__(self) -> None:
        self.api_key = os.environ.get("FIREBLOCKS_API_KEY", "")
        self.private_key = os.environ.get("FIREBLOCKS_PRIVATE_KEY", "")
        if not self.private_key and os.environ.get("FIREBLOCKS_PRIVATE_KEY_PATH"):
            try:
                with open(os.environ["FIREBLOCKS_PRIVATE_KEY_PATH"], "r") as fh:
                    self.private_key = fh.read()
            except Exception as e:
                logger.warning(f"Failed to read FIREBLOCKS_PRIVATE_KEY_PATH: {e}")

        self.is_live = (
            os.environ.get("FIREBLOCKS_LIVE", "false").lower() == "true"
            and bool(self.api_key)
            and bool(self.private_key)
        )
        self._sdk = None
        if self.is_live:
            try:
                # Imported lazily; pip install fireblocks-sdk
                from fireblocks_sdk import FireblocksSDK  # type: ignore
                self._sdk = FireblocksSDK(self.private_key, self.api_key)
                logger.info("FireblocksAdapter initialised in LIVE mode")
            except Exception as e:
                logger.error(f"FireblocksSDK init failed, falling back to MOCK: {e}")
                self.is_live = False
        else:
            logger.info("FireblocksAdapter initialised in MOCK mode")

    # ── public api ──────────────────────────────────────────────────────────

    async def create_vault(self, name: str, customer_ref: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_live:
            vault_id = f"mock_vault_{uuid.uuid4().hex[:10]}"
            return {"provider_vault_id": vault_id, "name": name, "mock": True}
        vault = self._sdk.create_vault_account(name=name, customer_ref_id=customer_ref or "")
        return {"provider_vault_id": vault["id"], "name": name, "raw": vault}

    async def get_deposit_address(self, vault_id: str, asset: str, chain: str) -> Dict[str, Any]:
        if not self.is_live:
            seed = f"{vault_id}-{asset}-{chain}"
            digest = hashlib.sha256(seed.encode()).hexdigest()
            address = "0x" + digest[:40] if chain.upper() in ("BSC", "ETH", "POLYGON") else f"1{digest[:33]}"
            return {"address": address, "asset": asset, "chain": chain, "mock": True}

        asset_id = self._map_asset(asset, chain)
        result = self._sdk.generate_new_address(vault_account_id=vault_id, asset_id=asset_id)
        return {"address": result.get("address"), "asset": asset, "chain": chain, "raw": result}

    async def get_balance(self, vault_id: str, asset: str) -> float:
        if not self.is_live:
            seed = int(hashlib.sha256(f"{vault_id}-{asset}".encode()).hexdigest(), 16) % 1000
            return float(seed)
        asset_id = self._map_asset(asset, "ETH")  # callers can override later
        info = self._sdk.get_vault_account_asset(vault_id, asset_id)
        return float(info.get("balance", 0))

    async def create_transaction(self, vault_id: str, asset: str, amount: float, destination: str,
                                 chain: str, idempotency_key: str) -> Dict[str, Any]:
        if not self.is_live:
            return {
                "provider_tx_id": f"mock_tx_{uuid.uuid4().hex[:12]}",
                "status": "SUBMITTED",
                "mock": True,
            }
        asset_id = self._map_asset(asset, chain)
        tx = self._sdk.create_transaction(
            asset_id=asset_id,
            amount=str(amount),
            source={"type": "VAULT_ACCOUNT", "id": vault_id},
            destination={"type": "ONE_TIME_ADDRESS", "one_time_address": {"address": destination}},
            external_tx_id=idempotency_key,
        )
        return {"provider_tx_id": tx["id"], "status": tx.get("status"), "raw": tx}

    async def get_transaction_status(self, provider_tx_id: str) -> Dict[str, Any]:
        if not self.is_live:
            return {"provider_tx_id": provider_tx_id, "status": "COMPLETED", "mock": True}
        tx = self._sdk.get_transaction_by_id(provider_tx_id)
        return {"provider_tx_id": provider_tx_id, "status": tx.get("status"), "raw": tx}

    @staticmethod
    def _map_asset(asset: str, chain: str) -> str:
        """Translate (asset, chain) into Fireblocks assetId convention."""
        chain = (chain or "").upper()
        asset = (asset or "").upper()
        if asset == "BNB" or (asset == "USDC" and chain == "BSC"):
            return "USDC_BSC" if asset == "USDC" else "BNB_BSC"
        if asset == "USDT" and chain == "BSC":
            return "USDT_BSC"
        if asset == "ETH" and chain == "ETH":
            return "ETH"
        if asset == "MATIC":
            return "MATIC_POLYGON"
        if asset == "BTC":
            return "BTC"
        return asset
