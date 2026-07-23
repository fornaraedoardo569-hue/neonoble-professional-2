# NeoNoble Ramp — Technical Brief for CONSOB CASP Authorisation

**Prepared in support of the application for CASP authorisation under**
**Regulation (EU) 2023/1114 (MiCAR), Title V, Article 60 et seq.**

Versione bilingue (EN principale, IT in appendice) — Maggio 2026.

---

## 1. Executive Summary

NeoNoble Ramp ("NeoNoble") has implemented, ahead of CASP authorisation, a
production-grade **CASP Operating Stack** comprising the seven operational
blocks required by MiCAR Title V and the corresponding RTS/ITS. The stack is
deployed in **shadow mode**: it is fully wired, runs against live business
data internally, and exposes every workflow that an authorised CASP must
demonstrate, while no fiat-on-ramp / fiat-off-ramp service is offered to
retail customers without an external licensed party (currently Transak — a
CASP-equivalent in transition).

This document describes the architecture, key controls, third-party providers,
and evidence trail that NeoNoble will rely on during the CONSOB / Banca
d'Italia authorisation procedure.

---

## 2. Scope of services intended under authorisation (MiCAR Art. 60)

| Service code (Art. 3(1)(16)) | Service | Initial scope |
|---|---|---|
| (a) | Custody and administration of crypto-assets on behalf of clients | YES — Block 3 |
| (b) | Operation of a trading platform for crypto-assets | NO (out of scope, v1) |
| (c) | Exchange of crypto-assets for funds | YES — OTC desk, B2B only (Block 4) |
| (d) | Exchange of crypto-assets for other crypto-assets | YES — OTC desk, B2B only (Block 4) |
| (e) | Execution of orders for crypto-assets on behalf of clients | YES — OTC desk (Block 4) |
| (f) | Placing of crypto-assets | NO (out of scope, v1) |
| (g) | Reception and transmission of orders | YES — B2B OTC (Block 4) |
| (h) | Advice on crypto-assets | NO |
| (i) | Portfolio management on crypto-assets | NO |
| (j) | Providing transfer services | YES — limited to MiCAR Art. 82, settlement only |

Capital adequacy class proposed: **Class 2 (€125,000)** under MiCAR Art. 67(1)(b).

---

## 3. Architecture overview

NeoNoble Ramp is a full-stack application:

- **Frontend** — React 19 + TailwindCSS, hosted on the same domain.
- **Backend** — FastAPI (Python 3.11) — RESTful API under `/api`.
- **Database** — MongoDB 7.x — single primary, daily snapshots.
- **Blockchain RPC** — BSC mainnet (`BSC_RPC_URL`) for read-only on-chain monitoring.

The CASP Operating Stack lives in `/app/backend/services/casp_service.py`
(orchestrator) and `/app/backend/services/casp/` (provider adapters).
The administrative back-office is at `/admin` and is restricted to users
with ADMIN base role + one or more CASP role claims (`casp_admin_users`
collection).

---

## 4. The seven operational blocks

### 4.1 Block 1 — Identity & Onboarding (MiCAR Art. 68, AMLD6)

| Control | Implementation |
|---|---|
| KYC retail (Tier 1/2/3) | `KycRecord` collection, Sumsub adapter (`services/casp/sumsub_adapter.py`) |
| KYB business | `KybRecord` collection with UBO list, LEI, NACE code |
| Sanctions / PEP screening | `SanctionsHit` collection (OFAC, EU, UN, UK_HMT) |
| Customer Risk Rating | `RiskRatingRecord` — score 0–100 → LOW/MED/HIGH/PROHIBITED |
| Tiered transaction limits | `RiskLimit` (per-asset, daily, monthly, kill-switch) |

Sumsub provides KYC liveness, document OCR, AML checks, ongoing monitoring.
Adapter switches to LIVE mode via `SUMSUB_LIVE=true` env flag.

### 4.2 Block 2 — Transaction Monitoring & AML

| Control | Implementation |
|---|---|
| Rule-based alerts | Velocity, structuring, geo-risk, threshold (€10k) |
| Blockchain analytics | Chainalysis KYT (`chainalysis_adapter.py`) for wallet & tx screening |
| Travel Rule (FATF R.16 / TFR) | Notabene (`notabene_adapter.py`) — outgoing/incoming flow per Reg. (EU) 2023/1113 |
| SAR generation | `SarRecord` → manual submission to UIF Italia (Banca d'Italia portal) |

### 4.3 Block 3 — Custody & Treasury (MiCAR Art. 75)

| Control | Implementation |
|---|---|
| Segregated wallets per client | `CustodialWallet.purpose = CUSTOMER_SEGREGATED` |
| MPC / multi-sig custody | Fireblocks (`fireblocks_adapter.py`) — 3-of-N policy on hot, 4-of-N on cold |
| Cold storage policy | ≥85% of asset value in `WalletKind = COLD` |
| Daily reconciliation | `ReconciliationRun` — on-chain vs internal ledger |
| Proof of Reserves | `ProofOfReserves` — Merkle root, published quarterly |

### 4.4 Block 4 — Order Management & Execution (Best Execution)

| Control | Implementation |
|---|---|
| OTC Desk B2B | `OtcQuoteB2B` collection — institutional flow only |
| 4-eye approval | Mandatory for any quote > **€50,000** (`OTC_APPROVAL_THRESHOLD_EUR`) |
| Best execution policy | Multi-venue mid-price check (Binance, Kraken, Coinbase) stored in `best_execution_evidence` |
| Pre-trade risk limits | `RiskLimit` checked before quote acceptance |
| Kill switch | `RiskLimit.kill_switch_active` halts new trading instantly |

### 4.5 Block 5 — Regulatory Reporting & Audit

| Control | Implementation |
|---|---|
| Immutable audit log (WORM) | `casp_audit_log` — SHA-256 hash-chained, monotonic `sequence` index, tamper-evident |
| MiCAR T+1 transaction reporting | `RegulatoryReport.report_type = MICAR_T_PLUS_1` — auto-generated daily |
| CONSOB quarterly returns | Reporting framework ready (`RegulatoryReport.report_type = CONSOB_QUARTERLY`) |
| Capital adequacy monitoring | `CapitalAdequacySnapshot` — daily own-funds vs requirement, COMPLIANT/WARNING/BREACH |

The audit chain can be verified anytime via `GET /api/casp/audit/verify` — replays every entry and returns the first break, if any. This satisfies the "evidence of integrity" expectation for ICT audits.

### 4.6 Block 6 — Customer Protection (MiCAR Art. 66 + Art. 71)

| Control | Implementation |
|---|---|
| Pre-contractual disclosure (whitepaper-equivalent) | `AssetDisclosure` per asset, versioned |
| Complaints procedure | `Complaint` — 15-day SLA enforced via `sla_deadline` |
| Escalation to financial ombudsman | Status `ESCALATED_OMBUDSMAN` recorded |
| Fee transparency | Public fee schedule published with each disclosure |

### 4.7 Block 7 — Internal Governance & RBAC

| Control | Implementation |
|---|---|
| Role-based access control | Six CASP roles: ADMIN / MLRO / COMPLIANCE_OFFICER / RISK_OFFICER / TREASURY_OFFICER / OTC_TRADER (+ AUDITOR read-only) |
| Segregation of duties (4-eye) | `ApprovalWorkflow` collection — no self-approval, mandatory secondary signer |
| DORA-equivalent incident register | `OperationalIncident` — SEV1-4, root-cause analysis, authority reporting flag |
| Conflicts-of-interest register | `ConflictOfInterest` — MiCAR Art. 72 |
| Vendor management | Outsourcing arrangements documented in registers (Sumsub, Chainalysis, Fireblocks, Notabene, Stripe, Transak) |

---

## 5. Third-party providers (outsourcing arrangements)

> **⚡ Autonomous Mode (default since v0.2.0, 2026-05-31)**
>
> NeoNoble runs in **fully autonomous** configuration by default
> (`CASP_AUTONOMOUS_MODE=true`). In this mode there is **no dependency on
> any third-party SaaS for KYC, blockchain analytics, custody or Travel
> Rule** — all four functions are performed by in-house adapters under
> `services/casp/internal/`. The external vendors below remain *optional
> integrations*, switchable via per-provider env flags
> (`SUMSUB_LIVE=true`, `CHAINALYSIS_LIVE=true`, …), should NeoNoble decide
> to add vendor coverage for operational redundancy or for proprietary
> intelligence not available from public sources.

### 5.1 Autonomous (in-house) operation

| Function | Internal implementation | Free public data source |
|---|---|---|
| KYC retail / KYB | `internal/kyc_adapter.py` — document upload (MongoDB), hash-pinned, manual MLRO review queue | OFAC SDN sanctioned individuals; EU consolidated; UN list |
| Sanctions screening | `internal/sanctions_data.py` — bundled list + refresh endpoint | https://www.treasury.gov/ofac/downloads/sdn.xml; webgate.ec.europa.eu/fsd; scsanctions.un.org |
| Blockchain analytics (KYT) | `internal/kyt_adapter.py` — sanctioned-address blacklist + 1-hop counterparty check + wallet age/volume heuristics | OFAC SDN crypto address subset (public); BscScan/Etherscan free-tier API |
| Custody | `internal/custody_adapter.py` — existing HD wallet (BIP44) + Gnosis Safe multi-sig (4-of-N) — *intent-record-then-external-sign* model | BSC RPC + Gnosis Safe public contracts |
| Travel Rule | `internal/trp_adapter.py` — IVMS-101 v1.0.1 over HTTPS + HMAC-SHA256, internal `vasp_directory` bilateral onboarding | IVMS-101 open standard (ivms101.org) |

### 5.2 Optional vendor integrations (currently OFF)

| Provider | Service | Activation env flag |
|---|---|---|
| **Sumsub** | KYC / KYB / liveness / sanctions | `SUMSUB_LIVE=true` + `SUMSUB_APP_TOKEN` / `SUMSUB_SECRET_KEY` |
| **Chainalysis** | Blockchain analytics (KYT) | `CHAINALYSIS_LIVE=true` + `CHAINALYSIS_API_KEY` |
| **Fireblocks** | MPC custody | `FIREBLOCKS_LIVE=true` + `FIREBLOCKS_API_KEY` / `FIREBLOCKS_PRIVATE_KEY` |
| **Notabene** | Travel Rule data exchange | `NOTABENE_LIVE=true` + `NOTABENE_API_KEY` |
| **Stripe** | EUR settlement & SEPA payouts (active) | Required for fiat off-ramp via banking rails |
| **Transak** | Retail on-ramp (interim, optional) | Required only for fiat on-ramp via licensed third party |

Each adapter follows an interface-first pattern in `services/casp/base.py`,
so any provider can be replaced with no impact on consumer code.

---

## 6. Evidence trail for the application

The following artefacts are produced automatically and can be exported during
the authorisation process:

1. **WORM audit log** — full hash-chained activity history (`/api/casp/audit`)
2. **Proof-of-Reserves snapshots** — quarterly Merkle commitments (`/api/casp/proof-of-reserves`)
3. **MiCAR T+1 reports** — daily JSON exports (`/api/casp/reports`)
4. **Capital adequacy snapshots** — daily own-funds vs required (`CapitalAdequacySnapshot`)
5. **AML alert lifecycle** — every alert with assignment, resolution & SAR reference
6. **Complaints register** — every complaint with SLA timer + resolution
7. **Conflict of interest register** — declared positions + mitigation
8. **Operational incident register** — DORA-style entries with root cause

---

## 7. Operating modes

The CASP Operating Stack supports three deployment modes:

1. **MOCK** (current default) — providers replaced by deterministic mocks. Used
   for QA, demos to CONSOB inspectors, and internal training.
2. **SHADOW** — partial LIVE: some providers active (Chainalysis), others mock
   (Fireblocks not yet contracted). Allows incremental rollout.
3. **PRODUCTION** — all four providers LIVE. Activated by setting the
   respective `*_LIVE=true` env flag — no code change required.

---

## 8. Roadmap to authorisation

| Milestone | ETA | Status |
|---|---|---|
| CASP Operating Stack v1 | Q2 2026 | ✅ DONE (this document) |
| Sumsub partner contract signed | Q2 2026 | In progress |
| Chainalysis KYT contract signed | Q3 2026 | Planning |
| Fireblocks vault provisioning | Q3 2026 | Planning |
| Notabene Travel Rule active | Q3 2026 | Planning |
| MiCAR CASP application filed | Q4 2026 | Drafting |
| CONSOB pre-application meeting | Q3 2026 | To request |
| Capital subscription (€125k Class 2) | Q4 2026 | Planning |
| Authorisation granted | Q2 2027 | Target |

---

## 9. Appendix — Italian summary (Sintesi italiana)

NeoNoble Ramp ha già implementato, in anticipo rispetto all'autorizzazione,
una piattaforma operativa ("CASP Operating Stack") completa dei sette blocchi
operativi richiesti dal MiCAR (Titolo V): identity & onboarding, transaction
monitoring & AML, custody & treasury, order management con desk OTC B2B,
regulatory reporting & audit, customer protection, internal governance.

I quattro fornitori esterni chiave (Sumsub, Chainalysis, Fireblocks, Notabene)
sono integrati tramite adapter sostituibili. La modalità "shadow" attualmente
attiva consente di esercitare i flussi operativi end-to-end senza erogare
servizi regolamentati prima dell'autorizzazione.

La pista di evidenza è garantita da un audit log immutabile (WORM)
hash-chained SHA-256, verificabile a sequenza monotona, idoneo come prova
di integrità per gli ispettori CONSOB / Banca d'Italia.

La classe di adeguatezza patrimoniale richiesta è la Classe 2 (€125.000 di
capitale iniziale), commisurata ai servizi (a), (c), (d), (e), (g), (j)
dell'Art. 3(1)(16) MiCAR.

---

*Document prepared by NeoNoble Engineering — May 2026. For circulation within
the authorisation procedure and to relevant compliance counsel only.*
