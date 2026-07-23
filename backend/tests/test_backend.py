"""End-to-end backend tests for NeoNoble Ramp - Option B auth hardening + webhooks + regressions."""
import os
import time
import json
import hmac
import hashlib
import base64
import uuid
import requests
import jwt as pyjwt
import pytest


# ---------- Auth: register / login / token shape ----------

class TestAuthRegisterLogin:
    def test_register_returns_access_refresh_legacy_token(self, api_client, base_url):
        email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
        r = api_client.post(
            f"{base_url}/api/auth/register",
            json={"email": email, "password": "TestPass123!", "role": "USER"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["success"] is True
        assert "access_token" in d and d["access_token"]
        assert "refresh_token" in d and d["refresh_token"]
        assert d.get("token") == d["access_token"], "legacy token alias must equal access_token"
        # Email is normalized to lowercase server-side (case-insensitive accounts)
        assert d["user"]["email"] == email.lower()
        assert d["user"]["role"] == "USER"

    def test_login_returns_access_refresh_legacy_token(self, api_client, base_url, user_account):
        r = api_client.post(
            f"{base_url}/api/auth/login",
            json={"email": user_account["email"], "password": user_account["password"]},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["access_token"] and d["refresh_token"]
        assert d["token"] == d["access_token"]
        assert d["user"]["email"] == user_account["email"].lower()

    def test_login_invalid_credentials(self, api_client, base_url, user_account):
        r = api_client.post(
            f"{base_url}/api/auth/login",
            json={"email": user_account["email"], "password": "wrongpass"},
        )
        assert r.status_code == 401

    def test_access_token_short_lived_15_min(self, user_account):
        # Decode without verification to inspect claims
        payload = pyjwt.decode(
            user_account["access_token"], options={"verify_signature": False}
        )
        ttl = payload["exp"] - payload["iat"]
        # Allow some slack: between 14 and 16 minutes
        assert 14 * 60 <= ttl <= 16 * 60, f"access token ttl={ttl}s, expected ~15min"
        assert payload.get("type", "access") == "access"

    def test_refresh_token_long_lived_7_days(self, user_account):
        payload = pyjwt.decode(
            user_account["refresh_token"], options={"verify_signature": False}
        )
        ttl = payload["exp"] - payload["iat"]
        # ~7 days = 604800s; allow tolerance
        assert 6 * 86400 <= ttl <= 8 * 86400, f"refresh token ttl={ttl}s, expected ~7d"
        assert payload.get("type") == "refresh"


# ---------- Auth: refresh endpoint ----------

class TestAuthRefresh:
    def test_refresh_with_valid_refresh_returns_new_pair(self, api_client, base_url, user_account):
        # JWT iat/exp use 1s resolution; sleep to guarantee distinct timestamps
        time.sleep(1.2)
        r = api_client.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": user_account["refresh_token"]},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["access_token"] and d["refresh_token"]
        # token rotation: new tokens must be different from originals
        assert d["access_token"] != user_account["access_token"]
        assert d["refresh_token"] != user_account["refresh_token"]
        # new access token should work on /me
        api_client.headers.update({"Authorization": f"Bearer {d['access_token']}"})
        me = api_client.get(f"{base_url}/api/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == user_account["email"].lower()

    def test_refresh_with_invalid_token_returns_401(self, api_client, base_url):
        r = api_client.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": "not.a.valid.jwt"},
        )
        assert r.status_code == 401

    def test_refresh_with_access_token_returns_401(self, api_client, base_url, user_account):
        # Passing the access token where a refresh token is expected must fail
        r = api_client.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": user_account["access_token"]},
        )
        assert r.status_code == 401


# ---------- Auth: /me ----------

class TestAuthMe:
    def test_me_with_access_token(self, base_url, user_account, user_authed_client):
        r = user_authed_client.get(f"{base_url}/api/auth/me")
        assert r.status_code == 200, r.text
        assert r.json()["email"] == user_account["email"].lower()

    def test_me_without_token(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/auth/me")
        assert r.status_code in (401, 403)


# ---------- Security headers ----------

class TestSecurityHeaders:
    def test_security_headers_on_health(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/health")
        assert r.status_code == 200
        h = r.headers
        assert h.get("X-Content-Type-Options") == "nosniff"
        assert h.get("X-Frame-Options") == "DENY"
        assert h.get("Referrer-Policy") == "no-referrer"
        assert "Permissions-Policy" in h and h["Permissions-Policy"]

    def test_security_headers_on_prices(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/ramp/prices")
        h = r.headers
        assert h.get("X-Content-Type-Options") == "nosniff"
        assert h.get("X-Frame-Options") == "DENY"


# ---------- Stripe webhook routing ----------

class TestStripeWebhook:
    def test_missing_signature_returns_400(self, api_client, base_url):
        r = api_client.post(
            f"{base_url}/api/webhooks/stripe",
            data="{}",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400, r.text
        # 404 would mean route not mounted - explicitly check it's NOT a 404
        assert r.status_code != 404
        body = r.json()
        # FastAPI default error envelope uses 'detail'
        assert "Missing Stripe-Signature" in (body.get("detail") or "")

    def test_bogus_signature_route_mounted_graceful(self, api_client, base_url):
        r = api_client.post(
            f"{base_url}/api/webhooks/stripe",
            data='{"id":"evt_test","type":"payout.paid"}',
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=0,v1=bogus",
            },
        )
        # Route is mounted (not 404) and handles gracefully
        assert r.status_code != 404
        # Per implementation: returns 200 with status=error when signature can't be verified
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("status") == "error"


# ---------- Regression: ramp endpoints ----------

class TestRampRegression:
    def test_prices_endpoint_returns_neno_10000(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/ramp/prices")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "prices" in d
        prices = d["prices"]
        assert "NENO" in prices
        # NENO is fixed at 10,000 EUR
        assert float(prices["NENO"]) == 10000.0

    def test_user_onramp_quote_with_auth(self, base_url, dev_authed_client):
        # Note: USER role now requires APPROVED KYC; DEVELOPER bypasses for API testing.
        r = dev_authed_client.post(
            f"{base_url}/api/ramp/onramp/quote",
            json={"fiat_amount": 100.0, "crypto_currency": "NENO"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("quote_id") or d.get("id")
        # Should compute ~0.01 NENO for 100 EUR (NENO=10000)
        crypto_amt = d.get("crypto_amount")
        assert crypto_amt is not None and float(crypto_amt) > 0

    def test_user_offramp_quote_returns_deposit_address_for_neno(self, base_url, dev_authed_client):
        # Note: USER role now requires APPROVED KYC; DEVELOPER bypasses for API testing.
        r = dev_authed_client.post(
            f"{base_url}/api/ramp/offramp/quote",
            json={"crypto_amount": 0.5, "crypto_currency": "NENO"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # NENO offramp quote should embed a deposit_address (HD wallet may or may not be configured)
        # If wallet isn't configured, accept absence but warn via xfail-style soft check.
        deposit_address = d.get("deposit_address")
        if deposit_address is None:
            pytest.skip(
                "deposit_address not returned - HD wallet (NENO_WALLET_MNEMONIC) likely not configured"
            )
        assert isinstance(deposit_address, str) and len(deposit_address) > 0


# ---------- HMAC-protected platform routes ----------

def _hmac_sign(timestamp: str, body_json: str, secret: str) -> str:
    msg = f"{timestamp}{body_json}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


class TestHmacProtectedRoutes:
    @pytest.fixture
    def platform_key(self, base_url, dev_authed_client):
        r = dev_authed_client.post(
            f"{base_url}/api/dev/api-keys",
            json={"name": f"TEST_{uuid.uuid4().hex[:6]}"},
        )
        assert r.status_code == 200, r.text
        return r.json()  # contains api_key and api_secret

    def test_hmac_onramp_quote_valid_signature(self, api_client, base_url, platform_key):
        api_key = platform_key["api_key"]
        api_secret = platform_key["api_secret"]
        body = {"fiat_amount": 100.0, "crypto_currency": "NENO"}
        body_json = json.dumps(body, separators=(",", ":"))
        ts = str(int(time.time()))
        sig = _hmac_sign(ts, body_json, api_secret)
        r = requests.post(
            f"{base_url}/api/ramp-api-onramp-quote",
            data=body_json,
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": api_key,
                "X-TIMESTAMP": ts,
                "X-SIGNATURE": sig,
            },
            timeout=20,
        )
        assert r.status_code == 200, f"HMAC onramp quote failed: {r.status_code} {r.text}"
        d = r.json()
        assert float(d["crypto_amount"]) > 0

    def test_hmac_bad_signature_returns_401(self, api_client, base_url, platform_key):
        body = {"fiat_amount": 100.0, "crypto_currency": "NENO"}
        body_json = json.dumps(body, separators=(",", ":"))
        ts = str(int(time.time()))
        r = requests.post(
            f"{base_url}/api/ramp-api-onramp-quote",
            data=body_json,
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": platform_key["api_key"],
                "X-TIMESTAMP": ts,
                "X-SIGNATURE": "deadbeef",
            },
            timeout=20,
        )
        assert r.status_code == 401

    def test_hmac_missing_headers_returns_401(self, api_client, base_url):
        r = requests.post(
            f"{base_url}/api/ramp-api-onramp-quote",
            json={"fiat_amount": 100.0, "crypto_currency": "NENO"},
            timeout=20,
        )
        assert r.status_code == 401


# ---------- Dev portal CRUD (registered DEVELOPER required) ----------

class TestDevPortalKeys:
    def test_create_list_revoke_key(self, base_url, dev_authed_client):
        # CREATE
        r = dev_authed_client.post(
            f"{base_url}/api/dev/api-keys",
            json={"name": f"TEST_{uuid.uuid4().hex[:6]}"},
        )
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["api_key"] and created["api_secret"]
        key_id = created["id"]

        # LIST
        r = dev_authed_client.get(f"{base_url}/api/dev/api-keys")
        assert r.status_code == 200
        keys = r.json()
        assert any(k["id"] == key_id for k in keys)

        # REVOKE
        r = dev_authed_client.delete(f"{base_url}/api/dev/api-keys/{key_id}")
        assert r.status_code == 200

    def test_dev_portal_requires_developer_role(self, base_url, user_authed_client):
        r = user_authed_client.get(f"{base_url}/api/dev/api-keys")
        # USER role must be forbidden from dev portal
        assert r.status_code in (401, 403)
