# Phase 4: Protected Routes and Admin Endpoints - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Authenticated users can access their own data; admins can manage all data; unauthenticated access to protected operations is rejected. This phase adds auth guards to existing routes and introduces admin-only endpoints (users CRUD, CSV upload, commemoration edit/delete). Scope is fixed by ROADMAP; discussion clarified how to implement it.

</domain>

<decisions>
## Implementation Decisions

### GET /names/by-user
- For non-admin: email only from JWT (current user); remove `email` query parameter — user always sees only their own data.
- For admin: optional `?email=...` — without param returns own data, with param returns that user's commemorations.
- Response format unchanged: `{ "user_email": "...", "commemorations": [...], "count": N }`.
- Keep `active_only` query parameter (default true).

### GET /orders and POST /orders
- GET `/orders`: require auth. User sees only their orders; admin sees all. Keep limit/offset pagination.
- POST `/orders`: if JWT present — set user_email from token (ignore/override body); without JWT — anonymous order (AUTH-01: names only, no email required).
- GET `/orders/{id}`, PATCH/DELETE order: admin only; regular user has no access by order id.

### Admin users API
- GET `/api/v1/admin/users`: list all accounts. Each item: id, email, role, is_active, created date, **orders_count**, **active_commemoration_count**.
- PATCH `/api/v1/admin/users/{id}`: body `{ "role": "admin" | "user", "is_active": true | false }` — both optional, partial update. Response: 200 + full user object.
- Protect against removing last admin: if action would demote/disable the last admin, return 400 or 403 with clear message.

### POST /upload/csv
- Require admin: `require_admin` dependency; 403 for non-admin.

### GET /commemorations and related
- GET `/commemorations` (list): require auth. User sees only commemorations from their orders; admin sees all. Existing filters (no_start_date, limit, offset) apply after scope filter.
- GET `/commemorations/{id}`: not introduced in this phase; PATCH/DELETE by id from list is sufficient.
- PATCH/DELETE `/commemorations/{id}`: admin only.
- POST `/commemorations/bulk-update`: admin only.

### Error format
- 401/403: standard FastAPI `{ "detail": "..." }` as in Phase 3.

### Claude's Discretion
- Exact Pydantic model names for admin user list and PATCH body.
- Implementation of orders_count / active_commemoration_count (queries or denormalization).
- Whether GET /commemorations list reuses existing get_commemorations with scope filter or new service method.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/api/deps.py` — `get_current_user`, `require_admin` (Phase 3); use on all protected routes.
- `app/services/query_service.py` — `get_by_user(db, user_email, active_only)`; already filters by Order.user_email.
- `app/api/routes/names.py` — GET `/names/by-user` exists; add Depends(get_current_user), derive email from user or query (admin).
- `app/api/routes/upload.py` — POST `/upload/csv`; add Depends(require_admin).
- `app/api/routes/orders.py` — GET/POST/GET id/PATCH/DELETE; add auth and scope (user vs admin).
- `app/api/routes/commemorations.py` — GET list, PATCH/DELETE by id, bulk-update; add auth and scope for list, require_admin for mutate.
- `app/models/models.py` — User (id, email, role, is_active, created_at, etc.), Order, Commemoration.

### Established Patterns
- Routes: APIRouter, prefix `/api/v1`, Depends(get_db), Depends(get_current_user) or Depends(require_admin).
- User loaded by email (deps use payload["sub"] = email).

### Integration Points
- New router: `app/api/routes/admin.py` (or similar) for GET/PATCH `/admin/users`; register in main.py with prefix `/api/v1`, tags ["admin"].
- Orders list: filter by `Order.user_email == current_user.email` for non-admin.
- Commemorations list: filter by order ownership (join Order, filter Order.user_email) for non-admin.

</code_context>

<specifics>
## Specific Ideas

- Admin user list includes orders_count and active_commemoration_count for dashboard/overview.
- Block demoting or disabling the last admin with explicit 400/403 and message.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-protected-routes-and-admin-endpoints*
*Context gathered: 2026-03-14*
