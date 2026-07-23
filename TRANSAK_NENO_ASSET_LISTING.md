# NENO ($NENO) — Asset Listing Dossier for Transak

_Prepared for the Transak Listing team. Attach with the KYB reply email
(`TRANSAK_COMPLIANCE_REPLY.md`) and/or submit via the "Add Custom Token"
form in the Transak Partner Dashboard._

---

## 1. Executive summary

**NENO** is the native utility token of the NeoNoble Ramp platform, issued
by **NeoNoble Technology Incorporation Limited** — a registered CASP under
MiCAR. NENO is a straightforward BEP-20 payment/utility token deployed on
Binance Smart Chain (BSC), with a fixed institutional reference price of
**EUR 10,000** for OTC trades and a market price on **PancakeSwap V2**
(NENO/USDC) for retail. We are requesting Transak to whitelist NENO so
retail customers can buy, sell and (once eligible) swap it directly from
the NeoNoble Ramp Start Trading widget.

## 2. Asset identity

| Field | Value |
| --- | --- |
| **Symbol** | NENO |
| **Name** | NeoNoble Token |
| **Contract address** | `0xeF3F5C1892A8d7A3304E4A15959E124402d69974` |
| **Network** | Binance Smart Chain (BSC) |
| **Chain ID** | 56 (mainnet) |
| **Token standard** | BEP-20 (ERC-20 compatible) |
| **Decimals** | 18 |
| **Ticker** | NENO |
| **Genesis / deploy date** | See BscScan on the address above |
| **Total supply** | See BscScan `totalSupply()` reading |
| **Circulating supply** | Same as total supply — no locked/vested tranches on the contract |
| **Logo** | Available at `https://neonoble-ramp.com/assets/neno-logo.png` (512×512 PNG, transparent) |
| **BscScan URL** | https://bscscan.com/token/0xeF3F5C1892A8d7A3304E4A15959E124402d69974 |

## 3. Issuer identity

| Field | Value |
| --- | --- |
| **Legal name** | NeoNoble Technology Incorporation Limited |
| **Registration** | Available on request (OAM Italy — CASP registration on file) |
| **Registered address** | On file with the Transak KYB submission |
| **CEO / MLRO** | Massimo Fornara |
| **Compliance email** | `compliance@neonoble-ramp.com` |
| **General enquiries** | `support@neonoble-ramp.com` |
| **Website** | https://neonoble-ramp.com |

## 4. Utility & tokenomics

- **Primary use case:** medium of exchange inside the NeoNoble Ramp
  ecosystem. Users can buy NENO with EUR/USD via the retail on-ramp
  (Transak once listed) or via the enterprise OTC desk (Stripe SEPA).
- **Secondary use case:** DEX-tradable liquidity pair NENO/USDC on
  **PancakeSwap V2** (address to be shared once seeded).
- **Fixed OTC reference price:** EUR 10,000 per NENO (enterprise B2B
  channel only — separate from retail ramp). Retail pricing is 100% market
  price via PancakeSwap V2.
- **No fee-on-transfer, no rebase, no dynamic supply.** The contract is a
  vanilla BEP-20 with `transfer`, `transferFrom`, `approve` — no hooks,
  no blacklist, no mint/burn callable by anyone except the issuer wallet.
- **Non-inflationary post-mint.** Once the initial supply is minted, no
  further mint operations are executed.
- **No lock-ups.** All tokens are freely transferable.

## 5. Compliance posture

### 5.1 KYC / AML on the retail flow

- Every retail buyer must complete NeoNoble's own **MiCAR-compliant KYC**
  before they can even request a Transak widget URL — the server-side
  `/api/transak/widget-url` endpoint returns HTTP 403 if the user's CASP
  KYC status ≠ APPROVED.
- The customer then goes through Transak's own KYC inside the widget as
  a **second layer**.
- KYC records are stored WORM hash-chained in our audit log (verifiable
  via `GET /api/casp/audit/verify` on our back-office).

### 5.2 On-chain sanctions & AML screening

- Every wallet interacting with the platform is screened against **OFAC,
  EU and UN** sanctions lists on each transaction (autonomous mode).
- Known mixer/tornado-cash addresses are hard-blocked with `is_critical=True`.
- Detected hits create an AML alert (`aml_alerts` collection) for MLRO
  review; a SAR can be drafted directly from the alert in `/admin/aml`.

### 5.3 Travel Rule (IVMS-101)

- Both outgoing and incoming crypto transfers ≥ EUR 1,000 emit an IVMS-101
  Travel Rule payload signed with our peer-VASP shared secret.
- Peer VASP directory is managed in `/admin/trp/vasps` (SIGNED / VERIFIED
  peer entries).

### 5.4 Regulatory reporting

- Automatic MiCAR T+1 reports (`/api/casp/reports/micar`) generated for
  every OTC transaction.
- Capital adequacy snapshots (Class 2 CASP, EUR 125k required) tracked in
  `/admin/treasury` — currently EUR 280k own funds, coverage 2.24×.

## 6. Contract technical review

The contract at `0xeF3F5C1892A8d7A3304E4A15959E124402d69974` is a vanilla
BEP-20 implementation. Recommended checks on your end:

1. Read `name()` / `symbol()` / `decimals()` / `totalSupply()` on BscScan.
2. Verify the source code is verified/published on BscScan (yes).
3. Confirm no `pause()`, `blacklist()`, or dynamic-fee logic — none present.
4. Confirm the owner address's ability is limited to what is normal for
   a BEP-20 issuer (no arbitrary transfers of other users' balances).

If you would like, we can arrange a technical call with our smart-contract
engineer for a walk-through of the deployment.

## 7. Liquidity & market data

- **Primary retail pair:** `NENO / USDC` on PancakeSwap V2 (BSC) — LP
  address to be provided once seeding is complete.
- **Reference DEX:** PancakeSwap V2 router
  `0x10ED43C718714eb63d5aA57B78B54704E256024E`.
- **Institutional reference:** EUR 10,000 fixed OTC price for enterprise
  B2B, quoted directly by NeoNoble via `/api/casp/otc/quote`. Retail flow
  uses the DEX market price, not this reference.

## 8. Widget request payload NeoNoble will send

Our backend already normalises the payload as follows the moment NENO is
enabled by Transak:

```json
POST /api/v2/auth/session   (server-side)
{
  "widgetParams": {
    "apiKey": "<partner_key>",
    "referrerDomain": "neonoble-ramp.com",
    "productsAvailed": "BUY | SELL | BUY,SELL",
    "cryptoCurrencyCode": "NENO",
    "cryptoCurrencyAddress": "0xeF3F5C1892A8d7A3304E4A15959E124402d69974",
    "network": "bsc",
    "defaultFiatCurrency": "EUR",
    "fiatCurrency": "EUR",
    "walletAddress": "<user's connected self-custody wallet>",
    "disableWalletAddressForm": "true",
    "hideMenu": "true",
    "themeColor": "7c3aed",
    "partnerCustomerId": "<user's wallet address>"
  }
}
```

Nothing changes in our stack once NENO is added to your allow-list — we
only need the confirmation from your side.

## 9. Requested actions

Please:

1. **Whitelist** the contract `0xeF3F5C1892A8d7A3304E4A15959E124402d69974`
   on Binance Smart Chain (chainId 56) for the NeoNoble partner account.
2. **Enable** the `NENO` `cryptoCurrencyCode` for both **BUY** and **SELL**
   products in Production.
3. **Confirm** the whitelisting in writing so we can flip
   `TRANSAK_SUPPORTS_NENO=true` in our `.env` and go live for retail.

## 10. Point of contact

- **Business / compliance:** Massimo Fornara — CEO / MLRO
- **Technical (contract, integration):** Available on request through the
  same email thread
- **Preferred channel:** email to the thread with Rahul Das + CC
  `compliance@transak.com` + `listing@transak.com`

_Prepared 2026-07-21 — for internal Transak Listing review only._
