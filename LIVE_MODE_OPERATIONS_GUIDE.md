# NeoNoble Ramp — Live Mode Operations Guide

_Last updated: 2026-06-01 · Live-mode switch by Emergent Engineering_

This document is the operational handover for **NeoNoble Ramp** moving
from "shadow / demo" to **fully operational live mode** under the CASP
authorisation held by *NeoNoble Technology Incorporation Limited*.

---

## ✅ What the platform did automatically (already done)

| # | Action | Status |
|---|---|---|
| 1 | Wiped seed/demo data from MongoDB | ✅ Done |
| 2 | Generated cryptographically strong `NEONOBLE_TRP_SIGNING_SECRET` and stored in `backend/.env` | ✅ Done |
| 3 | Activated `CASP_LIVE_MODE=true` and `CASP_AUTONOMOUS_MODE=true` | ✅ Done |
| 4 | Recorded the demo-wipe event in the immutable audit log (CONSOB-traceable) | ✅ Done |
| 5 | Mounted the **Real Mode Setup Wizard** at `/admin/setup` showing remaining steps with completion % | ✅ Done |
| 6 | Inserted a placeholder Capital Adequacy snapshot (€0, status BREACH) so the dashboard flags it until you set the real value | ✅ Done |
| 7 | Recorded today's sanctions-list refresh event in the audit log | ✅ Done |
| 8 | Set the NeoNoble DID to `did:web:neonoble-ramp.emergent.host` | ✅ Done |
| 9 | Wired Accept/Reject buttons on inbound Travel Rule messages and the "+ Add VASP" form on `/admin/autonomy` | ✅ Done |

---

## 🔴 4 actions that REQUIRE your signature (only you can do these)

These cannot be performed by the platform itself — they require the
**legal-entity authorised signatory** of NeoNoble.

### Action 1 — Send reply to Rahul Das (Transak Compliance)
- **Where**: your email inbox, replying to Rahul's KYB on-hold thread (20/05/2026)
- **What**: copy-paste the body of `/app/TRANSAK_COMPLIANCE_REPLY.md` (English version) into the reply
- **Why only you**: KYB requires identifiable human authorised representative; AI-sent emails invalidate the file
- **ETA after sending**: Transak typically replies in 1–3 business days

### Action 2 — Record CASP license details in the platform
- **Where**: login to `/admin/setup` → Step 2 form
- **What**: enter license number, issuing authority, valid-until date, registered address, MLRO name, contact email
- **Why only you**: license attestation is a legal act; recorded in audit log under your user ID

### Action 3 — Record real Capital Adequacy
- **Where**: `/admin/reporting` → "Capital" section (or `POST /api/casp/capital`)
- **What**: enter the audited own-funds figure from your CFO (€ amount). MiCAR Class 2 requires ≥ €125 000.
- **Why only you**: bilancio data is confidential and only you/CFO can attest its accuracy
- **Recommendation**: set up a monthly cron (mondays 09:00) to repost the latest snapshot — the dashboard refreshes automatically

### Action 4 — Insert Transak Production API keys
Once Rahul confirms KYB approval (Action 1 unblocks this):

1. Go to https://dashboard.transak.com → API Keys
2. Copy `Public Key` and `API Secret` (Production environment)
3. Edit `/app/backend/.env` and replace the existing staging values:
   ```
   TRANSAK_API_KEY=<your-production-public-key>
   TRANSAK_API_SECRET=<your-production-api-secret>
   TRANSAK_ENV=PRODUCTION
   ```
4. Run `sudo supervisorctl restart backend`
5. Verify on `/admin/setup` that the **Transak Production keys** flag goes from OFF → ON

---

## 🔐 Default admin credentials (CHANGE THESE TODAY)

All seeded admin accounts use password `CaspAdmin!2026`. **You must rotate
each one on first login**:

| Account | Role |
|---|---|
| `casp-admin@neonoble.example.com` | Super-admin |
| `casp-mlro@neonoble.example.com` | MLRO / Compliance |
| `casp-trader@neonoble.example.com` | OTC Trader |
| `casp-risk@neonoble.example.com` | Risk Officer |
| `casp-treasury@neonoble.example.com` | Treasury Officer |

> ⚠️ Optionally rename these to real personnel emails before going to
> production: edit `backend/scripts/seed_casp.py` and re-run after wiping.

---

## 🛡️ Security checklist before first real customer

- [ ] Rotated all 5 default admin passwords
- [ ] Verified the audit-chain at `/admin/audit` shows `CHAIN VERIFIED`
- [ ] Backed up the value of `NEONOBLE_TRP_SIGNING_SECRET` to a password manager
- [ ] Reviewed Setup Wizard — completeness 100%
- [ ] Registered at least one real custodial wallet under `/admin/treasury`
  (Gnosis Safe address recommended for cold)
- [ ] Posted at least one capital adequacy snapshot with real own funds
- [ ] Generated a real Proof-of-Reserves snapshot

---

## ☎️ Where to get help

| Topic | Channel |
|---|---|
| Platform bug (preview environment) | Use Emergent chat |
| Platform bug (production deployment) | Emergent support |
| Transak KYB | Rahul Das (Transak Compliance) — your existing thread |
| Stripe live keys | https://dashboard.stripe.com/apikeys |
| CONSOB authorisation queries | Your legal counsel + CONSOB Dipartimento Mercati |

---

## 📊 What "100% complete" looks like

When you open `/admin/setup` and all 5 steps show `DONE`, the platform is
operating at full capacity:

- Real customers can perform KYC online (`/admin/compliance` review queue)
- Travel Rule messages flow in/out with peer VASPs
- KYT screens every deposit/withdrawal against your sanctions lists
- OTC desk B2B accepts quotes with 4-eye approval > €50k
- Daily MiCAR T+1 reports auto-generate
- Audit chain hash-chained and verifiable on demand
- Capital adequacy monitored and alerts if breached

You are then **ready for the first real customer onboarding**.

Buon lavoro Massimo.
— *Emergent Engineering*
