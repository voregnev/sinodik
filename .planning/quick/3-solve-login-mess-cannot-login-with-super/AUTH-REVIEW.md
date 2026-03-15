# Auth flow — short audit

## Auth entrypoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/auth/request-otp` | Request OTP for email (normal users) |
| POST | `/api/v1/auth/verify-otp` | Verify OTP code; returns JWT + user |
| POST | `/api/v1/auth/password-login` | Superuser login by email + password from env |
| GET | `/api/v1/auth/login` | Issue JWT when `X-Remote-User` is set (nginx Basic Auth); only superuser_email accepted |
| GET | `/api/v1/auth/login-method?email=` | Returns `{ "method": "password" \| "otp" }` for given email (no superuser leak) |
| GET | `/api/v1/auth/me` | Current user from JWT; 401 if missing/expired |

## JWT and deps

- **JWT creation:** `auth_service.create_jwt_token` (used by verify_otp, login_superuser, login_via_nginx_basic).
- **JWT validation:** `api.deps.get_current_user` — used for protected routes; `api.deps.require_admin` for admin-only endpoints.

No changes to other auth behaviour; this document is for reference only.
