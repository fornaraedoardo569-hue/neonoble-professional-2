#!/usr/bin/env python3
"""Full integrity test — KYC gating, password reset, Transak, CASP, audit."""
from __future__ import annotations
import json, os, sys, time, uuid, base64, requests
from datetime import datetime, timezone

API = "http://localhost:8001/api"
G, R, Y, X = "\033[92m", "\033[91m", "\033[93m", "\033[0m"

p, f, results = 0, 0, []
def ok(name, cond, extra=""):
    global p, f
    if cond: p += 1; print(f"  [{G}OK{X}]  {name:<60} {extra}")
    else:    f += 1; print(f"  [{R}FAIL{X}] {name:<60} {extra}")
    results.append({"name": name, "ok": cond, "extra": extra})

def call(method, path, token=None, body=None, params=None):
    h = {}
    if token: h["Authorization"] = f"Bearer {token}"
    if body is not None: h["Content-Type"] = "application/json"
    r = requests.request(method, f"{API}{path}", json=body, params=params, headers=h, timeout=15)
    try: return r.status_code, r.json()
    except: return r.status_code, r.text

# ─── 1. Password reset full cycle ─────────────────────────────────────────
print(f"\n{Y}━━━ 1. Password Reset Flow ━━━{X}")
email = f"pwd_{uuid.uuid4().hex[:8]}@example.com"
P1, P2 = "FirstPass1!", "SecondPass2!"
sc, _ = call("POST", "/auth/register", body={"email": email, "password": P1, "role": "USER"})
ok("register user", sc == 200)
sc, _ = call("POST", "/auth/forgot-password", body={"email": email})
ok("forgot-password returns 200 (no enumeration)", sc == 200)

# Get the token directly from auth_service for testing
sys.path.insert(0, '/app/backend')
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from services.auth_service import AuthService
async def get_reset_token():
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ['DB_NAME']]
    a = AuthService(db)
    r = await a.issue_password_reset_token(email)
    c.close()
    return r[0] if r else None
reset_token = asyncio.run(get_reset_token())
ok("reset token issued", bool(reset_token))

sc, _ = call("POST", "/auth/reset-password", body={"token": reset_token, "new_password": P2})
ok("reset-password with valid token", sc == 200)
sc, d = call("POST", "/auth/login", body={"email": email, "password": P1})
ok("old password rejected", sc == 401, f"code={sc}")
sc, login_data = call("POST", "/auth/login", body={"email": email, "password": P2})
ok("new password accepted", sc == 200)
user_token = login_data.get("access_token")
sc, _ = call("POST", "/auth/reset-password", body={"token": reset_token, "new_password": "x"})
ok("reset token cannot be reused", sc == 400)
sc, _ = call("POST", "/auth/reset-password", body={"token": "fake.invalid.token", "new_password": "x"})
ok("invalid reset token rejected", sc == 400)
sc, _ = call("POST", "/auth/change-password", token=user_token,
              body={"current_password": P2, "new_password": "ThirdPass3!"})
ok("change-password (authed)", sc == 200)
sc, _ = call("POST", "/auth/change-password", token=user_token,
              body={"current_password": "WRONG", "new_password": "Bla123!"})
ok("change-password rejects wrong current", sc == 400)
# Restore P2 for later tests
sc, login_data = call("POST", "/auth/login", body={"email": email, "password": "ThirdPass3!"})
user_token = login_data.get("access_token")
user_id = login_data.get("user", {}).get("id")

def detail_of(body):
    if isinstance(body, dict):
        d = body.get("detail")
        if isinstance(d, dict):
            return d
        return {"detail": d}
    return {"raw": str(body)[:80]}

# ─── 2. KYC gate on transaction endpoints ─────────────────────────────────
print(f"\n{Y}━━━ 2. KYC Gate Enforcement ━━━{X}")
# Customer has NO KYC yet — every transaction endpoint must 403
sc, body = call("POST", "/ramp/onramp/quote", token=user_token,
                body={"fiat_amount": 100, "crypto_currency": "BTC"})
ok("ramp/onramp/quote blocked without KYC", sc == 403,
   f"d={detail_of(body)}")

sc, body = call("POST", "/ramp/offramp/quote", token=user_token,
                body={"crypto_amount": 0.001, "crypto_currency": "BTC"})
ok("ramp/offramp/quote blocked without KYC", sc == 403)

sc, body = call("POST", "/ramp/onramp/execute", token=user_token,
                body={"quote_id": "fake", "wallet_address": "0xabc"})
ok("ramp/onramp/execute blocked without KYC", sc == 403)

sc, body = call("POST", "/ramp/offramp/execute", token=user_token,
                body={"quote_id": "fake", "bank_account": "IT00..."})
ok("ramp/offramp/execute blocked without KYC", sc == 403)

sc, body = call("POST", "/transak/widget-url", token=user_token,
                body={"productsAvailed":"BUY","cryptoCurrencyCode":"USDC","network":"bsc",
                      "walletAddress":"0xAaBb1234567890AaBb1234567890AaBb12345678",
                      "referrerDomain":"test.example.com"})
ok("transak/widget-url blocked without KYC", sc == 403)

# Unauthenticated calls — must 401, not 403
sc, _ = call("POST", "/ramp/onramp/quote", body={"fiat_amount": 100, "crypto_currency": "BTC"})
ok("ramp/onramp/quote unauthed → 401", sc == 401)

# ─── 3. Customer completes KYC self-service ───────────────────────────────
print(f"\n{Y}━━━ 3. Self-service KYC Onboarding ━━━{X}")
sc, mykyc = call("GET", "/onboarding/my-kyc", token=user_token)
ok("GET /onboarding/my-kyc NOT_STARTED", sc == 200 and mykyc.get("status") == "NOT_STARTED")

sc, started = call("POST", "/onboarding/kyc/start", token=user_token,
                   body={"full_name": "Test Customer", "date_of_birth": "1990-01-01",
                         "nationality": "IT", "country_of_residence": "IT",
                         "document_type": "PASSPORT"})
kyc_id = started.get("kyc_id")
ok("start KYC", sc == 200 and bool(kyc_id))

b64doc = base64.b64encode(b"test-doc-content-XYZ").decode()
for dt in ("ID_FRONT", "SELFIE"):
    sc, _ = call("POST", "/onboarding/kyc/document", token=user_token,
                 body={"doc_type": dt, "document_b64": b64doc, "mime": "image/jpeg"})
    ok(f"upload {dt}", sc == 200)

sc, mykyc = call("GET", "/onboarding/my-kyc", token=user_token)
ok("KYC now IN_REVIEW", sc == 200 and mykyc.get("status") == "IN_REVIEW")

# ─── 4. After KYC start (IN_REVIEW), transactions still blocked ───────────
print(f"\n{Y}━━━ 4. KYC Gate Still Blocks During IN_REVIEW ━━━{X}")
sc, body = call("POST", "/ramp/onramp/quote", token=user_token,
                body={"fiat_amount": 100, "crypto_currency": "BTC"})
ok("onramp/quote blocked while IN_REVIEW", sc == 403,
   f"d={detail_of(body)}")

# ─── 5. MLRO approves → customer can transact ────────────────────────────
print(f"\n{Y}━━━ 5. After MLRO Approval ━━━{X}")
sc, adm = call("POST", "/auth/login", body={"email": "casp-mlro@neonoble.example.com", "password": "CaspAdmin!2026"})
mlro_token = adm.get("access_token")
sc, _ = call("POST", f"/casp/kyc/{kyc_id}/decision", token=mlro_token,
             body={"decision": "APPROVE", "reason": "All docs verified"})
ok("MLRO approves KYC", sc == 200)

sc, mykyc = call("GET", "/onboarding/my-kyc", token=user_token)
ok("Customer sees APPROVED", sc == 200 and mykyc.get("status") == "APPROVED")

# Now transactions should pass through the gate
sc, quote = call("POST", "/ramp/onramp/quote", token=user_token,
                 body={"fiat_amount": 100, "crypto_currency": "BTC"})
ok("ramp/onramp/quote now allowed", sc == 200,
   f"quote_id={quote.get('quote_id','')[:8] if isinstance(quote,dict) else 'n/a'}")

# transak widget-url — bypasses gate but Transak still 409 (KYB pending)
sc, body = call("POST", "/transak/widget-url", token=user_token,
                body={"productsAvailed":"BUY","cryptoCurrencyCode":"USDC","network":"bsc",
                      "walletAddress":"0xAaBb1234567890AaBb1234567890AaBb12345678",
                      "referrerDomain":"test.example.com"})
ok("transak/widget-url now reaches upstream (409 KYB pending expected)",
   sc == 409, f"detail_starts={str(body.get('detail',''))[:40]}")

# ─── 6. ADMIN/DEVELOPER bypass ────────────────────────────────────────────
print(f"\n{Y}━━━ 6. ADMIN/DEVELOPER Bypass ━━━{X}")
sc, body = call("POST", "/ramp/onramp/quote", token=mlro_token,
                body={"fiat_amount": 50, "crypto_currency": "ETH"})
ok("ADMIN bypasses KYC gate", sc == 200,
   f"quote_id={body.get('quote_id','')[:8] if isinstance(body,dict) and body.get('quote_id') else 'n/a'}")

# ─── 7. CASP regression: dashboard / audit / 4-eye still work ─────────────
print(f"\n{Y}━━━ 7. CASP Regression ━━━{X}")
sc, _ = call("GET", "/casp/dashboard", token=mlro_token)
ok("/casp/dashboard", sc == 200)
sc, av = call("GET", "/casp/audit/verify", token=mlro_token)
ok("audit hash-chain verified", sc == 200 and av.get("verified") is True,
   f"checked={av.get('checked')}")
sc, sanc = call("GET", "/casp/sanctions/status", token=mlro_token)
ok("sanctions/status", sc == 200 and sanc.get("ofac_crypto_addresses",0) >= 8)

# ─── Final ─────────────────────────────────────────────────────────────
total = p + f
print(f"\n{Y}━━━ FINAL ━━━{X}")
print(f"  {G}Passed:{X} {p}/{total}    {R}Failed:{X} {f}")
out = {"ran_at": datetime.now(timezone.utc).isoformat(), "total": total,
       "passed": p, "failed": f, "results": results}
os.makedirs("/app/test_reports", exist_ok=True)
with open("/app/test_reports/full_integrity.json", "w") as out_f:
    json.dump(out, out_f, indent=2, default=str)
sys.exit(0 if f == 0 else 1)
