---
phase: 04-protected-routes-and-admin-endpoints
plan: "04"
subsystem: api
tags: [fastapi, admin, sqlalchemy, pytest, httpx]

# Dependency graph
requires:
  - phase: 04-protected-routes-and-admin-endpoints
    provides: require_admin, get_current_user (deps)
provides:
  - GET /api/v1/admin/users (list all users with orders_count, active_commemoration_count)
  - PATCH /api/v1/admin/users/{id} (role, is_active; last-admin protection)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: "Admin routes with Depends(require_admin); scalar_subquery for counts; dependency override + AsyncClient for same-loop DB tests"

key-files:
  created: [app/api/routes/admin.py, tests/test_admin_routes.py]
  modified: [app/main.py]

key-decisions:
  - "GET /admin/users uses single query with scalar_subquery for orders_count and active_commemoration_count to avoid N+1"
  - "Last-admin guard: 400 with clear message when demoting or disabling the last active admin"
  - "PATCH tests use get_db override + session_factory created in test loop so AsyncClient and DB share same event loop"

patterns-established:
  - "Admin router: APIRouter(prefix='/admin'), registered with prefix=/api/v1"
  - "Integration tests for PATCH: override get_db and require_admin, use httpx.AsyncClient(ASGITransport(app=app)) in async test"

requirements-completed: [ADMN-02, ADMN-03, ADMN-04, ADMN-05]

# Metrics
duration: ~10min
completed: "2026-03-14"
---

# Phase 04 Plan 04: Admin Users API Summary

**GET /api/v1/admin/users and PATCH /api/v1/admin/users/{id} with last-admin protection; admin-only; tests cover ADMN-02–ADMN-05.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-14T20:47:41Z
- **Completed:** 2026-03-14T20:57:29Z
- **Tasks:** 2
- **Files modified:** 3 (admin.py created, main.py, test_admin_routes.py)

## Accomplishments

- Admin router with GET /admin/users returning all users and per-user orders_count and active_commemoration_count (single query, scalar_subquery).
- PATCH /admin/users/{id} with optional role and is_active; 404 when user not found; 400 when action would demote or disable the last admin.
- Tests: 401/403/200 for GET; promote 200, demote when other admin 200, demote/disable last admin 400, disable user 200, 404.

## Task Commits

Each task was committed atomically:

1. **Task 1: GET /admin/users — list all users with counts** - `e9fd68b` (feat)
2. **Task 2: PATCH /admin/users/{id} with last-admin protection** - `945a0ec` (feat)

## Files Created/Modified

- `app/api/routes/admin.py` - GET /users (list with counts), PATCH /users/{id} (role, is_active, last-admin guard)
- `app/main.py` - include_router(admin.router, prefix="/api/v1", tags=["admin"])
- `tests/test_admin_routes.py` - 9 tests: GET 401/403/200, PATCH promote/demote/disable/last-admin/404

## Decisions Made

- Used dependency_overrides for require_admin in GET tests (no real JWT).
- PATCH tests use async tests + _make_session_factory() + override get_db so endpoint and test share the same event loop (avoids asyncpg "different loop" with TestClient).
- Last-admin check: count active admins; if 1 and target is that admin and (role→user or is_active→false), return 400.

## Deviations from Plan

None - plan executed as written. Minor addition: test_patch_user_not_found_404 for 404 behaviour.

## Issues Encountered

- TestClient + async DB in same test caused "Future attached to a different loop" (asyncpg). Resolved by overriding get_db with a session_factory created in the async test and using httpx.AsyncClient(ASGITransport(app=app)) so app runs in the same loop.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Admin users API is implemented and tested. Phase 4 remaining plans (if any) can build on this router.

---
*Phase: 04-protected-routes-and-admin-endpoints*
*Completed: 2026-03-14*
