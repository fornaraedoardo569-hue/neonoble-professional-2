# NeoNoble Ramp — Product Requirements Document

_Living document. Last updated: 2026-05 (iter_5 — CASP Sprint 1)_

## Original Problem Statement

Build a full-stack on/off-ramp platform for the **NeoNoble Ramp** product
(NeoNoble Technology Incorporation Limited):

- User authentication (email/password, JWT) for both the public Ramp app
  and a Dev Portal.
- Platform API key management (AES-256-GCM + HMAC-SHA256).
- Public Ramp API (on/off-ramp quotes + execution).
- Real-time pricing via CoinGecko, NENO token fixed at €10,000.
- 60-minute quote TTL with locking.
- Real BSC blockchain integration (per-quote BEP-20 deposit address +
  on-chain detection + Stripe SEPA payout).
- **Transak Widget STAGING integration** for UK compliance video.
- **PancakeSwap V2 on-chain swap** for the custom NENO token.
- **CASP Operating Stack (new)** — full 7-block MiCAR back-office to
  prepare CONSOB authorisation while staying compliant via Transak / PancakeSwap
  in shadow mode. Sumsub / Chainalysis / Fireblocks / Notabene integrated via
  swappable adapter pattern (MOCK by default, LIVE flag per provider).

## Architecture (current)

- **Frontend**: React + Tailwind. Silent-refresh axios. Custom hooks +
  small components. Ethers v6 for on-chain calls.
- **Backend**: FastAPI + Motor (async MongoDB). Resend for email.
- **Auth**: JWT — 15 min access + 7 day refresh in `localStorage`.
  Case-insensitive email throughout. Single-use password reset via JWT
  with persisted `jti` on user doc. Welcome + reset emails via Resend
  with console-fallback. See `SECURITY.md`.
- **Blockchain**: web3.py polling on BSC (server-side, NeoNoble internal
  flow). On-chain swap via ethers + window.ethereum (client-side,
  PancakeSwap flow).
- **Stripe**: webhook mounted at `/api/webhooks/stripe`. Live keys
  pending.
- **Transak**: `@transak/ui-js-sdk` v2 against `global-stg.transak.com`.
  Partner staging key configured. Server-to-server webhook with
  HMAC-SHA256 verification at `/api/transak/webhook`.

## Implemented (✅)

### Iteration 1 (auth hardening)
- 15-min access + 7-day refresh + `/auth/refresh` rotation
- Silent refresh interceptor
- Security response headers middleware
- `/api/webhooks/stripe` registered

### Iteration 2 (Transak STAGING base)
- `useWallet`, `WalletConnect`, `ComplianceBanner`, `TransakLauncher`
- Public `/transak` page (3 pillars + 3 CTAs + event stream)
- `TRANSAK_DEMO_WALKTHROUGH.md` + `_IT.md`

### Iteration 3 (P0 case-sensitivity + password flows)
- **P0 bug fix**: email case-insensitivity (`_normalize_email`) + null
  guard in register auto-login. Migration script normalised 63 users.
- `/forgot-password`, `/reset-password`, `/change-password` endpoints + pages
- Welcome email on register
- Resend integration with console fallback when no API key
- 24h reset token TTL, single-use via persisted `jti`
- `AuthShell` component, login `Forgot your password?` link,
  dashboard `Change Password` nav

### Iteration 4 (Transak partner key + PancakeSwap + Enterprise OTC)
- **Transak partner staging key** wired in `.env`; API secret kept
  server-side for webhook verification
- **Transak server-to-server webhook** `POST /api/transak/webhook` with
  HMAC-SHA256 verification accepting `x-signature`, `transak-signature`,
  or `x-transak-signature` headers (both `sha256=<hex>` and raw hex
  formats). Always returns 200 to avoid probe enumeration; logs verified
  flag on persisted event.
- **8-token catalogue** quick-pick on `/transak` (USDC/USDT/BNB on BSC,
  ETH and USDC on Ethereum, USDC and MATIC on Polygon, BTC on Bitcoin),
  with a clear "Add Custom Token" hint pointing to the Transak Partner
  Dashboard for NENO and other unlisted tokens.
- **PancakeSwap V2 on-chain swap** UI at the bottom of `/transak`:
  USDC ↔ NENO, debounced quote via `getAmountsOut`, slippage presets
  (0.5%/1%/3%), allowance handling, balance pre-check, BscScan tx link.
  Fully non-custodial — every tx is signed by user's wallet.
- **Enterprise OTC banner** on internal `/dashboard` separating the
  NeoNoble fixed-price OTC desk from the non-custodial Transak ramp.
- Resend API key configured (welcome + reset emails go out live).
- `TRANSAK_SUPPORTS_NENO=false` flag — flip to `true` after Transak's
  Asset Listing approval, and NENO appears automatically in the picker.

### Iteration 5 (CASP Operating Stack Sprint 1, 2026-05-31)
- **CASP back-office at `/admin/*`** — 9-section console (Dashboard,
  KYC/KYB, AML & Alerts, Treasury, OTC Desk B2B, Reporting, Customer
  Protection, Governance, Audit Log) gated by base role `ADMIN` +
  CASP role claims (`casp_admin_users` collection).
- **All 7 MiCAR operational blocks** wired end-to-end with REST API
  (`/api/casp/*`) and React UI (`/app/frontend/src/pages/Admin.js`):
  Block 1 KYC/KYB/Risk/Sanctions • Block 2 AML/Travel-Rule/SAR •
  Block 3 Custody/Reconciliation/Proof-of-Reserves • Block 4 B2B OTC
  desk with **4-eye approval > €50k** + best-execution evidence •
  Block 5 Reporting + Capital Adequacy snapshots • Block 6 Complaints
  (15-day SLA) + Asset Disclosures • Block 7 RBAC + Operational
  Incidents (DORA) + Conflicts of Interest.
- **Provider adapter pattern** in `services/casp/`: Sumsub (KYC),
  Chainalysis (KYT), Fireblocks (MPC custody), Notabene (Travel Rule).
- **Immutable WORM audit log** (`casp_audit_log`) — SHA-256 hash-chained,
  monotonic `sequence` index, `/api/casp/audit/verify` replays chain.
- **CASP RBAC** with 7 roles + 7 pre-built FastAPI dependencies.
- **Seed script** `backend/scripts/seed_casp.py` (idempotent) with
  5 admin users + 6 retail + 1 B2B institutional client.
- **CONSOB technical brief** at `/app/CASP_CONSOB_BRIEF.md` (EN + IT).
- Testing: 36/36 pytest + 6/6 frontend (iteration_5.json).

## Iteration 6 (CASP Autonomous Mode, 2026-05-31)
- **`CASP_AUTONOMOUS_MODE=true`** flag (default ON) — the CaspService
  factory selects in-house adapters under `services/casp/internal/`
  instead of Sumsub / Chainalysis / Fireblocks / Notabene.
- **4 in-house adapters** replacing vendors 1-for-1 via interface
  inheritance from `services/casp/base.py`:
  * `internal/kyc_adapter.py` — document upload to MongoDB + manual MLRO
    review queue + name-based sanctions pre-screen
  * `internal/kyt_adapter.py` — bundled OFAC SDN crypto blacklist + known
    mixer set (Tornado Cash, Blender, ChipMixer, Garantex) + 1-hop
    counterparty check + wallet-age/volume heuristics via free BscScan /
    Etherscan API
  * `internal/custody_adapter.py` — reuses existing HD wallet (BIP44) for
    address derivation + on-chain Gnosis Safe multi-sig + intent-record-
    then-external-sign workflow
  * `internal/trp_adapter.py` — IVMS-101 v1.0.1 open standard over HTTPS
    with HMAC-SHA256, internal `casp_vasp_directory` for bilateral peer
    onboarding
- **New endpoints**: `POST /api/casp/kyc/{id}/documents` (upload),
  `GET /api/casp/sanctions/status`, `POST /api/casp/sanctions/refresh`,
  `GET/POST /api/casp/trp/vasps`, `GET/POST /api/casp/trp/inbox`
  (inbound endpoint open, HMAC-verified against per-VASP shared secret).
- **Bundled sanctions list** in `internal/sanctions_data.py` —
  8 OFAC-sanctioned crypto addresses (Tornado Cash, Blender, Garantex,
  ChipMixer), 2 known mixer contracts, 4 sanctioned individuals (sample
  for demo; full lists are public CSV/XML and can be refreshed daily).
- **Admin Console gets an "Autonomy" page** with live KYT tester,
  sanctions counts, VASP directory and TRP inbox views.
- **CONSOB brief Section 5** rewritten to document the autonomous mode
  as the primary operational configuration (vendors marked OPTIONAL).
- Test: 36/36 pytest still green in autonomous mode + manual E2E shows
  Tornado Cash → `risk_score: 100, is_critical: true, categories: [sanctions]`,
  inbound TRP HMAC verification works, audit chain 43 entries verified.

### Iteration 10 (Assistente AI Claude, 2026-07-22)
- **Anthropic claude-sonnet-4-6** via Emergent Universal Key
  (`emergentintegrations` + `EMERGENT_LLM_KEY` in backend/.env).
- **Backend `routes/chat.py`** — `/api/assistant/*`:
  * `POST /sessions` (context: dashboard|devportal|admin, role-gated)
  * `GET /sessions`, `GET /sessions/{id}/messages`
  * `POST /sessions/{id}/stream` — SSE streaming (X-Accel-Buffering: no),
    history ricostruita da MongoDB (`chat_sessions`, `chat_messages`,
    ultimi 30 msg) via `initial_messages`.
- **3 system prompt dedicati**: retail (KYC/NENO/Transak), dev (HMAC/API),
  admin (copilot compliance MiCAR 7 blocchi). Risponde nella lingua utente.
- **Frontend `components/assistant/AssistantWidget.jsx`** — FAB + pannello
  chat streaming, montato su Dashboard, DevPortal e Admin back-office.
  Session-id persistito in localStorage per contesto; pulsante new-chat.
- **Verificato E2E**: login → widget → invio → SSE → messaggi persistiti.
  ⚠️ La risposta LLM è bloccata da **budget Universal Key esaurito**
  (43.00/43.00 $) — l'utente deve ricaricare da Profile → Universal Key.
  L'errore degrada con messaggio pulito nel widget.

### Iteration 9 (current — Transak iframe modal + Start Trading workflow, 2026-07-21)
- **New `TransakIframeModal` component** (`components/transak/TransakIframeModal.jsx`):
  responsive Dialog + `<iframe>` (not popup) hosting the Transak widget.
  Handles postMessage events from the widget origin (production/staging
  auto-detected), records events server-side via `transakApi.logEvent()`,
  auto-closes on TRANSAK_ORDER_SUCCESSFUL / CANCELLED / WIDGET_CLOSE.
- **New `StartTradingCard`** on the Dashboard replaces `RetailRampCTA`:
  3 CTAs (Buy / Sell / Swap) that open the iframe modal in-place — no
  redirect, no popup. KYC-gated (ADMIN/DEVELOPER bypass).
- **New `TransakSandboxCard`** on the Developer Portal (`/dev`): shows
  the request payload for `/api/transak/widget-url`, copyable NENO
  contract, wallet-address input, and 3 launch buttons for BUY/SELL/SWAP.
- **Backend widget-url schema** now accepts `cryptoCurrencyAddress`,
  `cryptoCurrencyList`, `fiatAmount`. When `cryptoCurrencyCode='NENO'`,
  the service **automatically injects** the canonical BSC contract
  `0xeF3F5C1892A8d7A3304E4A15959E124402d69974` and forces `network='bsc'`
  + `defaultFiatCurrency='EUR'` / `fiatCurrency='EUR'`. Prunes empty
  values before hitting Transak.
- **Widget params guaranteed** (per user spec):
  * `apiKey` — server-controlled (env)
  * `referrerDomain` — server-controlled (host)
  * `cryptoCurrencyCode='NENO'` — from frontend
  * `cryptoCurrencyAddress='0xeF3F...9974'` — server-injected for NENO
  * `network='bsc'` — server-forced for NENO
  * `fiatCurrency='EUR'` + `defaultFiatCurrency='EUR'` — server default
  * `themeColor='7c3aed'`, `hideMenu='true'`, `disableWalletAddressForm='true'`
- **Verified E2E**: Playwright click on Buy → modal opens → backend
  called → 409 KYB_PENDING → clean error UX with Close button.
  When Transak KYB is approved, the same code path renders the actual
  iframe with the NENO buy flow — zero further changes needed.
- **Tests**: `pytest backend/tests/` still `119 passed, 1 skipped, 0 failed`
  (Transak + KYC gate suites re-verified: 33 passed / 1 skipped).

## Iteration 8 (KYC server-side enforcement + integrity hardening, 2026-06-02) (`middleware/kyc_gate.py`) enforced on ALL
  retail transaction endpoints:
  * `POST /api/ramp/onramp/quote`
  * `POST /api/ramp/onramp/execute`
  * `POST /api/ramp/offramp/quote`
  * `POST /api/ramp/offramp/execute`
  * `POST /api/transak/widget-url`
- **Status codes**:
  * `401` if no/invalid token
  * `403` with structured detail `{error: 'kyc_required', kyc_status: 'NOT_STARTED|IN_REVIEW|REJECTED|ON_HOLD', message: '...'}` if KYC not APPROVED
  * `200` (or 409 TRANSAK_KYB_PENDING for widget) if APPROVED
- **ADMIN/DEVELOPER roles bypass** the gate (internal CASP operators
  + dev testing via DEVELOPER token).
- **Frontend axios interceptor** dispatches `neonoble:kyc-required`
  CustomEvent on 403; `App.js` global listener shows sonner toast +
  auto-redirects to `/onboarding` after 1.5s — no per-page duplication.
- **Dashboard Retail Ramp CTA** visually gates Buy/Sell/Swap cards (opacity-60
  + link to `/onboarding` instead of `/transak`) until KYC = APPROVED.
- **Transak Production validated**: refresh-token API works with the new
  `e2bec76f-…` Live key; widget session API returns `HTTP 409 TRANSAK_KYB_PENDING`
  (waiting on Rahul Das KYB approval). Backend now correctly classifies
  this state as 409 instead of bubbling up as 502.
- **Password reset flow integrity**: full audit performed — 30/30 manual
  + 14/14 pytest pass:
  * forgot-password returns generic message (no enumeration)
  * reset-password with valid token works (200)
  * old password rejected (401)
  * new password accepted (200)
  * reset token cannot be reused (400, single-use jti enforced)
  * invalid reset token rejected (400)
  * change-password works with correct current password
  * change-password rejects wrong current password (400)
- **Test suite final**: `pytest backend/tests/` → **119 passed, 1 skipped, 0 failed**.
- **Test data drift fixes**:
  * `test_transak.py` now accepts STAGING|PRODUCTION env values
  * `test_casp.py::test_transak_widget_url` now accepts 409 KYB-pending
  * `test_backend.py::test_user_*ramp_quote_*` now uses `dev_authed_client`
    (DEVELOPER bypasses KYC gate) to test the ramp endpoint logic itself

## Iteration 7 (First Customer Onboarding Flow + live keys, 2026-06-01)
- **Public self-service KYC flow** at `/onboarding` — protected route, 4-step
  stepper (Personal Info → ID Document → Selfie → Status) with retail-grade
  data-testid hooks for testing.
- **New backend endpoints** (all auth-required, no CASP role needed because
  the user acts on their own behalf):
  * `GET /api/onboarding/my-kyc` — returns the calling user's KYC status
  * `POST /api/onboarding/kyc/start` — initiate a `casp_kyc` record with
    personal info (full_name, DOB, nationality, country, document_type)
  * `POST /api/onboarding/kyc/document` — upload base64 documents
    (ID_FRONT, ID_BACK, SELFIE, POA) with size limit ~6 MB; transitions
    KYC status to IN_REVIEW
- **Dashboard banner** (`data-testid=kyc-onboarding-banner`) prompts the
  customer to complete KYC when status is NOT_STARTED / PENDING / IN_REVIEW
  / REJECTED / ON_HOLD, hides on APPROVED.
- **End-to-end loop** validated: customer submits → record appears in
  `/admin/compliance` MLRO queue → MLRO approves → status flows back to the
  customer's `/onboarding` page as APPROVED.
- **.env updates** (live mode):
  * `STRIPE_SECRET_KEY=sk_live_...` + `STRIPE_PUBLISHABLE_KEY=pk_live_...`
  * `TRANSAK_API_KEY=e2bec76f-...` (developer/staging key) with
    `TRANSAK_ENVIRONMENT=STAGING` and `TRANSAK_ENV=STAGING` — production
    keys still blocked on Rahul Das (Transak compliance).
* Resend domain `neonoble-ramp.com` confirmed verified by the user;
  email delivery to arbitrary addresses now unblocked.
- Tests: 14/14 pytest in `backend/tests/test_onboarding.py` + Playwright
  smoke (banner shows, stepper navigates, redirect to /login when unauth).
  Regression confirmed for `/api/transak/widget-url`,
  `/api/casp/dashboard`, `/api/auth/login`.

## Iteration 6 (CASP Autonomous Mode, 2026-05-31)

## Backlog

### P0 — Pending external action
- 🚨 **Reply to Transak compliance (Rahul Das)** — copy-paste the email body
  from `/app/TRANSAK_COMPLIANCE_REPLY.md` (English version) into Rahul's
  thread of 20/05/2026 to lift the KYB "on hold" status (unlocks the
  production Transak key — staging now active).
- 🆔 **Submit NENO Asset Listing request** to Transak Partner Dashboard
  with contract `0xeF3F5C1892A8d7A3304E4A15959E124402d69974`.
- 🎬 **Record the Transak compliance video** locally using `/transak` +
  `TRANSAK_DEMO_WALKTHROUGH_IT.md` (cannot be done by the AI agent).
- 🔑 **Stripe webhook secret** (`whsec_…`) — get from Stripe CLI / dashboard
  and add to `.env` to verify webhook signatures (live keys already in `.env`).
- ✅ ~~Verify `neonoble-ramp.com` on Resend~~ — DONE 2026-06-01
- ✅ ~~Live Stripe keys~~ — DONE 2026-06-01
- 🤝 **CASP Sprint 2 — Sumsub onboarding**: provide partner API keys to
  flip Sumsub adapter to LIVE (`SUMSUB_LIVE=true` + tokens in `.env`).

### P1 — Scheduled
- 🍪 HttpOnly cookie auth migration (Option A) — next sprint.
- 🏊 **Provide initial liquidity** to a NENO/USDC PancakeSwap V2 pool on
  BSC mainnet so the swap UI returns actual quotes.
- 🔨 Refactor `execute_offramp`/`execute_onramp`/`process_deposit_received`
  in `services/ramp_service.py`.
- 🧪 **CASP Sprint 3** — Chainalysis KYT contract + live integration.
- 🏦 **CASP Sprint 4** — Fireblocks workspace provisioning + live custody.
- 🌐 **CASP Sprint 5** — Notabene Travel Rule live.
- 🪪 **Sub-admin base role** (`CASP_OPERATOR`) — to actually enforce
  CASP-role gating on specialists (today they are base=ADMIN per seed so
  super-admin bypass kicks in; the 4-eye guard is the real safety net but
  having proper role isolation is cleaner).

### P2 — Nice-to-haves
- Move Transak token catalogue to `.env` JSON (no redeploy)
- Admin endpoint listing all Transak webhook events
- Transak order-status push from webhook into user's notification panel
- 2FA TOTP for DEVELOPER + ADMIN roles
- Export audit log as a signed PDF (Adobe LTV/PAdES) for off-chain archival

## Files of Reference

```
/app/
├── backend/
│   ├── routes/        (auth, dev_portal, ramp_api, user_ramp, webhooks, transak)
│   ├── services/      (auth, api_key, ramp, pricing, wallet, blockchain_listener,
│   │                   stripe_payout, transak, email)
│   ├── utils/         (encryption, jwt_utils [+password_reset], password)
│   ├── tests/         (test_backend.py, test_transak.py, test_password_flows.py,
│   │                   conftest.py — 48 pytest tests, 1 expected skip)
│   ├── scripts/       (normalise_user_emails.py — idempotent, already ran)
│   └── server.py
├── frontend/
│   └── src/
│       ├── api/                 (index.js with silent refresh, transak.js)
│       ├── context/             (AuthContext.js)
│       ├── hooks/               (usePricing, useTransactions, useApiKeys,
│       │                         useWallet, use-toast)
│       ├── lib/                 (pancakeswap.js — ethers v6 swap helpers)
│       ├── components/
│       │   ├── auth/            (AuthShell)
│       │   ├── dashboard/       (PriceDisplay, TransactionList, RampPanel, …)
│       │   ├── devportal/       (StatsBar, CreateKeyForm, CreatedKeyModal, …)
│       │   └── transak/         (ComplianceBanner, WalletConnect,
│       │                         TransakLauncher, PancakeSwapPanel)
│       └── pages/               (Home, Login, Signup, Dashboard, DevLogin,
│                                 DevPortal, TransakDemo, ForgotPassword,
│                                 ResetPassword, ChangePassword)
├── memory/PRD.md
├── memory/test_credentials.md
├── SECURITY.md
├── TRANSAK_DEMO_WALKTHROUGH.md  + _IT.md
└── test_reports/
    ├── iteration_1.json   # 22/22 auth hardening
    ├── iteration_2.json   # 29/29 Transak STAGING
    ├── iteration_3.json   # 43/43 + 8/8 case-sensitivity + password reset
    └── iteration_4.json   # 48/48 webhook HMAC + PancakeSwap + Enterprise OTC
```

## Compliance pillar enforcement (Transak)

| Pillar | Where it's enforced |
|---|---|
| User-initiated Only | Buy/Sell/Swap buttons + PancakeSwap UI disabled until `wallet.address` is set. No backend endpoint creates a trade. |
| No Fund Intermediation | `/api/transak` only `GET /config` + `POST /events` + signed-only `POST /webhook`. No transfer/payout/order endpoint. |
| Direct Delivery | Widget URL built with `walletAddress=<user_addr>` + `disableWalletAddressForm=true`. PancakeSwap router invoked directly from user's wallet. |

## Tech-stack Notes

- MongoDB + Motor (user accepted, instead of PostgreSQL+Prisma).
- All authenticated routes use the `/api` prefix; bare-domain `/health`
  for Kubernetes liveness checks.
- Transak SDK: `@transak/ui-js-sdk` v2 — widget opened via popup window
  (NOT iframe) to bypass `frame-ancestors` for the staging preview URL.
- Ethers v6 for client-side on-chain calls.
- Resend v2.30.1 for transactional email.
