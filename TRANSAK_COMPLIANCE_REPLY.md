# Reply to Transak Compliance — Rahul Das
_Updated 2026-07-21 to reflect the new iframe modal integration and to explicitly request the KYB unlock + NENO asset listing._

> **How to send:**
> 1. Reply directly to Rahul's original thread of 20/05/2026 (subject: *"Dear Massimo, Thank you for your detailed response…"*) so the KYB review resumes on the existing application without resubmission.
> 2. Paste the **English version** as the email body.
> 3. Attach: (a) the demo screen recording (see `TRANSAK_DEMO_WALKTHROUGH_IT.md`), (b) the NENO Asset Listing dossier (`TRANSAK_NENO_ASSET_LISTING.md`), and (c) an updated screenshot of `/dashboard` (Start Trading iframe modal).
> 4. CC `compliance@transak.com` and `support@transak.com` so the ticket is visible to their KYB, Listing and Support teams simultaneously.

---

## ✉️ ENGLISH VERSION (send this)

**Subject:** NeoNoble × Transak — KYB Unlock Request + NENO Asset Listing (updated integration attached)

Dear Rahul,

I hope this email finds you well. Following our earlier exchange, I am reaching out to (a) provide the updated end-to-end integration confirmation now that our Production integration is complete, and (b) formally request two blocking approvals: the **KYB release** on our partner account and the **NENO ($NENO) asset listing** on the Transak Partner Dashboard.

Both approvals are the only external dependency remaining before we can onboard our first retail customers.

---

### 1. Partner integration is complete and in Production

Our backend is fully wired to Transak Production. The key/secret you released to us via the Partner Dashboard succeeds against `POST https://api.transak.com/partners/api/v2/refresh-token` (verified 200 OK, accessToken issued and cached with a 24-hour refresh buffer). The subsequent `POST https://api-gateway.transak.com/api/v2/auth/session` call is the only step that currently 401s — we understand this is the expected upstream state until you release the KYB hold. **The moment KYB is approved, our integration will be immediately operational — zero code changes required on our side.**

Integration highlights:

- **Server-side session URL only.** `apiKey` and `referrerDomain` are enforced on our backend and cannot be tampered with from the client. Widget parameters are validated by a strict Pydantic schema before being forwarded to `/api/v2/auth/session`.
- **Single-use widgetUrl per user flow.** Each URL is opened exactly once in the responsive iframe modal, expires 5 minutes after creation, and is never persisted.
- **Iframe modal — not a popup.** Following your preferred integration pattern, we now render the widget inside a responsive, in-page iframe modal (`<iframe src={widgetUrl}>` with the Transak-recommended permission list: `camera; microphone; fullscreen; payment; …`). This keeps the entire session inside Transak's own domain while giving the user a native in-app experience.
- **Wallet destination is locked.** `walletAddress` is set from the user's connected self-custody wallet and `disableWalletAddressForm=true` is enforced — the user cannot change the destination inside the widget.
- **Non-custodial by design.** NeoNoble operates zero hot wallets, zero omnibus accounts and zero internal ledgers for retail customers. On-chain balances are read live via `eth_getBalance` / ERC-20 `balanceOf`. All fiat and crypto flow directly between the user and Transak; funds never touch our infrastructure.
- **Post-message events are audit-logged only.** Every `TRANSAK_*` event emitted by the widget is verified against the widget origin (`global.transak.com` in Production) and forwarded to our WORM (Write-Once-Read-Many) hash-chained audit log — never used as a trade trigger.
- **MiCAR/AML KYC gate is enforced server-side before the session URL is ever requested.** Retail users must have an APPROVED KYC record in our CASP back-office before the `/api/transak/widget-url` endpoint returns a URL to the browser. This is on top of Transak's own KYC inside the widget.

The four compliance pillars — **User-initiated only • No fund intermediation • Direct delivery • Non-custodial by design** — remain published in the UI, and the Start Trading iframe modal now surfaces them in the header of every widget session.

---

### 2. Explicit request #1 — Please release the KYB hold

Could you please confirm the current status of our KYB review and, if possible, release the partner account so widget sessions can be created? All the clarifications and attestations you asked for in your 20/05/2026 message have been implemented and are demonstrably verifiable in the attached screen recording and in the live `/dashboard` and `/dev` environments.

If any additional written attestation, board resolution, insurance certificate, ownership schedule or ID document is still missing on your side to close the file, I will provide it same-day — just let me know.

---

### 3. Explicit request #2 — NENO ($NENO) asset listing on the Partner Dashboard

Our retail flow's primary target is our own utility token **NENO**, listed on Binance Smart Chain (BEP-20). Please find below the summary; the full dossier is attached as `TRANSAK_NENO_ASSET_LISTING.md`.

| Field | Value |
| --- | --- |
| Symbol | **NENO** |
| Name | NeoNoble Token |
| Contract | `0xeF3F5C1892A8d7A3304E4A15959E124402d69974` |
| Network | Binance Smart Chain (BSC, chainId 56) |
| Standard | BEP-20 |
| Decimals | 18 |
| Issuer | NeoNoble Technology Incorporation Limited (registered CASP) |
| Primary fiat | EUR |
| Use case | Payment / utility inside NeoNoble Ramp; fixed reference OTC price EUR 10,000 for institutional; DEX price via PancakeSwap V2 (NENO/USDC) for retail |
| KYC on ramp | Yes — enforced by NeoNoble CASP back-office + Transak |
| AML posture | Full on-chain screening against OFAC/EU/UN sanctions lists (autonomous mode) + Travel Rule (IVMS-101) messaging integrated |
| Contact | Massimo Fornara — CEO / MLRO — [email address on file] |

Our backend already whitelists the contract address so, the moment NENO is enabled by Transak, our widget request will automatically pass:

```json
{
  "productsAvailed": "BUY | SELL | BUY,SELL",
  "cryptoCurrencyCode": "NENO",
  "cryptoCurrencyAddress": "0xeF3F5C1892A8d7A3304E4A15959E124402d69974",
  "network": "bsc",
  "defaultFiatCurrency": "EUR",
  "referrerDomain": "<neonoble-ramp.com>"
}
```

Please treat this email as the formal Add-Custom-Token request and let me know if the Listing team needs anything beyond the dossier attached.

---

### 4. Timelines

Our retail launch window opens as soon as (a) KYB is released and (b) NENO is listed. I would be extremely grateful for any indicative timing you can share, and I remain fully available for a compliance walkthrough call at your convenience — either directly with your KYB team or with the Listing team.

Thank you again for your time and for the diligence of the Transak compliance function. Looking forward to your reply.

Best regards,
**Massimo Fornara**
CEO & MLRO — NeoNoble Technology Incorporation Limited
[phone] · [email] · https://neonoble-ramp.com

**Attachments:**
1. `TRANSAK_NENO_ASSET_LISTING.md` — full NENO asset listing dossier
2. `neonoble-transak-walkthrough.mp4` — 60-second E2E screen recording (script in `TRANSAK_DEMO_WALKTHROUGH_IT.md`)
3. `neonoble-dashboard-start-trading.png` — screenshot of the Start Trading iframe modal
4. `TRANSAK_COMPLIANCE_REPLY.md` (this document)

---

## 🇮🇹 ITALIAN VERSION (personal reference — non inviare)

**Oggetto:** NeoNoble × Transak — Sblocco KYB + Listing dell'asset NENO (integrazione aggiornata in allegato)

Gentile Rahul,

spero che tu stia bene. Sulla scia della nostra precedente corrispondenza, ti scrivo per (a) confermarti che l'integrazione Production è ora completa e (b) richiedere formalmente due sblocchi che sono l'unica dipendenza esterna rimasta prima del nostro lancio retail: la **release del KYB** sul nostro account partner e il **listing di NENO ($NENO)** sul Partner Dashboard di Transak.

### 1. Integrazione completa e in Production

Il nostro backend chiama con successo `POST https://api.transak.com/partners/api/v2/refresh-token` (200 OK, accessToken emesso e cacheato con buffer di refresh a 24h). La successiva `POST https://api-gateway.transak.com/api/v2/auth/session` è l'unico passaggio che restituisce ancora 401 — comprendiamo sia lo stato upstream atteso finché non rilasciate il KYB. **Nel momento in cui approvi il KYB, la nostra integrazione sarà operativa istantaneamente — zero modifiche al codice richieste.**

Punti chiave dell'integrazione:

- **Session URL server-side.** `apiKey` e `referrerDomain` sono controllati dal backend e non manomissibili dal client. Parametri validati con schema Pydantic prima di essere inoltrati a `/api/v2/auth/session`.
- **widgetUrl monouso.** Ogni URL viene aperto una sola volta nel modal iframe responsivo, scade dopo 5 minuti dalla creazione, e non viene mai persistito.
- **Modal iframe — non popup.** Seguendo il vostro pattern d'integrazione preferito, il widget è ora renderizzato in un modal iframe responsivo in-page (`<iframe src={widgetUrl}>` con la lista di permessi raccomandata da Transak: `camera; microphone; fullscreen; payment; …`). La sessione resta interamente nel dominio Transak con UX nativa in-app.
- **Destinazione wallet bloccata.** `walletAddress` è preso dal wallet self-custody connesso dell'utente e `disableWalletAddressForm=true` è forzato — l'utente non può modificare la destinazione dentro il widget.
- **Non-custodial by design.** NeoNoble non gestisce hot wallets, conti omnibus, né ledger interni per gli utenti retail. Balance letti live via `eth_getBalance` / ERC-20 `balanceOf`. Tutti i flussi fiat e crypto sono diretti tra utente e Transak.
- **Post-message events solo audit-logged.** Ogni evento `TRANSAK_*` è verificato per origine (`global.transak.com` in Production) e loggato nel nostro audit log WORM hash-chained — mai come trigger di trade.
- **KYC gate MiCAR/AML lato server prima di richiedere il session URL.** Gli utenti retail devono avere KYC APPROVED nel nostro back-office CASP prima che `/api/transak/widget-url` restituisca un URL al browser.

### 2. Richiesta esplicita #1 — Sblocco del KYB

Puoi confermarmi lo stato attuale della review KYB e, se possibile, rilasciare l'account partner? Ho implementato tutti i chiarimenti da te richiesti nel messaggio del 20/05/2026 e sono verificabili nel video demo allegato + negli ambienti live `/dashboard` e `/dev`. Se serve qualsiasi ulteriore attestazione (delibere del board, polizze, schema di proprietà, documenti d'identità aggiuntivi) la fornisco lo stesso giorno — basta dirmelo.

### 3. Richiesta esplicita #2 — Listing di NENO

Trovi il dossier completo in allegato (`TRANSAK_NENO_ASSET_LISTING.md`).

Grazie ancora, resto a disposizione per una call di walkthrough compliance quando preferisci.

Cordiali saluti,
**Massimo Fornara**
CEO & MLRO — NeoNoble Technology Incorporation Limited
