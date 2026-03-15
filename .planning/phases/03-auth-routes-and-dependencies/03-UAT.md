---
status: testing
phase: 03-auth-routes-and-dependencies
source: 03-01-SUMMARY.md, 03-02-SUMMARY.md
started: "2026-03-15T00:00:00Z"
updated: "2026-03-15T00:00:00Z"
---

## Current Test

number: 2
name: Request OTP
expected: |
  POST /api/v1/auth/request-otp with body { "email": "valid@example.com" } returns 202 and a JSON message; no exception. (In dev, optional dev_otp_code may appear in response.)
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: App starts cleanly; health or auth/me responds (200 or 401), no crash.
result: pass

### 2. Request OTP
expected: POST /api/v1/auth/request-otp with body { "email": "valid@example.com" } returns 202 and a JSON message; no exception. (In dev, optional dev_otp_code may appear in response.)
result: [pending]

### 3. Verify OTP — success
expected: After requesting OTP, POST /api/v1/auth/verify-otp with correct email and 6-digit code returns 200 with { "token": "...", "user": { "id", "email", "role", ... } }. Token can be used as Bearer for GET /auth/me.
result: [pending]

### 4. Verify OTP — invalid code
expected: POST /api/v1/auth/verify-otp with wrong or expired code returns 401 (and no token).
result: [pending]

### 5. GET /auth/me with valid token
expected: GET /api/v1/auth/me with header Authorization: Bearer <valid_jwt> returns 200 with current user (id, email, role). Without token or with invalid/expired token returns 401.
result: [pending]

### 6. Logout behavior
expected: After "logging out" (discarding the token client-side), calling GET /api/v1/auth/me without Bearer returns 401. No server-side session to clear.
result: [pending]

## Summary

total: 6
passed: 1
issues: 0
pending: 5
skipped: 0

## Gaps

[none yet]
