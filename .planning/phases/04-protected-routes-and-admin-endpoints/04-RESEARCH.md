# Phase 4: Protected Routes and Admin Endpoints — Research

**Researched:** 2026-03-14
**Domain:** FastAPI auth guards, scope filtering (user vs admin), admin-only endpoints
**Confidence:** HIGH

## Summary

Phase 4 applies the existing `get_current_user` and `require_admin` dependencies (Phase 3) to protect routes and introduce scope: authenticated users see only their own data; admins see all. It adds an optional-auth dependency for POST /orders (JWT present → set user_email from token; absent → anonymous order). New admin router provides GET/PATCH `/admin/users` with orders_count and active_commemoration_count; last-admin protection blocks demoting or disabling the last admin. No new auth libraries — only route changes, one new optional dependency, and a new admin module.

**Primary recommendation:** Add `get_current_user_optional` in deps.py (returns User | None, no 401); protect GET /names/by-user, GET/POST/GET id/PATCH/DELETE orders, GET/PATCH/DELETE commemorations and bulk-update, POST /upload/csv with auth/admin as per CONTEXT; implement GET/PATCH `/api/v1/admin/users` with scope filtering and last-admin check. Reuse existing `get_by_user` and extend or wrap `get_commemorations` for scope.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **GET /names/by-user:** Non-admin: email only from JWT (current user); remove `email` query parameter — user always sees only their own data. Admin: optional `?email=...` — without param returns own data, with param returns that user's commemorations. Response format unchanged: `{ "user_email": "...", "commemorations": [...], "count": N }`. Keep `active_only` (default true).
- **GET /orders and POST /orders:** GET `/orders`: require auth. User sees only their orders; admin sees all. Keep limit/offset. POST `/orders`: if JWT present — set user_email from token (ignore/override body); without JWT — anonymous order (AUTH-01). GET `/orders/{id}`, PATCH/DELETE order: admin only; regular user no access by order id.
- **Admin users API:** GET `/api/v1/admin/users`: list all accounts. Each item: id, email, role, is_active, created date, **orders_count**, **active_commemoration_count**. PATCH `/api/v1/admin/users/{id}`: body `{ "role": "admin" | "user", "is_active": true | false }` — both optional, partial update. Response: 200 + full user object. Protect against removing last admin: if action would demote/disable the last admin, return 400 or 403 with clear message.
- **POST /upload/csv:** Require admin: `require_admin` dependency; 403 for non-admin.
- **GET /commemorations and related:** GET `/commemorations`: require auth. User sees only commemorations from their orders; admin sees all. Existing filters (no_start_date, limit, offset) apply after scope. GET `/commemorations/{id}` not introduced; PATCH/DELETE by id from list sufficient. PATCH/DELETE `/commemorations/{id}`: admin only. POST `/commemorations/bulk-update`: admin only.
- **Error format:** 401/403: standard FastAPI `{ "detail": "..." }` as in Phase 3.

### Claude's Discretion
- Exact Pydantic model names for admin user list and PATCH body.
- Implementation of orders_count / active_commemoration_count (queries or denormalization).
- Whether GET /commemorations list reuses existing get_commemorations with scope filter or new service method.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| USER-01 | Authenticated user can view their own orders (matched by email) | GET /orders with Depends(get_current_user); filter Order by user_email == current_user.email for non-admin; admin: no filter. Existing list_orders adapted with scope. |
| ADMN-01 | Admin can view all orders across all users | GET /orders with same auth; when current_user.role == "admin", omit user_email filter. |
| ADMN-02 | Admin can view all user accounts (email, role, active status, created date) | GET /admin/users with Depends(require_admin); list User with orders_count and active_commemoration_count (subquery or separate queries). |
| ADMN-03 | Admin can promote a user to admin role | PATCH /admin/users/{id} with body.role = "admin"; update User.role; enforce last-admin check. |
| ADMN-04 | Admin can demote an admin to user role | PATCH /admin/users/{id} with body.role = "user"; if target is last admin, return 400/403. |
| ADMN-05 | Admin can disable a user account (is_active = false; JWT rejected) | PATCH /admin/users/{id} with body.is_active = false; if target is last admin, return 400/403. get_current_user already rejects inactive users. |
| ADMN-06 | Admin can edit any commemoration record | PATCH /commemorations/{id} with Depends(require_admin); existing handler logic unchanged. |
| ADMN-07 | Admin can delete any commemoration record | DELETE /commemorations/{id} with Depends(require_admin); existing handler unchanged. |
| ADMN-08 | CSV upload restricted to admin role only | POST /upload/csv with Depends(require_admin); 403 for non-admin. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ (project) | Depends, APIRouter, HTTPException | Already in use; deps from Phase 3 |
| app.api.deps | existing | get_current_user, require_admin | Phase 3; no changes to JWT validation |
| SQLAlchemy 2.0+ async | project | Filter Order/Commemoration by user_email, count admins | Already used in routes and query_service |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic BaseModel | project | Admin user list item, PATCH body | Request/response schemas for admin API |

### New Dependency (same file)
| Dependency | Purpose | When to Use |
|-------------|---------|-------------|
| get_current_user_optional | Returns User if valid Bearer present, else None. No 401. | POST /orders: when present, set order user_email from token; when absent, allow anonymous (body.user_email or null). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Optional dependency returning User \| None | Two routes (authenticated vs anonymous) | Single route with optional dep keeps one handler and clear override rule (JWT overrides body). |
| Subqueries for orders_count / active_commemoration_count | Denormalized counters on User | Counters need maintenance on order/commemoration changes; subqueries are correct and simple for admin list. |

**Installation:** No new packages. All dependencies already in project.

## Architecture Patterns

### Recommended Project Structure
```
app/
├── api/
│   ├── deps.py                    # add get_current_user_optional
│   └── routes/
│       ├── admin.py               # NEW: GET/PATCH /admin/users
│       ├── auth.py
│       ├── commemorations.py      # add get_current_user / require_admin, scope on GET
│       ├── names.py                # add get_current_user, scope for by-user
│       ├── orders.py               # add auth + scope; optional auth on POST
│       └── upload.py               # add require_admin
├── services/
│   └── query_service.py           # optional: get_commemorations_scoped or param user_email
└── main.py                        # include_router(admin.router, prefix="/api/v1", tags=["admin"])
```

### Pattern 1: Optional auth dependency
**What:** A dependency that uses the same Bearer extraction as get_current_user but returns None when credentials are missing or invalid, instead of raising 401.
**When to use:** Endpoints that accept both anonymous and authenticated calls (e.g. POST /orders).
**Example:**
```python
# deps.py
async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
    email = payload.get("sub")
    if not email:
        return None
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user
```

### Pattern 2: Scope filtering in list endpoints
**What:** After resolving current_user, pass an effective "filter email" to the service: for non-admin use current_user.email; for admin use query param (e.g. ?email=) or None for "all".
**When to use:** GET /orders, GET /names/by-user, GET /commemorations.
**Example (conceptual):**
```python
# In route: effective_email = current_user.email if current_user.role != "admin" else (query_email or current_user.email)
# For orders: filter Order.user_email == effective_email when not admin; when admin and no query, no filter.
```

### Pattern 3: Last-admin protection
**What:** Before applying PATCH that sets role to "user" or is_active to False, count users where role == "admin" and is_active == True. If count == 1 and the target user is that admin, raise HTTP 400 or 403 with a clear message (e.g. "Cannot demote or disable the last admin").
**When to use:** PATCH /admin/users/{id} when body contains role="user" or is_active=False.

### Anti-Patterns to Avoid
- **Using 403 for missing token:** Use 401 for missing/invalid JWT (Phase 3 contract); 403 only for "authenticated but not allowed" (e.g. non-admin on admin route).
- **Forgetting scope on GET list:** Every list endpoint that returns user-specific data must filter by current_user.email for non-admin.
- **Allowing email query for non-admin on /names/by-user:** CONTEXT locks: non-admin must not have email query param; only admin may use ?email=.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|--------------|-------------|-----|
| JWT validation | Custom parsing | get_current_user / require_admin (deps) | Already implemented; consistent 401/403 |
| Role check | Inline if role != "admin" | Depends(require_admin) | Single place; 403 detail |
| Optional auth | Ad-hoc try/except in route | get_current_user_optional dependency | Reusable; clear separation |

**Key insight:** Phase 3 already provides the auth primitives; this phase only composes them on routes and adds one optional variant.

## Common Pitfalls

### Pitfall 1: POST /orders user_email override wrong order
**What goes wrong:** Setting user_email from body when JWT is present, or ignoring JWT.
**Why it happens:** CONTEXT says "if JWT present — set user_email from token (ignore/override body)".
**How to avoid:** In POST /orders handler, call get_current_user_optional; if user is not None, pass user.email to create_manual_order and do not use body.user_email for linking.
**Warning signs:** Tests where authenticated POST has body.user_email different from token and order is created with body value.

### Pitfall 2: Last admin can be demoted/disabled
**What goes wrong:** PATCH allows role="user" or is_active=false on the only remaining admin.
**Why it happens:** Forgetting to count admins before update.
**How to avoid:** In PATCH /admin/users/{id}, before commit: if new role is "user" or new is_active is False, run count of (User where role=="admin" and is_active==True). If count == 1 and target user is admin and active, raise 400/403.
**Warning signs:** Single admin in DB; PATCH succeeds and next request gets no admin.

### Pitfall 3: GET /commemorations returns all for user
**What goes wrong:** List returns every commemoration instead of only those from orders where Order.user_email == current_user.email.
**Why it happens:** Reusing get_commemorations without a scope filter.
**How to avoid:** Either add optional user_email to get_commemorations and filter by Order.user_email when provided, or add get_commemorations_scoped(db, user, ...) that joins Order and filters; for admin pass None to mean no filter.
**Warning signs:** User sees other users' commemorations in list.

### Pitfall 4: GET /names/by-user still requires email query for user
**What goes wrong:** Non-admin must pass ?email= and can guess others' emails.
**Why it happens:** CONTEXT: for non-admin remove email query parameter — user always sees only their own data.
**How to avoid:** For non-admin, do not read email from query; use current_user.email only. For admin, optional ?email=; without param return own data.
**Warning signs:** Docs or tests require email for non-admin.

## Code Examples

### Optional auth in POST handler
```python
# orders.py (conceptual)
@router.post("/orders")
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    link_email = current_user.email if current_user else body.user_email
    comms = await create_manual_order(db, ..., user_email=link_email, ...)
    return {"order_id": comms[0].order_id, "commemorations_created": len(comms)}
```

### Admin list with counts (conceptual)
```python
# Option A: two subqueries in select
from sqlalchemy import select, func
# Count orders per user, count active commemorations per user (join Order -> Commemoration, filter is_active and expires_at >= today)
# Option B: list users then for each user run count orders and count active comms (N+1; avoid if list is large)
# Prefer Option A: single query with scalar_subquery or lateral join.
```

### Last-admin check
```python
# Before applying role or is_active change that would remove an admin:
admin_count = await db.scalar(
    select(func.count(User.id)).where(
        User.role == "admin",
        User.is_active == True,
    )
)
if admin_count == 1 and target_user.role == "admin" and target_user.is_active:
    if (body.role is not None and body.role != "admin") or (body.is_active is not None and body.is_active is False):
        raise HTTPException(400, detail="Cannot demote or disable the last admin")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No auth on orders/names/commemorations | Depends(get_current_user) or require_admin | Phase 4 | All protected routes require token except POST /orders (optional) and anonymous-friendly endpoints |

**Deprecated/outdated:** None for this phase — building on Phase 3 as-is.

## Open Questions

1. **orders_count / active_commemoration_count implementation**
   - What we know: CONTEXT leaves to discretion; subqueries are correct; denormalization adds write-path complexity.
   - Recommendation: Use correlated subqueries (or one query with group_by User.id and counts) in GET /admin/users to avoid N+1 and keep data correct without triggers.

2. **GET /commemorations reuse vs new method**
   - What we know: get_commemorations(db, no_start_date, limit, offset) has no user filter.
   - Recommendation: Add optional parameter `user_email: str | None = None`; when set, join Order and filter Order.user_email == user_email. Admin passes None; user passes current_user.email. Same response shape.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project) |
| Config file | pyproject.toml [tool.pytest.ini_options], testpaths = ["tests"] |
| Quick run command | `docker compose run --rm api pytest tests/ -v -x` |
| Full suite command | `docker compose run --rm api pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| USER-01 | GET /orders returns only own orders for user | integration | `pytest tests/test_orders_auth.py -x` | ❌ Wave 0 |
| ADMN-01 | GET /orders returns all for admin | integration | same | ❌ Wave 0 |
| ADMN-02 | GET /admin/users returns list with counts | integration | `pytest tests/test_admin_routes.py -x` | ❌ Wave 0 |
| ADMN-03 | PATCH /admin/users/{id} promote to admin | integration | same | ❌ Wave 0 |
| ADMN-04 | PATCH demote admin; last admin blocked | integration | same | ❌ Wave 0 |
| ADMN-05 | PATCH disable user; last admin blocked | integration | same | ❌ Wave 0 |
| ADMN-06 | PATCH /commemorations/{id} admin only | integration | `pytest tests/test_commemorations_auth.py -x` | ❌ Wave 0 |
| ADMN-07 | DELETE /commemorations/{id} admin only | integration | same | ❌ Wave 0 |
| ADMN-08 | POST /upload/csv 403 for non-admin | integration | `pytest tests/test_upload_auth.py -x` or combined | ❌ Wave 0 |

Additional coverage: GET /names/by-user scope (user vs admin ?email=), POST /orders JWT override (user_email from token when present), 401 on protected routes without token, 403 on admin routes as user.

### Sampling Rate
- **Per task commit:** `pytest tests/test_<affected>.py -v -x`
- **Per wave merge:** `docker compose run --rm api pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_orders_auth.py` or equivalent — GET/POST orders auth and scope
- [ ] `tests/test_admin_routes.py` — GET/PATCH admin/users, last-admin
- [ ] `tests/test_commemorations_auth.py` — GET list scope, PATCH/DELETE/bulk-update admin only
- [ ] `tests/test_upload_auth.py` or part of existing — POST /upload/csv require_admin
- [ ] `tests/test_names_by_user_auth.py` or equivalent — by-user scope and admin ?email=
- [ ] Shared fixtures: authenticated user (user + admin), DB with orders/commemorations (can build on existing test DB usage)
- Framework: pytest already present; no new install

## Sources

### Primary (HIGH confidence)
- Phase 3 RESEARCH.md and CONTEXT.md — auth endpoints and deps design
- 04-CONTEXT.md — locked decisions and code context
- app/api/deps.py, app/api/routes/orders.py, names.py, upload.py, commemorations.py — current implementations

### Secondary (MEDIUM confidence)
- FastAPI dependency injection and optional dependencies — standard pattern (return None instead of raise)
- SQLAlchemy select with filter by Order.user_email — existing get_by_user pattern

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — same stack as Phase 3; only one new optional dep and new router
- Architecture: HIGH — patterns follow CONTEXT and existing deps
- Pitfalls: HIGH — derived from CONTEXT and common mistakes on scope/last-admin

**Research date:** 2026-03-14
**Valid until:** ~30 days (stable FastAPI/SQLAlchemy usage)
