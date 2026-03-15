# Quick Task 3: solve login mess (super admin password) — Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Task Boundary

Solve totally mess: we can't login with super admin password. Full codebase auth review and rewrite login flow. Discuss simplest flow.

</domain>

<decisions>
## Implementation Decisions

### How superadmin logs in via UI
- **One form, flow by email:** If email matches `superuser_email` → show password field and call `POST /api/v1/auth/password-login`. Otherwise → existing OTP flow (request-otp → verify-otp). No separate "admin login" screen.

### Password bootstrap in lifespan (main.py)
- **Hash password as-is:** Do not truncate/re-encode in Python; pass `settings.superuser_password` to bcrypt. Bcrypt limits 72 bytes internally. Removes risk of corrupting non-ASCII and simplifies code.

### Login error API response
- Keep current: 401 with "Invalid credentials" for password-login. No new error contract.

### Scope of auth review
- Fix superadmin login (frontend calling password-login + lifespan hash fix) and add a short written audit of auth flow (OTP, JWT, password-login, nginx Basic, deps) — e.g. in codebase doc or CONTEXT/SUMMARY — without changing other auth behaviour.

### Claude's Discretion
- Frontend: after "Получить код", if backend or heuristics indicate superuser email, switch step to "password" and show password input; submit to password-login. Backend already has the endpoint.
- Ensure env vars SINODIK_SUPERUSER_EMAIL and SINODIK_SUPERUSER_PASSWORD are documented where other auth env is (e.g. CLAUDE.md or README).

</decisions>

<specifics>
## Specific Ideas

- Backend: `app/main.py` lifespan — simplify to `user.password_hash = pwd_ctx.hash(settings.superuser_password)` when set (no manual truncation).
- Backend: `app/services/auth_service.py` — no change to login_superuser logic except if needed for consistency.
- Frontend: `SinodikApp.jsx` — login flow: when user submits email, either call request-otp (normal user) or show password field and on submit call password-login (superuser). Detect superuser by: call a small endpoint or compare email to a config-like value; simplest is backend endpoint GET /api/v1/auth/login-method?email=... returning { "method": "password" | "otp" } to avoid leaking superuser email to frontend config. Alternatively: try password-login first for any email, 401 → fall back to OTP (simpler but two requests for non-superusers). Decision: use GET login-method?email=... to keep single request per path and not leak superuser.
- Auth review: list all auth entrypoints (request-otp, verify-otp, password-login, GET /auth/login with Basic), JWT creation/validation, and deps (get_current_user, require_admin). One short section in SUMMARY or new .planning/quick/3-.../AUTH-REVIEW.md.

</specifics>
