# Architecture Patterns

**Domain:** OTP auth + JWT sessions + RBAC on existing FastAPI async app
**Researched:** 2026-03-14

## Context: Existing Architecture

The codebase follows a clean layered pattern:

```
HTTP Request
    ↓
app/api/routes/*.py          ← FastAPI routers, Depends(get_db)
    ↓
app/services/*.py            ← Business logic, async DB operations
    ↓
app/models/models.py         ← SQLAlchemy ORM (Base, engine, session)
    ↓
PostgreSQL 18 (asyncpg)
```

Two cross-cutting concerns already exist as importable singletons:
- `from database import get_db` — session dependency injected via `Depends()`
- `from config import settings` — Pydantic settings with `SINODIK_` env prefix

The new auth system must follow both conventions exactly.

---

## New Component Map

```
app/
├── models/
│   └── models.py            ← ADD: User, OtpCode models (same file or new auth_models.py)
│
├── services/
│   ├── auth_service.py      ← NEW: OTP lifecycle, user lookup/create
│   └── email_service.py     ← NEW: SMTP sending via aiosmtplib (or sync fallback)
│
├── api/
│   ├── deps.py              ← NEW: get_current_user, require_admin dependencies
│   └── routes/
│       └── auth.py          ← NEW: POST /auth/request-otp, POST /auth/verify-otp
│                                   GET  /auth/me
│
└── config.py                ← ADD: SMTP settings, JWT secret, OTP TTL, token expiry
```

---

## Data Model Additions

### User

```
users
─────────────────────────────────────────────
id              Integer PK
email           String(255) UNIQUE NOT NULL   ← primary identity (matches Order.user_email)
role            String(20) NOT NULL           ← "user" | "admin"
is_active       Boolean DEFAULT TRUE
created_at      DateTime(timezone=True)
last_login_at   DateTime(timezone=True) NULL
```

No password column. Email is the sole identity. `role` is the RBAC field — kept simple (two roles, not a separate table) because the requirement is binary: admin or not.

The link to existing data: `User.email == Order.user_email`. No FK is needed — the column match is intentional (orders predate users, users auto-created on first OTP).

### OtpCode

```
otp_codes
─────────────────────────────────────────────
id              Integer PK
email           String(255) NOT NULL INDEX    ← target address, not FK to users (user may not exist yet)
code            String(8) NOT NULL            ← 6-digit string, stored hashed or plaintext (see pitfalls)
expires_at      DateTime(timezone=True)       ← now() + TTL (default 15 min)
used_at         DateTime(timezone=True) NULL  ← NULL = unused, timestamp = consumed
created_at      DateTime(timezone=True)
```

`email` is not a FK to `users` because the OTP flow bootstraps new users — the user row doesn't exist when the OTP is requested.

Expired, used codes are not deleted automatically — a cleanup job (or scheduled Alembic data migration) handles retention. Queries always filter `used_at IS NULL AND expires_at > now()`.

---

## Component Boundaries

| Component | Responsibility | Does NOT do |
|-----------|---------------|-------------|
| `auth.py` route | Parse request, call service, return response | Business logic |
| `auth_service.py` | OTP generation, verify, user create/lookup, JWT issue | Email I/O, route logic |
| `email_service.py` | Send OTP email via SMTP; fallback: return code string | Token logic |
| `deps.py` | `get_current_user`: decode JWT → User row; `require_admin`: check role | Auth business logic |
| `User` model | Schema only | No methods/logic |
| `OtpCode` model | Schema only | No methods/logic |
| `config.py` | New settings fields with `SINODIK_` prefix | Default values must be safe (no SMTP = dev fallback) |

---

## Data Flow

### 1. OTP Request

```
POST /auth/request-otp  { "email": "user@example.com" }
    ↓
auth.py route
    ↓
auth_service.request_otp(db, email)
    ├── generate 6-digit code
    ├── INSERT otp_codes(email, code, expires_at=now()+15min)
    ├── email_service.send_otp(email, code)
    │       ├── SMTP configured → send email, return None
    │       └── SMTP not configured → return code (dev mode)
    └── return { "sent": true, "dev_code": code | null }
```

### 2. OTP Verification → JWT

```
POST /auth/verify-otp  { "email": "user@example.com", "code": "123456" }
    ↓
auth.py route
    ↓
auth_service.verify_otp(db, email, code)
    ├── SELECT otp_codes WHERE email=email AND used_at IS NULL AND expires_at > now()
    │       ORDER BY created_at DESC LIMIT 1
    ├── code mismatch → raise 401
    ├── UPDATE otp_codes SET used_at=now()
    ├── SELECT users WHERE email=email
    │       NOT FOUND → INSERT users(email, role="user") auto-create
    ├── user.is_active=False → raise 403
    ├── UPDATE users SET last_login_at=now()
    └── jwt.encode({ sub: email, role: user.role, exp: now()+expiry }, SECRET, HS256)
    ↓
return { "access_token": "...", "token_type": "bearer" }
```

### 3. Authenticated Request

```
GET /api/v1/names/by-user  (Authorization: Bearer <token>)
    ↓
deps.get_current_user(token=Depends(oauth2_scheme), db=Depends(get_db))
    ├── jwt.decode(token, SECRET, algorithms=["HS256"])
    │       InvalidTokenError → raise 401
    ├── SELECT users WHERE email=payload["sub"]
    │       NOT FOUND or is_active=False → raise 401
    └── return User ORM object
    ↓
route function receives: current_user: User = Depends(get_current_user)
```

### 4. Admin-Only Request

```
POST /api/v1/upload/csv  (Authorization: Bearer <token>)
    ↓
deps.require_admin(user: User = Depends(get_current_user))
    ├── user.role != "admin" → raise 403
    └── return user
    ↓
route executes (existing upload logic unchanged)
```

---

## RBAC Guard Attachment to Existing Routes

FastAPI's `dependencies` parameter on path operations and routers allows guards to attach to existing routes without modifying their function signatures. This is the correct approach — no existing route function needs to change.

**Pattern A — single route guard:**

```python
# upload.py (existing route, no signature change)
@router.post("/upload/csv", dependencies=[Depends(require_admin)])
async def upload_csv(file: UploadFile = File(...), ...):
    ...
```

**Pattern B — entire router guard (future scope):**

```python
# If all routes in a module require auth:
router = APIRouter(dependencies=[Depends(get_current_user)])
```

For this milestone, Pattern A is preferable — it makes the guard explicit at the route level and avoids accidentally locking routes that should stay public (health, names read endpoints).

**Routes that get guards added:**

| Route | Guard | Rationale |
|-------|-------|-----------|
| `POST /api/v1/upload/csv` | `require_admin` | Admin only per requirements |
| `DELETE /api/v1/commemorations/{id}` | `require_admin` | Admin edit/delete |
| `PATCH /api/v1/commemorations/{id}` | `require_admin` | Admin edit |
| `GET /api/v1/names/by-user` | `get_current_user` | User scope — returns own data |
| `GET /api/v1/orders` (admin view) | `require_admin` | All orders view |
| `GET /api/v1/users` (new) | `require_admin` | User management |
| `PATCH /api/v1/users/{id}` (new) | `require_admin` | Role/active management |

Routes that stay unauthenticated: `GET /health`, `GET /api/v1/names/today`, `GET /api/v1/names/search`, `GET /api/v1/names/stats`.

---

## Dependency Graph

```
get_db (existing)
    ↑
    └── get_current_user (new, in deps.py)
            ├── oauth2_scheme (FastAPI HTTPBearer or OAuth2PasswordBearer)
            ├── jwt.decode()
            └── DB lookup of User
                    ↑
                    └── require_admin (new, in deps.py)
                            └── checks user.role == "admin"
```

`get_current_user` takes `db=Depends(get_db)` — FastAPI's caching ensures one session per request even if `get_db` is also declared separately in the route.

---

## JWT Structure

```json
{
  "sub": "user@example.com",
  "role": "admin",
  "exp": 1234567890
}
```

- Algorithm: `HS256` — symmetric, no key infrastructure needed, fits self-hosted context
- Secret: `SINODIK_JWT_SECRET` env var — required, no default (app fails to start if unset)
- Expiry: `SINODIK_JWT_EXPIRE_MINUTES` env var — default 10080 (7 days), fits infrequent login pattern
- Library: `PyJWT` — official FastAPI recommendation, actively maintained, no legacy `python-jose` dependency

Roles are embedded in the JWT to avoid a DB lookup on every admin check. `require_admin` reads `payload["role"]` directly. The `get_current_user` dependency still does a DB lookup to confirm `is_active` — this ensures a disabled account is blocked even with a valid token.

---

## Email Service Design

```python
# email_service.py
async def send_otp_email(to: str, code: str) -> str | None:
    """
    Returns None if email was sent.
    Returns the OTP code string if SMTP is not configured (dev fallback).
    """
    if not settings.smtp_host:
        return code  # dev mode: caller exposes code in response
    async with aiosmtplib.SMTP(...) as smtp:
        await smtp.send_message(message)
    return None
```

`aiosmtplib` is the correct choice for this async stack — wrapping `smtplib` in `run_in_executor` would work but is fragile and unnecessary given the library exists.

SMTP settings added to `config.py`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `SINODIK_SMTP_HOST` | SMTP server hostname | `""` (disables SMTP) |
| `SINODIK_SMTP_PORT` | SMTP port | `587` |
| `SINODIK_SMTP_USER` | SMTP username | `""` |
| `SINODIK_SMTP_PASSWORD` | SMTP password | `""` |
| `SINODIK_SMTP_FROM` | From address | `""` |
| `SINODIK_JWT_SECRET` | JWT signing secret | required |
| `SINODIK_JWT_EXPIRE_MINUTES` | Token lifetime | `10080` |
| `SINODIK_OTP_TTL_MINUTES` | OTP expiry | `15` |
| `SINODIK_ADMIN_EMAIL` | Seed first admin on startup | `""` |

---

## Admin Bootstrap

First-admin chicken-and-egg is solved by a lifespan hook in `main.py`:

```
startup → if SINODIK_ADMIN_EMAIL is set:
    UPSERT users(email=SINODIK_ADMIN_EMAIL, role="admin") ON CONFLICT(email) DO UPDATE SET role="admin"
```

This runs every startup but is idempotent. If the admin logs in via OTP normally and their role is already "admin", nothing changes.

---

## Frontend Integration (SinodikApp.jsx)

The frontend is a single JSX file compiled in-browser with Babel — no build step. Auth integration is purely additive:

1. Add a `localStorage.setItem("token", ...)` on successful verify-otp response
2. Add `Authorization: Bearer ${token}` header to all API calls
3. Add login screen state conditional (if no token → show OTP form)
4. Add "My Orders" tab reading from `GET /api/v1/names/by-user`
5. Add admin panel tab conditional on JWT payload `role === "admin"` (decode client-side with `atob` — no library needed for display logic, security enforced server-side)

No changes to the CDN-loaded React 19 setup, no new script tags required.

---

## Suggested Build Order

Build order follows the dependency graph — each step must complete before the next can be tested end-to-end.

**Step 1: Schema (no code dependency)**
- Alembic migration: `users` table + `otp_codes` table
- Add `User` and `OtpCode` ORM models to `models.py`
- Add new config fields to `config.py`

**Step 2: Auth Service (depends on Step 1 models)**
- `app/services/auth_service.py`: OTP generation, verify logic, user auto-create, JWT issue
- `app/services/email_service.py`: SMTP send + dev fallback
- Unit-testable without HTTP layer

**Step 3: Auth Routes (depends on Step 2 services)**
- `app/api/routes/auth.py`: `/auth/request-otp`, `/auth/verify-otp`, `/auth/me`
- Register router in `main.py`
- End-to-end OTP flow testable here

**Step 4: Auth Dependencies (depends on Step 1 models + JWT from Step 2)**
- `app/api/deps.py`: `get_current_user`, `require_admin`
- No route changes yet — just the dependency functions

**Step 5: Guard Existing Routes (depends on Step 4 deps)**
- Add `dependencies=[Depends(require_admin)]` to `POST /upload/csv`
- Add `dependencies=[Depends(require_admin)]` to commemoration edit/delete routes
- This is the integration risk step — test all guarded routes

**Step 6: New Protected Routes (depends on Steps 4 + 5)**
- `GET /api/v1/names/by-user` — user's own active names (filter by `current_user.email`)
- Admin user management routes (`GET /users`, `PATCH /users/{id}`)

**Step 7: Frontend (depends on Steps 3 + 6)**
- Edit `SinodikApp.jsx`: login state, token storage, auth headers, tabs

---

## Patterns to Follow

### Pattern: Dependency-Injected Auth Guard

Do not import `settings` or call `jwt.decode` inside route functions. Keep JWT logic in `deps.py` only.

```python
# deps.py
oauth2_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.get(User, payload["sub"])  # or filter by email
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or unknown user")
    return user
```

### Pattern: Role Guard as Thin Wrapper

```python
async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user
```

### Pattern: Optional Auth (user context if present, anonymous otherwise)

For future use on read endpoints that behave differently for logged-in users:

```python
async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    # ... same JWT decode, return None on error instead of raising
```

---

## Anti-Patterns to Avoid

### Anti-Pattern: Storing Roles in a Separate Table

A roles table adds joins on every request. For a two-role system (user/admin), a `role` string column on `User` is sufficient. If roles expand later, migrate then.

### Anti-Pattern: Server-Side Sessions

The project decision log explicitly mandates JWT (stateless). Do not introduce any Redis or DB-session-store dependency.

### Anti-Pattern: Modifying Existing Route Function Signatures for Auth

Use `dependencies=[Depends(...)]` on the decorator instead. Keeps existing routes readable and audit-friendly — the guard is declared where the route is, not buried in function parameters.

### Anti-Pattern: Storing Raw OTP Codes

Codes are short-lived (15 min), 6 digits, single-use. Hashing is not required for this threat model — but also costs nothing. Use `secrets.token_hex` for generation, store as-is or hashed. Do NOT log OTP codes.

### Anti-Pattern: JWT Without Expiry Verification

Always pass `options={"require": ["exp"]}` or equivalent to `jwt.decode`. PyJWT validates `exp` by default — do not pass `options={"verify_exp": False}` in any environment.

---

## Scalability Considerations

| Concern | Now (single instance) | If horizontally scaled |
|---------|----------------------|----------------------|
| JWT verification | Stateless, works on all nodes | Still works — symmetric key shared via env var |
| OTP codes | Single DB, fine | Still fine — DB is shared |
| Email sending | Per-request SMTP connection | Consider connection pool or queue |
| Admin bootstrap | Idempotent upsert on startup | Safe — all nodes upsert same row |

---

## Sources

- FastAPI security tutorial (JWT): https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — HIGH confidence (official docs)
- FastAPI OAuth2 scopes (RBAC patterns): https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/ — HIGH confidence (official docs)
- FastAPI path operation dependencies: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-in-path-operation-decorators/ — HIGH confidence (official docs)
- aiosmtplib async SMTP: referenced from FastAPI async ecosystem analysis — MEDIUM confidence (library exists, API confirmed via docs fetch)
- PyJWT: current FastAPI-recommended JWT library replacing deprecated `python-jose` — HIGH confidence (official FastAPI docs explicitly recommend PyJWT)
- Existing codebase patterns: read directly from source — HIGH confidence
