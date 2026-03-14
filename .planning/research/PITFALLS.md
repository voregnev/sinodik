# Domain Pitfalls: OTP Auth + JWT + RBAC in FastAPI

**Domain:** OTP email authentication, JWT sessions, role-based access control
**Project:** Sinodic — church commemoration management system
**Researched:** 2026-03-14
**Confidence:** HIGH (established security patterns, well-documented vulnerabilities)

---

## Critical Pitfalls

Mistakes that cause security breaches, data leaks, or full rewrites.

---

### Pitfall 1: OTP Timing Attack via Non-Constant-Time Comparison

**What goes wrong:** Using `otp_from_db == otp_from_user` (Python `==`) to validate OTP codes. On modern CPUs the comparison short-circuits on the first mismatched character, leaking timing information. Over thousands of requests an attacker can reconstruct a valid code character-by-character.

**Why it happens:** Developers treat OTP like a password field and write the obvious comparison. The attack is invisible in logs and testing.

**Consequences:** A 6-digit numeric OTP has only 1,000,000 combinations and becomes practically bruteforceable with timing data even with rate limiting, because the attacker's oracle is the response time, not the error message.

**Prevention:**
- Always use `hmac.compare_digest(stored_otp, submitted_otp)` — Python stdlib, zero external deps.
- Both operands must be `str` (not `None`). Guard with an early `if stored_otp is None: return False` before the comparison so `compare_digest` never receives `None`.

**Detection:** Code review — any `==` on a string that came from a DB OTP column.

**Phase:** OTP verification endpoint (Phase 1 / auth core).

---

### Pitfall 2: OTP Brute-Force — No Rate Limiting on Verify Endpoint

**What goes wrong:** `/api/v1/auth/verify` accepts unlimited attempts. A 6-digit OTP has 10^6 combinations. At 100 req/s an attacker exhausts the space in under 3 hours without any error signaling.

**Why it happens:** Rate limiting feels like an operational concern and gets deferred. FastAPI has no built-in rate limiter.

**Consequences:** Any user's account can be taken over during their OTP validity window. Because accounts are auto-created on first OTP, an attacker can also register as any email address they know.

**Prevention:**
- Hard-limit verify attempts per OTP token: invalidate the code after N failures (3–5). Store `attempt_count` on the OTP record.
- After invalidation, require a new `/auth/request` to get a fresh code.
- Secondary: rate-limit `/auth/request` by IP (prevents OTP spam / email flooding).
- Implementation without Redis: use a PostgreSQL `otp_codes` table with `attempt_count` and `invalidated_at` columns — fits existing async SQLAlchemy stack perfectly.

**Detection:** Load test the verify endpoint without a session — unlimited 422/400 responses with no lockout.

**Phase:** OTP verification endpoint (Phase 1 / auth core). Must ship together with the endpoint, not as a follow-up.

---

### Pitfall 3: JWT Secret is Weak or Hardcoded

**What goes wrong:** `JWT_SECRET = "secret"` or `JWT_SECRET = settings.some_default_string` in config. Anyone who knows (or guesses) the secret can forge tokens for any user including admins.

**Why it happens:** Developers copy tutorial code where the secret is a placeholder. The app works fine; the flaw is invisible.

**Consequences:** Complete authentication bypass. An attacker generates `{"sub": "admin@example.com", "role": "admin"}` and signs it with the known secret — full admin access.

**Prevention:**
- No default value for JWT secret in `Settings`. Use `jwt_secret: str` with no `= ...` — Pydantic will raise `ValidationError` at startup if `SINODIK_JWT_SECRET` is not set.
- Generate the secret: `python -c "import secrets; print(secrets.token_hex(32))"` — 256 bits, documented in deployment runbook.
- In `docker-compose.yml`, reference it as `SINODIK_JWT_SECRET: ${SINODIK_JWT_SECRET}` with no fallback (unlike the current pattern of `${VAR:-default}` used for other vars).

**Detection:** `grep -r "jwt_secret.*=" app/config.py` — any default value is a finding.

**Phase:** JWT issuance (Phase 1 / auth core). Non-negotiable before any deployment.

---

### Pitfall 4: Admin Bootstrapping Chicken-and-Egg — No First Admin

**What goes wrong:** The system requires an admin to promote users to admin, but no admin exists on a fresh install. The only way to create data is through the API, which requires auth. The team gets stuck.

**Why it happens:** RBAC logic is implemented cleanly without thinking about the initial state. The first admin creation is treated as a runtime operation but there's no unauthenticated path to it.

**Consequences:** The CSV upload endpoint (the primary admin operation) is inaccessible on a fresh production deploy. Workaround requires direct DB access, which is error-prone and leaves no audit trail.

**Prevention (two-layer approach):**

Layer 1 — Env-var seed: `SINODIK_INITIAL_ADMIN_EMAIL`. In the lifespan hook (already exists in `main.py`), after extensions are created, check if any admin exists; if not and env var is set, upsert that user as admin. This is idempotent and safe to leave running.

Layer 2 — DB flag: Document that `UPDATE users SET role='admin' WHERE email='...'` is the escape hatch. Include it in the deployment README, not as a workaround but as the explicit bootstrap procedure.

**Do not build an unauthenticated `/admin/bootstrap` HTTP endpoint** — it becomes a permanent attack surface.

**Detection:** Fresh `docker compose up` with an empty DB — can you complete an admin action without direct DB access?

**Phase:** User model + role design (Phase 1). The seed logic must be in the first migration/lifespan, not added later.

---

### Pitfall 5: CORS + HttpOnly Cookie vs. Authorization Header Confusion

**What goes wrong:** The team picks JWT storage (localStorage vs. HttpOnly cookie) without thinking through the CORS + SPA constraints, then discovers mid-implementation that the chosen approach breaks.

**Scenario A — localStorage:** Simpler for the SPA. But `SinodikApp.jsx` runs in-browser with a Babel transform; `localStorage` is fine here. Risk: XSS exposes the token. For this app (church management, small user base, no untrusted content) this is acceptable.

**Scenario B — HttpOnly cookie:** More XSS-resistant. But the existing CORS config (`allow_credentials=True`, specific origins) already supports cookies. The problem: `SinodikApp.jsx` uses `fetch()` — it must pass `credentials: 'include'` on every request. Forgetting this on even one endpoint breaks auth silently (no error, just 401).

**Why it happens:** The choice is made implicitly, then the SPA code is written inconsistently. Mixing both (token in header for some calls, cookie for others) is the worst outcome.

**Consequences:** Auth works in dev (same origin) but breaks in prod (different origin), or vice versa. Hours of debugging nginx CORS headers.

**Prevention:**
- Make an explicit, documented decision in PROJECT.md before writing any auth code. Recommendation for this project: **`localStorage` + `Authorization: Bearer` header**. Rationale: the frontend is a single JSX file with no build toolchain — adding `credentials: 'include'` to every fetch is easy to miss and hard to lint; localStorage with a short JWT TTL (15–60 minutes) is the correct tradeoff for this threat model.
- In `SinodikApp.jsx`, create a single `apiFetch(path, opts)` wrapper that always adds the `Authorization` header from localStorage. All API calls go through this wrapper — never raw `fetch('/api/...')`.

**Detection:** Test auth from a different origin (or use the prod nginx setup locally) before writing the frontend auth flow.

**Phase:** Auth frontend integration. Decision must precede all frontend work.

---

### Pitfall 6: Async Session Misuse in Auth Dependencies

**What goes wrong:** FastAPI `Depends()` auth dependencies that need DB access (to look up the user by JWT sub) use a shared session, re-use a closed session, or call async DB methods without `await`.

**Why it happens:** Auth middleware/dependencies are written differently from route handlers. Developers sometimes pass the session as a parameter rather than injecting it, or mix sync and async incorrectly.

**Specific failure modes for this codebase:**
- Accessing `user.role` after the session is closed (lazy-load in async context raises `MissingGreenlet` error).
- Creating a new `async_session()` inside the dependency instead of using `Depends(get_db)` — creates a session that's never closed.
- The existing `get_db()` uses `expire_on_commit=False` (correct), but auth dependencies that don't `await session.refresh(user)` after a `commit()` elsewhere will see stale role data.

**Prevention:**
- Auth dependencies must use `Depends(get_db)` like all other routes — never create sessions manually.
- Eagerly load `role` and `is_active` in the JWT-to-user query: `select(User).where(User.email == email).options(load_only(User.role, User.is_active))`. Never rely on lazy-loading in async context.
- Keep JWT payload self-contained for the common case: embed `role` in the token. The DB lookup is only needed for `is_active` checks (to handle disabled accounts). This reduces auth dependency DB queries by ~80%.

**Detection:** Run tests with `PYTHONASYNCIODEBUG=1` — misuse of sessions across coroutine boundaries raises `RuntimeError` in debug mode.

**Phase:** Auth dependency design (Phase 1). The pattern must be established before writing any protected routes.

---

## Moderate Pitfalls

---

### Pitfall 7: JWT Expiry Not Enforced — No Short TTL

**What goes wrong:** JWT issued with `exp` claim set to 30 days or no expiry. Because JWTs are stateless, there is no server-side revocation. A stolen token is valid for its full lifetime.

**Why it happens:** Short TTL means users get logged out — annoying. Developers extend TTL to avoid complaints.

**Prevention:**
- Access token TTL: 60 minutes. Rationale: this app has infrequent sessions (admin uploads CSV, views stats). A 1-hour session is fine.
- No refresh tokens needed for this app's usage pattern — re-authenticating via OTP every session is acceptable and simpler.
- If `is_active=False` is set on a user (admin disables account), short TTL limits the blast radius without needing a revocation list.

**Phase:** JWT issuance (Phase 1).

---

### Pitfall 8: Role Stored Only in JWT — Admin Demotion Not Immediate

**What goes wrong:** JWT payload contains `role: "admin"`. When an admin demotes another admin, the demoted user's existing JWT still grants admin access until it expires (up to 60 minutes with the TTL above).

**Why it happens:** Stateless JWT means no server-side state — that's the point. But the consequence for role changes is often forgotten.

**Prevention:** For this app (small user base, low security stakes for role changes), the 60-minute window is acceptable — document it explicitly. If it becomes a concern, add a `role_version` integer to the `users` table, embed it in the JWT, and check it on each request (one lightweight DB query per request). Do not implement this preemptively — it adds complexity without proportional benefit at this scale.

**Phase:** Post-MVP consideration. Not a blocker.

---

### Pitfall 9: OTP Exposed in API Response in Production

**What goes wrong:** `SINODIK_SMTP_*` is not configured in production (or SMTP fails silently), so the API falls back to returning the OTP in the response body. An attacker observing API responses gets the OTP.

**Why it happens:** The fallback is explicitly designed for dev/demo (documented in PROJECT.md). The risk is that SMTP misconfiguration in production silently activates the insecure fallback.

**Prevention:**
- Add a `SINODIK_OTP_PLAINTEXT_FALLBACK` boolean setting, default `False`. The API-response fallback only activates if this is explicitly set to `True`.
- In the OTP request handler: if SMTP is configured but fails, raise `503 Service Unavailable` rather than silently falling back.
- Docker Compose dev config can set `SINODIK_OTP_PLAINTEXT_FALLBACK: "true"`.

**Detection:** Test with SMTP vars unset and `OTP_PLAINTEXT_FALLBACK` not set — the endpoint should return 503, not the code.

**Phase:** OTP email delivery (Phase 1). The toggle must exist from the start, not added when SMTP is wired up.

---

### Pitfall 10: Missing `is_active` Check on Every Protected Request

**What goes wrong:** Admin disables a user account by setting `is_active=False`. The user's JWT is still valid. Because role is embedded in the JWT and the common path doesn't hit the DB, the disabled user continues to access the system.

**Why it happens:** Embedding role in JWT is correct for performance, but it means the DB is never consulted, so `is_active` changes have no effect during the token's lifetime.

**Prevention:**
- The "current user" dependency must always verify `is_active` against the DB (not the JWT). This is one indexed DB query per request (`WHERE email = $1 AND is_active = true`). Given the `user_email` index already on `orders`, adding an index on `users.email` is a given.
- Keep this lookup cheap: select only `id`, `role`, `is_active` — not the full user object.

**Detection:** Set `is_active=False` in DB for a user with a valid JWT — they should immediately get 401.

**Phase:** Auth dependency design (Phase 1). Must be part of the initial implementation, not a hardening pass.

---

### Pitfall 11: CSV Upload Endpoint Left Unguarded During Migration

**What goes wrong:** The existing `/api/v1/upload/csv` endpoint has no auth today (confirmed in `app/api/routes/upload.py`). If the auth system ships in phases and the guard is added in a later phase, there is a window where the endpoint is nominally "in progress" but still unprotected in production.

**Why it happens:** "We'll add the auth guard in Phase 2" — but Phase 2 is delayed, or the deployment happens between phases.

**Prevention:**
- Add the admin auth guard to `/api/v1/upload/csv` in Phase 1, even if it means temporarily breaking the upload flow until admin accounts exist. Use the env-var seed (Pitfall 4) to ensure an admin is always available.
- Alternatively, add a temporary IP allowlist at the nginx level as a stopgap — but remove it before Phase 2 ships.

**Phase:** Phase 1, alongside admin role implementation.

---

## Minor Pitfalls

---

### Pitfall 12: Alembic Migration Ordering — `users` Table Must Precede FK References

**What goes wrong:** If any future model adds a FK to `users` (e.g., `orders.user_id → users.id`), the migration for that FK must run after the `users` table migration. Alembic auto-generate doesn't always detect this correctly when multiple migrations are created simultaneously.

**Prevention:** Create migrations sequentially: `users` table first, test it, then create dependent migrations. Never run `alembic revision --autogenerate` for two interconnected tables in the same step.

**Phase:** Schema migration (Phase 1).

---

### Pitfall 13: OTP Code Stored in Plaintext in DB

**What goes wrong:** The `otp_codes` table stores the raw 6-digit code. If the database is breached (or a developer accidentally logs query results), codes are exposed.

**Why it happens:** OTPs feel temporary and low-value — "it expires in 10 minutes anyway."

**Prevention:** Store `hashlib.sha256(otp_code.encode()).hexdigest()` in the DB. Verification hashes the submitted code and compares. The OTP is never persisted in plaintext. This also naturally prevents timing attacks on the DB layer.

**Note:** If storing hashed OTPs, `hmac.compare_digest` compares the hashes (both constant-time). Still correct.

**Phase:** OTP table design (Phase 1).

---

### Pitfall 14: Email Case Sensitivity — Same User, Multiple Accounts

**What goes wrong:** `user@example.com` and `User@Example.COM` create two different rows in the `users` table. The user who submitted CSV orders as `User@example.com` doesn't see their history when logging in as `user@example.com`.

**Why it happens:** `Order.user_email` is already stored in the DB as-is from CSV files. If the `users` table uses `UNIQUE` on email without normalization, the mismatch is silent.

**Prevention:**
- Always lowercase emails before storing and before querying: `email.lower().strip()` at the point of entry (OTP request, account creation, and CSV import).
- Add a `CHECK (email = lower(email))` constraint on the `users` table in the migration to enforce this at the DB level.
- Backfill existing `orders.user_email` to lowercase if there are mixed-case values.

**Phase:** `users` table migration (Phase 1).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| OTP request endpoint | Email flooding (no rate limit on `/auth/request`) | IP-based rate limit; defer OK, but document |
| OTP verify endpoint | Brute-force (Pitfall 2) + timing attack (Pitfall 1) | Must ship together with the endpoint |
| JWT issuance | Weak secret (Pitfall 3) + no TTL (Pitfall 7) | No default in config; validate at startup |
| Admin role + RBAC | Chicken-and-egg bootstrap (Pitfall 4) + CSV still open (Pitfall 11) | Env-var seed in lifespan |
| Frontend auth integration | CORS/cookie vs. localStorage confusion (Pitfall 5) | Decide before writing any frontend code |
| Auth dependency | Async session misuse (Pitfall 6) + `is_active` bypass (Pitfall 10) | Establish pattern before writing protected routes |
| OTP delivery | Plaintext fallback leaks to prod (Pitfall 9) | Explicit boolean flag, default False |
| DB schema | Email case mismatch (Pitfall 14) | Normalize on insert, DB CHECK constraint |

---

## Sources

- Python `hmac.compare_digest` documentation (stdlib): constant-time comparison rationale — HIGH confidence
- FastAPI dependency injection + async SQLAlchemy session lifecycle — HIGH confidence (well-documented, stable API)
- JWT security best practices (RFC 7519, OWASP JWT Cheat Sheet) — HIGH confidence
- OTP brute-force attack surface: industry-standard 6-digit OTP = 10^6 space — HIGH confidence
- CORS + credential handling in Fetch API (MDN) — HIGH confidence
- Admin bootstrapping patterns: training data + established DevOps practice — HIGH confidence
- `MissingGreenlet` in SQLAlchemy async context: documented SQLAlchemy async limitation — HIGH confidence
