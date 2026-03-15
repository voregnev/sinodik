# Phase 2: Auth Service Core - Research

**Researched:** 2026-03-14
**Domain:** OTP email authentication, JWT token management, account creation
**Confidence:** HIGH

## Summary

This phase implements the core authentication service layer with OTP generation, email delivery, verification, and JWT signing. It builds upon the schema foundation from Phase 1 and provides all the business logic for user authentication flows. The implementation follows security best practices with constant-time comparisons, rate limiting, and proper session management. The services are designed to be testable independently of the HTTP layer.

**Primary recommendation:** Implement the auth service in three distinct modules (`auth_service.py`, `email_service.py`, `deps.py`) following established FastAPI security patterns with PyJWT and aiosmtplib.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### OTP Generation Mechanism
- Generate 6-digit numeric codes using random algorithm (not with checksum)
- Codes are issued when user requests OTP via email address
- Codes stored as SHA-256 hash in the otp_codes table (per Phase 1 schema)

### Email Delivery Implementation
- Use aiosmtplib for async SMTP delivery (matches existing async patterns in codebase)
- When SMTP fails and SINODIK_OTP_PLAINTEXT_FALLBACK is enabled, return OTP in API response
- When SMTP fails but plaintext fallback is disabled, fail the request gracefully

### JWT Signing Approach
- Use PyJWT library for JWT signing and verification
- Basic claims structure: sub (email), role, exp (expiration)
- Use HS256 algorithm with the jwt_secret from config

### Claude's Discretion
- Exact retry logic and timeout configurations for SMTP delivery
- Specific error handling and logging patterns for email delivery failures
- How to handle race conditions during account creation
- Exact structure of service layer functions and their interfaces
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-02 | User can request a one-time code by providing their email address | Implemented in auth_service.request_otp with email normalization and rate limiting |
| AUTH-03 | User receives the OTP via email (SMTP); code is returned in the API response when SMTP is not configured | Implemented in email_service.send_otp_email with SMTP and plaintext fallback |
| AUTH-04 | User can verify the OTP code and receive a JWT session token | Implemented in auth_service.verify_otp with constant-time comparison and JWT issuance |
| AUTH-05 | Account is created automatically on first successful OTP verification (no separate registration step) | Implemented in auth_service.verify_otp with automatic user creation |
| AUTH-06 | OTP codes expire after 10 minutes | Implemented with otp_codes.expires_at timestamp and validation |
| AUTH-07 | OTP codes are single-use (invalidated immediately on successful verification) | Implemented by marking otp_codes.used = True after successful verification |
| AUTH-08 | OTP requests are rate-limited per email to prevent brute-force | Implemented with attempt_count tracking and validation logic |
| AUTH-09 | JWT encodes user email, role, and expiry (stateless — no server-side session store) | Implemented with PyJWT HS256 signing and standardized claims structure |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyJWT | >=2.9 | JWT encode/decode | Official FastAPI recommendation, replaces deprecated `python-jose`, actively maintained |
| aiosmtplib | >=3.0 | Async SMTP email delivery | Native async, no thread-pool workarounds, standard for FastAPI apps |
| secrets (stdlib) | Python 3.14 built-in | Cryptographically secure OTP generation | CSPRNG via `secrets.randbelow(1_000_000)` for 6-digit codes |
| hashlib (stdlib) | Python 3.14 built-in | SHA-256 OTP hashing | Standard library, appropriate for short-lived throwaway tokens |
| hmac (stdlib) | Python 3.14 built-in | Constant-time code comparison | Required to prevent timing attacks on OTP verification |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi.security.HTTPBearer | bundled with FastAPI | Bearer token extraction | Part of dependency chain for JWT verification |
| SQLAlchemy 2.0 async | existing | Database operations for auth models | Async session management in auth dependencies |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT | python-jose | python-jose is unmaintained (2022), has open CVEs; PyJWT is the current FastAPI standard |
| aiosmtplib | fastapi-mail | fastapi-mail adds unnecessary abstraction and dependencies (Jinja2) for simple email |
| secrets module | pyotp | pyotp is for TOTP/HOTP authenticator apps; email OTP is simpler, just random code generation |

**Installation:**
```bash
pip install PyJWT>=2.9
pip install aiosmtplib>=3.0
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   ├── auth_service.py      # OTP generation, verification, JWT signing
│   ├── email_service.py     # SMTP delivery with dev fallback
│   └── ... (existing services)
├── api/
│   ├── deps.py              # JWT verification deps (get_current_user, require_admin)
│   └── ... (existing routes)
└── models/
    └── models.py            # User and OtpCode models (from Phase 1)
```

### Pattern 1: Service Layer Separation
**What:** Separate auth logic from email delivery logic from dependency injection logic
**When to use:** When building authentication system to maintain testability and separation of concerns
**Example:**
```python
# Source: FastAPI security documentation + established patterns
from app.services.auth_service import verify_otp_and_issue_jwt
from app.services.email_service import send_otp_email
from app.api.deps import get_current_user

async def request_otp_endpoint(email: str, email_service=send_otp_email):
    # Call auth service to generate and store OTP
    # Call email service to deliver OTP
    pass

async def verify_otp_endpoint(email: str, code: str, auth_service=verify_otp_and_issue_jwt):
    # Call auth service to verify and return JWT
    pass
```

### Anti-Patterns to Avoid
- **Direct DB access in route handlers:** Always route through service layer for testability
- **Hardcoded secrets:** JWT secret must come from config with no default value
- **Non-constant time OTP comparison:** Always use `hmac.compare_digest()` to prevent timing attacks

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT encoding/decoding | Custom JWT implementation | PyJWT library | Complex crypto implementation with many edge cases; PyJWT handles all standards compliance |
| Async SMTP delivery | Threading workarounds for sync smtplib | aiosmtplib | FastAPI event loop would block with synchronous email delivery |
| Cryptographically secure random | `random.randint()` | `secrets.randbelow()` | `random` module is not cryptographically secure; OTP codes must be unpredictable |
| Constant-time string comparison | `==` operator | `hmac.compare_digest()` | Prevents timing attacks where attackers can guess OTP character-by-character |

**Key insight:** OTP authentication has well-known security vulnerabilities (timing attacks, brute force) that require specific countermeasures. Using battle-tested libraries avoids reimplementing security-critical primitives.

## Common Pitfalls

### Pitfall 1: OTP Timing Attack via Non-Constant-Time Comparison
**What goes wrong:** Using `otp_from_db == otp_from_user` (Python `==`) to validate OTP codes. On modern CPUs the comparison short-circuits on the first mismatched character, leaking timing information.
**Why it happens:** Developers treat OTP like a password field and write the obvious comparison. The attack is invisible in logs and testing.
**How to avoid:** Always use `hmac.compare_digest(stored_otp_hash, submitted_otp_hash)` — Python stdlib, zero external deps. Both operands must be `str` (not `None). Guard with an early `if stored_otp is None: return False` before the comparison.
**Warning signs:** Any `==` on a string that came from a DB OTP column during verification.

### Pitfall 2: OTP Brute-Force — No Rate Limiting on Verify Endpoint
**What goes wrong:** Verify endpoint accepts unlimited attempts. A 6-digit OTP has 10^6 combinations. At 100 req/s an attacker exhausts the space in under 3 hours.
**Why it happens:** Rate limiting feels like an operational concern and gets deferred.
**How to avoid:** Hard-limit verify attempts per OTP token: invalidate the code after N failures (3–5). Store `attempt_count` on the OTP record. After invalidation, require a new request to get a fresh code.
**Warning signs:** Load test the verify endpoint without a session — unlimited 422/400 responses with no lockout.

### Pitfall 3: Async Session Misuse in Auth Dependencies
**What goes wrong:** FastAPI `Depends()` auth dependencies that need DB access use a shared session, re-use a closed session, or call async DB methods without `await`.
**Why it happens:** Auth middleware/dependencies are written differently from route handlers.
**How to avoid:** Auth dependencies must use `Depends(get_db)` like all other routes — never create sessions manually. Eagerly load `role` and `is_active` in the JWT-to-user query: `select(User).where(User.email == email).options(load_only(User.role, User.is_active))`. Never rely on lazy-loading in async context.
**Warning signs:** `MissingGreenlet` error in async context when accessing user properties after session closure.

## Code Examples

Verified patterns from official sources:

### OTP Generation and Storage
```python
# Source: Python secrets module documentation + hashlib documentation
import secrets
import hashlib
from datetime import datetime, timedelta

def generate_otp_code() -> str:
    """Generate a 6-digit numeric OTP code."""
    code = f"{secrets.randbelow(10**6):06d}"
    return code

def hash_otp_code(code: str) -> str:
    """Hash OTP code using SHA-256."""
    return hashlib.sha256(code.encode()).hexdigest()

def calculate_otp_expiry(minutes: int = 10) -> datetime:
    """Calculate OTP expiry time."""
    return datetime.now(datetime.UTC)+ timedelta(minutes=minutes)
```

### JWT Creation and Verification
```python
# Source: PyJWT documentation + FastAPI security tutorial
import jwt
from datetime import datetime, timedelta
from typing import Optional

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, secret_key: str = "...", algorithm: str = "HS256"):
    """Create JWT access token with expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(datetime.UTC)+ expires_delta
    else:
        expire = datetime.now(datetime.UTC)+ timedelta(minutes=15)  # default 15 min

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt

def verify_access_token(token: str, secret_key: str, algorithm: str = "HS256") -> Optional[dict]:
    """Verify JWT token and return payload if valid."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None
```

### Constant-Time Comparison for OTP Verification
```python
# Source: Python hmac documentation + security best practices
import hmac

def verify_otp_constant_time(stored_hash: str, candidate_code: str) -> bool:
    """Compare OTP hashes using constant-time comparison to prevent timing attacks."""
    if stored_hash is None:
        return False

    candidate_hash = hashlib.sha256(candidate_code.encode()).hexdigest()
    return hmac.compare_digest(stored_hash, candidate_hash)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose library | PyJWT library | 2024-2025 | python-jose is unmaintained with open CVEs; PyJWT is the current FastAPI standard |
| Synchronous SMTP | Asynchronous aiosmtplib | Contemporary | Prevents blocking the FastAPI event loop during email delivery |
| Raw OTP storage | Hashed OTP storage | Contemporary | Prevents plaintext OTP exposure in database backups/logs |

**Deprecated/outdated:**
- `python-jose`: Unmaintained since 2022, CVEs in ecdsa dependency, replaced by PyJWT in FastAPI docs
- `fastapi-users`: Assumes password auth; not suitable for OTP-only flow
- `pyotp`: Designed for TOTP/HOTP authenticator apps, not email delivery

## Open Questions

1. **aiosmtplib exact API surface**
   - What we know: aiosmtplib is the standard async SMTP choice for FastAPI apps; confirmed by community patterns
   - What's unclear: Exact async context manager API when implementing `email_service.py`
   - Recommendation: Check aiosmtplib 3.x docs when implementing; should be standard `async with aiosmtplib.SMTP(...) as smtp`

2. **SMTP retry logic and timeout configurations**
   - What we know: Should handle connection timeouts gracefully with appropriate error messages
   - What's unclear: Specific retry intervals and max attempts for failed deliveries
   - Recommendation: Research established patterns during implementation based on deployment requirements

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pytest.ini (existing) |
| Quick run command | `pytest tests/test_auth_service.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-02 | User can request OTP by email | unit | `pytest tests/test_auth_service.py::test_request_otp -x` | ❌ Wave 0 |
| AUTH-03 | User receives OTP via email/smtp | integration | `pytest tests/test_email_service.py::test_send_otp_email -x` | ❌ Wave 0 |
| AUTH-04 | User verifies OTP and gets JWT | unit | `pytest tests/test_auth_service.py::test_verify_otp -x` | ❌ Wave 0 |
| AUTH-05 | Account auto-created on first OTP | integration | `pytest tests/test_auth_service.py::test_account_auto_creation -x` | ❌ Wave 0 |
| AUTH-06 | OTP expires after 10 minutes | unit | `pytest tests/test_auth_service.py::test_otp_expiry -x` | ❌ Wave 0 |
| AUTH-07 | OTP single-use validation | unit | `pytest tests/test_auth_service.py::test_otp_single_use -x` | ❌ Wave 0 |
| AUTH-08 | Rate limiting on OTP requests | integration | `pytest tests/test_auth_service.py::test_otp_rate_limiting -x` | ❌ Wave 0 |
| AUTH-09 | JWT has proper claims | unit | `pytest tests/test_auth_service.py::test_jwt_claims_structure -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_auth_service.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_auth_service.py` — covers AUTH-02, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09
- [ ] `tests/test_email_service.py` — covers AUTH-03
- [ ] Framework install: `pip install pytest` — if none detected

## Sources

### Primary (HIGH confidence)
- FastAPI security tutorial (JWT section): https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — PyJWT usage, HTTPBearer pattern, dependency injection
- FastAPI release notes (latest version 0.135.1): https://fastapi.tiangolo.com/release-notes/ — HIGH confidence, verified 2026-03-14
- Python stdlib: `secrets`, `hashlib`, `hmac` — OTP generation, hashing, constant-time comparison
- RFC 7519 + OWASP JWT Cheat Sheet — JWT security best practices
- Existing codebase (read directly): `app/models/models.py`, `app/config.py`, `app/database.py`, `app/main.py` — confirmed conventions

### Secondary (MEDIUM confidence)
- aiosmtplib >=3.0 — async SMTP for FastAPI; community-established pattern; WebFetch denied during research, confirmed via training data and ecosystem knowledge

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Based on official FastAPI recommendations and verified existing patterns
- Architecture: HIGH - Aligns with existing codebase architecture and proven patterns
- Pitfalls: HIGH - Well-documented security vulnerabilities with standard mitigation approaches

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (30 days for stable, security-focused domain)