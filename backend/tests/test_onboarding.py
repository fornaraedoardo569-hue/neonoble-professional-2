"""Tests for customer onboarding (self-service KYC) flow.

Covers:
- GET /api/onboarding/my-kyc for fresh users (NOT_STARTED)
- POST /api/onboarding/kyc/start (creates record + persists personal info)
- POST /api/onboarding/kyc/document (validation, size limit, IN_REVIEW transition)
- Auth gating (401 when unauth)
- Cross-user isolation (user A cannot see user B's KYC)
- MLRO can see record in /api/casp/kyc?status=IN_REVIEW and decide
- Regression: /api/auth/login, /api/auth/me, /api/casp/dashboard, /api/transak/widget-url
"""
import base64
import os
import uuid
import pytest
import requests

ADMIN_PASSWORD = "CaspAdmin!2026"
MLRO_EMAIL = "casp-mlro@neonoble.example.com"


def _tiny_b64(size_bytes=2048):
    return base64.b64encode(b"x" * size_bytes).decode()


def _register(api_client, base_url, role="USER"):
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass123!"
    r = api_client.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "password": password, "role": role},
        timeout=20,
    )
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return {"email": email, "password": password, **r.json()}


# --- Module: onboarding endpoints ---

class TestOnboardingAuthGating:
    def test_my_kyc_requires_auth(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/onboarding/my-kyc", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code} {r.text}"

    def test_start_kyc_requires_auth(self, api_client, base_url):
        r = api_client.post(f"{base_url}/api/onboarding/kyc/start", json={
            "full_name": "X", "date_of_birth": "2000-01-01",
            "nationality": "IT", "country_of_residence": "IT",
        }, timeout=15)
        assert r.status_code in (401, 403)

    def test_upload_document_requires_auth(self, api_client, base_url):
        r = api_client.post(f"{base_url}/api/onboarding/kyc/document", json={
            "doc_type": "ID_FRONT", "document_b64": _tiny_b64(), "mime": "image/jpeg",
        }, timeout=15)
        assert r.status_code in (401, 403)


class TestOnboardingHappyPath:
    def test_fresh_user_not_started(self, user_authed_client, base_url):
        r = user_authed_client.get(f"{base_url}/api/onboarding/my-kyc", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("status") == "NOT_STARTED"

    def test_full_flow_start_upload_in_review(self, user_authed_client, base_url):
        payload = {
            "full_name": "Mario Rossi",
            "date_of_birth": "1990-05-15",
            "nationality": "IT",
            "country_of_residence": "IT",
            "document_type": "ID_CARD",
            "wallet_address": "0x" + "a" * 40,
        }
        start = user_authed_client.post(
            f"{base_url}/api/onboarding/kyc/start", json=payload, timeout=20
        )
        assert start.status_code == 200, start.text
        sdata = start.json()
        # service returns kyc_id and provider_applicant_id
        assert "kyc_id" in sdata or "id" in sdata, sdata
        kyc_id = sdata.get("kyc_id") or sdata.get("id")
        assert kyc_id

        # Upload ID_FRONT
        up = user_authed_client.post(
            f"{base_url}/api/onboarding/kyc/document",
            json={"doc_type": "ID_FRONT", "document_b64": _tiny_b64(), "mime": "image/jpeg"},
            timeout=20,
        )
        assert up.status_code == 200, up.text

        # Upload SELFIE
        up2 = user_authed_client.post(
            f"{base_url}/api/onboarding/kyc/document",
            json={"doc_type": "SELFIE", "document_b64": _tiny_b64(), "mime": "image/jpeg"},
            timeout=20,
        )
        assert up2.status_code == 200, up2.text

        # GET my-kyc should reflect new state + personal fields
        r = user_authed_client.get(f"{base_url}/api/onboarding/my-kyc", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") in ("IN_REVIEW", "PENDING"), data
        # personal info preserved
        assert data.get("full_name") == "Mario Rossi"
        assert data.get("nationality") == "IT"
        assert data.get("document_type") == "ID_CARD"

    def test_invalid_doc_type_400(self, user_authed_client, base_url):
        # First start
        user_authed_client.post(f"{base_url}/api/onboarding/kyc/start", json={
            "full_name": "A B", "date_of_birth": "1990-01-01",
            "nationality": "IT", "country_of_residence": "IT",
        }, timeout=20)
        r = user_authed_client.post(
            f"{base_url}/api/onboarding/kyc/document",
            json={"doc_type": "BOGUS", "document_b64": _tiny_b64(), "mime": "image/jpeg"},
            timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_oversized_document_413(self, user_authed_client, base_url):
        user_authed_client.post(f"{base_url}/api/onboarding/kyc/start", json={
            "full_name": "A B", "date_of_birth": "1990-01-01",
            "nationality": "IT", "country_of_residence": "IT",
        }, timeout=20)
        big = "a" * 8_000_001  # > 8MB threshold in route
        r = user_authed_client.post(
            f"{base_url}/api/onboarding/kyc/document",
            json={"doc_type": "ID_FRONT", "document_b64": big, "mime": "image/jpeg"},
            timeout=30,
        )
        assert r.status_code == 413, f"expected 413, got {r.status_code}"

    def test_upload_without_start_returns_400(self, user_authed_client, base_url):
        r = user_authed_client.post(
            f"{base_url}/api/onboarding/kyc/document",
            json={"doc_type": "ID_FRONT", "document_b64": _tiny_b64(), "mime": "image/jpeg"},
            timeout=15,
        )
        assert r.status_code == 400, r.text


class TestCrossUserIsolation:
    def test_user_b_cannot_see_user_a_kyc(self, api_client, base_url):
        # Register user A
        
        a = _register(api_client, base_url, role="USER")
        a_sess = requests.Session()
        a_sess.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {a['access_token']}",
        })
        a_sess.post(f"{base_url}/api/onboarding/kyc/start", json={
            "full_name": "Alice A", "date_of_birth": "1991-01-01",
            "nationality": "IT", "country_of_residence": "IT",
        }, timeout=20)

        # Register user B
        b = _register(api_client, base_url, role="USER")
        b_sess = requests.Session()
        b_sess.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {b['access_token']}",
        })
        r = b_sess.get(f"{base_url}/api/onboarding/my-kyc", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # User B is fresh: must NOT see Alice's record
        assert data.get("status") == "NOT_STARTED", data
        assert data.get("full_name") != "Alice A"


# --- Module: MLRO admin queue integration ---

class TestMLROCanSeeAndDecide:
    @pytest.fixture
    def mlro_token(self, api_client, base_url):
        r = api_client.post(f"{base_url}/api/auth/login", json={
            "email": MLRO_EMAIL, "password": ADMIN_PASSWORD,
        }, timeout=20)
        if r.status_code != 200:
            pytest.skip(f"MLRO login failed ({r.status_code}); seed_casp.py may not have run")
        return r.json()["access_token"]

    def test_submitted_kyc_appears_in_admin_queue_and_can_decide(
        self, api_client, base_url, mlro_token
    ):
        # 1. Customer submits via onboarding flow
        
        u = _register(api_client, base_url, role="USER")
        u_sess = requests.Session()
        u_sess.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {u['access_token']}",
        })
        start = u_sess.post(f"{base_url}/api/onboarding/kyc/start", json={
            "full_name": "Giulia Bianchi", "date_of_birth": "1988-03-22",
            "nationality": "IT", "country_of_residence": "IT",
            "document_type": "PASSPORT",
        }, timeout=20)
        assert start.status_code == 200, start.text
        kyc_id = start.json().get("kyc_id") or start.json().get("id")

        u_sess.post(f"{base_url}/api/onboarding/kyc/document", json={
            "doc_type": "ID_FRONT", "document_b64": _tiny_b64(), "mime": "image/jpeg",
        }, timeout=20)
        u_sess.post(f"{base_url}/api/onboarding/kyc/document", json={
            "doc_type": "SELFIE", "document_b64": _tiny_b64(), "mime": "image/jpeg",
        }, timeout=20)

        # 2. MLRO lists IN_REVIEW queue
        m_sess = requests.Session()
        m_sess.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {mlro_token}",
        })
        r = m_sess.get(f"{base_url}/api/casp/kyc", params={"status": "IN_REVIEW"}, timeout=20)
        assert r.status_code == 200, r.text
        listing = r.json()
        # Find our record
        rows = listing if isinstance(listing, list) else listing.get("items", [])
        match = [row for row in rows if row.get("id") == kyc_id or row.get("full_name") == "Giulia Bianchi"]
        assert match, f"Submitted KYC not found in IN_REVIEW queue. Got {len(rows)} rows."
        rec = match[0]
        # full_name + nationality preserved through admin queue
        assert rec.get("full_name") == "Giulia Bianchi"
        assert rec.get("nationality") == "IT"

        # 3. MLRO approves
        target_id = rec.get("id") or kyc_id
        d = m_sess.post(
            f"{base_url}/api/casp/kyc/{target_id}/decision",
            json={"decision": "APPROVE", "reason": "Documents verified"},
            timeout=20,
        )
        assert d.status_code in (200, 201), d.text

        # 4. Verify status changed for the user
        check = u_sess.get(f"{base_url}/api/onboarding/my-kyc", timeout=15)
        assert check.status_code == 200
        assert check.json().get("status") == "APPROVED"


# --- Module: regression of pre-existing endpoints ---

class TestRegression:
    def test_login_works(self, api_client, base_url, user_account):
        r = api_client.post(f"{base_url}/api/auth/login", json={
            "email": user_account["email"], "password": user_account["password"],
        }, timeout=20)
        assert r.status_code == 200, r.text
        assert "access_token" in r.json()

    def test_auth_me_works(self, user_authed_client, base_url):
        r = user_authed_client.get(f"{base_url}/api/auth/me", timeout=15)
        assert r.status_code == 200, r.text
        assert "email" in r.json()

    def test_casp_dashboard(self, api_client, base_url):
        login = api_client.post(f"{base_url}/api/auth/login", json={
            "email": MLRO_EMAIL, "password": ADMIN_PASSWORD,
        }, timeout=20)
        if login.status_code != 200:
            pytest.skip("MLRO login unavailable")
        token = login.json()["access_token"]
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        r = s.get(f"{base_url}/api/casp/dashboard", timeout=20)
        assert r.status_code == 200, r.text

    def test_transak_widget_url(self, user_authed_client, base_url):
        r = user_authed_client.get(
            f"{base_url}/api/transak/widget-url",
            params={"fiat_amount": 100, "fiat_currency": "EUR", "crypto_currency": "USDT"},
            timeout=20,
        )
        # accept 200 with widget url, or 400/422 if params differ — fail only on 500
        assert r.status_code < 500, f"transak endpoint 5xx: {r.status_code} {r.text}"
        if r.status_code == 200:
            data = r.json()
            assert any(k in data for k in ("widget_url", "url"))
