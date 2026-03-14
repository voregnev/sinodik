---
phase: 03-auth-routes-and-dependencies
plan: 01
subsystem: auth
tags: [jwt, fastapi, dependencies, pyjwt, http-bearer]

# Dependency graph
requires:
  - phase: 02-auth-service-core
    provides: create_jwt_token, User model, JWT payload (sub=email, role)
provides:
  - get_current_user dependency (Bearer JWT → User or 401)
  - require_admin dependency (403 if role != admin)
affects: phase 04 protected routes, auth routes in plan 03-02

# Tech tracking
tech-stack:
  added: []
  patterns: FastAPI Depends(HTTPBearer(auto_error=False)), PyJWT decode in deps only

key-files:
  created: [app/api/deps.py, tests/test_auth_deps.py]
  modified: []

key-decisions:
  - "JWT verification and User load live only in deps.py; routes depend on get_current_user/require_admin"

patterns-established:
  - "Auth gate: HTTPBearer(auto_error=False) so 401 is raised explicitly for missing token"
  - "get_current_user: decode JWT → payload[sub] → load User by email → 401 if invalid/inactive"

requirements-completed: []

# Metrics
duration: 5
completed: "2026-03-14"
---

# Phase 03 Plan 01: JWT and Role Dependencies Summary

**Shared FastAPI dependencies for JWT verification and admin role check (get_current_user, require_admin) so any route can protect endpoints without duplicating JWT logic.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-14
- **Completed:** 2026-03-14
- **Tasks:** 1
- **Files modified:** 2 (created)

## Accomplishments

- `app/api/deps.py`: `get_current_user` validates Bearer JWT with PyJWT, loads User by `payload["sub"]`, returns 401 for missing/invalid/expired/inactive token.
- `require_admin` depends on `get_current_user` and returns 403 when `role != "admin"`.
- `tests/test_auth_deps.py`: import and callable/coroutine checks for both dependencies.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create app/api/deps.py and tests/test_auth_deps.py** - `1a1475d` (feat)

**Plan metadata:** `9b17663` (docs: complete 03-01 plan)

## Self-Check: PASSED

- FOUND: app/api/deps.py
- FOUND: tests/test_auth_deps.py
- FOUND: commit 1a1475d

## Files Created/Modified

- `app/api/deps.py` - get_current_user, require_admin, HTTPBearer(auto_error=False), JWT decode and User load
- `tests/test_auth_deps.py` - import and iscoroutinefunction checks for deps

## Decisions Made

None — followed plan as specified. Imports use project convention (config, database, models.models) to match main.py and database.py.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 03-02 (auth routes) can depend on `get_current_user` and `require_admin` from `app.api.deps` (or `api.deps` in container).
- No blockers.

---
*Phase: 03-auth-routes-and-dependencies*
*Completed: 2026-03-14*
