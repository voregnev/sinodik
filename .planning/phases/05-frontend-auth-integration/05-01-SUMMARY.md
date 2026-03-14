---
phase: 05-frontend-auth-integration
plan: "01"
subsystem: api
tags: [query_service, by-user, order_id, frontend]

# Dependency graph
requires:
  - phase: 04-protected-routes-and-admin-endpoints
    provides: GET /api/v1/names/by-user (auth), get_by_user in query_service
provides:
  - get_by_user returns order_id per commemoration for frontend "Мои заказы" grouping
  - GET /api/v1/names/by-user response commemorations include order_id
affects: [05-frontend-auth-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [by-user response shape: user_email, commemorations with order_id, count]

key-files:
  created: []
  modified: [app/services/query_service.py, tests/test_names_by_user_auth.py]

key-decisions:
  - "order_id exposed in by-user response for frontend order-grouped cards (no schema change; Commemoration.order_id already present)"

patterns-established:
  - "by-user contract: commemorations[].order_id required for grouping by order"

requirements-completed: [FRNT-02]

# Metrics
duration: 5min
completed: "2026-03-15"
---

# Phase 05 Plan 01: Add order_id to get_by_user — Summary

**get_by_user now returns order_id per commemoration so the frontend can group "Мои заказы" by order (one card per order with type, period, expiry, names/count).**

## Performance

- **Duration:** ~5 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `query_service.get_by_user` selects `Order.id.label("order_id")` and includes it in each returned dict
- GET /api/v1/names/by-user response shape: `{ user_email, commemorations: [{ ..., order_id }, ...], count }`
- Test coverage: `test_by_user_response_includes_order_id_in_commemorations` asserts order_id in response

## Task Commits

1. **Task 1: Add order_id to get_by_user** — `188049f` (feat)
2. **Task 2: Assert order_id in by-user response in tests** — `81fe7e6` (test)

## Files Created/Modified

- `app/services/query_service.py` — Added Order.id as order_id to select and to returned dict in get_by_user
- `tests/test_names_by_user_auth.py` — Added test_by_user_response_includes_order_id_in_commemorations

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Plan verification referenced `tests/test_orders.py` which does not exist in the repo (only `test_orders_auth.py`); ran `tests/test_names_by_user_auth.py` only — all 5 tests passed.

## User Setup Required

None.

## Next Phase Readiness

- by-user API contract includes order_id; frontend can implement "Мои заказы" grouped by order.
- Ready for Plan 05-02 (or next phase plan).

## Self-Check: PASSED

- FOUND: .planning/phases/05-frontend-auth-integration/05-01-SUMMARY.md
- FOUND: 188049f, 81fe7e6

---
*Phase: 05-frontend-auth-integration*
*Completed: 2026-03-15*
