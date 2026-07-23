# Test Credentials

Tests register ephemeral users dynamically — no persistent seeded account is required.

## How tests create users
- Email: `TEST_<uuid>@example.com` (unique per run)
- Password: `TestPass123!`
- Role: `USER` or `DEVELOPER`

## CASP back-office accounts (seeded by `backend/scripts/seed_casp.py`)
All passwords: **`CaspAdmin!2026`** — **rotate before going to real production!**

| Email | Base role | CASP roles | Department |
|---|---|---|---|
| `casp-admin@neonoble.example.com` | ADMIN | ADMIN (all) | Executive |
| `casp-mlro@neonoble.example.com` | ADMIN | MLRO, COMPLIANCE_OFFICER | Compliance |
| `casp-trader@neonoble.example.com` | ADMIN | OTC_TRADER | Trading |
| `casp-risk@neonoble.example.com` | ADMIN | RISK_OFFICER | Risk |
| `casp-treasury@neonoble.example.com` | ADMIN | TREASURY_OFFICER | Treasury |

Login → navigate to `/admin` (Dashboard) or `/admin/setup` (Setup Wizard).

## Live-mode env flags (already set in `backend/.env`)
```
CASP_LIVE_MODE=true
CASP_AUTONOMOUS_MODE=true
NEONOBLE_TRP_SIGNING_SECRET=<rotated 2026-06-01>
NEONOBLE_VASP_DID=did:web:neonoble-ramp.emergent.host
```

## Manual smoke account
```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2 | tr -d '"')
curl -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@neonoble.example.com","password":"TestPass123!","role":"DEVELOPER"}'
```

## External integrations not yet configured (require user action)
- `TRANSAK_API_KEY` / `TRANSAK_API_SECRET` (Production) — pending Rahul Das KYB approval. **Developer/staging key now active** (`e2bec76f-…`) with `TRANSAK_ENVIRONMENT=STAGING`.
- `STRIPE_SECRET_KEY` (live `sk_live_…`) — **configured 2026-06-01** ✅
- `STRIPE_WEBHOOK_SECRET` — pending (run `stripe listen` in your terminal to obtain `whsec_…`)
- `RESEND_API_KEY` — **configured** ✅ (domain `neonoble-ramp.com` verified per user)

## Re-seed CASP if needed
```bash
cd /app/backend && python scripts/seed_casp.py     # recreate admin accounts + sample data
cd /app/backend && python scripts/wipe_casp_demo.py # remove all demo records (keeps admins + audit log)
```
