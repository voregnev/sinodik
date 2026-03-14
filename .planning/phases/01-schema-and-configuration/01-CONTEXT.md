# Phase 1: Schema and Configuration - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `users` and `otp_codes` database tables, their SQLAlchemy ORM models, and all auth-related config settings to `config.py`. Auth business logic (OTP generation, JWT signing) is Phase 2 — this phase delivers only the schema and configuration foundation.

</domain>

<decisions>
## Implementation Decisions

### JWT Configuration
- Add `jwt_secret: str` to Settings — required field (no default); app must hard-crash at startup with a clear error if unset
- Add `jwt_ttl_days: int = 7` to Settings — overridable via `SINODIK_JWT_TTL_DAYS`
- No `jwt_algorithm` field — hardcode `HS256` in the signing logic (Phase 2)
- Only `jwt_secret` and `jwt_ttl_days` are needed in Phase 1; Phase 2 consumes them

### Admin Bootstrap
- Config field: `admin_emails: list[str] = []` — env var `SINODIK_ADMIN_EMAILS` (comma-separated list)
- Admin role is assigned at first OTP verification: when a new account is auto-created, check if email (lowercased) is in `settings.admin_emails` (all lowercased) — set `role = "admin"` if so
- If `SINODIK_ADMIN_EMAILS` is empty/unset: allowed — no admin at startup; that's fine for dev/test
- Matching is case-insensitive (normalize both sides to lowercase before comparison)

### otp_codes Table Schema
- Store `email` directly (no FK to users) — OTP is requested before account may exist
- Include `attempt_count: int = 0` column — incremented on each failed verification, code invalidated at 5 attempts (AUTH-08 logic lives in Phase 2)
- Cleanup strategy: Phase 2 deletes on successful verify; expired unverified codes accumulate until a periodic cleanup job (out of Phase 1 scope)
- Full column set: `id`, `email`, `code_hash` (SHA-256, Phase 2 fills), `created_at`, `expires_at`, `used` (bool), `attempt_count`

### users Table Schema
- Minimal schema: `id`, `email` (unique), `role` (str: "user" | "admin"), `is_active` (bool, default True), `created_at`
- No `last_login_at` — keep schema minimal; can add in a later phase if needed

### OTP Dev Fallback Config
- Add `otp_plaintext_fallback: bool = False` to Settings — env var `SINODIK_OTP_PLAINTEXT_FALLBACK`
- When True, Phase 2's OTP service includes the raw code in the API response (dev/demo mode)

### Migration
- Hand-write migration `0006_add_auth_tables.py` following the existing sequential naming pattern
- Include the `_ensure_base_tables()` safety pattern already established in `0001`

### Claude's Discretion
- Exact column ordering and index choices for the new tables
- Whether to add a GIN index on `otp_codes.email` for lookup performance
- How to validate `jwt_secret` at startup (pydantic validator vs lifespan hook check)

</decisions>

<specifics>
## Specific Ideas

- "Hard crash with clear error if SINODIK_JWT_SECRET is unset" — this is explicitly a success criterion (#3) in the roadmap
- The existing `Order.user_email` field already exists and is nullable — no migration needed for USER-02 linkage; Phase 1 just needs to confirm this in the success criteria

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/config.py` — pydantic-settings Settings class with `SINODIK_` prefix; just add new fields
- `app/models/models.py` — follows Column + Index + relationship pattern; new models go in the same file
- `alembic/versions/0001_extend_schema.py` — `_ensure_base_tables()` safety pattern to copy for migration `0006`

### Established Patterns
- Imports use `app/` as root: `from config import settings`, `from database import Base`
- `DateTime(timezone=True)` for all timestamps
- `default=datetime.utcnow` (existing pattern; note: utcnow is deprecated in Python 3.12+ but consistent with current code)
- Module-level docstrings in Russian explaining design decisions

### Integration Points
- `app/main.py` lifespan hook — startup validation for `SINODIK_JWT_SECRET` can go here
- `app/models/models.py` — `User` and `OtpCode` models added here, imported by Phase 2 services
- `app/config.py` — new auth fields consumed by Phase 2 (`auth_service.py`) and Phase 3 (`deps.py`)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-schema-and-configuration*
*Context gathered: 2026-03-14*
