---
phase: 04-protected-routes-and-admin-endpoints
plan: "03"
subsystem: api
tags: [fastapi, auth, admin, jwt, scope]

requires:
  - phase: 03-auth-routes-and-dependencies
    provides: get_current_user, require_admin (api.deps)
provides:
  - POST /upload/csv restricted to admin only (ADMN-08)
  - GET /commemorations requires auth; user sees own order commemorations, admin sees all
  - PATCH/DELETE /commemorations/{id} and POST /commemorations/bulk-update require admin (ADMN-06, ADMN-07)
affects: []

tech-stack:
  added: []
  patterns: [Depends(require_admin) for admin-only routes, get_commemorations(db, user_email=...) for scope]

key-files:
  created: [tests/test_upload_auth.py, tests/test_commemorations_auth.py]
  modified: [app/api/routes/upload.py, app/api/routes/commemorations.py, app/services/query_service.py]

key-decisions:
  - "Override route-module deps (e.g. upload_routes.require_admin) in tests so dependency_overrides key matches"

patterns-established:
  - "Admin-only route: add _admin: User = Depends(require_admin); GET list with scope: effective_email = None if admin else current_user.email, pass to service"

requirements-completed: [ADMN-06, ADMN-07, ADMN-08]

duration: 15min
completed: "2026-03-14"
---

# Phase 4 Plan 03: Upload and Commemorations Auth Summary

**CSV upload admin-only and commemorations list/mutate guarded: GET list scoped by user vs admin; PATCH/DELETE/bulk-update admin-only.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-14T20:47:24Z
- **Completed:** 2026-03-14T20:55:00Z
- **Tasks:** 2
- **Files modified:** 5 (3 modified, 2 test files created/rewritten)

## Accomplishments

- POST /api/v1/upload/csv requires admin; non-admin receives 403 (ADMN-08).
- GET /api/v1/commemorations requires auth; non-admin sees only commemorations from orders where user_email matches; admin sees all.
- PATCH/DELETE /commemorations/{id} and POST /commemorations/bulk-update require admin (ADMN-06, ADMN-07).
- query_service.get_commemorations extended with optional user_email for scope filtering.
- Tests: 401 without token, 403 for non-admin, scope (user vs admin), and admin mutate with mocked DB where needed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Require admin on POST /upload/csv** - `4242386` (feat)
2. **Task 2: Guard and scope GET /commemorations; require_admin on mutate** - `2ab7e10` (feat)

## Files Created/Modified

- `app/api/routes/upload.py` - Added Depends(require_admin), import User and require_admin.
- `app/api/routes/commemorations.py` - GET: get_current_user, effective_email, get_commemorations(..., user_email=...); PATCH/DELETE/bulk-update: require_admin.
- `app/services/query_service.py` - get_commemorations(..., user_email=None); when set, filter by Order.user_email.
- `tests/test_upload_auth.py` - 401, 403, 200 (admin + mock process_csv_upload); override upload_routes.require_admin for key match.
- `tests/test_commemorations_auth.py` - 401 GET; user scope and admin all GET; 403 mutate as user; admin PATCH/DELETE (mock get_db for delete to avoid event-loop).

## Decisions Made

- Tests override the dependency from the route module (e.g. `upload_routes.require_admin`, `commemorations_routes.get_current_user`) so FastAPI’s dependency_overrides key matches the route’s Depends() callable.
- Delete-as-admin test mocks get_db via `commemorations_routes.get_db` to avoid asyncpg “attached to a different loop” in TestClient.

## Deviations from Plan

None - plan executed as written. Minor implementation detail: dependency override key must be the same reference the route uses (route-module import), not a separate import of deps in the test file.

## Issues Encountered

- In Docker, overriding `get_current_user` or `require_admin` by importing from `api.deps` in the test did not apply (401 instead of 403) because the route’s Depends() holds the reference from the route module. Using `upload_routes.require_admin` and `commemorations_routes.get_current_user` / `require_admin` / `get_db` for overrides fixed it.
- test_delete_commemoration_as_admin hit “Future attached to a different loop” when using real DB; fixed by overriding get_db with a mock session (using `commemorations_routes.get_db` as override key).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Upload and commemorations routes are guarded per CONTEXT; get_commemorations supports user_email scope; tests cover 401, 403, and scope.
- Ready for further phase 4 plans (e.g. admin users API if not already done).

## Self-Check: PASSED

- 04-03-SUMMARY.md present
- Commits 4242386, 2ab7e10, 5677ece present

---
*Phase: 04-protected-routes-and-admin-endpoints*
*Completed: 2026-03-14*
