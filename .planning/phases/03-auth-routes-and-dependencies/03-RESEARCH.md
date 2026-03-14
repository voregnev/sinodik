# Phase 3: Auth Routes and Dependencies — Research

**Researched:** 2026-03-14
**Domain:** FastAPI HTTP auth layer, JWT dependencies, OTP endpoints
**Confidence:** HIGH

## Summary

Phase 3 exposes the existing auth service (Phase 2) over HTTP: three auth endpoints under `/api/v1/auth/` and shared dependencies in `app/api/deps.py` for JWT validation and role checks. No new business logic — routes call `auth_service.request_otp` / `verify_otp` and map results to HTTP status and bodies. Use FastAPI's `HTTPBearer(auto_error=False)` to extract the token and return 401 (not 403) for missing/invalid tokens; implement `get_current_user` (decode JWT, load user by `sub`/email, check `is_active`) and `require_admin` (depends on `get_current_user`, raise 403 if role != admin). Existing project research (`.planning/research/ARCHITECTURE.md`, `STACK.md`) and Phase 2 code already define the JWT payload (`sub` = email, `role`), PyJWT usage, and dependency patterns.

**Primary recommendation:** Add `api/routes/auth.py` and `api/deps.py`; register auth router in `main.py`. Use `HTTPBearer(auto_error=False)` plus manual 401 so missing token returns 401 (FastAPI's default HTTPBearer is 403). Load user by email (`payload["sub"]`) in `get_current_user`; do not add server-side logout — client discards JWT; `/auth/me` rejects expired/missing via deps.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Auth endpoints under `/api/v1/auth/`: POST `request-otp`, POST `verify-otp`, GET `me`
- Request OTP: success 202 with `{ "message": "OTP sent" }`; when plaintext fallback, include `dev_otp_code` in body; rate limit → 429; invalid email → 400
- Verify OTP: success 200 with `{ "token": "<jwt>", "user": { "email", "role" } }`; invalid/expired code → 401 with `{ "detail": "Invalid or expired code" }` (no distinction)
- GET /auth/me: success 200 with `email`, `role`, `id`, `is_active`; missing/invalid/expired token → 401
- Dependencies in `app/api/deps.py`: `get_current_user` (validates JWT, loads user, 401 on failure), `require_admin` (depends on `get_current_user`, 403 if not admin)
- No server-side logout; logout = client discards JWT; GET /auth/me rejects expired or missing tokens

### Claude's Discretion
- Exact Pydantic request/response model names and field names
- How to extract JWT (Authorization: Bearer vs header name)
- Optional: request-otp response model vs free-form dict
- Error response shape consistency (FastAPI default vs custom)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| USER-03 | User can log out (client-side: discard JWT) | No server endpoint. GET /auth/me returns 401 for missing/expired token (deps + route). Client discards token; automated test can assert /auth/me 401 without Authorization header and with expired JWT. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ (project) | Routes, Depends, HTTPException, status | Already in use; security docs use Depends + OAuth2PasswordBearer or HTTPBearer |
| PyJWT | >=2.9 (project) | Decode JWT in deps | Same as auth_service.encode; project STACK.md and ARCHITECTURE.md mandate PyJWT |
| fastapi.security.HTTPBearer | bundled | Extract Bearer token from Authorization | Built-in; use `auto_error=False` to return 401 instead of 403 for missing token |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy (async) | 2.0+ (project) | Load User by email in get_current_user | Already used; deps need AsyncSession via Depends(get_db) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTTPBearer(auto_error=False) | OAuth2PasswordBearer(tokenUrl="...") | tokenUrl only affects Swagger; HTTPBearer is simpler for Bearer-only. OAuth2PasswordBearer also returns 401 when token missing. |
| PyJWT decode in deps | python-jose | Project already uses PyJWT; python-jose unmaintained (STACK.md). |

**Installation:** No new packages. PyJWT and FastAPI already in project.

## Architecture Patterns

### Recommended Project Structure
```
app/
├── api/
│   ├── deps.py           # get_current_user, require_admin, oauth2_scheme
│   └── routes/
│       ├── auth.py       # POST request-otp, POST verify-otp, GET me
│       ├── health.py
│       ├── upload.py
│       └── ...
├── services/
│   └── auth_service.py   # request_otp, verify_otp, create_jwt_token (Phase 2)
└── main.py               # include_router(auth.router, prefix="/api/v1", tags=["auth"])
```

### Pattern 1: Extract Bearer and return 401 for missing/invalid
**What:** Use `HTTPBearer(auto_error=False)` so we control status code; raise `HTTPException(401)` when credentials are missing or JWT invalid/expired.
**When to use:** When contract requires 401 for "not authenticated" (RFC 6750); FastAPI's HTTPBearer default is 403.
**Example:**
```python
# deps.py (pattern from .planning/research/ARCHITECTURE.md)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.models import User  # User not in models.__all__; use models.models

oauth2_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user
```

### Pattern 2: require_admin as thin wrapper
**What:** Dependency that depends on `get_current_user` and raises 403 if `user.role != "admin"`.
**When to use:** Any route that must be admin-only.
**Example:**
```python
async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user
```

### Pattern 3: Route → service → HTTP mapping
**What:** Route receives request body, calls `auth_service.request_otp` / `verify_otp` with `Depends(get_db)`, maps return dict to status and body. Do not duplicate OTP/JWT logic in routes.
**When to use:** All three auth endpoints.
**Example (request-otp):**
- `result = await request_otp(body.email, db)`
- If `result["success"]` and "dev_otp_code" in result → 202, body with message + dev_otp_code
- If not success and "Rate limit" in message → 429
- If not success (e.g. invalid email from ValueError) → 400

### Anti-Patterns to Avoid
- **JWT decode in route:** Keep decode only in `deps.py`; routes never touch raw token.
- **403 for missing token:** Use 401; use `HTTPBearer(auto_error=False)` and raise 401 manually.
- **Loading user by id from JWT:** JWT payload uses `sub` = email; load `User` by email, not by id.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bearer extraction | Manual header parsing | HTTPBearer (fastapi.security) | Handles Authorization format and OpenAPI scheme |
| JWT decode/verify | Custom decode + exp check | PyJWT decode with algorithms=["HS256"] | PyJWT validates exp by default; avoid verify_exp=False |
| Role check | Inline if in every route | require_admin dependency | Single place, reusable, 403 semantics |

## Common Pitfalls

### Pitfall 1: HTTPBearer returns 403 when token missing
**What goes wrong:** Contract expects 401 for missing/invalid token; default HTTPBearer raises 403.
**Why it happens:** FastAPI issue #10177; HTTPBearer auto_error uses 403.
**How to avoid:** Use `HTTPBearer(auto_error=False)` and raise `HTTPException(status_code=401, ...)` when credentials is None or decode fails.
**Warning signs:** Tests expect 401, integration returns 403.

### Pitfall 2: User lookup by id when JWT has email
**What goes wrong:** get_current_user does `db.get(User, payload["sub"])` but payload["sub"] is email (string).
**Why it happens:** FastAPI tutorial often uses username as sub; our auth_service sets sub=email.
**How to avoid:** `select(User).where(User.email == payload["sub"])` then scalar_one_or_none().
**Warning signs:** 401 for valid token or TypeError on get(User, str).

### Pitfall 3: request_otp raises ValueError for invalid email
**What goes wrong:** Route catches generic Exception and returns 500; contract expects 400 for invalid email.
**Why it happens:** auth_service.request_otp raises ValueError for invalid email; rate limit returns dict with success False.
**How to avoid:** Catch ValueError → 400; check result["success"] and "Rate limit" in message → 429; else 202 or 500 as appropriate.

### Pitfall 4: verify_otp returns None; route must return 401 with generic message
**What goes wrong:** Returning different messages for "wrong code" vs "expired" leaks information.
**Why it happens:** auth_service returns None for both.
**How to avoid:** Single 401 body: `{ "detail": "Invalid or expired code" }` (per CONTEXT).

## Code Examples

### Request OTP route (high level)
```python
@router.post("/auth/request-otp", status_code=202)
async def request_otp_endpoint(body: RequestOtpBody, db: AsyncSession = Depends(get_db)):
    try:
        result = await request_otp(body.email, db)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email")
    if not result["success"]:
        if "Rate limit" in result.get("message", ""):
            raise HTTPException(status_code=429, detail=result["message"])
        raise HTTPException(status_code=400, detail=result.get("message", "Bad request"))
    response = {"message": result["message"]}
    if "dev_otp_code" in result:
        response["dev_otp_code"] = result["dev_otp_code"]
    return response
```

### Verify OTP route
```python
@router.post("/auth/verify-otp")
async def verify_otp_endpoint(body: VerifyOtpBody, db: AsyncSession = Depends(get_db)):
    out = await verify_otp(body.email, body.code, db)
    if out is None:
        raise HTTPException(status_code=401, detail="Invalid or expired code")
    return {"token": out["token"], "user": out["user"]}
```

### GET /auth/me
```python
@router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose for JWT | PyJWT | FastAPI docs / ecosystem | Use jwt.decode (PyJWT) in deps |
| HTTPBearer() default | HTTPBearer(auto_error=False) + manual 401 | RFC 6750 / FastAPI issue #10177 | Correct 401 for missing token |

**Deprecated/outdated:** python-jose (unmaintained; STACK.md). Do not use verify_exp=False in jwt.decode.

## Open Questions

1. **Import style for routes**
   - What we know: Existing routes use `from database import get_db`, `from models import ...` (no `app.` prefix); main.py uses `from config import settings`, `from database import engine`. Pyproject has `pythonpath = ["app"]` for tests.
   - What's unclear: Whether app runs with cwd=project root and app on path, or cwd=app. RESEARCH assumes same style as orders.py (database, models, services).
   - Recommendation: Match existing route imports; if deps.py lives under app/api/, use `from app.config import settings` and `from app.database import get_db` if other api modules do so, else relative to app (database, config) per existing routes.

2. **Response model for /auth/me**
   - What we know: CONTEXT requires 200 with email, role, id, is_active.
   - What's unclear: Whether to declare response_model=UserMeResponse (Pydantic) for OpenAPI.
   - Recommendation: Define a Pydantic model for /auth/me response for clear docs and validation; optional for request-otp (dict is acceptable per CONTEXT).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (asyncio_mode = "auto") |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_auth_routes.py -v -x` |
| Full suite command | `docker compose run --rm api pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| USER-03 | Logout = client discards JWT; /auth/me rejects missing/expired token | integration | `pytest tests/test_auth_routes.py -v -x` | ❌ Wave 0 |
| (Phase success criteria) | POST /auth/request-otp 202, 429 on rate limit, 400 invalid email | integration | same | ❌ Wave 0 |
| (Phase success criteria) | POST /auth/verify-otp 200 with token+user, 401 invalid/expired code | integration | same | ❌ Wave 0 |
| (Phase success criteria) | GET /auth/me 200 with user when valid JWT, 401 when missing/expired | integration | same | ❌ Wave 0 |
| (Phase success criteria) | get_current_user / require_admin usable by other routes | unit/integration | deps tests or route tests | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_auth_routes.py tests/test_auth_deps.py -v -x` (if deps tests split) or `pytest tests/test_auth_routes.py -v -x`
- **Per wave merge:** `docker compose run --rm api pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_auth_routes.py` — covers auth endpoints and USER-03 (401 without token / expired)
- [ ] Optional: `tests/test_auth_deps.py` — unit tests for get_current_user / require_admin with mocked DB and JWT
- [ ] Existing `tests/test_auth_service.py` — already covers service layer; no change required for Phase 3
- [ ] No conftest.py in repo; add if shared fixtures (e.g. client, db session) needed for auth route tests

## Sources

### Primary (HIGH confidence)
- .planning/research/ARCHITECTURE.md — Dependency-Injected Auth Guard, Role Guard, HTTPBearer(auto_error=False), JWT decode in deps only
- .planning/research/STACK.md — PyJWT, HTTPBearer, no python-jose
- app/services/auth_service.py — request_otp return shape (success, message, dev_otp_code), verify_otp return (token, user), create_jwt_token payload (sub=email, role)
- FastAPI security tutorial (Context7) — get_current_user, decode JWT, raise 401, chain dependencies

### Secondary (MEDIUM confidence)
- WebSearch: FastAPI HTTPBearer 403 vs 401 — use auto_error=False and raise 401 manually
- WebSearch: OAuth2PasswordBearer vs HTTPBearer for Bearer-only — tokenUrl for Swagger; HTTPBearer sufficient

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — project already uses FastAPI, PyJWT; ARCHITECTURE/STACK document deps pattern
- Architecture: HIGH — patterns match CONTEXT and existing route style
- Pitfalls: HIGH — HTTPBearer 403 vs 401 and sub=email verified; request_otp/verify_otp mapping from code

**Research date:** 2026-03-14
**Valid until:** 30 days (stable stack)
