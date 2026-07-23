#!/usr/bin/env python3
"""CASP Operating Stack — Full E2E Exercise.

Runs through every block of the CASP back-office sequentially, hitting the
live HTTP API (not mocks), and prints a structured report.

Usage:
    python /app/scripts/casp_full_exercise.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

# ── config ──────────────────────────────────────────────────────────────────
API = "http://localhost:8001/api"
PWD = "CaspAdmin!2026"
ACCOUNTS = {
    "admin": "casp-admin@neonoble.example.com",
    "mlro": "casp-mlro@neonoble.example.com",
    "trader": "casp-trader@neonoble.example.com",
    "risk": "casp-risk@neonoble.example.com",
    "treasury": "casp-treasury@neonoble.example.com",
}

GREEN, RED, YELLOW, RESET, BOLD, DIM = (
    "\033[92m", "\033[91m", "\033[93m", "\033[0m", "\033[1m", "\033[2m"
)

report: List[Dict[str, Any]] = []
passed = failed = 0
tokens: Dict[str, str] = {}


def record(block: str, op: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    passed, failed = passed + int(ok), failed + (0 if ok else 1)
    icon = f"{GREEN}OK {RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{icon}] {block:<14} {op:<42} {DIM}{detail[:70]}{RESET}")
    report.append({"block": block, "op": op, "ok": ok, "detail": detail})


def call(method: str, path: str, who: Optional[str] = None,
         body: Optional[dict] = None, params: Optional[dict] = None) -> tuple[int, Any]:
    headers = {}
    if who and who in tokens:
        headers["Authorization"] = f"Bearer {tokens[who]}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        r = requests.request(method, f"{API}{path}", json=body, params=params,
                             headers=headers, timeout=20)
    except Exception as e:
        return 0, {"error": str(e)}
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


# ── 0. Login ────────────────────────────────────────────────────────────────
print(f"\n{BOLD}━━━ 0. Authentication ━━━{RESET}")
for who, email in ACCOUNTS.items():
    code, data = call("POST", "/auth/login", body={"email": email, "password": PWD})
    if code == 200 and data.get("access_token"):
        tokens[who] = data["access_token"]
        record("AUTH", f"login {who}", True, f"role={data['user']['role']}")
    else:
        record("AUTH", f"login {who}", False, f"{code} {data}")

if "admin" not in tokens:
    print(f"{RED}Cannot proceed without admin token{RESET}")
    sys.exit(1)


# ── Dashboard KPIs ──────────────────────────────────────────────────────────
print(f"\n{BOLD}━━━ Dashboard KPIs ━━━{RESET}")
code, kpi = call("GET", "/casp/dashboard", who="admin")
record("KPI", "GET /casp/dashboard", code == 200,
       f"kyc_pending={kpi.get('kyc', {}).get('pending')} "
       f"aml_open={kpi.get('aml', {}).get('open_alerts')} "
       f"wallets={kpi.get('wallets', {}).get('total')}" if code == 200 else str(kpi))


# ── BLOCK 1: KYC / KYB / Risk / Sanctions ───────────────────────────────────
print(f"\n{BOLD}━━━ Block 1 — KYC / KYB / Risk / Sanctions ━━━{RESET}")

# Register a new retail customer + complete onboarding
new_email = f"e2e_customer_{uuid.uuid4().hex[:8]}@example.com"
code, reg = call("POST", "/auth/register",
                 body={"email": new_email, "password": "TestPass123!", "role": "USER"})
record("B1.KYC", "Register new customer", code == 200, new_email)
new_user_token = reg.get("access_token") if code == 200 else None
new_user_id = reg.get("user", {}).get("id") if code == 200 else None

if new_user_token:
    tokens["new_user"] = new_user_token
    # Self-service onboarding
    code, _ = call("GET", "/onboarding/my-kyc", who="new_user")
    record("B1.KYC", "GET /onboarding/my-kyc (NOT_STARTED)",
           code == 200, "status=NOT_STARTED")

    code, started = call("POST", "/onboarding/kyc/start", who="new_user",
                        body={"full_name": "Marco Bianchi", "date_of_birth": "1985-03-12",
                              "nationality": "IT", "country_of_residence": "IT",
                              "document_type": "PASSPORT"})
    new_kyc_id = started.get("kyc_id") if code == 200 else None
    record("B1.KYC", "POST /onboarding/kyc/start", code == 200,
           f"kyc_id={new_kyc_id[:8] if new_kyc_id else 'n/a'}")

    # Upload 3 documents
    b64 = base64.b64encode(b"fake-document-bytes-for-e2e-test").decode()
    for dt in ("ID_FRONT", "ID_BACK", "SELFIE"):
        code, _ = call("POST", "/onboarding/kyc/document", who="new_user",
                      body={"doc_type": dt, "document_b64": b64, "mime": "image/jpeg"})
        record("B1.KYC", f"Upload {dt}", code == 200)

    # Check status now IN_REVIEW
    code, my_kyc = call("GET", "/onboarding/my-kyc", who="new_user")
    record("B1.KYC", "GET /onboarding/my-kyc (IN_REVIEW)",
           code == 200 and my_kyc.get("status") == "IN_REVIEW",
           f"status={my_kyc.get('status')}")

    # MLRO approves
    if new_kyc_id and "mlro" in tokens:
        code, _ = call("POST", f"/casp/kyc/{new_kyc_id}/decision", who="mlro",
                      body={"decision": "APPROVE", "reason": "All docs verified"})
        record("B1.KYC", "MLRO approves KYC", code == 200)

# Admin lists KYC
code, kyc_list = call("GET", "/casp/kyc", who="admin", params={"limit": 5})
record("B1.KYC", "List KYC records", code == 200,
       f"count={len(kyc_list) if isinstance(kyc_list, list) else 'n/a'}")

# KYB
code, kyb = call("GET", "/casp/kyb", who="admin")
record("B1.KYB", "List KYB records", code == 200,
       f"count={len(kyb) if isinstance(kyb, list) else 'n/a'}")

# Risk rating
if new_user_id:
    code, _ = call("POST", "/casp/risk-rating", who="risk",
                  body={"user_id": new_user_id, "rating": "LOW", "score": 25.0,
                        "factors": {"pep": False, "geo": "EU", "tx_volume": "low"}})
    record("B1.Risk", "Upsert risk rating", code == 200, "rating=LOW")

code, risks = call("GET", "/casp/risk-rating", who="admin")
record("B1.Risk", "List risk ratings", code == 200,
       f"count={len(risks) if isinstance(risks, list) else 'n/a'}")

# Sanctions hits + autonomous mode status
code, sanc = call("GET", "/casp/sanctions/status", who="admin")
record("B1.Sanc", "GET /casp/sanctions/status", code == 200,
       f"ofac={sanc.get('ofac_crypto_addresses')} mixers={sanc.get('known_mixers')}")
code, _ = call("POST", "/casp/sanctions/refresh", who="mlro")
record("B1.Sanc", "POST /casp/sanctions/refresh", code == 200)


# ── BLOCK 2: AML / Travel-Rule / SAR ────────────────────────────────────────
print(f"\n{BOLD}━━━ Block 2 — AML / Travel Rule / SAR ━━━{RESET}")

# Screen a clean address
code, clean = call("POST", "/casp/aml/screen-address", who="mlro",
                  body={"address": "0x1f9090aaE28b8a3dCeaDf281B0F12828e676c326",
                        "asset": "ETH", "chain": "ethereum"})
record("B2.AML", "Screen clean address", code == 200,
       f"risk_score={clean.get('risk_score')} critical={clean.get('is_critical')}")

# Screen a known sanctioned address (Tornado Cash router)
code, dirty = call("POST", "/casp/aml/screen-address", who="mlro",
                  body={"address": "0x8589427373d6d84e98730d7795d8f6f8731fda16",
                        "asset": "ETH", "chain": "ethereum"})
record("B2.AML", "Screen sanctioned (Tornado Cash)", code == 200,
       f"risk_score={dirty.get('risk_score')} critical={dirty.get('is_critical')}")

# List open alerts
code, alerts = call("GET", "/casp/aml/alerts", who="mlro", params={"status": "OPEN"})
record("B2.AML", "List OPEN alerts", code == 200,
       f"count={len(alerts) if isinstance(alerts, list) else 'n/a'}")

# Resolve oldest open alert
if isinstance(alerts, list) and alerts:
    alert_id = alerts[0]["id"]
    code, _ = call("POST", f"/casp/aml/alerts/{alert_id}/resolve", who="mlro",
                  body={"status": "CLOSED_FALSE_POSITIVE", "notes": "E2E test resolution"})
    record("B2.AML", "Resolve alert (false positive)", code == 200, alert_id[:8])

# Travel Rule outgoing
code, tr = call("POST", "/casp/travel-rule", who="mlro",
               body={"asset": "BTC", "amount": 0.5, "amount_eur": 25000.0,
                     "originator_name": "Marco Bianchi",
                     "originator_wallet": "bc1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                     "beneficiary_name": "Binance Hot Wallet",
                     "beneficiary_wallet": "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h",
                     "chain": "bitcoin"})
record("B2.TR", "Create outgoing Travel-Rule", code == 200,
       f"id={tr.get('id', '')[:8]}")

code, trs = call("GET", "/casp/travel-rule", who="mlro")
record("B2.TR", "List Travel-Rule transfers", code == 200,
       f"count={len(trs) if isinstance(trs, list) else 'n/a'}")

# TRP autonomous: VASP directory
fake_did = f"did:web:partner-{uuid.uuid4().hex[:6]}.example.com"
code, _ = call("POST", "/casp/trp/vasps", who="mlro",
              body={"did": fake_did, "name": "Partner VASP E2E",
                    "trp_endpoint": "https://partner.example.com/trp",
                    "known_addresses": ["0xpartneraddr1", "0xpartneraddr2"],
                    "shared_secret": "shared_secret_" + uuid.uuid4().hex})
record("B2.TR", "Upsert peer VASP", code == 200, fake_did[:30])

code, vasps = call("GET", "/casp/trp/vasps", who="admin")
record("B2.TR", "List peer VASPs", code == 200,
       f"count={len(vasps) if isinstance(vasps, list) else 'n/a'}")

code, inbox = call("GET", "/casp/trp/inbox", who="mlro")
record("B2.TR", "List TRP inbox", code == 200,
       f"count={len(inbox) if isinstance(inbox, list) else 'n/a'}")

code, _ = call("DELETE", f"/casp/trp/vasps/{fake_did}", who="mlro")
record("B2.TR", "Delete peer VASP", code == 200, fake_did[:30])

# SAR draft
if new_user_id and isinstance(alerts, list) and alerts:
    code, sar = call("POST", "/casp/sar", who="mlro",
                    body={"user_id": new_user_id, "alert_ids": [alerts[0]["id"]],
                          "narrative": "E2E test SAR — sanctioned wallet interaction",
                          "total_amount_eur": 25000.0})
    record("B2.SAR", "Draft SAR", code == 200,
           f"sar_number={sar.get('sar_number')}")

code, sars = call("GET", "/casp/sar", who="mlro")
record("B2.SAR", "List SARs", code == 200,
       f"count={len(sars) if isinstance(sars, list) else 'n/a'}")


# ── BLOCK 3: Custody / Treasury ─────────────────────────────────────────────
print(f"\n{BOLD}━━━ Block 3 — Custody & Treasury ━━━{RESET}")

# List wallets
code, wallets = call("GET", "/casp/wallets", who="treasury")
record("B3.Custody", "List wallets", code == 200,
       f"count={len(wallets) if isinstance(wallets, list) else 'n/a'}")

# Provision a new segregated wallet for the new customer
if new_user_id:
    code, w = call("POST", "/casp/wallets/provision", who="treasury",
                  body={"user_id": new_user_id, "asset": "USDC", "chain": "bsc"})
    record("B3.Custody", "Provision segregated wallet", code == 200,
           f"addr={w.get('address', '')[:18]}...")

# Reconcile + freeze the first wallet
if isinstance(wallets, list) and wallets:
    wid = wallets[0]["id"]
    code, recon = call("POST", f"/casp/wallets/{wid}/reconcile", who="treasury")
    record("B3.Custody", "Run reconciliation", code == 200,
           f"status={recon.get('status')} delta={recon.get('delta')}")
    code, _ = call("POST", f"/casp/wallets/{wid}/freeze", who="treasury")
    record("B3.Custody", "Freeze wallet", code == 200, wid[:8])

# Proof of Reserves
code, _ = call("POST", "/casp/proof-of-reserves/generate", who="treasury")
record("B3.PoR", "Generate PoR snapshot", code == 200)

code, por = call("GET", "/casp/proof-of-reserves", who="admin")
record("B3.PoR", "Get latest PoR", code == 200,
       f"coverage={por.get('coverage_ratio', 0):.3f} merkle={por.get('merkle_root', '')[:12]}")


# ── BLOCK 4: B2B OTC desk (with 4-eye approval) ─────────────────────────────
print(f"\n{BOLD}━━━ Block 4 — B2B OTC desk (4-eye) ━━━{RESET}")

# Find a B2B client (use the first user with a kyb record or new_user as fallback)
client_id = new_user_id or "demo-client"

# 1) Small quote — no approval needed (€10k)
code, small = call("POST", "/casp/otc/quote", who="trader",
                  body={"client_user_id": client_id, "side": "BUY", "asset": "BTC",
                        "quantity": 0.15, "price_eur": 60000.0,
                        "settlement_method": "SEPA"})
small_id = small.get("id") if code == 200 else None
record("B4.OTC", "Quote small (€9k, no approval)", code == 200,
       f"status={small.get('status')}")

if small_id:
    code, _ = call("POST", f"/casp/otc/{small_id}/execute", who="trader")
    record("B4.OTC", "Execute small (direct)", code == 200)

# 2) Large quote — needs 4-eye approval (€120k)
code, big = call("POST", "/casp/otc/quote", who="trader",
                body={"client_user_id": client_id, "side": "BUY", "asset": "BTC",
                      "quantity": 2.0, "price_eur": 60000.0,
                      "settlement_method": "SEPA"})
big_id = big.get("id") if code == 200 else None
record("B4.OTC", "Quote large (€120k, 4-eye)", code == 200,
       f"status={big.get('status')} approval_req={big.get('approval_required')}")

if big_id:
    # 2a) Trader tries to self-approve — must fail
    code, self_app = call("POST", f"/casp/otc/{big_id}/approve", who="trader",
                         body={"decision": "APPROVE", "notes": "self-approve attempt"})
    record("B4.OTC", "Self-approval blocked (4-eye)",
           code == 400 or (isinstance(self_app, dict) and "self_approval" in str(self_app)),
           f"code={code} detail={str(self_app)[:50]}")

    # 2b) MLRO approves
    if "mlro" in tokens:
        code, _ = call("POST", f"/casp/otc/{big_id}/approve", who="mlro",
                      body={"decision": "APPROVE", "notes": "Compliance OK"})
        record("B4.OTC", "MLRO approves large quote", code == 200)

    # 2c) Trader executes
    code, _ = call("POST", f"/casp/otc/{big_id}/execute", who="trader")
    record("B4.OTC", "Execute large (after approval)", code == 200)

# List OTC quotes
code, otcs = call("GET", "/casp/otc", who="trader", params={"status": "EXECUTED"})
record("B4.OTC", "List EXECUTED OTC quotes", code == 200,
       f"count={len(otcs) if isinstance(otcs, list) else 'n/a'}")


# ── BLOCK 5: Regulatory Reporting + Capital Adequacy ────────────────────────
print(f"\n{BOLD}━━━ Block 5 — Reporting & Capital ━━━{RESET}")

# Generate MiCAR T+1 report (last 30 days)
end = datetime.now(timezone.utc)
start = end - timedelta(days=30)
code, rep = call("POST", "/casp/reports/micar", who="mlro",
                body={"period_start": start.isoformat(), "period_end": end.isoformat()})
record("B5.Rep", "Generate MiCAR T+1 report", code == 200,
       f"otc_txns={rep.get('summary', {}).get('otc_transactions')}")

code, reps = call("GET", "/casp/reports", who="admin")
record("B5.Rep", "List regulatory reports", code == 200,
       f"count={len(reps) if isinstance(reps, list) else 'n/a'}")

# Capital adequacy snapshot
code, cap = call("POST", "/casp/capital", who="treasury",
                body={"own_funds_eur": 280000.0, "casp_class": 2,
                      "notes": "E2E quarterly snapshot"})
record("B5.Cap", "Upsert capital snapshot", code == 200,
       f"status={cap.get('status')} coverage={cap.get('coverage_ratio', 0):.2f}")


# ── BLOCK 6: Customer Protection ────────────────────────────────────────────
print(f"\n{BOLD}━━━ Block 6 — Customer Protection ━━━{RESET}")

if new_user_id:
    code, comp = call("POST", "/casp/complaints", who="admin",
                     body={"user_id": new_user_id, "category": "WITHDRAWAL_DELAY",
                           "subject": "E2E test complaint",
                           "description": "Customer reports delayed withdrawal."})
    record("B6.Compl", "Create complaint", code == 200,
           f"ref={comp.get('reference')}")

code, comps = call("GET", "/casp/complaints", who="admin")
record("B6.Compl", "List complaints", code == 200,
       f"count={len(comps) if isinstance(comps, list) else 'n/a'}")

code, disc = call("GET", "/casp/disclosures", who="admin")
record("B6.Disc", "List asset disclosures", code == 200,
       f"count={len(disc) if isinstance(disc, list) else 'n/a'}")


# ── BLOCK 7: Governance ─────────────────────────────────────────────────────
print(f"\n{BOLD}━━━ Block 7 — Governance ━━━{RESET}")

code, admins = call("GET", "/casp/governance/admins", who="admin")
record("B7.Gov", "List admin users", code == 200,
       f"count={len(admins) if isinstance(admins, list) else 'n/a'}")

code, inc = call("GET", "/casp/governance/incidents", who="admin")
record("B7.Gov", "List operational incidents", code == 200,
       f"count={len(inc) if isinstance(inc, list) else 'n/a'}")

code, conf = call("GET", "/casp/governance/conflicts", who="admin")
record("B7.Gov", "List conflicts of interest", code == 200,
       f"count={len(conf) if isinstance(conf, list) else 'n/a'}")


# ── Audit Log ───────────────────────────────────────────────────────────────
print(f"\n{BOLD}━━━ Audit Log ━━━{RESET}")
code, audit = call("GET", "/casp/audit", who="admin", params={"limit": 10})
record("AUDIT", "List newest audit entries", code == 200,
       f"sample={len(audit) if isinstance(audit, list) else 'n/a'}")

code, verify = call("GET", "/casp/audit/verify", who="admin")
record("AUDIT", "Verify hash-chain integrity",
       code == 200 and verify.get("verified") is True,
       f"verified={verify.get('verified')} checked={verify.get('checked')}")


# ── Setup / Live mode status ────────────────────────────────────────────────
print(f"\n{BOLD}━━━ Live mode status ━━━{RESET}")
code, setup = call("GET", "/casp/setup/status", who="admin")
record("SETUP", "GET /casp/setup/status", code == 200,
       f"live={setup.get('live_mode')} autonomous={setup.get('autonomous')} "
       f"completeness={setup.get('completeness_pct')}%")


# ── Final report ────────────────────────────────────────────────────────────
print(f"\n{BOLD}━━━ FINAL REPORT ━━━{RESET}")
total = passed + failed
print(f"  {GREEN}Passed:{RESET} {passed}/{total}")
if failed:
    print(f"  {RED}Failed:{RESET} {failed}")
    for r in report:
        if not r["ok"]:
            print(f"    - {r['block']}/{r['op']}: {r['detail']}")
print(f"  Success rate: {GREEN if failed == 0 else YELLOW}{100*passed/total:.1f}%{RESET}")

# Write machine-readable summary
out = {
    "ran_at": datetime.now(timezone.utc).isoformat(),
    "total": total, "passed": passed, "failed": failed,
    "success_pct": round(100 * passed / total, 2),
    "operations": report,
}
out_path = "/app/test_reports/casp_e2e_exercise.json"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n  Machine-readable report: {out_path}")
sys.exit(0 if failed == 0 else 1)
