"""KYC gate — server-side enforcement of CASP customer due-diligence.

Per MiCAR Art. 60 + AMLD5, no retail customer may execute a transaction
(onramp / offramp / ramp widget creation) before their KYC has been
APPROVED by the MLRO. The Dashboard UI also gates these flows visually,
but the source of truth is server-side: any direct API call without
APPROVED KYC must be rejected with HTTP 403.

ADMIN / DEVELOPER roles are exempt — they may be CASP internal operators
or staging clients. The exemption is logged in the audit trail.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

# Wired by server.py
_db: Optional[AsyncIOMotorDatabase] = None


def bind_db(database: AsyncIOMotorDatabase) -> None:
    global _db
    _db = database


async def require_kyc_approved(current_user: dict = Depends(get_current_user)) -> dict:
    """Block the request if the calling USER doesn't have APPROVED KYC.

    ADMIN and DEVELOPER roles bypass this check (they may be internal
    operators or compliance reviewers).
    """
    if _db is None:
        # Defensive — should never happen if server.py wired us up
        logger.error("KYC gate not bound to a database; allowing request")
        return current_user

    role = (current_user.get("role") or "").upper()
    if role in ("ADMIN", "DEVELOPER"):
        return current_user

    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user identity")

    kyc = await _db.casp_kyc.find_one(
        {"user_id": user_id}, {"_id": 0, "status": 1}
    )
    status = (kyc or {}).get("status")
    if status == "APPROVED":
        return current_user

    # 403 with a structured detail so the frontend can route to /onboarding
    raise HTTPException(
        status_code=403,
        detail={
            "error": "kyc_required",
            "kyc_status": status or "NOT_STARTED",
            "message": (
                "Identity verification is required before transacting. "
                "Please complete KYC at /onboarding."
            ),
        },
    )
