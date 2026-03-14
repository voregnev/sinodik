# Feature Landscape: OTP Email Auth + RBAC

**Domain:** Email-OTP authentication with two-role RBAC for a FastAPI web app
**Researched:** 2026-03-14
**Confidence:** HIGH — OTP auth and JWT RBAC are well-established patterns with stable, unambiguous best practices

---

## Table Stakes

Features users expect. Missing = auth is broken, insecure, or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| OTP request endpoint (`POST /auth/request-otp`) | Entry point for passwordless flow; without it there is no auth | Low | Accepts email, creates/upserts OTP record, triggers delivery |
| OTP verification endpoint (`POST /auth/verify-otp`) | Core of the flow; returns JWT on success | Low | Must consume (single-use) the code on first valid use |
| OTP expiry enforcement | Codes must expire or they become permanent passwords | Low | Industry standard: 10–15 min window |
| OTP single-use enforcement | Replay attack prevention; a verified code must be invalidated | Low | Mark `used_at` on OTP record, reject if already set |
| OTP rate limiting / brute-force protection | 6-digit code = 1M possibilities; without limiting, trivially brute-forceable | Medium | Max N attempts per email per window; lock out or throttle |
| Secure random code generation | Predictable codes (time-seeded, sequential) can be guessed | Low | `secrets.randbelow(1_000_000)` zero-padded to 6 digits |
| Account auto-creation on first OTP success | Defined requirement; no pre-registration step | Low | Upsert user row keyed on email |
| JWT issuance with role claim | Stateless session carrier; must encode role to avoid DB hit on every request | Low | `{"sub": email, "role": "user"\|"admin", "exp": ...}` |
| JWT expiry | Infinite tokens are an incident waiting to happen | Low | 7–30 days typical for low-frequency apps like this |
| JWT signature verification on protected routes | Any protected route must reject tampered/expired tokens | Low | FastAPI `Depends(get_current_user)` dependency |
| Role enforcement on admin routes | Admin routes must reject `role=user` tokens | Low | `Depends(require_admin)` dependency wrapping `get_current_user` |
| `users` table with role and active flag | Persistent identity store; needed for disable/promote operations | Low | `id, email, role, is_active, created_at` |
| OTP codes table | Must not store codes in `users`; need expiry/used tracking | Low | `id, user_id, code_hash, created_at, expires_at, used_at` |
| OTP stored hashed, not plaintext | Codes in DB plaintext = DB breach exposes active sessions | Low | SHA-256 of code is sufficient (short-lived, no password); bcrypt is overkill |
| SMTP delivery with fallback to response body | Project requirement: codes in API response when SMTP unconfigured | Low | Controlled by `SINODIK_SMTP_*` env var presence |
| Admin-only: list all users | Management feature; admin must see who has accounts | Low | `GET /api/v1/admin/users` |
| Admin-only: promote/demote/disable user | Core management operations defined in PROJECT.md | Low | `PATCH /api/v1/admin/users/{id}` |
| Guard existing CSV upload with admin role | PROJECT.md explicit requirement; currently unguarded | Low | Add `Depends(require_admin)` to existing endpoint |
| User-scoped orders view | Core value proposition: submitter sees only their own data | Low | Filter `Order.user_email == current_user.email` |
| Admin-scoped orders view (all) | Admin must see everything for operational oversight | Low | No email filter on query |
| First-admin bootstrap | Chicken-and-egg: can't promote first admin if no admin exists | Low | Seed via `SINODIK_ADMIN_EMAILS` env var checked at account creation |
| Frontend: login screen | Auth flow must be reachable in the UI | Medium | OTP request form + code entry form; SinodikApp.jsx edit |
| Frontend: "My Orders" view for users | Core user-facing feature | Medium | Tab in SinodikApp.jsx; calls authenticated endpoint |
| Frontend: admin panel tab | Admin management UI; show all orders + user list | Medium | Conditionally rendered based on JWT role claim |
| Auth state in frontend (JWT storage + decode) | Browser must hold and send the token | Low | `localStorage` + `Authorization: Bearer` header on all API calls |

---

## Differentiators

Features that add value for this specific app but are not expected by default.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| OTP in API response as dev fallback | Zero-friction local dev and demo without SMTP setup | Low | Already decided; controlled by env var |
| Matched historical CSV orders on login | User sees orders submitted by their email before they ever logged in | Low | `Order.user_email` already stored; no backfill needed |
| Admin can edit/delete commemorations | Operational correctness; errors happen in CSV data | Medium | PATCH + DELETE on `/api/v1/commemorations/{id}` with admin guard |
| Soft account disable (is_active flag) | Revoke access without destroying history | Low | Check `is_active` in `get_current_user` dependency |
| Role visible in JWT (client-side decode) | Frontend can conditionally render admin tab without an extra API call | Low | Include `role` in JWT payload; decode in browser with `atob` |

---

## Anti-Features

Features to explicitly NOT build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Password-based auth | Adds password storage, hashing, reset flow, breach risk; OTP makes it unnecessary | OTP-only as designed |
| Refresh token rotation | Doubles implementation complexity (two token types, rotation DB table, race conditions) | Single JWT with adequate expiry (30 days); users re-auth via OTP if expired |
| OAuth / social login | This user base (church administrators) doesn't need it; adds 3rd-party dependency | OTP email is sufficient and simpler |
| Server-side sessions / Redis | Adds infrastructure dependency; contradicts the stateless JWT decision | JWT already provides stateless sessions |
| Email confirmation on registration | Registration IS verification — the OTP flow IS the confirmation | Auto-create on first successful OTP |
| TOTP authenticator app support | Requires QR code setup flow, TOTP secret management; massive scope increase | Email OTP covers the use case |
| Granular permissions (beyond two roles) | Two roles (user/admin) cover all defined requirements; ABAC/fine-grained RBAC is premature | `role` field on User; extend only if new requirements emerge |
| Self-serve role upgrade requests | Explicit out-of-scope in PROJECT.md | Admin assigns roles manually |
| Account deletion / GDPR flow | Not requested; adds data retention complexity | Out of scope |
| Audit log | Useful operationally but not required; adds schema and query complexity | Consider in a future milestone |
| Per-user API keys | No machine-to-machine use case defined | JWT covers the browser session use case |
| Multi-tenancy / per-church isolation | Single church deployment; no tenant concept needed | Single `is_admin` boundary is sufficient |

---

## Feature Dependencies

```
OTP codes table (schema) ──────────────────────┐
users table (schema) ─────────────────────────┐│
                                               ││
OTP request endpoint ──────────────────────────┼┘
  → requires: users table, OTP codes table     │
  → requires: SMTP service / fallback          │
                                               │
OTP verify endpoint ──────────────────────────►├──→ JWT issuance
  → requires: OTP request endpoint             │      → requires: JWT secret config
  → requires: OTP expiry + single-use logic    │
  → requires: Account auto-creation            │
                                               │
get_current_user dependency ───────────────────┼──→ All protected routes
  → requires: JWT verification                 │
  → requires: users table (is_active check)    │
                                               │
require_admin dependency ──────────────────────┤
  → requires: get_current_user                 │
                                               │
Guard CSV upload ─────────────────────────────►┤
  → requires: require_admin                    │
                                               │
Admin user management endpoints ──────────────►┤
  → requires: require_admin                    │
                                               │
User orders endpoint ─────────────────────────►┤
  → requires: get_current_user                 │
                                               │
First-admin bootstrap ─────────────────────────┘
  → requires: account auto-creation logic
  → requires: SINODIK_ADMIN_EMAILS env var

Frontend login screen ─────────────────────────→ OTP request + verify endpoints
Frontend My Orders tab ────────────────────────→ User orders endpoint + auth state
Frontend admin panel ──────────────────────────→ Admin endpoints + role in JWT
Auth state (JWT storage) ──────────────────────→ All frontend API calls
```

---

## MVP Recommendation

The entire feature set described in PROJECT.md is already tightly scoped for an MVP. Build in this order:

1. **Schema + Alembic migrations** — `users` and `otp_codes` tables; foundation for everything
2. **OTP flow endpoints** — request + verify + account auto-creation + JWT issuance; core auth is done
3. **FastAPI auth dependencies** — `get_current_user` and `require_admin`; gates for all protected routes
4. **Guard existing routes** — CSV upload + new user/admin endpoints; enforces RBAC
5. **Frontend auth layer** — login screen, JWT storage, conditional rendering; makes auth usable

Defer to a follow-up milestone:
- Admin commemoration edit/delete (functional but lower priority than access control)
- Audit logging

---

## Sources

- Project requirements: `/Users/kolia/sinodic/.planning/PROJECT.md`
- Existing data model: `/Users/kolia/sinodic/app/models/models.py`
- OTP auth security patterns: training knowledge (HIGH confidence — stable, well-established domain)
- JWT best practices: training knowledge (HIGH confidence — RFC 7519 + industry consensus)
- FastAPI dependency injection patterns: training knowledge (HIGH confidence — matches existing codebase style)
