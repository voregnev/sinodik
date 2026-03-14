---
phase: 03-auth-routes-and-dependencies
plan: 02
subsystem: auth
tags: [fastapi, jwt, otp, auth-routes, pytest]

# Dependency graph
requires:
  - phase: 03-01
    provides: get_current_user, require_admin, JWT verification
provides:
  - POST /api/v1/auth/request-otp (202/429/400)
  - POST /api/v1/auth/verify-otp (200/401)
  - GET /api/v1/auth/me (200/401)
affects: [frontend-login, user-context]

# Tech tracking
tech-stack:
  added: []
  patterns: [FastAPI APIRouter with Depends(get_db), dependency_overrides in tests]

key-files:
  created: [app/api/routes/auth.py, tests/test_auth_routes.py]
  modified: [app/main.py, app/services/auth_service.py, app/services/email_service.py]

key-decisions:
  - "Auth routes use same import style as orders (database, models.models, services, api.deps) for Docker"
  - "Tests use mocks for verify_otp/rate_limit/me to avoid async loop/DB conflicts with TestClient"

patterns-established:
  - "Auth API: request-otp 202 + message (+ optional dev_otp_code); verify-otp 200 token+user or 401; GET me via get_current_user"

requirements-completed: [USER-03]

# Metrics
duration: ~15min
completed: "2026-03-14"
---

# Phase 03 Plan 02: Auth HTTP Endpoints Summary

**Auth API exposed over HTTP: POST request-otp, POST verify-otp, GET me; router registered under /api/v1; integration tests cover phase criteria and USER-03 (logout = client discard, /me rejects missing/expired token).**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 5 (3 created/added, 2 modified)

## Accomplishments

- `app/api/routes/auth.py`: POST /auth/request-otp (202/429/400), POST /auth/verify-otp (200/401), GET /auth/me (200/401)
- Auth router registered in `main.py` under prefix `/api/v1`, tags=["auth"]
- `tests/test_auth_routes.py`: 8 tests for phase success criteria and USER-03

## Task Commits

1. **Task 1: Create app/api/routes/auth.py with three endpoints** — `52c1bba` (feat)
2. **Task 2: Register auth router in main.py** — `099c40f` (feat)
3. **Task 3: Add tests/test_auth_routes.py** — `2f1b483` (test)

## Files Created/Modified

- `app/api/routes/auth.py` — Auth HTTP endpoints (request-otp, verify-otp, me)
- `app/main.py` — include_router(auth.router, prefix="/api/v1", tags=["auth"])
- `tests/test_auth_routes.py` — Integration tests (request_otp, verify_otp, GET /me)
- `app/services/auth_service.py` — Imports fixed for Docker (no app.); datetime.UTC → timezone.utc
- `app/services/email_service.py` — Imports fixed for Docker (no app.)

## Decisions Made

- Use non-prefixed imports (config, models.models, services) in auth routes and auth_service/email_service so the app runs in Docker where PYTHONPATH=/app and there is no top-level `app` package.
- Test strategy: mock verify_otp, check_rate_limit, and use dependency_overrides for get_current_user to avoid TestClient/asyncpg event-loop conflicts while still testing route behavior and response shapes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Docker imports in auth_service and email_service**
- **Found during:** Task 1 (import auth in verification)
- **Issue:** auth_service/email_service used `from app.models.models` / `from app.config`; in container there is no `app` package (contents of app/ are at /app).
- **Fix:** Switched to `from models.models`, `from config` in auth_service and email_service.
- **Files modified:** app/services/auth_service.py, app/services/email_service.py
- **Committed in:** 52c1bba (Task 1)

**2. [Rule 1 - Bug] datetime.UTC not available in Python 3.14 (AttributeError)**
- **Found during:** Task 3 (running tests)
- **Issue:** auth_service used `datetime.now(datetime.UTC)`; AttributeError in runtime.
- **Fix:** Use `from datetime import timezone` and `datetime.now(timezone.utc)`.
- **Files modified:** app/services/auth_service.py
- **Committed in:** 2f1b483 (Task 3)

**3. [Rule 1 - Bug] test_request_otp_valid_email flaky (429 after rate limit)**
- **Found during:** Task 3 (full run / re-runs)
- **Issue:** Single real request_otp could hit rate limit if same email was used in previous runs.
- **Fix:** Mock check_rate_limit to return True in test_request_otp_valid_email_returns_202_and_message.
- **Files modified:** tests/test_auth_routes.py
- **Committed in:** 2f1b483 (amend)

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 bugs)
**Impact on plan:** All necessary for Docker and test stability. No scope creep.

## Issues Encountered

- TestClient with multiple requests that hit the DB caused "Future attached to a different loop" (asyncpg). Addressed by mocking verify_otp and using dependency_overrides for get_current_user so multi-request tests do not share DB connections across loops.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Auth API is reachable at POST /api/v1/auth/request-otp, POST /api/v1/auth/verify-otp, GET /api/v1/auth/me.
- USER-03 satisfied: client discards JWT for logout; /me returns 401 for missing or expired token.
- Full test suite has pre-existing failures in test_auth_service.py (app. imports, datetime.utcnow) and test_phase1.py (SQLAlchemy mapper); test_auth_routes.py passes.

---
*Phase: 03-auth-routes-and-dependencies*
*Completed: 2026-03-14*
