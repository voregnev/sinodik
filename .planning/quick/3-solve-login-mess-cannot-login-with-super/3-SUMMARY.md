# Quick Task 3: Solve login mess (super admin password) — Summary

**Superadmin password login via UI: lifespan hashes password as-is, GET login-method branches to password or OTP, one-form flow in frontend; AUTH-REVIEW.md and CLAUDE.md env docs added.**

## Performance

- **Tasks:** 3 completed
- **Commits:** 3 (one per task)

## Accomplishments

- Backend: superuser password in lifespan hashed with `pwd_ctx.hash(settings.superuser_password)` as-is (no truncation). GET `/api/v1/auth/login-method?email=` returns `{ "method": "password" | "otp" }` without leaking superuser email.
- Frontend: one form — after "Получить код" call login-method; if `password` show password field and POST `/api/v1/auth/password-login`; if `otp` keep existing request-otp → verify-otp flow. State `loginPassword` and step `password` added.
- Docs: AUTH-REVIEW.md with auth entrypoints and JWT/deps; CLAUDE.md updated with `SINODIK_SUPERUSER_EMAIL` and `SINODIK_SUPERUSER_PASSWORD`.

## Task Commits

1. **Task 1: Backend — lifespan hash as-is + GET login-method** — `6aadd14` (feat) — *main.py hash-as-is was already in quick-2; this commit added login-method endpoint and config import in auth.py*
2. **Task 2: Frontend — one form, branch by login-method** — `2a78d6e` (feat)
3. **Task 3: Auth review doc + env docs** — `d8ebcfa` (docs)

## Files Created/Modified

- `app/api/routes/auth.py` — GET `/auth/login-method`, import settings
- `app/main.py` — (unchanged in this run; hash as-is already from quick-2)
- `frontend/SinodikApp.jsx` — loginPassword state, handleRequestOtp → login-method then password/otp, handlePasswordLogin, password step UI
- `.planning/quick/3-solve-login-mess-cannot-login-with-super/AUTH-REVIEW.md` — created
- `CLAUDE.md` — env table: SINODIK_SUPERUSER_EMAIL, SINODIK_SUPERUSER_PASSWORD

## Decisions Made

None — followed plan and CONTEXT decisions (one form by email, hash as-is, GET login-method, 401 for password-login, doc only for auth review).

## Deviations from Plan

None — plan executed as written.

## Issues Encountered

- `test_auth_service.py::test_verify_otp_success` fails with `datetime.datetime` has no attribute `UTC` (pre-existing, not caused by this task). Auth routes tests pass.

---
*Quick task 3 — Completed 2026-03-15*
