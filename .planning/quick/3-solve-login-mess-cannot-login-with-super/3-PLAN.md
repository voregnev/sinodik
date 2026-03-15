---
phase: quick-3-solve-login-mess
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/main.py
  - app/api/routes/auth.py
  - app/config.py
  - frontend/SinodikApp.jsx
  - .planning/quick/3-solve-login-mess-cannot-login-with-super/AUTH-REVIEW.md
  - CLAUDE.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "Superadmin can log in with password from .env via UI"
    - "Normal users still use OTP flow (request-otp → verify-otp)"
    - "One form: email first, then either password field or OTP field by backend hint"
  artifacts:
    - path: app/main.py
      provides: "Superuser bootstrap with correct password hash (no truncation)"
    - path: app/api/routes/auth.py
      provides: "GET login-method, POST password-login"
    - path: frontend/SinodikApp.jsx
      provides: "Login flow branching by login-method"
    - path: .planning/quick/3-solve-login-mess-cannot-login-with-super/AUTH-REVIEW.md
      provides: "Short auth flow audit"
  key_links:
    - from: frontend/SinodikApp.jsx
      to: "/api/v1/auth/login-method"
      via: "GET before request-otp or password step"
    - from: frontend/SinodikApp.jsx
      to: "/api/v1/auth/password-login"
      via: "POST when step is password"
    - from: app/main.py
      to: "bcrypt hash"
      via: "pwd_ctx.hash(settings.superuser_password) as-is"
---

<objective>
Fix superadmin login: hashing in lifespan corrupts password; frontend never calls password-login or shows password step. Implement one-form flow (email → login-method → password or OTP) and document auth entrypoints.
Purpose: Allow superadmin to log in with SINODIK_SUPERUSER_PASSWORD; keep OTP for others; single request per path, no superuser email leak to frontend.
Output: Working superuser password login from UI; GET /auth/login-method; lifespan hashes password as-is; AUTH-REVIEW.md; CLAUDE.md updated with superuser env vars.
</objective>

<context>
@CLAUDE.md
@.planning/quick/3-solve-login-mess-cannot-login-with-super/3-CONTEXT.md

Locked decisions (from CONTEXT):
- One form, flow by email: if email matches superuser → show password field and call POST /api/v1/auth/password-login; else OTP flow.
- Hash password as-is in lifespan (no truncate/re-encode).
- GET /api/v1/auth/login-method?email=... returning { "method": "password" | "otp" } to avoid leaking superuser email.
- Keep 401 "Invalid credentials" for password-login.
- Auth review: short audit in SUMMARY or AUTH-REVIEW.md; document SINODIK_SUPERUSER_EMAIL and SINODIK_SUPERUSER_PASSWORD where other auth is (CLAUDE.md).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — lifespan hash as-is + GET login-method</name>
  <files>app/main.py, app/api/routes/auth.py</files>
  <action>
Backend (two changes):

1) app/main.py — lifespan superuser bootstrap
- When settings.superuser_password is set, set user.password_hash with:
  user.password_hash = pwd_ctx.hash(settings.superuser_password)
- Remove all truncation/encode/decode/while logic. Pass the string as-is; bcrypt handles 72-byte limit internally.

2) app/api/routes/auth.py
- Add GET /auth/login-method with query param email (e.g. email: str).
- Return JSON: { "method": "password" } if email.lower() == settings.superuser_email.lower() and settings.superuser_password is truthy; else { "method": "otp" }.
- Do not leak superuser email to response; only expose method. Use config from app.config.settings.
  </action>
  <verify>
    <automated>docker compose run --rm api pytest tests/test_auth_service.py tests/test_auth_routes.py -v -x 2>/dev/null || pytest tests/test_auth_service.py -v -x</automated>
  </verify>
  <done>Superuser password hashed without truncation; GET /auth/login-method returns method by email; existing auth tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Frontend — one form, branch by login-method</name>
  <files>frontend/SinodikApp.jsx</files>
  <action>
Login flow in SinodikApp.jsx:

1) State
- Add loginPassword and setLoginPassword (string). Reset in openLogin and closeLogin along with other login state.
- loginStep remains "email" | "otp"; add "password" as a third step.

2) After user clicks "Получить код" (email step)
- Trim email; if empty return.
- Call GET /api/v1/auth/login-method?email={encodeURIComponent(email)} (no body).
- If response.method === "password": setLoginStep("password"), setLoginError(""), and do NOT call request-otp.
- If response.method === "otp": call existing request-otp (POST /auth/request-otp) and on 202 setLoginStep("otp").

3) Password step UI
- When loginStep === "password": show label "Пароль", input type="password", value loginPassword, onChange setLoginPassword, placeholder "Пароль", Enter key submits password login.
- Button: "Войти" (or "Отправка..." when submitting). On click: POST /api/v1/auth/password-login with body { email: loginEmail.trim(), password: loginPassword }. On 200: set token and user from response, closeLogin. On 401: setLoginError("Неверные данные"). Handle network/other errors with setLoginError.

4) Modal step branching
- Keep loginStep === "email" as current (email input + "Получить код").
- Keep loginStep === "otp" as current (code input + "Войти").
- Add branch for loginStep === "password" as above. Use same error display and modal shell.
  </action>
  <verify>
    <automated>Build or lint if present; otherwise manual: open login modal, enter superuser email, click "Получить код" → password field appears; submit password → login succeeds.</automated>
  </verify>
  <done>One form: email → login-method → either password field (and password-login) or OTP flow; superuser can log in with password from UI.</done>
</task>

<task type="auto">
  <name>Task 3: Auth review doc + env docs</name>
  <files>.planning/quick/3-solve-login-mess-cannot-login-with-super/AUTH-REVIEW.md, CLAUDE.md</files>
  <action>
1) Create AUTH-REVIEW.md in .planning/quick/3-solve-login-mess-cannot-login-with-super/
- One short section listing:
  - Auth entrypoints: POST /api/v1/auth/request-otp, POST /api/v1/auth/verify-otp, POST /api/v1/auth/password-login, GET /api/v1/auth/login (X-Remote-User Basic Auth), GET /api/v1/auth/login-method?email=, GET /api/v1/auth/me.
  - JWT: created in auth_service (create_jwt_token), validated in api/deps (get_current_user); used for protected routes and admin (require_admin).
  - No changes to other auth behaviour; this task is documentation only.

2) CLAUDE.md — Environment Configuration table
- Add two rows: SINODIK_SUPERUSER_EMAIL (superuser email; used for password login and nginx Basic), SINODIK_SUPERUSER_PASSWORD (optional; if set, superuser can log in with password and hash is stored at startup).
  </action>
  <verify>
    <automated>File AUTH-REVIEW.md exists and contains the listed entrypoints and JWT/deps mention; CLAUDE.md contains SINODIK_SUPERUSER_EMAIL and SINODIK_SUPERUSER_PASSWORD.</automated>
  </verify>
  <done>AUTH-REVIEW.md exists with auth entrypoints and deps; CLAUDE.md documents superuser env vars.</done>
</task>

</tasks>

<verification>
- Run auth tests. Open app, enter superuser email, get password field, submit password → logged in. Normal email → OTP flow unchanged.
</verification>

<success_criteria>
- Superadmin can log in via UI with SINODIK_SUPERUSER_PASSWORD. Lifespan hashes password as-is. Frontend uses login-method then password-login or OTP. Auth review and env docs in place.
</success_criteria>

<output>
After completion, optional: add .planning/quick/3-solve-login-mess-cannot-login-with-super/3-SUMMARY.md with what was changed (for quick tasks often omitted).
</output>
