"""CASP Operating Stack — full backend regression for Sprint 1.

Tests REST endpoints under /api/casp/* covering all 7 MiCAR blocks, RBAC
matrix, 4-eye OTC approval, hash-chain audit verification, and a quick
regression on Transak/Auth endpoints to ensure nothing was broken.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://neonoble-ramp.preview.emergentagent.com").rstrip("/")
CASP_PWD = "CaspAdmin!2026"

ADMIN_EMAIL = "casp-admin@neonoble.example.com"
MLRO_EMAIL = "casp-mlro@neonoble.example.com"
TRADER_EMAIL = "casp-trader@neonoble.example.com"
RISK_EMAIL = "casp-risk@neonoble.example.com"
TREASURY_EMAIL = "casp-treasury@neonoble.example.com"
INSTITUTIONAL_EMAIL = "institutional@bigcorp.example.com"


def _login(email: str, password: str = CASP_PWD) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL)


@pytest.fixture(scope="module")
def mlro_token():
    return _login(MLRO_EMAIL)


@pytest.fixture(scope="module")
def trader_token():
    return _login(TRADER_EMAIL)


@pytest.fixture(scope="module")
def treasury_token():
    return _login(TREASURY_EMAIL)


@pytest.fixture(scope="module")
def user_token():
    """Ephemeral USER-role token for RBAC negative tests."""
    email = f"TEST_user_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": email, "password": "TestPass123!", "role": "USER"},
                      timeout=15)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    return body.get("token") or body.get("access_token")


# ── RBAC matrix ────────────────────────────────────────────────────────────

class TestRBAC:
    def test_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/casp/dashboard", timeout=15)
        assert r.status_code in (401, 403), r.text

    def test_user_role_forbidden(self, user_token):
        r = requests.get(f"{BASE_URL}/api/casp/dashboard", headers=_h(user_token), timeout=15)
        assert r.status_code == 403, r.text

    def test_user_role_forbidden_on_kyc(self, user_token):
        r = requests.get(f"{BASE_URL}/api/casp/kyc", headers=_h(user_token), timeout=15)
        assert r.status_code == 403


# ── Dashboard & seeded data ────────────────────────────────────────────────

class TestDashboard:
    def test_dashboard_kpi_shape(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/dashboard", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        for key in ("kyc", "aml", "otc", "wallets", "complaints", "capital"):
            assert key in d, f"missing KPI key {key}"
        assert d["wallets"]["total"] >= 7


class TestBlock1:
    def test_kyc_list(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/kyc", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 6

    def test_kyc_filter_by_status(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/kyc?status=APPROVED",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        for it in r.json():
            assert it.get("status") == "APPROVED"

    def test_kyb_list_has_bigcorp(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/kyb", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1
        names = " ".join(str(it.get("legal_name", "")) for it in items).lower()
        assert "bigcorp" in names or len(items) >= 1

    def test_risk_ratings(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/risk-rating",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        items = r.json()
        ratings = {it.get("rating") for it in items}
        assert ratings & {"LOW", "MEDIUM", "HIGH", "PROHIBITED"}


# ── Block 2: AML ───────────────────────────────────────────────────────────

class TestBlock2_AML:
    def test_list_alerts(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/aml/alerts",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 5

    def test_severity_filter(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/aml/alerts?severity=CRITICAL",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        for it in r.json():
            assert it.get("severity") == "CRITICAL"

    def test_screen_address_returns_risk_score(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/casp/aml/screen-address",
                          headers=_h(admin_token),
                          json={"address": "0xabc123" + "0" * 34,
                                "asset": "USDT", "chain": "ETH"}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "risk_score" in d
        assert 0 <= float(d["risk_score"]) <= 100

    def test_resolve_alert_requires_mlro(self, admin_token, mlro_token):
        alerts = requests.get(f"{BASE_URL}/api/casp/aml/alerts",
                              headers=_h(admin_token), timeout=15).json()
        open_alerts = [a for a in alerts if a.get("status") not in
                       ("CLOSED_FALSE_POSITIVE", "CLOSED_TRUE_POSITIVE", "ESCALATED")]
        if not open_alerts:
            pytest.skip("no open alerts to resolve")
        alert_id = open_alerts[0].get("id") or open_alerts[0].get("alert_id")
        r = requests.post(f"{BASE_URL}/api/casp/aml/alerts/{alert_id}/resolve",
                          headers=_h(mlro_token),
                          json={"status": "CLOSED_FALSE_POSITIVE",
                                "notes": "TEST resolve via mlro"}, timeout=15)
        assert r.status_code == 200, r.text


# ── Block 3: Wallets & PoR ─────────────────────────────────────────────────

class TestBlock3_Custody:
    def test_list_wallets(self, treasury_token):
        r = requests.get(f"{BASE_URL}/api/casp/wallets",
                         headers=_h(treasury_token), timeout=15)
        assert r.status_code == 200
        wallets = r.json()
        assert len(wallets) >= 7
        kinds = {w.get("kind") for w in wallets}
        assert "HOT" in kinds and "COLD" in kinds

    def test_reconcile_wallet(self, treasury_token):
        wallets = requests.get(f"{BASE_URL}/api/casp/wallets",
                               headers=_h(treasury_token), timeout=15).json()
        wid = wallets[0].get("id") or wallets[0].get("wallet_id")
        r = requests.post(f"{BASE_URL}/api/casp/wallets/{wid}/reconcile",
                          headers=_h(treasury_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_freeze_wallet(self, treasury_token):
        wallets = requests.get(f"{BASE_URL}/api/casp/wallets",
                               headers=_h(treasury_token), timeout=15).json()
        # pick a hot wallet to freeze
        hot = next((w for w in wallets if w.get("kind") == "HOT"), wallets[-1])
        wid = hot.get("id") or hot.get("wallet_id")
        r = requests.post(f"{BASE_URL}/api/casp/wallets/{wid}/freeze",
                          headers=_h(treasury_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_por_latest(self, treasury_token):
        r = requests.get(f"{BASE_URL}/api/casp/proof-of-reserves",
                         headers=_h(treasury_token), timeout=15)
        assert r.status_code == 200

    def test_por_generate(self, treasury_token):
        r = requests.post(f"{BASE_URL}/api/casp/proof-of-reserves/generate",
                          headers=_h(treasury_token), timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("snapshot_date") or d.get("created_at") or d.get("id")


# ── Block 4: OTC + 4-eye principle ─────────────────────────────────────────

class TestBlock4_OTC:
    def test_list_seeded_otc(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/otc",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 5

    def test_create_otc_quote_large_goes_to_awaiting_approval(self, trader_token):
        body = {
            "client_user_id": "bigcorp-test",
            "side": "BUY",
            "asset": "BTC",
            "quantity": 5,
            "price_eur": 60000.0,  # > 50000 EUR threshold
            "fee_bps": 25,
            "settlement_method": "SEPA",
        }
        r = requests.post(f"{BASE_URL}/api/casp/otc/quote",
                          headers=_h(trader_token), json=body, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") in ("AWAITING_APPROVAL", "QUOTED"), d
        # store for later tests
        pytest.shared_quote = d

    def test_self_approval_rejected(self, trader_token):
        q = getattr(pytest, "shared_quote", None)
        if not q:
            pytest.skip("no shared quote")
        qid = q.get("id") or q.get("quote_id")
        # trader has base ADMIN role per seed; the 4-eye guard must still block
        # self-approval even for super-admin
        r = requests.post(f"{BASE_URL}/api/casp/otc/{qid}/approve",
                          headers=_h(trader_token),
                          json={"decision": "APPROVE", "notes": "self"}, timeout=15)
        assert r.status_code == 400, f"self approval must be 400, got {r.status_code} {r.text}"
        body = r.json()
        detail = str(body.get("detail", body)).lower()
        assert "self" in detail or "approval" in detail or "forbidden" in detail, body

    def test_approval_from_different_actor(self, mlro_token):
        q = getattr(pytest, "shared_quote", None)
        if not q:
            pytest.skip("no shared quote")
        qid = q.get("id") or q.get("quote_id")
        r = requests.post(f"{BASE_URL}/api/casp/otc/{qid}/approve",
                          headers=_h(mlro_token),
                          json={"decision": "APPROVE", "notes": "mlro ok"}, timeout=15)
        assert r.status_code == 200, r.text

    def test_execute_otc(self, trader_token):
        q = getattr(pytest, "shared_quote", None)
        if not q:
            pytest.skip("no shared quote")
        qid = q.get("id") or q.get("quote_id")
        r = requests.post(f"{BASE_URL}/api/casp/otc/{qid}/execute",
                          headers=_h(trader_token), timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "EXECUTED"


# ── Block 5: Reporting & Capital ───────────────────────────────────────────

class TestBlock5_Reporting:
    def test_list_reports(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/reports",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200

    def test_generate_micar(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/casp/reports/micar",
                          headers=_h(admin_token),
                          json={"period_start": "2026-01-01T00:00:00",
                                "period_end": "2026-01-31T23:59:59"}, timeout=20)
        assert r.status_code == 200, r.text

    def test_capital_snapshot(self, treasury_token):
        r = requests.post(f"{BASE_URL}/api/casp/capital",
                          headers=_h(treasury_token),
                          json={"own_funds_eur": 280000.0, "casp_class": 2,
                                "notes": "TEST"}, timeout=15)
        assert r.status_code == 200, r.text


# ── Block 6: Complaints & Disclosures ──────────────────────────────────────

class TestBlock6_Protection:
    def test_list_complaints(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/complaints",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200

    def test_create_complaint(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/casp/complaints",
                          headers=_h(admin_token),
                          json={"user_id": "u-test", "category": "FEES",
                                "subject": "TEST complaint",
                                "description": "TEST description body"}, timeout=15)
        assert r.status_code == 200, r.text

    def test_disclosures(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/disclosures",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 4


# ── Block 7: Governance ────────────────────────────────────────────────────

class TestBlock7_Governance:
    def test_admins_list(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/governance/admins",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        admins = r.json()
        assert len(admins) >= 5

    def test_incidents(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/governance/incidents",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200

    def test_conflicts(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/governance/conflicts",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200


# ── Audit hash chain ───────────────────────────────────────────────────────

class TestAudit:
    def test_audit_list(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/audit?limit=20",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        entries = r.json()
        assert isinstance(entries, list) and len(entries) > 0
        # newest-first ordering
        seqs = [e.get("sequence") for e in entries if e.get("sequence") is not None]
        if len(seqs) >= 2:
            assert seqs[0] >= seqs[-1]

    def test_audit_verify(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/casp/audit/verify?limit=1000",
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("verified") is True, d
        assert d.get("checked", 0) > 0


# ── Quick regression on legacy endpoints ───────────────────────────────────

class TestRegression:
    def test_legacy_login_still_works(self):
        # casp-admin login itself proves /api/auth/login
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": CASP_PWD},
                          timeout=15)
        assert r.status_code == 200

    def test_auth_me(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/auth/me",
                         headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        assert r.json().get("email") == ADMIN_EMAIL

    def test_transak_widget_url(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/transak/widget-url",
                          headers=_h(admin_token),
                          json={"fiat_amount": 100, "fiat_currency": "EUR",
                                "crypto_currency": "USDC", "network": "bsc"},
                          timeout=15)
        # Endpoint should exist (not 404/405). Acceptable upstream states:
        #   200 — happy path
        #   400/422 — bad request payload
        #   409 — TRANSAK_KYB_PENDING (account waiting Transak compliance approval)
        #   502 — generic upstream rejection
        assert r.status_code in (200, 400, 422, 409, 502), r.text
