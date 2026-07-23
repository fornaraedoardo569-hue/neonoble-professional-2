# Security Posture & Trade-offs

_Last updated: 2026-02_

## Current State

NeoNoble Ramp uses **JWT bearer-token authentication** stored in
`localStorage` on the frontend. Tokens are sent in the `Authorization`
header for every authenticated request.

This document captures the **pragmatic hardening** applied today and the
**planned migration** to `HttpOnly` cookies in a future sprint.

---

## Applied Hardening (Option B – this sprint)

1. **Short-lived access tokens (15 min)**
   - File: `backend/utils/jwt_utils.py`
   - Limits the blast radius of a leaked access token to 15 minutes.
   - Tunable via `ACCESS_TOKEN_EXPIRE_MINUTES` env var.

2. **Long-lived refresh tokens (7 days)**
   - File: `backend/utils/jwt_utils.py`
   - Issued alongside the access token on `POST /api/auth/login` and
     `POST /api/auth/register`.
   - Tagged `type=refresh` and rejected by access-token validation paths.
   - Tunable via `REFRESH_TOKEN_EXPIRE_DAYS` env var.

3. **Silent refresh endpoint**
   - `POST /api/auth/refresh` — exchanges a refresh token for a fresh
     access+refresh pair (rotation on every refresh).
   - Frontend axios interceptor (`frontend/src/api/index.js`)
     automatically retries the original request on `401` after refreshing,
     transparent to the user.

4. **Security response headers (defense-in-depth)**
   - FastAPI middleware in `backend/server.py`:
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `Referrer-Policy: no-referrer`
     - `Permissions-Policy: geolocation=(), microphone=(), camera=()`

5. **No development noise in production**
   - All `console.error` calls in the frontend are wrapped in
     `if (process.env.NODE_ENV === 'development')`. No stack traces leak
     to end users.

---

## Known Residual Risk

`localStorage` is reachable by any JavaScript executing on the page,
so a successful XSS attack can still exfiltrate the (short-lived)
access token and the refresh token. The mitigations above shrink the
attack window but do not eliminate it.

We currently rely on:

- Strict React rendering (no `dangerouslySetInnerHTML` anywhere in the
  app — verified during this refactor).
- Pydantic input validation on every backend route.
- HMAC-SHA256 signed Dev Portal API calls (separate auth scheme,
  unaffected by the user JWT flow).

### Why no CSP meta tag yet?

`frontend/public/index.html` currently loads several first-party and
third-party scripts (Emergent platform helpers, PostHog analytics,
Tailwind CDN inside the visual editor iframe). A strict CSP would
break those legitimately-needed scripts. CSP will be re-evaluated as
part of the cookie migration below, when we can lock down the origin
list precisely.

---

## Planned Migration (Option A – next sprint)

Move bearer-token storage to `HttpOnly; Secure; SameSite=Lax` cookies +
CSRF double-submit tokens. Outline:

| Layer | Change |
|---|---|
| Backend `routes/auth.py` | `Set-Cookie` access + refresh; clear on `/logout` |
| Backend middleware | Add CSRF double-submit check on mutating routes |
| Backend `server.py` | Tighten `CORS_ORIGINS` to a list of exact origins + `allow_credentials=True` |
| Frontend `api/index.js` | `withCredentials: true`; read CSRF cookie → `X-CSRF-Token` header |
| Frontend `AuthContext` | Stop touching `localStorage`; use `/auth/me` for session probe |
| Infra | Front-end and back-end must share a parent domain (cookie scope) |

This migration is **scheduled for the next sprint** so it can be
delivered together with the corresponding staging cut-over and
end-to-end tests, avoiding the auth outage risk of a rushed change.

---

## Threat Model Summary

| Threat | Today | After Option A |
|---|---|---|
| Token stolen by XSS | ⚠️ Short-lived (15 min) but reachable | ✅ Not reachable from JS |
| CSRF on auth'd endpoints | ✅ N/A (Authorization header, no cookie) | ✅ Mitigated by CSRF token |
| Token replay after logout | ✅ Refresh chain rotated | ✅ Cookies cleared server-side |
| Long-lived session compromise | ⚠️ Up to 7 days (refresh) | ✅ Same, but token un-stealable |
