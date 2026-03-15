---
phase: quick-2-add-superuser-with-login-admin-and-passw
plan: 2
subsystem: auth
tags: [superuser, bcrypt, passlib, jwt, admin]

# Dependency graph
requires: []
provides:
  - Superuser account at startup (email from SINODIK_SUPERUSER_EMAIL)
  - Superuser protected from PATCH demotion/disable in admin
  - POST /api/v1/auth/password-login for superuser email+password → JWT
affects: [admin, auth]

# Tech tracking
tech-stack:
  added: [passlib[bcrypt]]
  patterns: [lifespan bootstrap get-or-create, superuser-only password login]

key-files:
  created: [alembic/versions/0007_add_user_password_hash.py]
  modified: [app/config.py, app/main.py, app/models/models.py, app/api/routes/admin.py, app/services/auth_service.py, app/api/routes/auth.py, requirements.txt]

key-decisions:
  - "Superuser bootstrap in lifespan after extensions; password_hash set only when SINODIK_SUPERUSER_PASSWORD is set"
  - "Password login allowed only for email matching superuser_email and only when user has password_hash"

patterns-established:
  - "Superuser guard: reject admin PATCH when target user email equals settings.superuser_email (400)"

requirements-completed: [quick-superuser]

# Metrics
duration: ~10min
completed: "2026-03-15"
---

# Quick 2: Add superuser with login (admin + password) — Summary

**Superuser from .env (email + optional password): bootstrap at startup, protected from admin PATCH, password login returns JWT.**

## Performance

- **Tasks:** 3 completed
- **Commits:** 3 (one per task)

## Accomplishments

- Config: `superuser_email` (default admin@example.com), `superuser_password` (optional)
- User model: optional `password_hash` column; migration 0007
- Lifespan: get-or-create user by `superuser_email`, role=admin, is_active=True; set `password_hash` when `superuser_password` is set (bcrypt via passlib)
- Admin: PATCH /api/v1/admin/users/{id} returns 400 when target email is superuser_email
- Auth: `login_superuser()` in auth_service; POST /auth/password-login with email+password body, returns token+user or 401
- requirements.txt: passlib[bcrypt] added

## Task Commits

1. **Task 1: Config + bootstrap superuser in lifespan** — `3aade8c` (feat)
2. **Task 2: Admin PATCH guard for superuser** — `07d1bcc` (feat)
3. **Task 3: Password login for superuser only** — `747733d` (feat)

## Files Created/Modified

- `app/config.py` — superuser_email, superuser_password settings
- `app/main.py` — lifespan bootstrap: get-or-create superuser, set password_hash if password set
- `app/models/models.py` — User.password_hash column
- `alembic/versions/0007_add_user_password_hash.py` — migration for password_hash
- `app/api/routes/admin.py` — guard: 400 when PATCH target is superuser
- `app/services/auth_service.py` — login_superuser(email, password, db)
- `app/api/routes/auth.py` — LoginPasswordBody, POST /auth/password-login
- `requirements.txt` — passlib[bcrypt]

## Decisions Made

None — plan executed as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Admin tests failed in Docker due to pre-existing SQLAlchemy mapper issue (`models.models.Commemoration` path); not caused by these changes. Scope boundary: no fix applied.

## User Setup Required

- Set `SINODIK_SUPERUSER_EMAIL` (optional, default admin@example.com).
- Set `SINODIK_SUPERUSER_PASSWORD` to enable password login for superuser; if unset, superuser exists but password-login returns 401.

## Self-Check

- [x] Created files exist: 0007_add_user_password_hash.py, 2-SUMMARY.md
- [x] Commits exist: 3aade8c, 07d1bcc, 747733d

---
*Quick task: 2-add-superuser-with-login-admin-and-passw*
*Completed: 2026-03-15*
