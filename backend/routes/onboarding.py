"""Public-facing customer onboarding routes.

Lets an authenticated regular USER submit their own KYC for review.
Requires JWT but NOT a CASP role — the user is acting on their own behalf.
The MLRO then approves/rejects via /api/casp/kyc/{id}/decision (CASP-gated).
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from middleware.auth import get_current_user

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

_casp = None


def set_services(casp) -> None:
    global _casp
    _casp = casp


class StartKycReq(BaseModel):
    full_name: str
    date_of_birth: str  # ISO date
    nationality: str   # ISO-3166 alpha-2
    country_of_residence: str
    wallet_address: Optional[str] = None
    document_type: str = "ID_CARD"  # PASSPORT | ID_CARD | DRIVER_LICENSE


class DocumentReq(BaseModel):
    doc_type: str  # ID_FRONT | ID_BACK | SELFIE | POA
    document_b64: str
    mime: str = "image/jpeg"


@router.get("/my-kyc")
async def my_kyc_status(user: dict = Depends(get_current_user)):
    """Returns the current KYC status for the calling user."""
    doc = await _casp.db.casp_kyc.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return doc or {"status": "NOT_STARTED"}


@router.post("/kyc/start")
async def start_my_kyc(body: StartKycReq, user: dict = Depends(get_current_user)):
    """Initiate KYC for the calling user (self-service)."""
    actor = {"user_id": user["user_id"], "email": user["email"], "role": user["role"]}
    result = await _casp.kyc_start(user["user_id"], user["email"], actor)
    # Persist the personal info the user provided
    await _casp.db.casp_kyc.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "full_name": body.full_name,
            "date_of_birth": body.date_of_birth,
            "nationality": body.nationality,
            "country_of_residence": body.country_of_residence,
            "document_type": body.document_type,
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    return result


@router.post("/kyc/document")
async def upload_my_document(body: DocumentReq, user: dict = Depends(get_current_user)):
    """Attach a document (ID front/back, selfie, proof-of-address) to the
    user's own KYC record. The user can only upload to their own record.
    """
    kyc = await _casp.db.casp_kyc.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not kyc:
        raise HTTPException(status_code=400, detail="Start KYC first via /onboarding/kyc/start")
    if body.doc_type not in ("ID_FRONT", "ID_BACK", "SELFIE", "POA"):
        raise HTTPException(status_code=400, detail="Invalid doc_type")
    if len(body.document_b64) > 8_000_000:  # ~6 MB after base64 overhead
        raise HTTPException(status_code=413, detail="Document too large (max ~6 MB)")
    actor = {"user_id": user["user_id"], "email": user["email"], "role": user["role"]}
    return await _casp.attach_kyc_document(kyc["id"], body.doc_type, body.document_b64, body.mime, actor)
