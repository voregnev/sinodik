# Phase 3: Auth Routes and Dependencies - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

The auth API is reachable over HTTP: OTP request and verify endpoints are live, JWT verification and role-checking dependencies exist and are importable by any route. This phase delivers the HTTP layer only; business logic (OTP, JWT, email) is implemented in Phase 2.

</domain>

<decisions>
## Implementation Decisions

### URL and routing
- Auth endpoints live under `/api/v1/auth/` (same prefix as existing API: `/api/v1/upload`, `/api/v1/orders`, etc.)
- Routes: POST `/api/v1/auth/request-otp`, POST `/api/v1/auth/verify-otp`, GET `/api/v1/auth/me`

### Request OTP (POST /auth/request-otp)
- Success: HTTP 202 with body e.g. `{ "message": "OTP sent" }`; when plaintext fallback is used, include `dev_otp_code` in the response body (per Phase 2)
- Rate limit exceeded: HTTP 429 Too Many Requests
- Invalid email: 400 with appropriate detail

### Verify OTP (POST /auth/verify-otp)
- Success: 200 with body `{ "token": "<jwt>", "user": { "email": "...", "role": "user"|"admin" } }`
- Invalid or expired code: HTTP 401 with body `{ "detail": "Invalid or expired code" }` (no distinction between wrong code vs expired for security)

### GET /auth/me
- Success: 200 with body including `email`, `role`, `id`, `is_active`
- Missing or invalid/expired token: HTTP 401

### Dependencies (for use by other routes)
- Location: `app/api/deps.py` (shared API dependencies)
- `get_current_user`: dependency that validates JWT, loads user from DB, returns user or raises 401
- `require_admin`: dependency that depends on `get_current_user` and raises 403 if role is not admin

### Logout
- No server-side logout endpoint in this phase
- Logout = client discards the JWT; GET /auth/me will reject expired or missing tokens

### Claude's Discretion
- Exact Pydantic request/response model names and field names
- How to extract JWT (Authorization: Bearer vs header name)
- Optional: request-otp response model vs free-form dict
- Error response shape consistency (FastAPI default vs custom)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/auth_service.py` — `request_otp`, `verify_otp`, `create_jwt_token`; accept `AsyncSession`, return dicts
- `app/services/email_service.py` — used by auth_service for OTP delivery
- `app/database.py` — `get_db` async generator for `AsyncSession`
- `app/config.py` — `settings.jwt_secret`, `settings.jwt_ttl_days`, `settings.admin_emails`

### Established Patterns
- Routes use `APIRouter()`, registered in `main.py` with `include_router(..., prefix="/api/v1", tags=[...])`
- DB access via `db: AsyncSession = Depends(get_db)`
- No existing auth middleware; dependencies will be the first use of Bearer JWT

### Integration Points
- New router module (e.g. `api/routes/auth.py`) with prefix `/api/v1`, tags `["auth"]`
- New `api/deps.py` with `get_current_user`, `require_admin`; importable by `api/routes/upload.py`, `names.py`, etc. in Phase 4

</code_context>

<specifics>
## Specific Ideas

- Response shapes chosen so frontend can use `/auth/me` and verify response without decoding JWT
- 429 for rate limit to align with HTTP semantics; 401 for auth failures with a single generic message to avoid leaking info

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-auth-routes-and-dependencies*
*Context gathered: 2026-03-15*
