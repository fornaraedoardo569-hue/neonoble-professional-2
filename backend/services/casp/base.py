"""Abstract base interfaces for CASP provider adapters.

Every provider (Sumsub, Chainalysis, Fireblocks, Notabene) must implement
the corresponding interface. The orchestrator (CaspService) consumes only
the interface so we can A/B providers or run in mock mode transparently.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class KycProvider(ABC):
    """Sumsub / Onfido style identity verification provider."""

    name: str = "abstract"
    is_live: bool = False

    @abstractmethod
    async def create_applicant(self, user_id: str, email: str, **kwargs) -> Dict[str, Any]:
        """Create a remote applicant. Returns provider_applicant_id + access_token."""

    @abstractmethod
    async def get_applicant_status(self, applicant_id: str) -> Dict[str, Any]:
        """Poll the current verification status."""

    @abstractmethod
    async def verify_webhook(self, body: bytes, signature: str) -> bool:
        """Verify provider webhook HMAC signature."""

    @abstractmethod
    async def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise webhook into a provider-agnostic event."""


class BlockchainAnalyticsProvider(ABC):
    """Chainalysis / Elliptic / TRM style wallet screening provider."""

    name: str = "abstract"
    is_live: bool = False

    @abstractmethod
    async def screen_address(self, address: str, asset: str, chain: str) -> Dict[str, Any]:
        """Returns risk score + categories for a wallet address."""

    @abstractmethod
    async def screen_transaction(self, tx_hash: str, chain: str) -> Dict[str, Any]:
        """Returns KYT classification for a specific tx."""

    @abstractmethod
    async def register_transfer(self, **kwargs) -> Dict[str, Any]:
        """Register an outgoing transfer for monitoring."""


class CustodyProvider(ABC):
    """Fireblocks / Copper / BitGo style MPC custody provider."""

    name: str = "abstract"
    is_live: bool = False

    @abstractmethod
    async def create_vault(self, name: str, customer_ref: Optional[str] = None) -> Dict[str, Any]:
        """Create a segregated vault (per MiCAR Art. 75)."""

    @abstractmethod
    async def get_deposit_address(self, vault_id: str, asset: str, chain: str) -> Dict[str, Any]:
        """Generate a deposit address inside an existing vault."""

    @abstractmethod
    async def get_balance(self, vault_id: str, asset: str) -> float:
        """Return current balance (native units)."""

    @abstractmethod
    async def create_transaction(self, vault_id: str, asset: str, amount: float, destination: str,
                                 chain: str, idempotency_key: str) -> Dict[str, Any]:
        """Initiate a custody-side transaction (requires multi-sig approval)."""

    @abstractmethod
    async def get_transaction_status(self, provider_tx_id: str) -> Dict[str, Any]:
        """Poll status of a custody-side transaction."""


class TravelRuleProvider(ABC):
    """Notabene / Sumsub TRP / Veriscope style Travel Rule provider."""

    name: str = "abstract"
    is_live: bool = False

    @abstractmethod
    async def identify_vasp(self, wallet_address: str, chain: str) -> Optional[Dict[str, Any]]:
        """Heuristic + KYV: identify if a wallet belongs to a known VASP."""

    @abstractmethod
    async def create_outgoing_transfer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit outgoing Travel Rule data to counterparty VASP."""

    @abstractmethod
    async def get_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        """Poll Travel Rule transfer status."""

    @abstractmethod
    async def list_inbox(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Inbound Travel Rule transfers awaiting our acknowledgement."""
