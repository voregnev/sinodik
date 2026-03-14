# Technology Stack — Auth Milestone

**Project:** Sinodic user authentication (OTP + JWT)
**Researched:** 2026-03-14
**Scope:** Adding OTP-via-email + JWT sessions to existing FastAPI 0.135 / Python 3.14 / SQLAlchemy 2.0 async / PostgreSQL 18 app

---

## Recommended Stack

### JWT Token Management

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PyJWT | >=2.9 | Encode/decode JWT access tokens | Official FastAPI recommendation (as of 2026); actively maintained; replaces deprecated `python-jose` which has no maintained cryptography backend. Uses `jwt.encode()` / `jwt.decode()` directly — no wrapper abstraction needed. |

**Confidence: HIGH** — verified via official FastAPI security tutorial (fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).

Algorithm choice: **HS256** (HMAC-SHA256). Symmetric — one secret, no key pair management. Sufficient for a single-service deployment. RS256 only makes sense when multiple services need to verify tokens independently; this app has one API.

No `python-jose` — it is unmaintained (last release 2022, open CVEs on its `ecdsa` dependency). FastAPI docs switched to PyJWT.

No `fastapi-jwt-auth`, `fastapi-security`, or similar wrapper libraries. They add abstraction without benefit and lag behind FastAPI releases.

### OTP Code Generation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `secrets` (stdlib) | Python 3.14 built-in | Generate cryptographically secure numeric OTPs | `secrets.randbelow(10**6)` produces a 6-digit code with CSPRNG. No dependency. TOTP libraries (pyotp) are overkill — they add a shared secret management layer designed for authenticator apps, not email delivery. |

**Confidence: HIGH** — Python stdlib, no external dependency needed.

No `pyotp` — it is designed for TOTP/HOTP flows where the user has an authenticator app. Email OTP is simpler: generate a random code, store it hashed in the DB with an expiry, verify once. No shared TOTP secret needed.

### Email Delivery

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `aiosmtplib` | >=3.0 | Async SMTP email sending | Pure-async SMTP client; no thread pool workaround needed. Works natively with asyncio event loop that FastAPI/uvicorn runs. Supports STARTTLS, SSL, plain SMTP. Simple API: `await aiosmtplib.send(message, ...)`. |

**Confidence: MEDIUM** — aiosmtplib is the standard async SMTP choice for FastAPI apps; confirmed by community patterns and FastAPI ecosystem. Version pinned to >=3.0 for Python 3.12+ compatibility (3.x dropped Python 3.7 support and modernized the async interface).

No `fastapi-mail` — it wraps aiosmtplib but adds Jinja2 template dependency and abstraction that is not needed for a single plaintext OTP email. Adds 2 dependencies for no benefit here.

No stdlib `smtplib` — it is synchronous and would block the async event loop.

### Password/Secret Hashing (OTP storage)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `hashlib` (stdlib) | Python 3.14 built-in | Hash OTP codes before storing in DB | OTP codes are short-lived (10 minutes) and single-use. SHA-256 via `hashlib.sha256()` is sufficient — the attack surface is minimal (attacker needs live DB access AND the code before expiry). No bcrypt/argon2 needed: those are for long-lived password storage. Storing the raw code would be acceptable too, but a single hash step costs nothing. |

**Confidence: HIGH** — stdlib, no dependency.

Note: `pwdlib` / `passlib` / `argon2-cffi` are for password hashing (designed to be slow). OTP codes are throwaway tokens — they do not need slow KDFs.

### FastAPI Security Integration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `fastapi.security.HTTPBearer` | bundled with FastAPI 0.135 | Extract Bearer token from Authorization header | Built-in. Returns the raw token string; PyJWT then decodes it. No extra library. |

Use `Depends(HTTPBearer())` to extract the token, then a second dependency `Depends(get_current_user)` to decode and look up the user. This is the canonical FastAPI pattern.

### Database Schema (new tables)

No new ORM libraries needed. Extend existing SQLAlchemy 2.0 async setup:

**`users` table:**

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `email` | String(255) UNIQUE NOT NULL | Primary identifier; matched to `orders.user_email` |
| `role` | String(20) NOT NULL default `"user"` | `"user"` or `"admin"` |
| `is_active` | Boolean NOT NULL default `True` | Admin can disable |
| `created_at` | DateTime(timezone=True) | |
| `last_login_at` | DateTime(timezone=True) nullable | |

**`otp_codes` table:**

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `email` | String(255) NOT NULL index | Who requested it |
| `code_hash` | String(64) NOT NULL | SHA-256 hex of the 6-digit code |
| `expires_at` | DateTime(timezone=True) NOT NULL | `now + 10 minutes` |
| `used_at` | DateTime(timezone=True) nullable | Set on consumption; NULL = still valid |
| `created_at` | DateTime(timezone=True) | |

One `otp_codes` row per request. Verification: hash candidate code, compare to `code_hash`, check `expires_at > now` and `used_at IS NULL`. After successful verification, set `used_at = now` (prevents replay). Periodic cleanup of expired rows via a simple background task or cron.

### Configuration (new env vars)

Extend existing `app/config.py` `Settings` class (SINODIK_ prefix):

| Variable | Type | Purpose |
|----------|------|---------|
| `SINODIK_JWT_SECRET` | str | HS256 signing key — generate with `openssl rand -hex 32` |
| `SINODIK_JWT_EXPIRE_MINUTES` | int default 10080 | Token lifetime (7 days default) |
| `SINODIK_OTP_EXPIRE_MINUTES` | int default 10 | OTP code lifetime |
| `SINODIK_SMTP_HOST` | str optional | SMTP server hostname |
| `SINODIK_SMTP_PORT` | int default 587 | SMTP port (587 = STARTTLS) |
| `SINODIK_SMTP_USER` | str optional | SMTP username |
| `SINODIK_SMTP_PASSWORD` | str optional | SMTP password |
| `SINODIK_SMTP_FROM` | str optional | From address for OTP emails |
| `SINODIK_ADMIN_EMAIL` | str optional | Seed first admin on startup |

When `SINODIK_SMTP_HOST` is unset, the OTP endpoint returns `{"otp": "123456"}` in the response. This satisfies the dev/demo fallback requirement without a mode flag.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| JWT library | PyJWT >=2.9 | python-jose | Unmaintained since 2022, CVEs in ecdsa dependency, FastAPI docs dropped it |
| JWT library | PyJWT >=2.9 | joserfc | Newer, correct, but less documentation and FastAPI examples available |
| OTP generation | `secrets` stdlib | pyotp | TOTP/HOTP for authenticator apps; overkill for single-use email codes |
| SMTP | aiosmtplib | fastapi-mail | fastapi-mail wraps aiosmtplib but adds Jinja2 dep; not needed for one plaintext email |
| SMTP | aiosmtplib | smtplib (stdlib) | Synchronous; blocks event loop |
| OTP hashing | hashlib SHA-256 | argon2 / bcrypt | KDFs are intentionally slow — wrong tool for short-lived throwaway tokens |
| Session storage | JWT (stateless) | Redis sessions | Adds infrastructure dependency; JWT is sufficient for this scale |
| Auth framework | Hand-rolled | fastapi-users | fastapi-users assumes password auth; its OTP/magic-link support is not a first-class feature and the library would fight the custom flow needed here |

---

## Installation

New packages to add to `requirements.txt`:

```
PyJWT>=2.9
aiosmtplib>=3.0
```

No other new dependencies. Everything else uses Python stdlib (`secrets`, `hashlib`, `smtplib.SMTP` types) or is already in the project (FastAPI, SQLAlchemy, Pydantic, asyncpg, Alembic).

---

## JWT Payload Structure

```python
{
    "sub": "user@example.com",   # email as subject
    "role": "user",              # "user" | "admin" — avoid DB round-trip on every request
    "exp": 1234567890,           # expiry (set by PyJWT from timedelta)
    "iat": 1234560000            # issued-at (PyJWT sets automatically)
}
```

Include `role` in the payload to avoid a DB lookup on every authenticated request. Tradeoff: role changes require re-login to take effect. Acceptable for this use case (small admin team, infrequent role changes). If immediate role revocation is needed later, add a `jti` (JWT ID) and a revocation table — but that is out of scope here.

---

## Auth Flow Summary

```
POST /api/v1/auth/otp/request
  body: { email }
  → generate 6-digit code via secrets.randbelow(10**6)
  → store SHA-256(code) + expiry in otp_codes table
  → if SMTP configured: send email; else return { "otp": code }
  → 200 OK

POST /api/v1/auth/otp/verify
  body: { email, code }
  → hash candidate, compare to stored hash, check expiry + used_at
  → if valid: mark used_at, upsert user (create if first login), issue JWT
  → return { "access_token": "...", "token_type": "bearer" }

GET /api/v1/... (protected endpoints)
  header: Authorization: Bearer <token>
  → HTTPBearer() extracts token
  → jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
  → get_current_user() returns user payload
  → role-check dependency for admin routes
```

---

## Sources

- FastAPI security tutorial (JWT section): https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — HIGH confidence, verified 2026-03-14
- FastAPI release notes (latest version 0.135.1): https://fastapi.tiangolo.com/release-notes/ — HIGH confidence, verified 2026-03-14
- aiosmtplib: community-established async SMTP standard for FastAPI — MEDIUM confidence (WebFetch denied; based on training data + ecosystem knowledge)
- PyJWT vs python-jose deprecation: reflected in FastAPI official docs switch — HIGH confidence
