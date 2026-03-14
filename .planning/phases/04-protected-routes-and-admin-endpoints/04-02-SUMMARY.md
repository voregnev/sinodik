---
phase: 04-protected-routes-and-admin-endpoints
plan: "02"
subsystem: auth
tags: [jwt, fastapi, deps, scope, admin]

requires:
  - phase: 03-auth-routes-and-dependencies
    provides: get_current_user, require_admin, auth routes
provides:
  - get_current_user_optional for optional-auth endpoints
  - GET /names/by-user guarded and scoped (user own data, admin ?email=)
  - GET /orders scoped by user_email; POST links to JWT when present
  - GET/PATCH/DELETE /orders/{id} admin-only
affects: [04-03, 04-04, frontend]

tech-stack:
  added: []
  patterns: [dependency_overrides from route module in tests, mock get_db for list_orders]

key-files:
  created: [tests/test_names_by_user_auth.py, tests/test_orders_auth.py]
  modified: [app/api/deps.py, app/api/routes/names.py, app/api/routes/orders.py]

key-decisions:
  - "Optional auth via get_current_user_optional: return None on no/invalid token instead of 401"
  - "Orders list: non-admin filtered by Order.user_email == current_user.email; admin sees all"
  - "POST /orders: link_email = current_user.email if authenticated else body.user_email"

patterns-established:
  - "Override same dependency object the route uses (e.g. api.routes.names.get_current_user) for tests"
  - "Mock get_by_user / get_db at route module to avoid asyncpg/model conflicts in TestClient"

requirements-completed: [USER-01, ADMN-01]

duration: 25min
completed: "2026-03-14"
---

# Phase 04 Plan 02: Protected Routes and Admin Endpoints Summary

**Optional-auth dependency, names/by-user and orders guarded and scoped: user sees own data, admin sees all; POST /orders links to JWT user when present; order by-id and mutate admin-only.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3
- **Files modified:** 5 (deps, names, orders, 2 test files)

## Accomplishments

- `get_current_user_optional` in deps.py: same JWT decode and User lookup as `get_current_user`, returns `None` on no/invalid token or user not found/inactive.
- GET /names/by-user requires auth; effective_email = current_user.email for non-admin; admin can pass optional `?email=` to view another user's data; response shape unchanged.
- GET /orders requires auth; filtered by `Order.user_email == current_user.email` for non-admin; admin sees all. POST /orders uses `get_current_user_optional`: when authenticated, `user_email` is taken from token; otherwise from body (anonymous order). GET/PATCH/DELETE /orders/{id} require admin.
- Tests: 401 without token for names and orders list; user scope and admin scope for names and orders; POST with/without token; GET /orders/{id} 403 as user, 200 as admin.

## Task Commits

1. **Task 1: Add get_current_user_optional to deps.py** — `a09d6ca` (feat)
2. **Task 2: Guard and scope GET /names/by-user** — `45fa871` (feat)
3. **Task 3: Guard and scope orders** — `23a6109` (feat)

## Files Created/Modified

- `app/api/deps.py` — added `get_current_user_optional`
- `app/api/routes/names.py` — `get_current_user` on by-user, optional `email` query, effective_email logic
- `app/api/routes/orders.py` — `get_current_user` on list, `get_current_user_optional` on POST, `require_admin` on get/patch/delete by id; list filter for non-admin
- `tests/test_names_by_user_auth.py` — 401, user token own data, admin own/other via ?email=; override from route module, mock get_by_user
- `tests/test_orders_auth.py` — 401, user scope, admin all, POST JWT/anon, 403 by-id user, 200 by-id admin; override get_db from route module

## Decisions Made

- Optional auth: return `None` instead of raising 401 so POST /orders can accept both authenticated and anonymous requests.
- Tests use dependency overrides keyed by the dependency imported in the route module (e.g. `api.routes.names.get_current_user`) so FastAPI applies the override; mock `get_by_user` / `get_db` to avoid real DB and model registry conflicts in Docker test run.

## Deviations from Plan

None — plan executed as written. Test strategy used route-module dependency override and mocks for DB/service to satisfy verification in Docker without hitting asyncpg/model conflicts.

## Issues Encountered

- Dependency override in tests had to use the same callable reference the route uses (from the route module) so FastAPI’s override key matches.
- Names/by-user tests mock `api.routes.names.get_by_user` to avoid SQLAlchemy “Multiple classes for models.models.Commemoration” in container. Orders tests override `get_db` from `api.routes.orders` and provide a mock session so list_orders and get_order don’t hit the real DB.

## Next Phase Readiness

- USER-01 and ADMN-01 satisfied. Ready for 04-03 (upload/commemorations guard) and 04-04 (admin users).

---
*Phase: 04-protected-routes-and-admin-endpoints*
*Completed: 2026-03-14*
