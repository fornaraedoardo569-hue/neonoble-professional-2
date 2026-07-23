"""CASP admin routes — REST API consumed by the /admin frontend console.

Grouping convention:
  /api/casp/dashboard           -> KPI summary
  /api/casp/kyc, /kyb, /risk    -> Block 1
  /api/casp/aml, /travel-rule, /sar -> Block 2
  /api/casp/wallets, /reconciliation, /por -> Block 3
  /api/casp/otc                 -> Block 4
  /api/casp/reports, /capital   -> Block 5
  /api/casp/complaints, /disclosures -> Block 6
  /api/casp/governance          -> Block 7
  /api/casp/audit               -> WORM log
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
import json

from middleware.casp_rbac import (
    require_any_admin, require_compliance, require_mlro,
    require_risk, require_treasury, require_otc_trader, require_otc_approver,
)
from services.casp_service import CaspService
from services.audit_log_service import AuditLogService

router = APIRouter(prefix="/casp", tags=["CASP"])

# Service handles wired by server.py
_casp: Optional[CaspService] = None
_audit: Optional[AuditLogService] = None


def set_services(casp: CaspService, audit: AuditLogService) -> None:
    global _casp, _audit
    _casp = casp
    _audit = audit


# ── Dashboard ───────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(actor: dict = Depends(require_any_admin)) -> Dict[str, Any]:
    return await _casp.kpi_summary()


# ── BLOCK 1: KYC / KYB / Risk / Sanctions ───────────────────────────────────

class KycStartReq(BaseModel):
    user_id: str
    email: EmailStr


@router.post("/kyc/start")
async def kyc_start(body: KycStartReq, actor: dict = Depends(require_compliance)):
    return await _casp.kyc_start(body.user_id, body.email, actor)


class KycDecisionReq(BaseModel):
    decision: str  # APPROVE | REJECT | HOLD
    reason: Optional[str] = None


@router.post("/kyc/{kyc_id}/decision")
async def kyc_decision(kyc_id: str, body: KycDecisionReq, actor: dict = Depends(require_compliance)):
    if body.decision not in ("APPROVE", "REJECT", "HOLD"):
        raise HTTPException(status_code=400, detail="Invalid decision")
    return await _casp.kyc_decision(kyc_id, body.decision, body.reason, actor)


@router.get("/kyc")
async def kyc_list(status: Optional[str] = None, limit: int = 100,
                   actor: dict = Depends(require_compliance)):
    return await _casp.kyc_list(status, limit)


@router.get("/kyb")
async def kyb_list(status: Optional[str] = None, limit: int = 100,
                   actor: dict = Depends(require_compliance)):
    return await _casp.kyb_list(status, limit)


class RiskRatingReq(BaseModel):
    user_id: str
    rating: str  # LOW | MEDIUM | HIGH | PROHIBITED
    score: float = Field(ge=0, le=100)
    factors: Dict[str, Any] = Field(default_factory=dict)


@router.post("/risk-rating")
async def upsert_risk_rating(body: RiskRatingReq, actor: dict = Depends(require_risk)):
    return await _casp.upsert_risk_rating(body.user_id, body.rating, body.score, body.factors, actor)


@router.get("/risk-rating")
async def list_risk_ratings(limit: int = 100, actor: dict = Depends(require_risk)):
    return await _casp.list_risk_ratings(limit)


@router.get("/sanctions")
async def list_sanctions(status: Optional[str] = None, limit: int = 100,
                         actor: dict = Depends(require_compliance)):
    return await _casp.list_sanctions_hits(status, limit)


# ── BLOCK 2: AML / Travel Rule / SAR ────────────────────────────────────────

class ScreenAddressReq(BaseModel):
    address: str
    asset: str
    chain: str


@router.post("/aml/screen-address")
async def screen_address(body: ScreenAddressReq, actor: dict = Depends(require_compliance)):
    return await _casp.evaluate_address(body.address, body.asset, body.chain, actor)


@router.get("/aml/alerts")
async def list_aml_alerts(status: Optional[str] = None, severity: Optional[str] = None,
                          limit: int = 100, actor: dict = Depends(require_compliance)):
    return await _casp.list_aml_alerts(status, severity, limit)


class ResolveAlertReq(BaseModel):
    status: str  # CLOSED_FALSE_POSITIVE | CLOSED_TRUE_POSITIVE | ESCALATED
    notes: Optional[str] = None


@router.post("/aml/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, body: ResolveAlertReq, actor: dict = Depends(require_mlro)):
    return await _casp.resolve_aml_alert(alert_id, body.status, body.notes, actor)


class TravelRuleReq(BaseModel):
    transaction_id: Optional[str] = None
    asset: str
    amount: float
    amount_eur: float
    originator_name: str
    originator_wallet: str
    beneficiary_name: str
    beneficiary_wallet: str
    chain: str


@router.post("/travel-rule")
async def create_travel_rule(body: TravelRuleReq, actor: dict = Depends(require_compliance)):
    return await _casp.create_travel_rule_transfer(
        transaction_id=body.transaction_id, asset=body.asset, amount=body.amount,
        amount_eur=body.amount_eur, originator_name=body.originator_name,
        originator_wallet=body.originator_wallet, beneficiary_name=body.beneficiary_name,
        beneficiary_wallet=body.beneficiary_wallet, chain=body.chain, actor=actor,
    )


@router.get("/travel-rule")
async def list_travel_rule(direction: Optional[str] = None, limit: int = 100,
                          actor: dict = Depends(require_compliance)):
    return await _casp.list_travel_rule(direction, limit)


class SarDraftReq(BaseModel):
    user_id: str
    alert_ids: List[str]
    narrative: str
    total_amount_eur: float


@router.post("/sar")
async def draft_sar(body: SarDraftReq, actor: dict = Depends(require_mlro)):
    return await _casp.draft_sar(body.user_id, body.alert_ids, body.narrative,
                                 body.total_amount_eur, actor)


@router.get("/sar")
async def list_sars(limit: int = 100, actor: dict = Depends(require_mlro)):
    return await _casp.list_sars(limit)


# ── BLOCK 3: Custody / Reconciliation / PoR ─────────────────────────────────

class ProvisionWalletReq(BaseModel):
    user_id: str
    asset: str
    chain: str


@router.post("/wallets/provision")
async def provision_wallet(body: ProvisionWalletReq, actor: dict = Depends(require_treasury)):
    return await _casp.provision_segregated_wallet(body.user_id, body.asset, body.chain, actor)


@router.get("/wallets")
async def list_wallets(kind: Optional[str] = None, purpose: Optional[str] = None,
                      limit: int = 200, actor: dict = Depends(require_treasury)):
    return await _casp.list_wallets(kind, purpose, limit)


@router.post("/wallets/{wallet_id}/freeze")
async def freeze_wallet(wallet_id: str, actor: dict = Depends(require_treasury)):
    return await _casp.freeze_wallet(wallet_id, actor)


@router.post("/wallets/{wallet_id}/reconcile")
async def reconcile(wallet_id: str, actor: dict = Depends(require_treasury)):
    return await _casp.run_reconciliation(wallet_id, actor)


@router.get("/proof-of-reserves")
async def latest_por(actor: dict = Depends(require_any_admin)):
    return await _casp.latest_proof_of_reserves()


@router.post("/proof-of-reserves/generate")
async def generate_por(actor: dict = Depends(require_treasury)):
    return await _casp.generate_proof_of_reserves(actor)


# ── BLOCK 4: B2B OTC desk ───────────────────────────────────────────────────

class OtcQuoteReq(BaseModel):
    client_user_id: str
    side: str  # BUY | SELL
    asset: str
    quantity: float
    price_eur: float
    fee_bps: int = 25
    settlement_method: str = "SEPA"
    settlement_account: Optional[str] = None
    settlement_wallet: Optional[str] = None


@router.post("/otc/quote")
async def create_otc(body: OtcQuoteReq, actor: dict = Depends(require_otc_trader)):
    if body.side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")
    return await _casp.create_otc_quote(
        client_user_id=body.client_user_id, side=body.side, asset=body.asset,
        quantity=body.quantity, price_eur=body.price_eur, fee_bps=body.fee_bps,
        settlement_method=body.settlement_method,
        settlement_account=body.settlement_account,
        settlement_wallet=body.settlement_wallet,
        actor=actor,
    )


class OtcApproveReq(BaseModel):
    decision: str  # APPROVE | REJECT
    notes: Optional[str] = None


@router.post("/otc/{quote_id}/approve")
async def approve_otc(quote_id: str, body: OtcApproveReq, actor: dict = Depends(require_otc_approver)):
    result = await _casp.approve_otc(quote_id, body.decision, body.notes, actor)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/otc/{quote_id}/execute")
async def execute_otc(quote_id: str, actor: dict = Depends(require_otc_trader)):
    result = await _casp.execute_otc(quote_id, actor)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/otc")
async def list_otc(status: Optional[str] = None, limit: int = 100,
                  actor: dict = Depends(require_any_admin)):
    return await _casp.list_otc(status, limit)


# ── BLOCK 5: Reporting & Capital ────────────────────────────────────────────

class ReportReq(BaseModel):
    period_start: datetime
    period_end: datetime


@router.post("/reports/micar")
async def generate_micar(body: ReportReq, actor: dict = Depends(require_compliance)):
    return await _casp.generate_micar_report(body.period_start, body.period_end, actor)


@router.get("/reports")
async def list_reports(limit: int = 100, actor: dict = Depends(require_any_admin)):
    return await _casp.list_regulatory_reports(limit)


class CapitalReq(BaseModel):
    own_funds_eur: float
    casp_class: int = 2
    notes: Optional[str] = None


@router.post("/capital")
async def upsert_capital(body: CapitalReq, actor: dict = Depends(require_treasury)):
    return await _casp.upsert_capital_snapshot(body.own_funds_eur, body.casp_class, body.notes, actor)


# ── BLOCK 6: Complaints & disclosures ───────────────────────────────────────

class ComplaintReq(BaseModel):
    user_id: str
    category: str
    subject: str
    description: str


@router.post("/complaints")
async def create_complaint(body: ComplaintReq, actor: dict = Depends(require_compliance)):
    return await _casp.create_complaint(body.user_id, body.category, body.subject, body.description, actor)


@router.get("/complaints")
async def list_complaints(status: Optional[str] = None, limit: int = 100,
                         actor: dict = Depends(require_compliance)):
    return await _casp.list_complaints(status, limit)


@router.get("/disclosures")
async def list_disclosures(actor: dict = Depends(require_any_admin)):
    return await _casp.list_disclosures()


# ── BLOCK 7: Governance ─────────────────────────────────────────────────────

class AdminUserReq(BaseModel):
    user_id: str
    email: EmailStr
    casp_roles: List[str]
    department: Optional[str] = None


@router.post("/governance/admins")
async def add_admin(body: AdminUserReq, actor: dict = Depends(require_any_admin)):
    # Only super-admins can create admin users
    if actor.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can manage admin users")
    return await _casp.ensure_admin_user(body.user_id, body.email, body.casp_roles, body.department)


@router.get("/governance/admins")
async def list_admins(actor: dict = Depends(require_any_admin)):
    return await _casp.list_admin_users()


@router.get("/governance/incidents")
async def list_incidents(status: Optional[str] = None, limit: int = 100,
                        actor: dict = Depends(require_risk)):
    return await _casp.list_incidents(status, limit)


@router.get("/governance/conflicts")
async def list_conflicts(actor: dict = Depends(require_any_admin)):
    return await _casp.list_conflicts()


# ── Audit log ──────────────────────────────────────────────────────────────

@router.get("/audit")
async def list_audit(limit: int = Query(100, le=500), skip: int = 0,
                     entity_id: Optional[str] = None,
                     actor: dict = Depends(require_any_admin)):
    return await _audit.list(limit=limit, skip=skip, entity_id=entity_id)


@router.get("/audit/verify")
async def verify_audit(limit: int = Query(1000, le=10000),
                       actor: dict = Depends(require_any_admin)):
    return await _audit.verify_chain(limit=limit)


# ── Autonomous operations (KYC docs, TRP inbox, VASP directory, sanctions) ──

class KycDocReq(BaseModel):
    doc_type: str  # ID_FRONT | ID_BACK | SELFIE | POA
    document_b64: str
    mime: str = "image/jpeg"


@router.post("/kyc/{kyc_id}/documents")
async def upload_kyc_document(kyc_id: str, body: KycDocReq,
                              actor: dict = Depends(require_compliance)):
    result = await _casp.attach_kyc_document(kyc_id, body.doc_type, body.document_b64,
                                              body.mime, actor)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/kyc/{kyc_id}/documents")
async def list_kyc_documents(kyc_id: str, actor: dict = Depends(require_compliance)):
    return await _casp.list_kyc_documents(kyc_id)


@router.get("/sanctions/status")
async def sanctions_status(actor: dict = Depends(require_compliance)):
    return await _casp.sanctions_status()


@router.post("/sanctions/refresh")
async def sanctions_refresh(actor: dict = Depends(require_compliance)):
    return await _casp.sanctions_record_refresh(actor)


@router.get("/trp/inbox")
async def list_trp_inbox(limit: int = 100, actor: dict = Depends(require_compliance)):
    return await _casp.list_trp_inbox(limit)


class TrpInboundReq(BaseModel):
    payload: Dict[str, Any]


from fastapi import Request


@router.post("/trp/inbox")
async def trp_inbound(request: Request):
    """Inbound Travel Rule endpoint — accepts signed IVMS-101 messages from
    peer CASPs. No JWT auth (peers don't have our auth tokens); we verify
    via HMAC using the shared secret from `casp_vasp_directory`.
    """
    body = await request.body()
    peer_did = request.headers.get("X-TRP-Originator-DID") or ""
    ts = request.headers.get("X-TRP-Timestamp") or ""
    sig = request.headers.get("X-TRP-Signature") or ""

    # Look up peer
    verified = False
    if peer_did:
        peer = await _casp.db.casp_vasp_directory.find_one(
            {"did": peer_did}, {"_id": 0, "shared_secret": 1}
        )
        if peer and peer.get("shared_secret"):
            verified = _casp.notabene.verify_inbound_signature(  # type: ignore[attr-defined]
                body, ts, sig, peer["shared_secret"]
            ) if hasattr(_casp.notabene, "verify_inbound_signature") else False

    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")
    entry = await _casp.ingest_trp_inbound(payload, peer_did or "unknown", verified)
    return {"status": "received", "id": entry["id"], "verified": verified}


@router.get("/trp/vasps")
async def list_vasps(actor: dict = Depends(require_compliance)):
    return await _casp.list_vasps()


class VaspReq(BaseModel):
    did: str
    name: str
    trp_endpoint: str
    known_addresses: List[str] = Field(default_factory=list)
    shared_secret: str


@router.post("/trp/vasps")
async def upsert_vasp(body: VaspReq, actor: dict = Depends(require_compliance)):
    return await _casp.upsert_vasp(
        body.did, body.name, body.trp_endpoint,
        body.known_addresses, body.shared_secret, actor,
    )


@router.delete("/trp/vasps/{did:path}")
async def delete_vasp(did: str, actor: dict = Depends(require_compliance)):
    result = await _casp.delete_vasp(did, actor)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result)
    return result


class TrpDecisionReq(BaseModel):
    decision: str  # ACCEPT | REJECT
    notes: Optional[str] = None


@router.post("/trp/inbox/{trp_id}/decision")
async def trp_decision(trp_id: str, body: TrpDecisionReq,
                       actor: dict = Depends(require_compliance)):
    if body.decision not in ("ACCEPT", "REJECT"):
        raise HTTPException(status_code=400, detail="decision must be ACCEPT or REJECT")
    result = await _casp.decide_trp_inbound(trp_id, body.decision, body.notes, actor)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result)
    return result


# ── Real-mode Setup Wizard ─────────────────────────────────────────────────


@router.get("/setup/status")
async def setup_status(actor: dict = Depends(require_any_admin)):
    return await _casp.live_mode_status()


class LegalEntityReq(BaseModel):
    legal_name: str
    license_number: str
    license_authority: str  # e.g. "CONSOB" or "Banca d'Italia"
    license_valid_until: str  # ISO date
    registered_address: str
    vat_number: Optional[str] = None
    lei: Optional[str] = None
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    mlro_name: Optional[str] = None


@router.post("/setup/legal-entity")
async def setup_legal_entity(body: LegalEntityReq, actor: dict = Depends(require_any_admin)):
    if actor.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only super-admin can register legal entity")
    return await _casp.save_legal_entity(body.model_dump(), actor)


@router.post("/setup/mark-demo-wiped")
async def setup_mark_wiped(actor: dict = Depends(require_any_admin)):
    if actor.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only super-admin can mark demo wiped")
    await _casp.mark_demo_wiped(actor)
    return {"ok": True}
