# Phase 1: Schema and Configuration - Research

**Researched:** 2026-03-14
**Domain:** SQLAlchemy ORM models, pydantic-settings, Alembic migrations
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**JWT Configuration**
- Add `jwt_secret: str` to Settings — required field (no default); app must hard-crash at startup with a clear error if unset
- Add `jwt_ttl_days: int = 7` to Settings — overridable via `SINODIK_JWT_TTL_DAYS`
- No `jwt_algorithm` field — hardcode `HS256` in the signing logic (Phase 2)
- Only `jwt_secret` and `jwt_ttl_days` are needed in Phase 1; Phase 2 consumes them

**Admin Bootstrap**
- Config field: `admin_emails: list[str] = []` — env var `SINODIK_ADMIN_EMAILS` (comma-separated list)
- Admin role is assigned at first OTP verification: when a new account is auto-created, check if email (lowercased) is in `settings.admin_emails` (all lowercased) — set `role = "admin"` if so
- If `SINODIK_ADMIN_EMAILS` is empty/unset: allowed — no admin at startup; that's fine for dev/test
- Matching is case-insensitive (normalize both sides to lowercase before comparison)

**otp_codes Table Schema**
- Store `email` directly (no FK to users) — OTP is requested before account may exist
- Include `attempt_count: int = 0` column — incremented on each failed verification, code invalidated at 5 attempts (AUTH-08 logic lives in Phase 2)
- Cleanup strategy: Phase 2 deletes on successful verify; expired unverified codes accumulate until a periodic cleanup job (out of Phase 1 scope)
- Full column set: `id`, `email`, `code_hash` (SHA-256, Phase 2 fills), `created_at`, `expires_at`, `used` (bool), `attempt_count`

**users Table Schema**
- Minimal schema: `id`, `email` (unique), `role` (str: "user" | "admin"), `is_active` (bool, default True), `created_at`
- No `last_login_at` — keep schema minimal; can add in a later phase if needed

**OTP Dev Fallback Config**
- Add `otp_plaintext_fallback: bool = False` to Settings — env var `SINODIK_OTP_PLAINTEXT_FALLBACK`
- When True, Phase 2's OTP service includes the raw code in the API response (dev/demo mode)

**Migration**
- Hand-write migration `0006_add_auth_tables.py` following the existing sequential naming pattern
- Include the `_ensure_base_tables()` safety pattern already established in `0001`

### Claude's Discretion
- Exact column ordering and index choices for the new tables
- Whether to add a GIN index on `otp_codes.email` for lookup performance
- How to validate `jwt_secret` at startup (pydantic validator vs lifespan hook check)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | Anonymous user can submit an order with names only (no email required) | Confirmed: `Order.user_email` is already nullable in `orders` table — no schema change needed. Anonymous submission path in `upload.py` / `order_service.py` requires no modification. |
| USER-02 | Authenticated user's new orders are automatically linked to their account email | Confirmed: `Order.user_email` column already exists (`String(255), nullable=True, index=True`). Phase 1 verifies this field exists and documents it as the linkage point. No migration needed. |
| BOOT-01 | First admin account is seeded via `SINODIK_ADMIN_EMAILS` env var (checked at account creation time) | `admin_emails: list[str] = []` field in Settings; pydantic-settings parses comma-separated env var into `list[str]` via a custom validator. Logic (comparison at user creation) lives in Phase 2 auth service — Phase 1 only adds the config field. |
</phase_requirements>

## Summary

Phase 1 is a pure scaffolding phase: no business logic, no endpoints. It delivers three artifacts — two new ORM models (`User`, `OtpCode`), three new config fields in `Settings`, and one hand-written Alembic migration.

The project already provides all necessary patterns. `app/models/models.py` has three working models to copy column/index style from. `alembic/versions/0001_extend_schema.py` has the `_ensure_base_tables()` idempotency pattern that migration `0006` must replicate. `app/config.py` is a minimal pydantic-settings file — adding fields is a one-liner per field. The one non-trivial decision is how to enforce `jwt_secret` at startup: a pydantic `@field_validator` is cleaner and fires at import time (before the lifespan hook), while a lifespan hook check is consistent with existing patterns but fires later.

The USER-02 requirement (linkage field ready) requires no code change — `Order.user_email` already exists as `String(255), nullable=True, index=True`. The success criterion is verification, not implementation.

**Primary recommendation:** Add `User` and `OtpCode` to `models/models.py`, add four fields to `config.py`, write migration `0006`, and add a startup guard for `jwt_secret`. All four tasks are independent and can be done in one wave.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic-settings | (already installed) | Settings from env vars | Already in use — BaseSettings with `SINODIK_` prefix |
| SQLAlchemy | 2.0+ (already installed) | ORM models, Column definitions | Already in use — declarative Base pattern |
| Alembic | (already installed) | Schema migrations | Already in use — sequential `0001`–`0005` chain |

No new dependencies are required for Phase 1.

### Config Field Parsing — list[str] from comma-separated env var

pydantic-settings v2 does NOT automatically split a comma-separated string into `list[str]`. A custom `@field_validator` (or `@model_validator`) is needed, or the env var must be a JSON array. The project has no existing list field that uses comma-separation, so a validator must be added for `admin_emails`.

**Verified pattern (pydantic-settings v2):**
```python
from pydantic import field_validator

class Settings(BaseSettings):
    admin_emails: list[str] = []

    @field_validator("admin_emails", mode="before")
    @classmethod
    def parse_admin_emails(cls, v):
        if isinstance(v, str):
            return [e.strip().lower() for e in v.split(",") if e.strip()]
        return [e.lower() for e in v] if v else []
```

The existing `cors_origins: list[str]` field does NOT use a custom validator — this means it expects the env var to be a JSON array (`["http://..."]`). For `admin_emails`, comma-separated is the user-friendly choice (easier to write in docker-compose), so the validator is necessary.

## Architecture Patterns

### Recommended Project Structure (no changes to structure)

Phase 1 only modifies existing files and adds one new file:

```
app/
├── config.py           # Add jwt_secret, jwt_ttl_days, admin_emails, otp_plaintext_fallback
├── models/models.py    # Add User and OtpCode classes
└── main.py             # Add startup guard for jwt_secret (in lifespan or validator)

alembic/versions/
└── 0006_add_auth_tables.py   # New hand-written migration
```

### Pattern 1: ORM Model (from existing codebase)

**What:** All models inherit from `database.Base`, use `Column()` with explicit types, `DateTime(timezone=True)` for all timestamps, `default=datetime.utcnow` for `created_at`.

**When to use:** For every new table.

**Example (matching existing style):**
```python
# Source: app/models/models.py (existing codebase)
class User(Base):
    """
    Учётная запись пользователя.
    Создаётся автоматически при первой успешной верификации OTP.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default="user")   # "user" | "admin"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<User #{self.id} {self.email} role={self.role}>"


class OtpCode(Base):
    """
    Одноразовый код подтверждения.
    email хранится без FK — код запрашивается до создания аккаунта.
    """
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    code_hash = Column(String(64), nullable=True)   # SHA-256 hex; Phase 2 fills on issue
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    attempt_count = Column(Integer, nullable=False, default=0)
```

**Note on index for `otp_codes.email`:** A regular B-tree index (`index=True`) is appropriate. GIN trigram index is only useful for LIKE/similarity queries. OTP lookup is always exact by email — B-tree is optimal and simpler.

### Pattern 2: Alembic Migration (from existing codebase)

**What:** Hand-written migration following sequential revision ID `0006`, `down_revision = "0005"`. Uses `_ensure_base_tables()` pattern to be idempotent for fresh installs.

**When to use:** Whenever new tables are created.

**Example structure (matching 0001 pattern):**
```python
# Source: alembic/versions/0001_extend_schema.py (existing codebase)
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def _ensure_base_tables() -> None:
    """Fresh install safety: create auth tables if they don't exist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("role", sa.String(20), nullable=False, server_default="user"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "otp_codes" not in tables:
        op.create_table(
            "otp_codes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("code_hash", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_otp_codes_email", "otp_codes", ["email"])


def upgrade() -> None:
    _ensure_base_tables()


def downgrade() -> None:
    op.drop_table("otp_codes")
    op.drop_table("users")
```

### Pattern 3: Startup Validation for jwt_secret

**Two viable approaches — recommendation: pydantic validator**

**Option A: pydantic `@field_validator` (recommended)**

Fires at import time when `settings = Settings()` is evaluated. Hard-crash with a `ValidationError` before the app even starts. Most consistent with pydantic-settings philosophy.

```python
# Source: pydantic-settings pattern
from pydantic import field_validator

class Settings(BaseSettings):
    jwt_secret: str  # no default — pydantic raises if env var is absent

    model_config = {"env_prefix": "SINODIK_"}
```

With `jwt_secret: str` and no default, pydantic-settings v2 will raise `ValidationError` at `Settings()` instantiation if `SINODIK_JWT_SECRET` is unset. The error message is clear: `1 validation error for Settings / jwt_secret / Field required`. No custom validator needed — the absence of a default is sufficient.

**Option B: lifespan hook check**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.jwt_secret:
        raise RuntimeError("SINODIK_JWT_SECRET is required but not set")
    # ...existing extension setup...
    yield
```

Option B is weaker: the settings object would need a default (e.g., `""`) to avoid crashing at import, making it possible to import with an empty string undetected. Option A is strictly better.

**Recommendation: use Option A — `jwt_secret: str` with no default.** The ValidationError from pydantic is a clear, early, unambiguous hard-crash.

### Anti-Patterns to Avoid

- **Adding `jwt_algorithm` to config:** Locked decision — hardcode `HS256` in Phase 2, not in config.
- **Adding FK from `otp_codes.email` to `users.email`:** Locked decision — OTP is requested before account exists.
- **Using `datetime.utcnow` as `server_default`:** Use `default=datetime.utcnow` (Python-side, consistent with existing code). Note: `datetime.utcnow` is deprecated in Python 3.12+ but matches existing pattern — do not change existing code style in this phase.
- **Splitting `User` and `OtpCode` into separate files:** Existing models are all in `app/models/models.py` — keep them together.
- **Setting `cors_origins`-style JSON array for `admin_emails`:** Comma-separated is the locked decision. Need custom validator (see above).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var → Settings validation | Custom env-parsing code | pydantic-settings `BaseSettings` | Already in use, handles type coercion, prefix, missing required fields |
| Required field enforcement | if/else startup checks | `jwt_secret: str` with no default | pydantic raises `ValidationError` at instantiation — no code needed |
| Migration idempotency | Complex conditional logic | `_ensure_base_tables()` pattern from `0001` | Already established, proven to work on fresh installs |

**Key insight:** pydantic-settings v2 with no default on a required field IS the startup validation. No extra validation code needed beyond the field declaration.

## Common Pitfalls

### Pitfall 1: pydantic-settings v2 list parsing from comma-separated string

**What goes wrong:** `admin_emails: list[str] = []` with env var `SINODIK_ADMIN_EMAILS=a@x.com,b@x.com` will NOT split automatically. pydantic-settings v2 tries to JSON-parse the string first; `a@x.com,b@x.com` is not valid JSON so it raises a validation error.

**Why it happens:** pydantic-settings v2 changed list parsing behavior versus v1. The existing `cors_origins` field works because it expects a JSON array in the env var.

**How to avoid:** Add `@field_validator("admin_emails", mode="before")` that splits on comma for string input (see code example in Pattern 1 above).

**Warning signs:** `ValidationError` on startup with message about `admin_emails` not being a valid list.

### Pitfall 2: Migration chain break — wrong `down_revision`

**What goes wrong:** If `down_revision` in `0006` is set to anything other than `"0005"`, Alembic will either create a branch or fail on `upgrade head`.

**Why it happens:** The current head is `0005` (confirmed by glob of `alembic/versions/`). Setting `down_revision = "0005"` continues the linear chain.

**How to avoid:** Verify by reading `0005_persons_embedding_vector.py` — `revision = "0005"`. Set `down_revision = "0005"` in `0006`.

**Warning signs:** `alembic upgrade head` produces a branch warning or applies nothing.

### Pitfall 3: `server_default` vs Python `default` mismatch

**What goes wrong:** Using `default=True` in Column definition sets the Python-side default but NOT the PostgreSQL server default. If rows are inserted with raw SQL (e.g., in tests), the column may be NULL.

**Why it happens:** Alembic `create_table` uses `server_default` for the DB-level default, while SQLAlchemy ORM `Column(default=...)` is Python-only.

**How to avoid:** In the migration's `create_table`, use `server_default=sa.text("true")` for booleans and `server_default="0"` for integers (matching `0001` pattern). In the ORM model, use `default=True` / `default=0` for Python-side defaults.

**Warning signs:** `NOT NULL constraint violation` when inserting directly with SQL.

### Pitfall 4: `users` as a reserved word in some PostgreSQL contexts

**What goes wrong:** `users` is not a reserved word in PostgreSQL (confirmed — it's allowed as a table name), but some tools/ORMs may quote it. SQLAlchemy handles this correctly.

**Why it happens:** Developers sometimes confuse PostgreSQL with MySQL where `users` may behave differently.

**How to avoid:** No action needed — `__tablename__ = "users"` works fine in PostgreSQL with SQLAlchemy.

### Pitfall 5: Order.user_email already exists — do NOT re-add it

**What goes wrong:** Migration `0006` might accidentally try to add `user_email` to `orders` if the developer conflates USER-02 with needing a schema change.

**Why it happens:** USER-02 says "new orders are automatically linked to their account email" — the linkage field already exists.

**How to avoid:** `Order.user_email` is confirmed present in `app/models/models.py` (`String(255), nullable=True, index=True`) and in `0001`'s `_ensure_base_tables()`. No schema change needed. Phase 1's USER-02 deliverable is verification, not migration.

## Code Examples

### Adding new fields to Settings

```python
# Source: app/config.py (existing codebase pattern)
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ... existing fields ...

    # Auth
    jwt_secret: str                        # required — no default → crash if unset
    jwt_ttl_days: int = 7                  # SINODIK_JWT_TTL_DAYS
    admin_emails: list[str] = []           # SINODIK_ADMIN_EMAILS (comma-separated)
    otp_plaintext_fallback: bool = False   # SINODIK_OTP_PLAINTEXT_FALLBACK

    @field_validator("admin_emails", mode="before")
    @classmethod
    def parse_admin_emails(cls, v):
        if isinstance(v, str):
            return [e.strip().lower() for e in v.split(",") if e.strip()]
        return [e.lower() for e in v] if v else []

    model_config = {"env_prefix": "SINODIK_"}


settings = Settings()
```

### Confirming Order.user_email exists (USER-02 verification)

The column is present in `app/models/models.py`:
```python
# Source: app/models/models.py line 118 (existing code)
user_email = Column(String(255), nullable=True, index=True)
```

No migration needed. Phase 1 success criterion #4 and #5 are satisfied by existing code.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow` (deprecated) | `datetime.now(UTC)` preferred in Python 3.12+ | Python 3.12 | Existing codebase uses deprecated form — match existing pattern, do not change in this phase |
| pydantic v1 `@validator` | pydantic v2 `@field_validator` | pydantic v2 | Must use `@field_validator` with `mode="before"` and `@classmethod` |
| pydantic-settings v1 automatic list splitting | pydantic-settings v2 expects JSON array or custom validator | pydantic-settings v2 | Requires explicit validator for comma-separated lists |

**Deprecated/outdated:**
- `datetime.utcnow`: Deprecated since Python 3.12. Existing code uses it — match the existing pattern for consistency within this phase. Do not refactor.
- `@validator` (pydantic v1): Use `@field_validator` instead.

## Open Questions

1. **Static files mounting in main.py**
   - What we know: `main.py` does NOT include `app.mount("/", StaticFiles(...))` in the current file (import is present but mount is absent from the file read). The `StaticFiles` import exists on line 9 but is not used in the routes shown.
   - What's unclear: Whether the static files mount is somewhere else or intentionally omitted. This does not affect Phase 1 but is a potential gap to note.
   - Recommendation: No action in Phase 1 — not in scope.

2. **`jwt_ttl_days` name vs TTL concerns**
   - What we know: STATE.md notes a concern: "research recommends 60 min default, not 7 days." The CONTEXT.md locked decision is `jwt_ttl_days: int = 7` (7 days). The field name is Phase 1, the concern is Phase 2.
   - What's unclear: Whether the concern should alter the field name (e.g., `jwt_ttl_hours` for finer granularity).
   - Recommendation: Honor the locked decision — add `jwt_ttl_days: int = 7`. Document the concern for Phase 2 to address if needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in pyproject.toml) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` with `pythonpath = ["app"]`, `testpaths = ["tests"]` |
| Quick run command | `docker compose run --rm api pytest tests/ -v` |
| Full suite command | `docker compose run --rm api pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Anonymous order submission still works (no email required) | smoke/integration | `docker compose run --rm api pytest tests/test_phase1.py::test_anonymous_order_unaffected -x` | ❌ Wave 0 |
| USER-02 | `Order.user_email` column exists and is nullable | unit | `docker compose run --rm api pytest tests/test_phase1.py::test_order_user_email_exists -x` | ❌ Wave 0 |
| BOOT-01 | `SINODIK_ADMIN_EMAILS` parsed correctly (comma-separated, lowercase) | unit | `docker compose run --rm api pytest tests/test_phase1.py::test_admin_emails_config -x` | ❌ Wave 0 |
| BOOT-01 | `SINODIK_JWT_SECRET` unset → startup crash with clear error | unit | `docker compose run --rm api pytest tests/test_phase1.py::test_jwt_secret_required -x` | ❌ Wave 0 |

**Note on AUTH-01 smoke test:** The existing test suite (`test_name_extractor.py`) tests NLP only and runs in Docker. The anonymous-order test requires a live DB — it is integration-level and may be marked `pytest.mark.skip` or run as a lighter model-import test instead.

### Sampling Rate
- **Per task commit:** `docker compose run --rm api pytest tests/test_phase1.py -x`
- **Per wave merge:** `docker compose run --rm api pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_phase1.py` — covers AUTH-01, USER-02, BOOT-01 (new file, does not exist yet)

*(Existing `tests/test_name_extractor.py` covers the NLP pipeline only and is unaffected by Phase 1 changes.)*

## Sources

### Primary (HIGH confidence)
- Existing codebase — `app/config.py`, `app/models/models.py`, `app/main.py`, `alembic/versions/0001_extend_schema.py`, `alembic/versions/0005_persons_embedding_vector.py` — direct inspection of all patterns to replicate
- `pyproject.toml` — pytest configuration confirmed

### Secondary (MEDIUM confidence)
- pydantic-settings v2 list parsing behavior — based on known pydantic v2 behavior change from v1; `cors_origins` field in existing codebase implicitly confirms JSON-array expectation (no comma-split validator present)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use
- Architecture: HIGH — all patterns taken directly from existing codebase
- Pitfalls: HIGH — verified against actual existing code (migration chain, column presence, pydantic-settings behavior)

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable stack — pydantic-settings, SQLAlchemy, Alembic all pinned in project)
