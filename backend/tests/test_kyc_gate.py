"""
Tests for server-side KYC gate (middleware/kyc_gate.py).

Matrix:
- Password reset full cycle (single-use, old pwd rejected, token reuse blocked)
- change-password (success + wrong current password)
- KYC 403 gate on /api/ramp/onramp/quote|execute, /api/ramp/offramp/quote|execute, /api/transak/widget-url
- Self-service KYC: NOT_STARTED -> IN_REVIEW still blocked -> MLRO APPROVED unlocks
- After APPROVED: onramp/quote returns 200, transak widget-url returns 409 TRANSAK_KYB_PENDING
- ADMIN bypass via CASP seeded admin
- Unauthenticated => 401 (not 403)
"""
import os
import uuid
import base64
import requests
import pytest


BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    env_path = '/app/frontend/.env'
    if os.path.exists(env_path):
        with open(env_path) as fh:
            for line in fh:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
                    break


ADMIN_EMAIL = "casp-admin@neonoble.example.com"
MLRO_EMAIL = "casp-mlro@neonoble.example.com"
CASP_PASSWORD = "CaspAdmin!2026"


# ---------- helpers ----------

def _register_user(role="USER"):
    """Register a fresh ephemeral user and return {email,password,token}."""
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass123!"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "role": role},
        timeout=20,
    )
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return {"email": email, "password": password, "token": data["access_token"], "refresh": data.get("refresh_token")}


def _login(email, password):
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    return r


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _start_kyc(token):
    return requests.post(
        f"{BASE_URL}/api/onboarding/kyc/start",
        headers=_auth(token),
        json={
            "full_name": "Test User",
            "date_of_birth": "1990-01-01",
            "nationality": "NL",
            "country_of_residence": "NL",
            "document_type": "PASSPORT",
        },
        timeout=20,
    )


def _mlro_token():
    r = _login(MLRO_EMAIL, CASP_PASSWORD)
    if r.status_code != 200:
        pytest.skip(f"MLRO seeded account not available: {r.status_code} {r.text}")
    return r.json()["access_token"]


def _admin_token():
    r = _login(ADMIN_EMAIL, CASP_PASSWORD)
    if r.status_code != 200:
        pytest.skip(f"CASP admin seeded account not available: {r.status_code} {r.text}")
    return r.json()["access_token"]


# ---------- Password reset / change ----------

class TestPasswordFlows:
    def test_forgot_password_returns_generic_200(self):
        # Generic response (anti-enumeration) for ANY email
        r = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "nobody@example.com"},
            timeout=20,
        )
        assert r.status_code == 200
        assert r.json().get("success") is True

    def test_reset_password_invalid_token(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={"token": "not-a-real-token", "new_password": "NewPass123!"},
            timeout=20,
        )
        assert r.status_code == 400

    def test_full_reset_cycle(self):
        # Register user
        user = _register_user()
        old_password = user["password"]
        new_password = "NewPass123!"

        # Trigger forgot-password to create a persisted jti, then mint a real token using it
        r_fp = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": user["email"]},
            timeout=20,
        )
        assert r_fp.status_code == 200

        # Read jti from MongoDB and re-sign (same way Resend email would carry it)
        import time as _t
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        db = MongoClient(mongo_url)[db_name]
        normalized = user["email"].strip().lower()
        deadline = _t.time() + 6.0
        jti = None
        user_id = None
        while _t.time() < deadline:
            d = db.users.find_one({"email": normalized}, {"id": 1, "password_reset_jti": 1})
            if d and d.get("password_reset_jti"):
                jti = d["password_reset_jti"]
                user_id = d["id"]
                break
            _t.sleep(0.3)
        assert jti, "password_reset_jti was not persisted"

        import sys as _sys
        _sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from utils.jwt_utils import create_password_reset_token
        token = create_password_reset_token(user_id=user_id, jti=jti)

        # Reset with the real token
        r = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={"token": token, "new_password": new_password},
            timeout=20,
        )
        assert r.status_code == 200, r.text

        # Old password must be rejected
        r_old = _login(user["email"], old_password)
        assert r_old.status_code == 401

        # New password must work
        r_new = _login(user["email"], new_password)
        assert r_new.status_code == 200

        # Token reuse must be blocked (single-use)
        r_reuse = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={"token": token, "new_password": "OtherPass123!"},
            timeout=20,
        )
        assert r_reuse.status_code == 400

    def test_change_password_success_and_wrong_current(self):
        user = _register_user()
        new_password = "Changed123!"

        # Wrong current password -> 400
        r_bad = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            headers=_auth(user["token"]),
            json={"current_password": "WrongPass!", "new_password": new_password},
            timeout=20,
        )
        assert r_bad.status_code == 400

        # Correct current password -> 200
        r_ok = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            headers=_auth(user["token"]),
            json={"current_password": user["password"], "new_password": new_password},
            timeout=20,
        )
        assert r_ok.status_code == 200

        # New password should now work for login
        r_login = _login(user["email"], new_password)
        assert r_login.status_code == 200


# ---------- KYC Gate (401 / 403) ----------

# Sample quote payload (small fiat to avoid limits)
ONRAMP_Q = {"fiat_amount": 100.0, "crypto_currency": "BTC"}
OFFRAMP_Q = {"crypto_amount": 0.001, "crypto_currency": "BTC"}
EXEC_BODY = {"quote_id": "00000000-0000-0000-0000-000000000000", "wallet_address": "0xabc", "bank_account": "NL00BANK000"}
TRANSAK_BODY = {"cryptoCurrencyCode": "USDC", "fiatCurrency": "EUR"}

GATED_ENDPOINTS = [
    ("POST", "/api/ramp/onramp/quote", ONRAMP_Q),
    ("POST", "/api/ramp/onramp/execute", EXEC_BODY),
    ("POST", "/api/ramp/offramp/quote", OFFRAMP_Q),
    ("POST", "/api/ramp/offramp/execute", EXEC_BODY),
    ("POST", "/api/transak/widget-url", TRANSAK_BODY),
]


class TestUnauthenticated:
    @pytest.mark.parametrize("method,path,body", GATED_ENDPOINTS)
    def test_no_token_returns_401(self, method, path, body):
        r = requests.request(method, f"{BASE_URL}{path}", json=body, timeout=20)
        # Gate must NOT swallow 401 -> 403
        assert r.status_code == 401, f"{path} returned {r.status_code}: {r.text}"


class TestKycRequired403:
    """USER with NOT_STARTED KYC -> 403 with structured detail."""

    @pytest.fixture(scope="class")
    def fresh_user(self):
        return _register_user()

    @pytest.mark.parametrize("method,path,body", GATED_ENDPOINTS)
    def test_not_started_blocked(self, fresh_user, method, path, body):
        r = requests.request(
            method, f"{BASE_URL}{path}",
            headers=_auth(fresh_user["token"]),
            json=body, timeout=20,
        )
        assert r.status_code == 403, f"{path} expected 403, got {r.status_code}: {r.text}"
        data = r.json()
        detail = data.get("detail")
        assert isinstance(detail, dict), f"detail must be structured object, got: {detail}"
        assert detail.get("error") == "kyc_required"
        assert "kyc_status" in detail
        assert "message" in detail

    def test_in_review_still_blocked(self, fresh_user):
        # Start KYC -> status becomes IN_REVIEW
        rs = _start_kyc(fresh_user["token"])
        assert rs.status_code == 200, rs.text

        # Confirm status via self-service endpoint
        rk = requests.get(f"{BASE_URL}/api/onboarding/my-kyc", headers=_auth(fresh_user["token"]), timeout=20)
        assert rk.status_code == 200
        status = rk.json().get("status")
        assert status in ("IN_REVIEW", "PENDING", "SUBMITTED"), f"unexpected status: {status}"

        # Onramp quote must still be blocked
        r = requests.post(
            f"{BASE_URL}/api/ramp/onramp/quote",
            headers=_auth(fresh_user["token"]),
            json=ONRAMP_Q, timeout=20,
        )
        assert r.status_code == 403
        assert r.json()["detail"]["error"] == "kyc_required"


class TestKycApprovedUnlocks:
    """After MLRO approves a user's KYC, retail endpoints unlock."""

    def test_full_unlock_flow(self):
        user = _register_user()

        # Start KYC
        rs = _start_kyc(user["token"])
        assert rs.status_code == 200

        # Get the user's kyc_id directly via /onboarding/my-kyc (returns record)
        rk0 = requests.get(f"{BASE_URL}/api/onboarding/my-kyc", headers=_auth(user["token"]), timeout=20)
        assert rk0.status_code == 200
        kyc_id = rk0.json().get("id") or rk0.json().get("kyc_id")
        assert kyc_id, f"my-kyc did not return id: {rk0.json()}"

        # Confirm MLRO can list the record (any status)
        mlro_token = _mlro_token()
        rl = requests.get(f"{BASE_URL}/api/casp/kyc", headers=_auth(mlro_token), timeout=20)
        assert rl.status_code == 200
        match = next((x for x in rl.json() if x.get("id") == kyc_id), None)
        assert match, "MLRO cannot see user's KYC record in /casp/kyc listing"

        # MLRO approves
        rd = requests.post(
            f"{BASE_URL}/api/casp/kyc/{kyc_id}/decision",
            headers=_auth(mlro_token),
            json={"decision": "APPROVE", "reason": "auto-test"},
            timeout=20,
        )
        assert rd.status_code == 200, rd.text

        # /onboarding/my-kyc should reflect APPROVED
        rk = requests.get(f"{BASE_URL}/api/onboarding/my-kyc", headers=_auth(user["token"]), timeout=20)
        assert rk.status_code == 200
        assert rk.json().get("status") == "APPROVED"

        # Onramp quote should now return 200
        rq = requests.post(
            f"{BASE_URL}/api/ramp/onramp/quote",
            headers=_auth(user["token"]),
            json=ONRAMP_Q, timeout=20,
        )
        assert rq.status_code == 200, f"approved user got {rq.status_code}: {rq.text}"
        body = rq.json()
        assert "quote_id" in body or "id" in body

        # Transak widget-url should return 409 TRANSAK_KYB_PENDING (expected upstream state)
        rt = requests.post(
            f"{BASE_URL}/api/transak/widget-url",
            headers=_auth(user["token"]),
            json=TRANSAK_BODY, timeout=20,
        )
        # 409 expected, but accept 200 if KYB later approves; never 403 since KYC is APPROVED
        assert rt.status_code in (200, 409), f"approved user got {rt.status_code} from transak: {rt.text}"
        if rt.status_code == 409:
            assert "TRANSAK_KYB_PENDING" in str(rt.json().get("detail", ""))


class TestAdminBypass:
    def test_admin_can_call_onramp_quote(self):
        token = _admin_token()
        r = requests.post(
            f"{BASE_URL}/api/ramp/onramp/quote",
            headers=_auth(token),
            json=ONRAMP_Q, timeout=20,
        )
        # Critical: KYC gate must NOT block admin (403 means gate rejected).
        # Pricing/external failures may surface as 400/502; those are not gate-related.
        assert r.status_code != 403, f"admin should bypass KYC gate but got 403: {r.text}"
        # Best-effort: log non-200 for visibility
        if r.status_code != 200:
            print(f"NOTE: admin onramp/quote non-200 (upstream pricing): {r.status_code} {r.text}")


# ---------- Quick regression smoke ----------

class TestCaspRegression:
    def test_casp_dashboard(self):
        token = _admin_token()
        r = requests.get(f"{BASE_URL}/api/casp/dashboard", headers=_auth(token), timeout=20)
        assert r.status_code == 200

    def test_casp_audit_verify(self):
        token = _admin_token()
        r = requests.get(f"{BASE_URL}/api/casp/audit/verify", headers=_auth(token), timeout=20)
        assert r.status_code == 200

    def test_casp_sanctions_status(self):
        token = _admin_token()
        r = requests.get(f"{BASE_URL}/api/casp/sanctions/status", headers=_auth(token), timeout=20)
        assert r.status_code == 200

    def test_aml_screen_address(self):
        token = _admin_token()
        r = requests.post(
            f"{BASE_URL}/api/casp/aml/screen-address",
            headers=_auth(token),
            json={"address": "0x0000000000000000000000000000000000000000", "asset": "ETH", "chain": "ETH"},
            timeout=20,
        )
        assert r.status_code == 200
