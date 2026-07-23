"""Seed the CASP back-office with realistic demo data.

Idempotent: re-running is safe (uses upserts where appropriate).

Usage:
    cd /app/backend && python scripts/seed_casp.py
"""

import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from motor.motor_asyncio import AsyncIOMotorClient

from models.casp import (
    KycRecord, KybRecord, RiskRatingRecord, CustomerRiskRating,
    AmlAlert, AmlAlertSeverity, SanctionsHit,
    CustodialWallet, WalletKind, WalletPurpose,
    OtcQuoteB2B, OtcSide, OtcStatus,
    Complaint, ComplaintStatus, AssetDisclosure,
    OperationalIncident, IncidentSeverity, ConflictOfInterest,
    CapitalAdequacySnapshot,
)
from services.audit_log_service import AuditLogService
from services.casp_service import CaspService
from services.auth_service import AuthService
from models.user import UserCreate, UserRole


SEED_ADMIN_EMAIL = os.environ.get("CASP_SEED_ADMIN_EMAIL", "casp-admin@neonoble.example.com")
SEED_ADMIN_PASSWORD = os.environ.get("CASP_SEED_ADMIN_PASSWORD", "CaspAdmin!2026")
SEED_MLRO_EMAIL = "casp-mlro@neonoble.example.com"
SEED_TRADER_EMAIL = "casp-trader@neonoble.example.com"
DEFAULT_PASS = "CaspAdmin!2026"


async def ensure_admin_account(auth_service, db, email: str, casp_roles, department: str) -> str:
    """Create user + admin record. Returns user_id."""
    existing = await db.users.find_one({"email": email.lower()})
    if existing:
        user_id = existing["id"]
    else:
        user, err = await auth_service.register(UserCreate(
            email=email, password=DEFAULT_PASS, role=UserRole.ADMIN
        ))
        if err:
            print(f"  ⚠️  failed to create {email}: {err}")
            user = await db.users.find_one({"email": email.lower()})
            user_id = user["id"]
        else:
            user_id = user.id

    # Make sure base role is ADMIN
    await db.users.update_one({"id": user_id}, {"$set": {"role": "ADMIN"}})

    casp = CaspService(db, AuditLogService(db))
    await casp.ensure_admin_user(user_id, email, casp_roles, department)
    print(f"  ✓ admin {email} ({', '.join(casp_roles)}) → {user_id}")
    return user_id


async def main() -> None:
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ.get("DB_NAME", "neonoble_ramp")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    audit = AuditLogService(db)
    await audit.initialize()
    casp = CaspService(db, audit)
    await casp.initialize()

    auth_service = AuthService(db)

    actor_system = {"user_id": "system", "email": "system@neonoble", "role": "ADMIN"}

    print("→ Seeding admin users…")
    admin_id = await ensure_admin_account(auth_service, db, SEED_ADMIN_EMAIL,
                                          ["ADMIN"], "Executive")
    mlro_id = await ensure_admin_account(auth_service, db, SEED_MLRO_EMAIL,
                                          ["MLRO", "COMPLIANCE_OFFICER"], "Compliance")
    trader_id = await ensure_admin_account(auth_service, db, SEED_TRADER_EMAIL,
                                            ["OTC_TRADER"], "Trading")
    risk_id = await ensure_admin_account(auth_service, db, "casp-risk@neonoble.example.com",
                                          ["RISK_OFFICER"], "Risk")
    treasury_id = await ensure_admin_account(auth_service, db, "casp-treasury@neonoble.example.com",
                                              ["TREASURY_OFFICER"], "Treasury")
    actor_admin = {"user_id": admin_id, "email": SEED_ADMIN_EMAIL, "role": "ADMIN"}

    print("→ Seeding sample retail customers…")
    customers = []
    for i in range(6):
        email = f"client_{i:02d}@neonoble-demo.example.com"
        u = await db.users.find_one({"email": email})
        if not u:
            user, err = await auth_service.register(UserCreate(
                email=email, password=DEFAULT_PASS, role=UserRole.USER
            ))
            if err:
                u = await db.users.find_one({"email": email})
            else:
                u = {"id": user.id, "email": email}
        customers.append(u["id"])
    print(f"  ✓ {len(customers)} retail demo customers")

    print("→ Seeding KYC records (tiered)…")
    statuses = ["APPROVED", "APPROVED", "IN_REVIEW", "PENDING", "APPROVED", "REJECTED"]
    tiers = ["TIER_2", "TIER_3", "TIER_2", "TIER_1", "TIER_3", "TIER_1"]
    for uid, st, tier in zip(customers, statuses, tiers):
        rec = KycRecord(
            user_id=uid, status=st, tier=tier,
            full_name=f"Demo Client {uid[:6].upper()}",
            country_of_residence=random.choice(["IT", "DE", "FR", "ES", "NL"]),
            nationality="IT",
            provider_applicant_id=f"sumsub_{uuid.uuid4().hex[:10]}",
            submitted_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60)),
            reviewed_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 5)) if st != "PENDING" else None,
            reviewed_by=mlro_id if st != "PENDING" else None,
            rejection_reason="Document quality insufficient" if st == "REJECTED" else None,
        ).model_dump()
        await db.casp_kyc.replace_one({"user_id": uid}, rec, upsert=True)
    print(f"  ✓ {len(customers)} KYC records")

    print("→ Seeding KYB (institutional) records…")
    inst_email = "institutional@bigcorp.example.com"
    iu = await db.users.find_one({"email": inst_email})
    if not iu:
        u_user, _ = await auth_service.register(UserCreate(
            email=inst_email, password=DEFAULT_PASS, role=UserRole.USER
        ))
        iu = {"id": u_user.id if u_user else (await db.users.find_one({"email": inst_email}))["id"]}
    inst_uid = iu["id"]
    kyb = KybRecord(
        user_id=inst_uid, status="APPROVED",
        legal_name="BigCorp Capital Management S.p.A.",
        legal_form="S.p.A.", country_of_incorporation="IT",
        lei="529900W18LQJJN6SJ336",
        registration_number="IT-2025-998877",
        registered_address="Via del Corso 1, 00187 Roma, IT",
        business_activity="Institutional crypto investing",
        nace_code="K.64.20",
        annual_revenue_eur=12_500_000,
        expected_monthly_volume_eur=2_000_000,
        ubo_list=[{"name": "Mario Rossi", "share": 60}, {"name": "Anna Bianchi", "share": 40}],
        directors=[{"name": "Mario Rossi", "role": "CEO"}],
        submitted_at=datetime.now(timezone.utc) - timedelta(days=30),
        reviewed_at=datetime.now(timezone.utc) - timedelta(days=20),
        reviewed_by=mlro_id,
    ).model_dump()
    await db.casp_kyb.replace_one({"user_id": inst_uid}, kyb, upsert=True)
    print(f"  ✓ KYB: BigCorp Capital → {inst_uid}")

    print("→ Seeding risk ratings…")
    ratings = ["LOW", "MEDIUM", "LOW", "HIGH", "MEDIUM", "PROHIBITED"]
    scores = [22, 48, 30, 78, 55, 95]
    for uid, r, s in zip(customers, ratings, scores):
        doc = RiskRatingRecord(
            user_id=uid, rating=CustomerRiskRating(r), score=s,
            factors={"geography": "LOW", "product": "MEDIUM",
                     "channel": "LOW", "customer": r},
            next_review_at=datetime.now(timezone.utc) + timedelta(days=365),
        ).model_dump()
        await db.casp_risk_rating.replace_one({"user_id": uid}, doc, upsert=True)
    # Institutional client = MEDIUM
    inst_rr = RiskRatingRecord(
        user_id=inst_uid, rating=CustomerRiskRating.MEDIUM, score=50,
        factors={"geography": "LOW", "product": "HIGH", "channel": "LOW", "customer": "MEDIUM"},
    ).model_dump()
    await db.casp_risk_rating.replace_one({"user_id": inst_uid}, inst_rr, upsert=True)
    print(f"  ✓ {len(customers) + 1} risk ratings")

    print("→ Seeding AML alerts…")
    await db.casp_aml_alerts.delete_many({"rule_id": {"$regex": "^DEMO_"}})
    alerts = [
        ("DEMO_VELOCITY", "High velocity: 10 tx in 1h", "MEDIUM", 14500, 65),
        ("DEMO_GEO", "Transfer to high-risk jurisdiction", "HIGH", 28000, 78),
        ("DEMO_STRUCTURING", "Possible structuring (3x €9.5k)", "HIGH", 28500, 82),
        ("DEMO_DARKNET", "Counterparty linked to darknet market", "CRITICAL", 12000, 95),
        ("DEMO_SANCTIONS", "Sanctioned address in transaction graph", "CRITICAL", 50000, 99),
    ]
    for rule_id, desc, sev, amt, score in alerts:
        a = AmlAlert(
            user_id=random.choice(customers),
            rule_id=rule_id, rule_name=desc,
            severity=AmlAlertSeverity(sev),
            description=desc, amount_eur=amt,
            provider="chainalysis", risk_score=score,
            source_address="0x" + uuid.uuid4().hex[:40],
        ).model_dump()
        await db.casp_aml_alerts.insert_one(a)
    print(f"  ✓ {len(alerts)} AML alerts")

    print("→ Seeding sanctions hit (1 dismissed)…")
    await db.casp_sanctions_hits.delete_many({"list_name": {"$regex": "^OFAC$"}})
    sh = SanctionsHit(
        user_id=customers[3], list_name="OFAC", match_type="SANCTIONS",
        match_score=72, matched_name="Demo False-Positive",
        raw_payload={"reason": "Name partial match — different DoB"},
        status="DISMISSED", reviewed_by=mlro_id,
        reviewed_at=datetime.now(timezone.utc),
    ).model_dump()
    await db.casp_sanctions_hits.insert_one(sh)
    print(f"  ✓ 1 sanctions hit (dismissed)")

    print("→ Seeding custodial wallets…")
    await db.casp_wallets.delete_many({"address": {"$regex": "^0xdemo"}})
    for i, asset, chain in [(0, "NENO", "BSC"), (1, "USDC", "BSC"), (2, "BTC", "BTC"),
                            (3, "ETH", "ETH"), (4, "USDT", "BSC")]:
        w = CustodialWallet(
            user_id=customers[i] if i < len(customers) else None,
            kind=WalletKind.HOT,
            purpose=WalletPurpose.CUSTOMER_SEGREGATED,
            chain=chain, address=f"0xdemo{uuid.uuid4().hex[:36]}",
            asset=asset, provider_vault_id=f"vault_{i}",
            signing_policy={"threshold": 3, "signers": ["sigA", "sigB", "sigC", "sigD"]},
            balance_native=random.uniform(0.5, 10) if asset == "BTC" else random.uniform(1000, 50000),
            balance_eur=random.uniform(10000, 250000),
        ).model_dump()
        await db.casp_wallets.insert_one(w)
    # 2 cold storage wallets
    for asset in ["BTC", "ETH"]:
        cw = CustodialWallet(
            kind=WalletKind.COLD,
            purpose=WalletPurpose.HOUSE_TREASURY,
            chain=asset, address=f"0xdemoCOLD{uuid.uuid4().hex[:32]}",
            asset=asset, provider_vault_id=f"vault_cold_{asset}",
            signing_policy={"threshold": 4, "signers": ["sigA", "sigB", "sigC", "sigD", "sigE"]},
            balance_native=random.uniform(5, 50),
            balance_eur=random.uniform(500_000, 2_000_000),
        ).model_dump()
        await db.casp_wallets.insert_one(cw)
    print(f"  ✓ 7 custodial wallets (5 hot, 2 cold)")

    print("→ Seeding OTC B2B quotes…")
    await db.casp_otc_b2b.delete_many({"reference": {"$regex": "^OTC-"}})
    demo_otc = [
        ("BUY", "BTC", 5, 95000, "QUOTED", False),
        ("SELL", "ETH", 50, 3200, "QUOTED", False),
        ("BUY", "BTC", 20, 95500, "AWAITING_APPROVAL", True),
        ("BUY", "USDC", 250000, 1.0, "EXECUTED", False),
        ("SELL", "NENO", 5, 10000, "SETTLED", False),
    ]
    for i, (side, asset, qty, price, status, approval) in enumerate(demo_otc, start=1):
        total = qty * price
        fee = round(total * 25 / 10000, 2)
        net = total - fee if side == "SELL" else total + fee
        ref = f"OTC-{datetime.now(timezone.utc).year}-{i:06d}"
        q = OtcQuoteB2B(
            reference=ref,
            client_user_id=inst_uid,
            trader_id=trader_id,
            approver_id=mlro_id if status in ("APPROVED", "EXECUTED", "SETTLED") else None,
            side=OtcSide(side), asset=asset,
            quantity=qty, price_eur=price, total_eur=total,
            fee_eur=fee, net_eur=net,
            settlement_method="SEPA" if asset != "BTC" else "ON_CHAIN",
            status=OtcStatus(status), approval_required=approval,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            executed_at=datetime.now(timezone.utc) - timedelta(hours=1) if status in ("EXECUTED", "SETTLED") else None,
            settled_at=datetime.now(timezone.utc) - timedelta(minutes=30) if status == "SETTLED" else None,
            best_execution_evidence={
                "venues_checked": ["binance", "kraken", "coinbase"],
                "mid_price_eur": price, "spread_bps": 25,
                "rationale": "Best mid-price from 3 venues, ±5 bps tolerance.",
            },
        ).model_dump()
        await db.casp_otc_b2b.insert_one(q)
    print(f"  ✓ {len(demo_otc)} OTC B2B quotes")

    print("→ Seeding capital snapshot…")
    cap = CapitalAdequacySnapshot(
        casp_class=2, required_capital_eur=125_000,
        own_funds_eur=275_000, surplus_eur=150_000,
        coverage_ratio=275_000 / 125_000, status="COMPLIANT",
        notes="Class 2 CASP — €275k own funds vs €125k requirement.",
    ).model_dump()
    await db.casp_capital_snapshots.insert_one(cap)
    print(f"  ✓ Capital snapshot (COMPLIANT, 220% coverage)")

    print("→ Seeding asset disclosures…")
    await db.casp_disclosures.delete_many({})
    for asset, chain, risk, contract in [
        ("NENO", "BSC", "VERY_HIGH", "0xef3f5C18..."),
        ("BTC", "BTC", "MEDIUM", None),
        ("ETH", "ETH", "MEDIUM", None),
        ("USDC", "BSC", "LOW", "0x8AC76a51..."),
    ]:
        d = AssetDisclosure(
            asset=asset, asset_chain=chain, contract_address=contract,
            risk_level=risk,
            disclosure_md=(
                f"# {asset} — Pre-contractual Disclosure\n\n"
                f"Risk level: **{risk}**.\n\nThis is a MiCAR Art. 66 disclosure stub. "
                "Replace with full whitepaper-equivalent content before going live."
            ),
            published_by=admin_id,
        ).model_dump()
        await db.casp_disclosures.insert_one(d)
    print(f"  ✓ 4 asset disclosures")

    print("→ Seeding complaints…")
    await db.casp_complaints.delete_many({"reference": {"$regex": "^CMP-"}})
    for i, (cat, subj) in enumerate([
        ("FEES", "Unclear conversion fee on EUR→BTC"),
        ("KYC", "KYC under review for 5 days"),
    ], start=1):
        c = Complaint(
            reference=f"CMP-{datetime.now(timezone.utc).year}-{i:05d}",
            user_id=random.choice(customers),
            category=cat, subject=subj,
            description=f"Customer says: {subj}",
            sla_deadline=datetime.now(timezone.utc) + timedelta(days=15),
        ).model_dump()
        await db.casp_complaints.insert_one(c)
    print(f"  ✓ 2 complaints")

    print("→ Seeding operational incidents & conflicts…")
    await db.casp_incidents.delete_many({"reference": {"$regex": "^INC-"}})
    inc = OperationalIncident(
        reference=f"INC-{datetime.now(timezone.utc).year}-0001",
        title="Brief Transak API degradation",
        description="3rd-party widget URL endpoint returned 401 for 30 min.",
        severity=IncidentSeverity.SEV3,
        detected_at=datetime.now(timezone.utc) - timedelta(hours=12),
        resolved_at=datetime.now(timezone.utc) - timedelta(hours=11),
        impact="No customer funds affected; 4 onramp attempts deferred.",
        root_cause="Vendor whitelist mismatch.",
        remediation="Whitelist refreshed; vendor incident closed.",
        status="CLOSED",
    ).model_dump()
    await db.casp_incidents.insert_one(inc)

    await db.casp_conflicts.delete_many({"party": {"$regex": "demo"}})
    coi = ConflictOfInterest(
        party="demo_employee",
        nature="personal-trading",
        description="Trader holds <€500 of NENO personally.",
        mitigation="Position frozen; trades on NENO routed to second trader.",
        declared_by=trader_id,
        review_due=datetime.now(timezone.utc) + timedelta(days=180),
    ).model_dump()
    await db.casp_conflicts.insert_one(coi)
    print(f"  ✓ 1 incident, 1 conflict of interest")

    print("→ Generating initial Proof of Reserves & MiCAR report…")
    await casp.generate_proof_of_reserves(actor_system)
    await casp.generate_micar_report(
        period_start=datetime.now(timezone.utc) - timedelta(days=30),
        period_end=datetime.now(timezone.utc),
        actor=actor_system,
    )
    print(f"  ✓ PoR + MiCAR T+1 report")

    print("→ Seeding VASP directory (3 demo peers for autonomous Travel Rule)…")
    sample_vasps = [
        {
            "did": "did:web:bigexchange.example",
            "name": "BigExchange Ltd",
            "trp_endpoint": "https://bigexchange.example/trp/inbox",
            "known_addresses": ["0x28c6c06298d514db089934071355e5743bf21d60"],
            "shared_secret": "demo-shared-secret-bigexchange",
        },
        {
            "did": "did:web:safecustody.example",
            "name": "SafeCustody Bank",
            "trp_endpoint": "https://safecustody.example/api/trp",
            "known_addresses": ["0xbe0eb53f46cd790cd13851d5eff43d12404d33e8"],
            "shared_secret": "demo-shared-secret-safecustody",
        },
        {
            "did": "did:web:cryptoexch.example",
            "name": "CryptoExch SA",
            "trp_endpoint": "https://cryptoexch.example/.well-known/trp",
            "known_addresses": ["0x564286362092d8e7936f0549571a803b203aaced"],
            "shared_secret": "demo-shared-secret-cryptoexch",
        },
    ]
    for v in sample_vasps:
        await casp.upsert_vasp(
            did=v["did"], name=v["name"], trp_endpoint=v["trp_endpoint"],
            known_addresses=v["known_addresses"], shared_secret=v["shared_secret"],
            actor=actor_system,
        )
    print(f"  ✓ 3 peer VASPs registered")

    print("→ Recording initial sanctions-list refresh…")
    await casp.sanctions_record_refresh(actor_system)
    print("  ✓ Sanctions list refresh logged")

    print()
    print("=" * 68)
    print("CASP SEED COMPLETE")
    print("=" * 68)
    print(f"Super admin login: {SEED_ADMIN_EMAIL} / {DEFAULT_PASS}")
    print(f"MLRO login:        {SEED_MLRO_EMAIL} / {DEFAULT_PASS}")
    print(f"OTC Trader login:  {SEED_TRADER_EMAIL} / {DEFAULT_PASS}")
    print(f"Risk Officer:      casp-risk@neonoble.example.com / {DEFAULT_PASS}")
    print(f"Treasury Officer:  casp-treasury@neonoble.example.com / {DEFAULT_PASS}")
    print(f"Demo B2B client:   institutional@bigcorp.example.com / {DEFAULT_PASS}")
    print("=" * 68)
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
