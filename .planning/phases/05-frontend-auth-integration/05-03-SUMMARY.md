---
phase: 05-frontend-auth-integration
plan: "03"
subsystem: ui
tags: [react, jwt, auth, pwa, localStorage]

# Dependency graph
requires:
  - phase: 05-frontend-auth-integration
    provides: Auth state, Bearer and 401 handling (05-02)
provides:
  - Login modal (email → OTP in one popup, errors at top, no code-sent hint, no Back on OTP)
  - Conditional shell: guest = form + Войти; user = Записка + Мои заказы + Выйти; admin = full TABS
  - Выйти clears token and shows guest view
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: Single modal two-step login; role-based tab visibility; logout without confirm

key-files:
  created: []
  modified: [frontend/SinodikApp.jsx]

key-decisions:
  - "Login: one modal, two steps; errors at top; no 'Код отправлен' hint; no Back on OTP (per CONTEXT)"
  - "Non-admin sees only Записка and Мои заказы tabs; CSV/Стат./БД/Сегодня/Поиск admin-only"
  - "Выйти clears token immediately, no confirm dialog"

patterns-established:
  - "visibleTabs derived from user: null (guest), TABS_USER (add + myOrders), TABS_FULL (admin)"
  - "MyOrdersPage uses api('/orders') for user-scoped list; empty state per CONTEXT"

requirements-completed: [FRNT-01, FRNT-04, FRNT-07]

# Metrics
duration: ~8min
completed: "2026-03-15"
---

# Phase 05 Plan 03: Login modal and conditional shell — Summary

**Login modal (email → OTP in one popup, errors at top, no code-sent hint, no Back) and conditional header/tabs: guest sees form + Войти; user sees Записка + Мои заказы + Выйти; admin sees full TABS; Выйти clears token.**

## Performance

- **Duration:** ~8 min
- **Tasks:** 2 completed
- **Files modified:** 1 (frontend/SinodikApp.jsx)

## Accomplishments

- Login modal with email step (POST /auth/request-otp) and OTP step (POST /auth/verify-otp); errors at top; 429/4xx/401 handling; store token and user on success and close modal
- Conditional header: guest → Войти; authenticated → Мои заказы (non-admin) + Выйти
- Conditional tabs: guest → no tab bar (form only); non-admin → Записка + Мои заказы; admin → full TABS (Сегодня, Поиск, Записка, CSV, Стат., БД)
- MyOrdersPage: GET /orders, list or empty
- Logout: localStorage.removeItem(AUTH_KEY), setToken(null), setUser(null) — no confirm

## Task Commits

Each task was committed atomically:

1. **Task 1: Login modal (email → OTP)** - `0122bea` (feat)
2. **Task 2: Conditional header and tabs by auth and role** - `ca2e6b0` (feat)

## Files Created/Modified

- `frontend/SinodikApp.jsx` — Login modal state and UI; openLogin/closeLogin/handleRequestOtp/handleVerifyOtp; logout; visibleTabs (TABS_FULL / TABS_USER / null); conditional header (Войти vs Мои заказы + Выйти); conditional content and tab bar; MyOrdersPage component

## Decisions Made

- One popup two steps, errors at top, no "Код отправлен на …", no Back on OTP — per 05-CONTEXT.md
- Non-admin sees only Записка and Мои заказы; CSV/Стат./БД/Сегодня/Поиск only for admin
- Выйти clears token immediately, no confirmation dialog

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Login flow and role-based UI complete; manual UAT: open app unauthenticated → Войти → email → OTP → see Выйти and Мои заказы; logout → guest view; login as admin → all tabs; as user → only Записка and Мои заказы.
- Plan 05-04 can implement Податели (admin БД section) and any remaining frontend requirements.

## Self-Check: PASSED

- 05-03-SUMMARY.md present
- Commits 0122bea, ca2e6b0 present

---
*Phase: 05-frontend-auth-integration*
*Completed: 2026-03-15*
