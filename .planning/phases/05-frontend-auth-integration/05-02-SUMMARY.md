---
phase: 05-frontend-auth-integration
plan: "02"
subsystem: auth
tags: [react, jwt, localStorage, fetch, bearer]

# Dependency graph
requires:
  - phase: 04-protected-routes-and-admin-endpoints
    provides: GET /auth/me, protected routes
provides:
  - Auth state (token, user) and authRef in SinodikApp
  - api/apiOrThrow add Authorization Bearer when token present; on 401 clear token and user
  - Mount effect GET /auth/me when token in localStorage; anonymous requests send no Bearer
affects: 05-03 (login UI will set token into localStorage)

# Tech tracking
tech-stack:
  added: []
  patterns: [authRef for stable closure in fetch helpers, sinodik_token localStorage key]

key-files:
  created: []
  modified: [frontend/SinodikApp.jsx]

key-decisions:
  - "Auth ref (authRef.current) updated at render so api/apiOrThrow always see current token/setters"
  - "401 in api() returns null; in apiOrThrow() clears auth then throws with body detail when available"

patterns-established:
  - "Single fetch layer: api() and apiOrThrow() read authRef for Bearer and 401 clear; no per-route changes"

requirements-completed: [FRNT-05, FRNT-06, FRNT-07]

# Metrics
duration: 5
completed: "2026-03-15"
---

# Phase 05 Plan 02: Auth State Summary

**Auth state (token, user), localStorage key sinodik_token, api/apiOrThrow add Bearer and 401 clear; mount effect GET /auth/me when token exists.**

## Performance

- **Duration:** ~5 min
- **Tasks:** 2
- **Files modified:** 1 (frontend/SinodikApp.jsx)

## Accomplishments

- Token and user state in SinodikApp; AUTH_KEY = "sinodik_token"
- On mount: read localStorage; if token present call GET /auth/me with Bearer; on 401 clear token/user and localStorage; on success set token and user from response
- authRef holds { token, setToken, setUser } updated at render; api() and apiOrThrow() add Authorization: Bearer when authRef.current?.token set
- On 401 response: localStorage.removeItem(AUTH_KEY), setToken(null), setUser(null); api() returns null, apiOrThrow() throws
- Guest (no token): no Bearer header — anonymous POST /orders unchanged (FRNT-06)

## Task Commits

1. **Task 1: Auth state and hydrate on mount** — `3156759` (feat)
2. **Task 2: Fetch wrapper with Bearer and 401 handling** — `250702d` (feat)

## Files Created/Modified

- `frontend/SinodikApp.jsx` — AUTH_KEY, authRef; token/user state; mount useEffect GET /auth/me; api/apiOrThrow with Bearer and 401 clear

## Decisions Made

- authRef updated at start of SinodikApp render (not in useEffect) so ref is current for every call.
- 401 in apiOrThrow: clear auth first, then throw with optional body.detail.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

- Ready for 05-03: login modal can set token via setToken and persist to localStorage (key sinodik_token); existing fetch layer will send Bearer and handle 401.

## Self-Check: PASSED

- 05-02-SUMMARY.md present; commits 3156759, 250702d in git log.

---
*Phase: 05-frontend-auth-integration*
*Completed: 2026-03-15*
