# Transak Widget Demo — Walkthrough Script

**Purpose:** Record a 45–90 second end-to-end video for Transak's UK
compliance team. Demonstrates a fully non-custodial flow:
**Onboarding → Wallet Connect → Transak → Wallet → Interaction.**

**Demo URL:** `${REACT_APP_BACKEND_URL}/transak`
(currently: `https://neonoble-ramp.preview.emergentagent.com/transak`)

**Token shown:**
- **Primary intent:** NENO (BEP-20, `0xeF3F5C1892A8d7A3304E4A15959E124402d69974`)
- **Staging fallback:** USDC on BSC — NENO is not yet listed in Transak's
  staging catalog. The page UI clearly states this. Flip
  `TRANSAK_SUPPORTS_NENO=true` in `backend/.env` the moment Transak adds
  NENO and the widget will switch automatically.

**Environment:** Transak `STAGING` (`global-stg.transak.com`).

---

## Pre-flight (do this once, OFF-camera)

1. Install **MetaMask** in the browser used for the recording.
2. Create or import a **disposable** wallet (do NOT use your production keys).
3. Add **BNB Smart Chain (mainnet)** to the wallet — the page has a
   "Switch to BNB Smart Chain" button that will add it for you.
4. Fund the wallet with a tiny amount of BNB and a small USDC balance on
   BSC if you want the SELL flow to reach the final screen. The staging
   widget will accept test KYC, but the wallet needs balance for SELL.
5. Open a screen recorder (OBS, QuickTime, Loom, …) at 1080p.

---

## On-camera script (60–75 seconds)

| t | What's on screen | What to say (suggested VO) |
|---|---|---|
| 0–4s | Home page → click **Get Started → Login** → land on Dashboard | "This is NeoNoble Ramp. The compliance demo lives behind the **Transak Demo** tab." |
| 4–8s | Click **Transak Demo** in the Dashboard header → `/transak` page loads | "We open the dedicated, non-custodial demo route." |
| 8–18s | Hover the three pillar cards (User-initiated · No Fund Intermediation · Direct Delivery) | "Three pillars: user-initiated only, no fund intermediation, direct delivery — visibly enforced on this page." |
| 18–25s | Click **Connect Wallet** → MetaMask prompt → approve → green "Wallet connected" card appears | "Step one: the user explicitly connects their own wallet. This address is the only destination Transak will deliver to." |
| 25–30s | If chain is not BSC, click **Switch to BNB Smart Chain** | "We move to BNB Smart Chain — the network where NENO lives." |
| 30–40s | Click **Buy Crypto (On-Ramp)** → Transak widget opens with the connected address pre-filled and **disabled** | "Step two: Buy. Transak's widget opens with the user's own wallet address, locked via `disableWalletAddressForm` — they can't reroute the trade. The token is USDC on BSC for staging; NENO will be enabled the moment Transak whitelists our contract." |
| 40–50s | Close the widget. Click **Sell Crypto (Off-Ramp)** → widget reopens in SELL mode | "Step three: Sell. Same wallet, same lock. The user signs the outbound transfer themselves — NeoNoble has no signing authority." |
| 50–58s | Close, then click **Swap (Buy/Sell)** → both tabs available | "Step four: a unified Swap tab toggles between BUY and SELL with `productsAvailed=BUY,SELL`." |
| 58–70s | Scroll to **Transak event stream** card showing `TRANSAK_WIDGET_INITIALISED`, `…OPEN`, `…CLOSE` | "Every Transak SDK event is logged client-side and forwarded to our backend for audit — never as a trade trigger." |
| 70–75s | Open the collapsed **Widget configuration** section, showing the raw config JSON | "Here is the full read-only config the page is using: STAGING environment, BSC network, EUR fiat, walletAddress = user's address, `disableWalletAddressForm=true`. Done." |

---

## Compliance pillar → UI mapping

| Pillar | Where it's enforced | Visible to camera |
|---|---|---|
| **User-initiated Only** | The Buy/Sell/Swap buttons are disabled until `wallet.address` is set in `useWallet`. There is no backend endpoint that creates a trade. | Buttons are visibly greyed out until "Connect Wallet" succeeds; the disabled-note text says "Connect your wallet first to enable Buy/Sell/Swap." |
| **No Fund Intermediation** | The backend exposes only `GET /api/transak/config` (read-only) and `POST /api/transak/events` (log-only). No transfer, no payout, no custody endpoint. | The "Widget configuration" details JSON shows `non_custodial: true` and the `compliance` object. |
| **Direct Delivery** | The widget URL is built with `walletAddress=<user_address>` + `disableWalletAddressForm=true` + `partnerCustomerId=<user_address>`. | Inside the Transak modal, the destination wallet field is pre-filled and uneditable. The "Wallet connected" card shows the exact same address. |

---

## Common gotchas during recording

- **No injected wallet detected:** the page shows a yellow warning. Install
  MetaMask and reload before recording.
- **Buttons stay greyed out:** the wallet is connected but on the wrong
  network. Click **Switch to BNB Smart Chain**.
- **Widget opens with a different token:** the staging catalog occasionally
  remaps `cryptoCurrencyCode`. Confirm that the URL bar inside the iframe
  contains `cryptoCurrencyCode=USDC` (or `NENO` once supported). If not,
  flip `TRANSAK_FALLBACK_TOKEN` in `backend/.env` to a different listed token
  (e.g. `USDT`) and restart the backend.
- **`apiKey` not configured error:** `TRANSAK_API_KEY` is missing from
  `backend/.env`. Set it (default: the public staging key from Transak docs)
  and `sudo supervisorctl restart backend`.

---

## Tear-down (do this AFTER recording)

- Disconnect the disposable wallet from MetaMask → "Connected sites" →
  Remove `neonoble-ramp.preview.emergentagent.com`.
- Move/destroy the disposable wallet — do not reuse it for production.

---

## Backend endpoints referenced by this flow

```
GET  /api/transak/config        # public widget config (api_key, env, network, fiat, compliance flags)
POST /api/transak/events        # observational event logging from the user's widget session
GET  /api/transak/events?wallet_address=0x…   # read back events for that wallet
```

None of the above creates, routes, or settles a trade. The Transak
widget runs entirely in the user's browser and settles directly to the
user's wallet.
