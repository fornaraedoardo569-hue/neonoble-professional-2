# Walkthrough Demo Transak — Copione Video (v2, iframe modal)

**Obiettivo:** registrare un video end-to-end di **60-90 secondi** per il
team di compliance UK di Transak. Dimostra che il flusso è:
- **KYC-gated** (MiCAR compliant, gate server-side)
- **User-initiated** (nessun trade auto-avviato)
- **Non-custodial** (nessun wallet della piattaforma)
- **Direct delivery** (il wallet dell'utente è locked come destinazione)
- **In-app iframe** (widget dentro un modal responsivo, sessione firmata server-side, single-use, 5-min expiry)

**URL Demo:** `https://neonoble-ramp.preview.emergentagent.com/dashboard`
(la nuova esperienza "Start Trading" è la card in alto sulla Dashboard;
la vecchia pagina `/transak` resta disponibile come approfondimento
tecnico, ma il flusso principale è ora il modal in-page).

**Token target:**
- **Primary:** NENO su BSC (contract `0xeF3F5C1892A8d7A3304E4A15959E124402d69974`).
  Iniettato automaticamente dal backend quando `cryptoCurrencyCode=NENO`.
- **Fallback fino al listing:** USDC su BSC (evidenziato in UI).

**Ambiente:** Transak `PRODUCTION` (`global.transak.com`).

---

## Pre-flight (una tantum, OFF-camera)

1. Installa **MetaMask** nel browser che userai per la registrazione.
2. Crea o importa un wallet **usa-e-getta** (mai le tue chiavi di produzione).
3. Aggiungi **BNB Smart Chain (mainnet)** al wallet.
4. Assicurati che il KYC utente sia **APPROVED** nel back-office CASP:
   - Login come `casp-admin@neonoble.example.com` / `CaspAdmin!2026`
   - `/admin/compliance` → seleziona il KYC IN_REVIEW dell'account demo
   - Click "Approve" → il gate server-side ora ammette il widget-url per quell'utente.
5. Apri uno screen recorder (OBS / QuickTime / Loom) a 1080p.
6. Pulisci il tab della console browser (F12 → clear) — vogliamo mostrare
   che l'evento `TRANSAK_WIDGET_OPEN` arriva sul postMessage.

---

## Copione on-camera (60–90 secondi)

| t | Cosa si vede | Cosa dire (voiceover suggerito) |
|---|---|---|
| **0–5s** | Login come utente retail (APPROVED KYC), atterra sulla **Dashboard**. In alto, banner "Retail Ramp — non-custodial · PRODUCTION" | "Questo è NeoNoble Ramp. L'utente è un cliente retail con KYC MiCAR già APPROVED da parte del nostro MLRO." |
| **5–10s** | Zoom sulla card **Start Trading** (badge `BSC · EUR`). Tre CTA visibili: Buy · Sell · Swap. Nessun gate giallo perché KYC è APPROVED. | "La card Start Trading espone tre CTA: Buy, Sell, Swap. Target di default: NENO su BSC, fiat EUR." |
| **10–15s** | Passa sopra al footer del card che dice "Powered by Transak · single-use widget URL signed by NeoNoble's partner backend (expires in 5 min). We never touch your funds." | "Ogni sessione è firmata dal nostro backend partner tramite `/partners/api/v2/auth/session`, single-use, scadenza 5 minuti." |
| **15–20s** | Click su **Buy Crypto**. Il modal iframe **si apre in-page**, header viola "Buy Crypto via Transak · PRODUCTION · BSC · EUR". | "Click su Buy. Il modal iframe apre in-page — nessuna popup, nessuna redirezione. Sessione firmata istantaneamente dal backend." |
| **20–35s** | Il widget Transak carica dentro l'iframe. L'utente vede il flusso Transak nativo con importo, KYC status, metodo di pagamento pre-compilato. Nel campo "Wallet address" mostra l'indirizzo del wallet **grigio e non editabile** (`disableWalletAddressForm=true`). | "Dentro il modal è live il widget Transak. L'indirizzo wallet dell'utente è pre-compilato e bloccato — l'unica destinazione possibile è il suo wallet self-custody. Sotto il cofano il backend ha iniettato il contract NENO `0xeF3F...9974`, network `bsc`, fiat `EUR`." |
| **35–45s** | Apri DevTools → tab Console. Si vedono log arrivare: `TRANSAK_WIDGET_INITIALISED`, `TRANSAK_WIDGET_OPEN`. | "Ogni evento del widget arriva al frontend via postMessage, viene verificato per origin (`global.transak.com`) e loggato nel nostro audit log WORM. Mai come trigger di trade — solo per audit." |
| **45–52s** | Chiudi il modal cliccando la X. Il modal si dissolve, la Dashboard è pulita, nessuno stato residuo. | "Chiudo il modal. La sessione widgetUrl è single-use e già scaduta lato Transak." |
| **52–65s** | Click su **Sell Crypto** → il modal riapre in modalità SELL (header ora "Sell Crypto via Transak"). Stesso wallet lock, stesso backend flow. | "Sell riusa lo stesso pattern. Nuova sessione firmata, stesso wallet locked, stesso flow non-custodial." |
| **65–75s** | Chiudi. Click su **Swap** → il modal riapre in modalità BUY+SELL (`productsAvailed=BUY,SELL`). | "Swap è semplicemente `productsAvailed=BUY,SELL` — Transak decide internamente in base al saldo del wallet." |
| **75–85s** | Vai su **Dev Portal** (`/dev`) → mostra la card **Transak Sandbox** con il payload JSON esposto per sviluppatori. | "Per il team dev di Transak: il Dev Portal espone la Sandbox con payload preview, wallet input, e i 3 launch buttons. Bypassa il KYC gate perché ha ruolo DEVELOPER." |
| **85–90s** | Fine — logo NeoNoble Ramp + tagline "Non-custodial by design. User-initiated only. Direct delivery." | "NeoNoble Ramp — CASP MiCAR, integrazione Transak Production, retail-ready." |

---

## Mapping Pillar → UI (nuova versione iframe)

| Pillar | Dove è imposto | Cosa si vede in camera |
|---|---|---|
| **KYC-gated** | `middleware/kyc_gate.py` restituisce 403 su `POST /api/transak/widget-url` se KYC ≠ APPROVED | Utente non-APPROVED vede la card grigia "Identity verification required" con link a `/onboarding` |
| **User-initiated Only** | I 3 CTA sono click esplicito dell'utente. Nessun endpoint backend crea trade. | Buy/Sell/Swap sono click manuali; nessun cron/webhook li avvia |
| **No Fund Intermediation** | Il backend espone solo `POST /transak/widget-url` (crea session URL) e `POST /transak/events` (audit log). Zero endpoint di transfer / payout / custody. | Il payload JSON nel Dev Portal mostra `non_custodial: true` e l'oggetto `compliance` con i 3 flag |
| **Direct Delivery** | `walletAddress` = wallet self-custody connesso + `disableWalletAddressForm=true` | Dentro il modal, campo wallet grigio e non editabile |
| **In-app iframe** | Nuovo componente `TransakIframeModal.jsx`: iframe con permessi Transak-recommended, listener origin-verified sui postMessage | Modal responsivo si apre in-page; header viola NeoNoble sopra l'iframe Transak |
| **Session single-use, 5-min** | Backend chiama `POST /api/v2/auth/session` che genera URL con scadenza 5 min | Footer del modal recita "single-use session (5 min)" |

---

## Imprevisti tipici durante la registrazione

- **Modal apre ma iframe mostra "Cannot open Transak · Transak account KYB is pending":**
  è l'errore atteso finché Rahul non sblocca il KYB. **Per registrare il
  video devi aspettare lo sblocco.** Se serve girarlo prima per motivi
  interni, mostra il modal che si apre + il messaggio d'errore chiaro
  come proof dell'integrazione lato NeoNoble.
- **Modal apre ma iframe bianco:** verifica di essere loggato come utente
  con KYC APPROVED. Il gate server-side blocca gli utenti senza KYC.
- **KYC APPROVED ma comunque 403:** l'account potrebbe essere ADMIN
  (bypass) oppure il campo `role` non è impostato. Verifica su MongoDB:
  `db.casp_kyc.findOne({ user_id: "<id>" })` → `status: "APPROVED"`.
- **Errore CORS in console:** l'origin Transak sta rifiutando il
  `referrerDomain`. Confronta il valore inviato con quello registrato nel
  Partner Dashboard. Devono essere identici (senza `https://`, senza
  trailing slash).
- **Iframe non riceve postMessage:** verifica che l'origin whitelist nel
  componente `TransakIframeModal` matchi (`PROD_ORIGIN =
  'https://global.transak.com'`).

---

## Tear-down (DOPO la registrazione)

- Disconnetti il wallet usa-e-getta da MetaMask → Connected sites →
  Rimuovi `neonoble-ramp.preview.emergentagent.com`.
- Sposta o distruggi il wallet usa-e-getta — non riutilizzarlo in produzione.
- Cancella cache e localStorage del browser per non lasciare token JWT
  in giro se hai loggato con account reali.

---

## Endpoint backend usati da questo flusso

```
POST /api/transak/widget-url
     ↳ header: Authorization Bearer <user JWT>
     ↳ body:   { productsAvailed, cryptoCurrencyCode: "NENO",
                 cryptoCurrencyAddress (auto-injected server-side),
                 network: "bsc", defaultFiatCurrency: "EUR",
                 walletAddress, disableWalletAddressForm: "true", … }
     ↳ 200:    { widget_url, referrer_domain_sent, expires_in_seconds: 300 }
     ↳ 403:    { detail: { error: "kyc_required", kyc_status, message } }
     ↳ 409:    { detail: "TRANSAK_KYB_PENDING: ..." }

POST /api/transak/events    # audit-log dei postMessage del widget
GET  /api/transak/config    # config pubblica (api key, env, network, fiat)
GET  /api/transak/events    # rilettura audit
```

Nessuno di questi endpoint crea, instrada o regola un trade. Il widget
Transak gira interamente dentro l'iframe nel browser dell'utente e regola
i fondi direttamente sul wallet dell'utente. Il backend NeoNoble è
esclusivamente un partner-signer che emette il session URL.
