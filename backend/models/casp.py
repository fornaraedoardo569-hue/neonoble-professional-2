"""CASP (Crypto-Asset Service Provider) data models.

These models cover the 7 operational blocks required by MiCAR
(Regulation EU 2023/1114) for an authorised CASP:
  1. Identity & Onboarding (KYC/KYB)
  2. Transaction Monitoring & AML
  3. Custody & Treasury
  4. Order Management & Execution
  5. Regulatory Reporting & Audit
  6. Customer Protection
  7. Internal Governance

Every collection lives under MongoDB to stay consistent with the rest of
the NeoNoble stack. Pydantic v2 ConfigDict(extra="ignore") makes it
forward-compatible with provider payloads we don't yet model explicitly.
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK 1 — Identity & Onboarding (KYC/KYB)
# ─────────────────────────────────────────────────────────────────────────────


class KycTier(str, Enum):
    TIER_0 = "TIER_0"      # No KYC — wallet only, no fiat
    TIER_1 = "TIER_1"      # Basic — email + phone (limits €1k/day)
    TIER_2 = "TIER_2"      # ID + selfie + liveness (limits €15k/day)
    TIER_3 = "TIER_3"      # Full + PoA + source of funds (no limit)


class KycStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ON_HOLD = "ON_HOLD"


class CustomerType(str, Enum):
    RETAIL = "RETAIL"
    PROFESSIONAL = "PROFESSIONAL"  # MiFID II elective professional
    INSTITUTIONAL = "INSTITUTIONAL"


class KycRecord(BaseModel):
    """KYC record per user. One row per user; updated as tiers progress."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: str
    customer_type: CustomerType = CustomerType.RETAIL
    tier: KycTier = KycTier.TIER_0
    status: KycStatus = KycStatus.NOT_STARTED
    provider: str = "sumsub"
    provider_applicant_id: Optional[str] = None
    provider_inspection_id: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO date
    nationality: Optional[str] = None    # ISO-3166-1 alpha-2
    country_of_residence: Optional[str] = None
    document_type: Optional[str] = None  # PASSPORT, ID_CARD, DRIVER_LICENSE
    document_number_masked: Optional[str] = None
    source_of_funds: Optional[str] = None
    occupation: Optional[str] = None
    pep_status: bool = False
    sanctions_match: bool = False
    rejection_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None    # admin user_id
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class KybRecord(BaseModel):
    """KYB record for institutional/business clients."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: str
    status: KycStatus = KycStatus.NOT_STARTED
    provider: str = "sumsub"
    provider_applicant_id: Optional[str] = None
    legal_name: str
    trade_name: Optional[str] = None
    legal_form: Optional[str] = None
    registration_number: Optional[str] = None
    lei: Optional[str] = None  # Legal Entity Identifier
    country_of_incorporation: Optional[str] = None
    registered_address: Optional[str] = None
    business_activity: Optional[str] = None
    nace_code: Optional[str] = None
    annual_revenue_eur: Optional[float] = None
    expected_monthly_volume_eur: Optional[float] = None
    ubo_list: List[Dict[str, Any]] = Field(default_factory=list)  # Ultimate Beneficial Owners
    directors: List[Dict[str, Any]] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class CustomerRiskRating(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    PROHIBITED = "PROHIBITED"


class RiskRatingRecord(BaseModel):
    """Customer risk rating per AMLD6 Art. 30."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: str
    rating: CustomerRiskRating = CustomerRiskRating.MEDIUM
    score: float = 50.0  # 0-100
    factors: Dict[str, Any] = Field(default_factory=dict)
    # e.g. {"geography": "MEDIUM", "product": "LOW", "channel": "MEDIUM", "customer": "LOW"}
    last_reviewed_at: datetime = Field(default_factory=_utc_now)
    next_review_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK 2 — Transaction Monitoring & AML
# ─────────────────────────────────────────────────────────────────────────────


class AmlAlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AmlAlertStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    ESCALATED = "ESCALATED"
    CLOSED_FALSE_POSITIVE = "CLOSED_FALSE_POSITIVE"
    CLOSED_TRUE_POSITIVE = "CLOSED_TRUE_POSITIVE"
    SAR_FILED = "SAR_FILED"


class AmlAlert(BaseModel):
    """AML alert generated by rule engine or blockchain analytics provider."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: Optional[str] = None
    transaction_id: Optional[str] = None
    rule_id: str
    rule_name: str
    severity: AmlAlertSeverity = AmlAlertSeverity.MEDIUM
    status: AmlAlertStatus = AmlAlertStatus.OPEN
    description: str
    amount_eur: Optional[float] = None
    source_address: Optional[str] = None
    destination_address: Optional[str] = None
    provider: str = "internal"  # internal | chainalysis | elliptic | trm
    provider_data: Dict[str, Any] = Field(default_factory=dict)
    risk_score: Optional[float] = None  # 0-100
    assigned_to: Optional[str] = None  # admin user_id
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class SanctionsHit(BaseModel):
    """Sanctions / PEP screening result."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: str
    list_name: str  # OFAC, EU, UN, UK_HMT, WORLD_CHECK
    match_type: str  # SANCTIONS | PEP | ADVERSE_MEDIA
    match_score: float  # 0-100
    matched_name: str
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = "OPEN"  # OPEN | CONFIRMED | DISMISSED
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utc_now)


class TravelRuleTransfer(BaseModel):
    """Travel Rule (FATF R.16) data exchanged with counterparty VASP."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    direction: str  # OUTGOING | INCOMING
    transaction_id: Optional[str] = None
    tx_hash: Optional[str] = None
    asset: str
    amount: float
    amount_eur: float
    originator_name: str
    originator_address: Optional[str] = None
    originator_wallet: str
    beneficiary_name: str
    beneficiary_wallet: str
    counterparty_vasp: Optional[str] = None
    counterparty_vasp_did: Optional[str] = None
    provider: str = "notabene"
    provider_transfer_id: Optional[str] = None
    status: str = "PENDING"  # PENDING | ACCEPTED | REJECTED | TIMEOUT
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class SarRecord(BaseModel):
    """Suspicious Activity Report (UIF Italia)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    sar_number: str  # internal sequential ref
    user_id: str
    related_alerts: List[str] = Field(default_factory=list)  # alert IDs
    narrative: str
    total_amount_eur: float
    status: str = "DRAFT"  # DRAFT | SUBMITTED | ACKNOWLEDGED
    filed_at: Optional[datetime] = None
    filed_by: Optional[str] = None
    uif_reference: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK 3 — Custody & Treasury
# ─────────────────────────────────────────────────────────────────────────────


class WalletKind(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class WalletPurpose(str, Enum):
    CUSTOMER_SEGREGATED = "CUSTOMER_SEGREGATED"
    OMNIBUS_OPERATIONAL = "OMNIBUS_OPERATIONAL"
    HOUSE_TREASURY = "HOUSE_TREASURY"
    SETTLEMENT = "SETTLEMENT"


class CustodialWallet(BaseModel):
    """Custodial wallet under CASP custody (MiCAR Art. 75)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: Optional[str] = None  # null for house/omnibus wallets
    kind: WalletKind = WalletKind.HOT
    purpose: WalletPurpose = WalletPurpose.CUSTOMER_SEGREGATED
    chain: str  # BSC | ETH | POLYGON | BTC
    address: str
    asset: str  # NENO | USDC | USDT | BNB | ETH | BTC | EUR
    provider: str = "fireblocks"
    provider_vault_id: Optional[str] = None
    provider_account_id: Optional[str] = None
    signing_policy: Dict[str, Any] = Field(default_factory=dict)
    # e.g. {"threshold": 3, "signers": ["sigA", "sigB", "sigC", "sigD"]}
    balance_native: float = 0.0
    balance_eur: float = 0.0
    last_reconciled_at: Optional[datetime] = None
    status: str = "ACTIVE"  # ACTIVE | FROZEN | ARCHIVED
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ReconciliationRun(BaseModel):
    """Daily reconciliation between on-chain and internal ledger."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    wallet_id: str
    asset: str
    onchain_balance: float
    internal_balance: float
    delta: float
    status: str = "MATCH"  # MATCH | MISMATCH | INVESTIGATION
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)


class ProofOfReserves(BaseModel):
    """Public Proof-of-Reserves snapshot."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    snapshot_date: datetime = Field(default_factory=_utc_now)
    total_liabilities_eur: float  # what we owe customers
    total_assets_eur: float       # what we hold on-chain
    coverage_ratio: float         # assets / liabilities >= 1.0
    merkle_root: str
    leaves_count: int             # number of customer accounts
    audit_firm: Optional[str] = None
    published_url: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK 4 — Order Management & Execution (B2B OTC Desk)
# ─────────────────────────────────────────────────────────────────────────────


class OtcSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OtcStatus(str, Enum):
    DRAFT = "DRAFT"
    QUOTED = "QUOTED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OtcQuoteB2B(BaseModel):
    """OTC quote for institutional (B2B) clients.
    Implements 4-eye principle for tx > €50k via `approval_required` flag.
    """
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    reference: str  # human-readable OTC-2026-000123
    client_user_id: str
    trader_id: Optional[str] = None  # OTC_TRADER who quoted
    approver_id: Optional[str] = None  # MLRO / RISK_OFFICER who approved
    side: OtcSide
    asset: str  # NENO | BTC | ETH | USDC ...
    quantity: float
    price_eur: float
    total_eur: float
    fee_eur: float = 0.0
    net_eur: float
    settlement_method: str = "SEPA"  # SEPA | SWIFT | ON_CHAIN
    settlement_account: Optional[str] = None
    settlement_wallet: Optional[str] = None
    status: OtcStatus = OtcStatus.DRAFT
    approval_required: bool = False
    expires_at: datetime
    executed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    best_execution_evidence: Dict[str, Any] = Field(default_factory=dict)
    # e.g. {"venues_checked": ["binance", "kraken"], "best_price": 10100, "mid_price": 10050}
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class RiskLimit(BaseModel):
    """Pre-trade risk limit per client / asset."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: Optional[str] = None  # null = global limit
    asset: Optional[str] = None
    max_single_order_eur: float
    max_daily_eur: float
    max_monthly_eur: float
    kill_switch_active: bool = False
    updated_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK 5 — Regulatory Reporting & Audit
# ─────────────────────────────────────────────────────────────────────────────


class AuditLogEntry(BaseModel):
    """Immutable WORM audit log entry (hash-chained)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    sequence: int  # monotonic counter
    actor_id: Optional[str] = None  # user_id or "system"
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    action: str  # KYC_APPROVED | OTC_QUOTED | WALLET_FROZEN | ...
    entity_type: str  # KycRecord | OtcQuoteB2B | CustodialWallet | ...
    entity_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    prev_hash: str = "0" * 64
    hash: str = ""  # SHA-256 of (sequence + actor_id + action + entity_id + payload + prev_hash)
    created_at: datetime = Field(default_factory=_utc_now)


class RegulatoryReport(BaseModel):
    """Periodic regulatory report (CONSOB, UIF, etc.)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    report_type: str  # MICAR_T_PLUS_1 | CONSOB_QUARTERLY | UIF_AML_STATS
    period_start: datetime
    period_end: datetime
    status: str = "DRAFT"  # DRAFT | GENERATED | SUBMITTED | ACKNOWLEDGED
    file_url: Optional[str] = None
    submission_reference: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)


class CapitalAdequacySnapshot(BaseModel):
    """Daily capital-adequacy snapshot per MiCAR Art. 67.
    Class 1 CASP: €50k. Class 2: €125k. Class 3: €150k.
    """
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    snapshot_date: datetime = Field(default_factory=_utc_now)
    casp_class: int = 2  # 1 | 2 | 3
    required_capital_eur: float = 125000.0
    own_funds_eur: float
    surplus_eur: float
    coverage_ratio: float  # own_funds / required
    status: str  # COMPLIANT | WARNING | BREACH
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK 6 — Customer Protection
# ─────────────────────────────────────────────────────────────────────────────


class ComplaintStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED_OMBUDSMAN = "ESCALATED_OMBUDSMAN"


class Complaint(BaseModel):
    """Customer complaint per MiCAR Art. 71 (15-day reply rule)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    reference: str
    user_id: str
    category: str  # ACCOUNT | TRANSACTION | KYC | FEES | OTHER
    subject: str
    description: str
    status: ComplaintStatus = ComplaintStatus.OPEN
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    sla_deadline: datetime  # +15 working days
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class AssetDisclosure(BaseModel):
    """Pre-contractual disclosure per MiCAR Art. 66 (whitepaper-equivalent)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    asset: str
    asset_chain: str
    contract_address: Optional[str] = None
    issuer: Optional[str] = None
    risk_level: str  # LOW | MEDIUM | HIGH | VERY_HIGH
    whitepaper_url: Optional[str] = None
    audit_url: Optional[str] = None
    disclosure_md: str  # markdown body
    version: str = "1.0"
    published_at: datetime = Field(default_factory=_utc_now)
    published_by: Optional[str] = None
    active: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK 7 — Internal Governance
# ─────────────────────────────────────────────────────────────────────────────


class CaspRole(str, Enum):
    """CASP-specific RBAC roles (used in addition to base UserRole)."""
    ADMIN = "ADMIN"
    MLRO = "MLRO"                                # Money Laundering Reporting Officer
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    RISK_OFFICER = "RISK_OFFICER"
    TREASURY_OFFICER = "TREASURY_OFFICER"
    OTC_TRADER = "OTC_TRADER"
    AUDITOR = "AUDITOR"                          # read-only access


class AdminUser(BaseModel):
    """Back-office user (operates the CASP stack)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: str  # FK to users collection
    email: EmailStr
    casp_roles: List[CaspRole] = Field(default_factory=list)
    department: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ApprovalWorkflow(BaseModel):
    """4-eye approval workflow for sensitive actions."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    action_type: str  # OTC_EXECUTE | WALLET_FREEZE | LIMIT_OVERRIDE | KYC_APPROVE
    entity_id: str
    requested_by: str
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    required_approvals: int = 2
    approvals: List[Dict[str, Any]] = Field(default_factory=list)
    # [{"approver_id": "u_1", "decision": "APPROVE", "at": "...", "notes": "..."}]
    status: str = "PENDING"  # PENDING | APPROVED | REJECTED | EXPIRED
    expires_at: datetime
    final_decision_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utc_now)


class IncidentSeverity(str, Enum):
    SEV1 = "SEV1"  # outage
    SEV2 = "SEV2"  # major degradation
    SEV3 = "SEV3"  # minor
    SEV4 = "SEV4"  # informational


class OperationalIncident(BaseModel):
    """Operational/security incident register (DORA-equivalent)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    reference: str
    title: str
    description: str
    severity: IncidentSeverity = IncidentSeverity.SEV3
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    impact: Optional[str] = None
    root_cause: Optional[str] = None
    remediation: Optional[str] = None
    reported_to_authority: bool = False
    authority_reference: Optional[str] = None
    status: str = "OPEN"  # OPEN | INVESTIGATING | MITIGATED | CLOSED
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ConflictOfInterest(BaseModel):
    """Conflicts-of-interest register per MiCAR Art. 72."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_uuid)
    party: str  # employee / counterparty / related entity
    nature: str  # personal-trading | related-party | gift | other
    description: str
    mitigation: str
    declared_at: datetime = Field(default_factory=_utc_now)
    declared_by: str
    review_due: Optional[datetime] = None
    active: bool = True
