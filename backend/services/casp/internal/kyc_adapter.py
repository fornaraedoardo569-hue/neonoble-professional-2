"""In-house KYC adapter — replaces Sumsub.

Implements the KycProvider interface using:
  * MongoDB for document storage (base64-encoded; should be moved to object
    storage in production for files > a few MB).
  * Internal sanctions/PEP screening against bundled lists
    (services/casp/internal/sanctions_data.py).
  * Manual review by MLRO/COMPLIANCE_OFFICER through the existing
    POST /api/casp/kyc/{id}/decision workflow.

Document verification logic intentionally kept conservative: the adapter
does not auto-approve — it returns PENDING and triggers screening only.
The MLRO is the source of truth.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Optional, Dict, Any

from ..base import KycProvider
from .sanctions_data import screen_name

logger = logging.getLogger(__name__)


class InternalKycAdapter(KycProvider):
    name = "internal"
    is_live = True  # Always "live" — there is no external dependency.

    def __init__(self, db=None) -> None:
        self.db = db
        logger.info("InternalKycAdapter initialised — fully autonomous, no third-party.")

    async def create_applicant(self, user_id: str, email: str, **kwargs) -> Dict[str, Any]:
        applicant_id = f"neo_{uuid.uuid4().hex[:12]}"
        # We can also pre-screen by name if provided.
        sanctions_hit = None
        full_name = kwargs.get("full_name")
        if full_name:
            sanctions_hit = screen_name(full_name)
        access_token = hashlib.sha256(f"{applicant_id}{user_id}".encode()).hexdigest()
        return {
            "provider_applicant_id": applicant_id,
            "access_token": access_token,
            "expires_in": 1800,
            "sanctions_pre_screen": sanctions_hit,
            "raw": {
                "id": applicant_id,
                "external_user_id": user_id,
                "internal": True,
            },
        }

    async def get_applicant_status(self, applicant_id: str) -> Dict[str, Any]:
        """Returns a status snapshot for the applicant from our DB.
        In an internal model, status is whatever the MLRO last set.
        """
        if self.db is None:
            return {"id": applicant_id, "reviewStatus": "pending", "internal": True}
        doc = await self.db.casp_kyc.find_one(
            {"provider_applicant_id": applicant_id}, {"_id": 0, "status": 1}
        )
        if not doc:
            return {"id": applicant_id, "reviewStatus": "unknown", "internal": True}
        return {
            "id": applicant_id,
            "reviewStatus": "completed" if doc["status"] in ("APPROVED", "REJECTED") else "pending",
            "reviewResult": {"reviewAnswer": "GREEN" if doc["status"] == "APPROVED" else "RED"},
            "internal": True,
        }

    async def verify_webhook(self, body: bytes, signature: str) -> bool:
        # Internal mode does not emit external webhooks.
        return True

    async def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"provider": self.name, **payload}

    # ── Internal-only helpers (not on the abstract interface) ────────────

    async def attach_document(self, applicant_id: str, doc_type: str,
                              document_b64: str, mime: str = "image/jpeg") -> Dict[str, Any]:
        """Persist a KYC document (ID, selfie, proof-of-address, ...)."""
        if self.db is None:
            raise RuntimeError("InternalKycAdapter requires a DB handle")
        doc = {
            "id": str(uuid.uuid4()),
            "provider_applicant_id": applicant_id,
            "doc_type": doc_type,  # ID_FRONT | ID_BACK | SELFIE | POA
            "mime": mime,
            "sha256": hashlib.sha256(document_b64.encode()).hexdigest(),
            "size_bytes": len(document_b64),
            "payload_b64": document_b64,  # in prod: move to object storage and store URL
        }
        await self.db.casp_kyc_documents.insert_one(doc)
        logger.info(f"InternalKyc: attached {doc_type} for {applicant_id} ({doc['size_bytes']} b)")
        # never return payload back
        return {k: v for k, v in doc.items() if k not in ("payload_b64", "_id")}

    async def list_documents(self, applicant_id: str) -> list:
        if self.db is None:
            return []
        cur = self.db.casp_kyc_documents.find(
            {"provider_applicant_id": applicant_id},
            {"_id": 0, "payload_b64": 0},
        )
        return await cur.to_list(length=20)
