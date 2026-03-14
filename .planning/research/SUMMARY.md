# Project Research Summary

**Project:** Sinodic — Auth Milestone (OTP Email + JWT + RBAC)
**Domain:** Email-OTP authentication with two-role RBAC on an existing async FastAPI app
**Researched:** 2026-03-14
**Confidence:** HIGH

## Executive Summary

Sinodic needs passwordless authentication added to an existing, well-structured FastAPI async app. The approach — email OTP + stateless JWT + two-role RBAC — is a mature, well-documented pattern with no ambiguity in implementation choices. All four research files agree on the same dependency-ordered build sequence: schema first, then auth service logic, then route guards, then frontend. The technology choices are minimal and deliberate: PyJWT (replacing the deprecated `python-jose`), `aiosmtplib` for async SMTP, and Python stdlib `secrets`/`hashlib`/`hmac` for everything else. Two new packages total.

The recommended approach maps cleanly onto the existing codebase conventions. The existing layered architecture (routes → services → models → PostgreSQL) is extended with three new files (`auth_service.py`, `email_service.py`, `deps.py`), one new route file (`auth.py`), two new ORM models (`User`, `OtpCode`), and an Alembic migration. Existing routes are guarded without signature changes, using FastAPI's `dependencies=[]` parameter. Frontend auth is additive to `SinodikApp.jsx` — no build toolchain changes needed.

The primary risks are security-related and front-loaded in Phase 1: OTP brute-force attacks (must ship rate limiting with the verify endpoint), timing attacks on code comparison (use `hmac.compare_digest`), a weak or defaulted JWT secret (must have no default value in `Settings`), and the first-admin bootstrap chicken-and-egg (solved via `SINODIK_ADMIN_EMAIL` env var in the startup lifespan hook). None of these are novel problems — each has a standard, tested solution. The implementation can proceed with high confidence.

---

## Key Findings

### Recommended Stack

The auth milestone adds exactly two new pip packages to the project. PyJWT >=2.9 handles JWT encoding and decoding — it is the current official FastAPI recommendation, replacing the unmaintained `python-jose` (abandoned 2022, open CVEs). `aiosmtplib` >=3.0 handles async SMTP email delivery without blocking the uvicorn event loop. Everything else — OTP code generation (`secrets`), OTP hashing (`hashlib`), constant-time comparison (`hmac`), and Bearer token extraction (`fastapi.security.HTTPBearer`) — is stdlib or already bundled with FastAPI.

**Core technologies:**
- `PyJWT >=2.9`: JWT encode/decode — official FastAPI recommendation, replaces deprecated `python-jose`
- `aiosmtplib >=3.0`: async SMTP — native async, no thread-pool workarounds
- `secrets` (stdlib): CSPRNG OTP generation — `secrets.randbelow(1_000_000)` for 6-digit codes
- `hashlib` (stdlib): SHA-256 OTP hashing — appropriate for short-lived throwaway tokens
- `hmac` (stdlib): constant-time code comparison — required to prevent timing attacks
- `fastapi.security.HTTPBearer`: Bearer token extraction — bundled, no extra library
- Existing: SQLAlchemy 2.0 async + asyncpg + Pydantic settings — no changes needed

JWT algorithm: HS256 (symmetric). Sufficient for a single-service self-hosted deployment; RS256 only adds value for multi-service token sharing, which is out of scope.

### Expected Features

The feature set is fully defined by PROJECT.md and has been validated against security best practices. No feature is ambiguous. The entire scope is appropriately sized for a single milestone.

**Must have (table stakes):**
- OTP request endpoint — entry point for passwordless flow
- OTP verification endpoint — issues JWT on success, single-use enforcement
- OTP expiry enforcement (10–15 min) — industry standard
- OTP rate limiting / attempt counting — 6-digit code is trivially brute-forceable without it
- Secure OTP code generation via `secrets` module
- Account auto-creation on first successful OTP — no pre-registration step
- JWT issuance with `sub` (email), `role`, `exp` claims
- JWT verification dependency (`get_current_user`) for all protected routes
- Role guard dependency (`require_admin`) wrapping `get_current_user`
- `users` table (email, role, is_active, created_at, last_login_at)
- `otp_codes` table (email, code_hash, expires_at, used_at, attempt_count)
- Guard existing `/api/v1/upload/csv` with `require_admin`
- Admin user management endpoints: list, promote/demote, disable
- User-scoped orders view (filtered by `current_user.email`)
- First-admin bootstrap via `SINODIK_ADMIN_EMAIL` env var
- Frontend login screen (OTP request + code entry forms)
- Frontend "My Orders" tab for authenticated users
- Frontend admin panel tab (conditionally rendered by JWT role claim)
- JWT storage in `localStorage` + `Authorization: Bearer` header on all API calls

**Should have (differentiators):**
- OTP code in API response as dev fallback (controlled by explicit `SINODIK_OTP_PLAINTEXT_FALLBACK` boolean, default False)
- Historical CSV orders visible on first login — `Order.user_email` already stored, no backfill needed
- Soft account disable (`is_active` flag) — revoke access without destroying order history
- Admin commemoration edit/delete (`PATCH`/`DELETE` on `/api/v1/commemorations/{id}`)
- `apiFetch()` wrapper in frontend — single point for adding Authorization header

**Defer to follow-up milestone:**
- Refresh token rotation — doubles complexity, single JWT with adequate TTL is sufficient
- Audit logging — useful but not required
- Granular permissions beyond user/admin
- OAuth / social login
- Account deletion / GDPR flow

### Architecture Approach

The new auth system extends the existing three-layer architecture (routes → services → models) without restructuring it. Three new service files (`auth_service.py`, `email_service.py`) and one new dependency module (`deps.py`) handle all auth logic. A new route file (`auth.py`) exposes the OTP endpoints. `User` and `OtpCode` ORM models are added to the existing models file or a new `auth_models.py`. Existing route functions require no signature changes — guards attach via `dependencies=[Depends(require_admin)]` on the route decorator. The `config.py` gains new SINODIK_-prefixed settings fields.

**Major components:**
1. `app/services/auth_service.py` — OTP generation, verification, user lookup/create, JWT issuance
2. `app/services/email_service.py` — async SMTP sending via aiosmtplib; dev fallback returns code string
3. `app/api/deps.py` — `get_current_user` (JWT decode + is_active DB check) and `require_admin` (role check)
4. `app/api/routes/auth.py` — `POST /auth/request-otp`, `POST /auth/verify-otp`, `GET /auth/me`
5. `User` + `OtpCode` ORM models — schema only, no business logic
6. Alembic migration — `users` and `otp_codes` tables with indexes and constraints
7. `SinodikApp.jsx` additions — login state, token storage, auth headers, conditional tabs

**Key patterns:**
- `Depends(get_db)` injected into auth dependencies — never create sessions manually
- Role embedded in JWT payload to avoid DB round-trip on every request; `is_active` checked against DB on every authenticated request (one indexed query)
- `oauth2_scheme = HTTPBearer(auto_error=False)` in `deps.py` — allows optional auth on some routes
- Admin bootstrap via idempotent upsert in lifespan hook — safe to run every startup

### Critical Pitfalls

1. **OTP timing attack via `==` comparison** — use `hmac.compare_digest(stored_hash, candidate_hash)` on every OTP comparison; never plain Python equality on secret strings. Guard against `None` inputs before calling.

2. **OTP brute-force (no rate limiting)** — add `attempt_count` column to `otp_codes` table; invalidate the code after 3–5 failed attempts; this must ship with the verify endpoint, not as a follow-up.

3. **Weak or defaulted JWT secret** — declare `jwt_secret: str` in Pydantic `Settings` with no default value; Pydantic raises `ValidationError` at startup if `SINODIK_JWT_SECRET` is unset; no fallback in docker-compose.

4. **OTP plaintext fallback silently active in production** — gate the dev fallback on an explicit `SINODIK_OTP_PLAINTEXT_FALLBACK: bool = False` setting; SMTP failure raises 503, not a silent code return.

5. **Async session misuse in auth dependencies** — use `Depends(get_db)` in `deps.py`; never create `async_session()` manually; eagerly load only `role` and `is_active` columns; never rely on lazy-loading in async context.

6. **Admin bootstrap chicken-and-egg** — wire `SINODIK_ADMIN_EMAIL` upsert into the existing lifespan hook on day one; without it, a fresh production deploy cannot perform any admin action.

7. **Email case sensitivity creating duplicate accounts** — normalize `email.lower().strip()` at every entry point; add `CHECK (email = lower(email))` DB constraint in the migration.

---

## Implications for Roadmap

All research files independently converged on the same build order, driven by hard dependencies. The sequence is unambiguous.

### Phase 1: Schema and Configuration Foundation

**Rationale:** Every other component depends on the ORM models and DB tables. Cannot write auth service code without User and OtpCode models. Config changes are also needed before any service code. This must be the first thing committed.

**Delivers:** `users` table, `otp_codes` table (with `attempt_count`, `invalidated_at`, `used_at`), `User` and `OtpCode` ORM models, updated `config.py` with JWT/SMTP/OTP settings, Alembic migration.

**Features addressed:** users table, otp_codes table, first-admin env var config, email normalization constraint.

**Pitfalls avoided:** Email case mismatch (Pitfall 14) — add DB CHECK constraint here; Alembic ordering (Pitfall 12) — create users table before any FK references; admin bootstrap (Pitfall 4) — SINODIK_ADMIN_EMAIL field added to config now.

### Phase 2: Auth Service Core (OTP Flow + JWT)

**Rationale:** Business logic layer before HTTP layer — matches the existing codebase convention and makes auth_service independently unit-testable without spinning up HTTP.

**Delivers:** `auth_service.py` (OTP generation, verify, user auto-create, JWT issuance), `email_service.py` (aiosmtplib SMTP + dev fallback), admin bootstrap upsert in `main.py` lifespan hook.

**Features addressed:** OTP request/verify logic, account auto-creation, JWT issuance with role claim, SMTP delivery, dev fallback controlled by explicit boolean flag.

**Pitfalls avoided:** Timing attack (Pitfall 1) — `hmac.compare_digest` here; brute-force (Pitfall 2) — attempt_count logic here; weak JWT secret (Pitfall 3) — no default in Settings enforced; plaintext fallback in prod (Pitfall 9) — explicit boolean flag; admin bootstrap (Pitfall 4) — lifespan hook.

### Phase 3: Auth Routes and Dependencies

**Rationale:** HTTP layer after service layer. `deps.py` must exist before any route can declare `Depends(get_current_user)`. Auth routes expose the OTP flow to the outside world.

**Delivers:** `app/api/routes/auth.py` (`POST /auth/request-otp`, `POST /auth/verify-otp`, `GET /auth/me`), `app/api/deps.py` (`get_current_user`, `require_admin`), router registration in `main.py`.

**Features addressed:** OTP request endpoint, OTP verify endpoint, JWT verification dependency, role guard dependency.

**Pitfalls avoided:** Async session misuse (Pitfall 6) — establish correct `Depends(get_db)` pattern in deps.py; is_active bypass (Pitfall 10) — DB check on every authenticated request in `get_current_user`.

### Phase 4: Route Guards and New Protected Endpoints

**Rationale:** Guards attach to existing routes only after `require_admin` exists. This is the integration risk phase — all guarded routes must be tested. The CSV upload guard must ship in this phase, not a later one.

**Delivers:** `require_admin` guard on `POST /api/v1/upload/csv`, commemoration edit/delete routes; new `GET /api/v1/names/by-user` (user-scoped), `GET /api/v1/admin/users`, `PATCH /api/v1/admin/users/{id}` (admin user management).

**Features addressed:** Guard CSV upload, user-scoped orders view, admin user management, admin commemoration edit/delete.

**Pitfalls avoided:** CSV endpoint left unguarded (Pitfall 11) — guard ships here, same phase as admin role; no existing route function signatures change (Architecture anti-pattern) — `dependencies=[Depends(...)]` on decorator only.

### Phase 5: Frontend Auth Integration

**Rationale:** Frontend is the last layer — it depends on all backend endpoints being stable. Decision on JWT storage (localStorage + Authorization header) must be explicit before writing any frontend code.

**Delivers:** Login screen (OTP request form + code entry form), `apiFetch()` wrapper with Authorization header, JWT stored in localStorage, "My Orders" tab, admin panel tab (conditionally rendered on `role === "admin"` from JWT payload decoded with `atob`), auth state persistence across page loads.

**Features addressed:** Frontend login screen, My Orders view, admin panel, auth state management.

**Pitfalls avoided:** CORS/localStorage confusion (Pitfall 5) — localStorage + Authorization header is the explicit, documented choice for this SPA; single `apiFetch()` wrapper ensures no raw `fetch()` calls bypass auth header.

### Phase Ordering Rationale

- Schema before services because ORM models must exist before service code can reference them.
- Services before routes because the service layer is independently testable and the HTTP layer is a thin wrapper over it — matching the existing codebase convention.
- `deps.py` (Phase 3) before guards (Phase 4) because guards import from `deps.py`.
- Frontend last because it requires all backend API endpoints to be stable.
- Admin bootstrap logic (lifespan hook + env var) must be in Phase 2 so that Phase 4 can test admin routes on a fresh install without direct DB access.
- OTP rate limiting (`attempt_count`) must be in Phase 2 (schema) and enforced in Phase 2 (service) — it cannot be deferred because the verify endpoint is a brute-force surface the moment it ships.

### Research Flags

Phases with well-documented patterns (skip `/gsd:research-phase`):
- **Phase 1 (Schema):** SQLAlchemy 2.0 async model definition and Alembic migrations are extensively documented and match existing codebase patterns exactly.
- **Phase 2 (Auth Service):** OTP generation, hashing, and JWT issuance with PyJWT are covered in detail in STACK.md with verified official sources.
- **Phase 3 (Routes and Deps):** FastAPI dependency injection patterns for auth are covered verbatim in official FastAPI security docs and match the architecture research.
- **Phase 4 (Guards):** FastAPI `dependencies=[]` parameter is documented and simple; the new protected endpoints follow existing service patterns.
- **Phase 5 (Frontend):** The frontend is vanilla JSX + CDN React with no build step — localStorage and fetch wrapper patterns are standard.

No phase requires additional `/gsd:research-phase` research. All implementation decisions are fully resolved by this research round.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyJWT and aiosmtplib choices verified against official FastAPI docs (2026-03-14). Stdlib choices (secrets, hashlib, hmac) are unambiguous. |
| Features | HIGH | Feature set derived from PROJECT.md (ground truth) + validated against security best practices. Well-established OTP/JWT/RBAC domain. |
| Architecture | HIGH | Build order and component boundaries verified against existing codebase conventions. Official FastAPI security docs confirm all dependency injection patterns. |
| Pitfalls | HIGH | OTP brute-force, timing attacks, JWT secret weaknesses, and async SQLAlchemy session misuse are all well-documented with standard mitigations. |

**Overall confidence:** HIGH

### Gaps to Address

- **aiosmtplib exact API surface:** STACK.md notes MEDIUM confidence on aiosmtplib (WebFetch denied during research; confirmed via training data). If the async context manager API differs from `async with aiosmtplib.SMTP(...) as smtp`, check the aiosmtplib 3.x docs when implementing `email_service.py`. Low-risk gap — the library is well-established.

- **SINODIK_ADMIN_EMAIL vs. SINODIK_ADMIN_EMAILS:** STACK.md uses singular `SINODIK_ADMIN_EMAIL`, PITFALLS.md uses `SINODIK_INITIAL_ADMIN_EMAIL`, ARCHITECTURE.md uses `SINODIK_ADMIN_EMAIL`. Standardize on `SINODIK_ADMIN_EMAIL` (single value) in Phase 1 config. No functional impact — just needs consistency.

- **OTP TTL:** STACK.md suggests 10 minutes, ARCHITECTURE.md suggests 15 minutes. The Pitfalls file says 10–15 min as industry standard. Decide at implementation time; 10 minutes is more conservative and preferable. Set as `SINODIK_OTP_TTL_MINUTES` with a default of 10.

- **JWT TTL:** Research recommends 60 minutes for access tokens (PITFALLS.md, Pitfall 7) but STACK.md uses 7 days (10080 minutes) as default. These reflect different security postures. Recommendation: use 60 minutes as the default, document re-auth via OTP as the intended flow. Resolve this in Phase 1 config before any JWT code is written.

---

## Sources

### Primary (HIGH confidence)
- FastAPI security tutorial (JWT): https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — PyJWT usage, HTTPBearer pattern, dependency injection
- FastAPI OAuth2 scopes: https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/ — RBAC patterns
- FastAPI path operation dependencies: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-in-path-operation-decorators/ — guard attachment without signature changes
- FastAPI release notes (0.135.1): https://fastapi.tiangolo.com/release-notes/ — version verification
- Python stdlib: `secrets`, `hashlib`, `hmac` — OTP generation, hashing, constant-time comparison
- RFC 7519 + OWASP JWT Cheat Sheet — JWT security best practices
- Existing codebase (read directly): `app/models/models.py`, `app/config.py`, `app/database.py`, `app/main.py` — confirmed conventions
- PROJECT.md — authoritative feature requirements

### Secondary (MEDIUM confidence)
- aiosmtplib >=3.0 — async SMTP for FastAPI; community-established pattern; WebFetch denied during research, confirmed via training data and ecosystem knowledge

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
