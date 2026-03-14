---
status: complete
phase: 02-auth-service-core
source: 02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md
started: "2026-03-15T12:00:00Z"
updated: "2026-03-15T12:00:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. Auth test suite passes
expected: Run in Docker: docker compose run --rm api pytest tests/test_auth_service.py tests/test_email_service.py -v; all tests pass, exit code 0. No import or runtime errors.
result: pass

### 2. Request OTP for email
expected: Calling the auth service to request an OTP for a valid email succeeds. With SINODIK_OTP_PLAINTEXT_FALLBACK=true the OTP can be seen (response or log); otherwise OTP is sent by email. Code is stored hashed in DB.
result: skipped
reason: Проверка через API будет в Phase 3 (HTTP). Сейчас сервис вызывается только из кода/тестов; автоматические тесты уже покрывают сценарий.

### 3. Verify correct OTP returns JWT
expected: After requesting an OTP, verifying with the correct code returns a JWT. The token decodes to the expected email and role (e.g. user or admin from SINODIK_ADMIN_EMails).
result: skipped
reason: Проверка через API будет в Phase 3 (HTTP). Логика покрыта автотестами.

### 4. Invalid or expired OTP rejected
expected: Verifying with a wrong code returns an error and no JWT. Verifying with an expired OTP (older than 10 minutes) also fails.
result: skipped
reason: Проверка через API будет в Phase 3 (HTTP). Логика покрыта автотестами.

### 5. OTP single-use
expected: First verification with a valid OTP succeeds and returns JWT. Second verification with the same OTP fails (code already used).
result: skipped
reason: Проверка через API будет в Phase 3 (HTTP). Логика покрыта автотестами.

### 6. Rate limiting invalidates code after 5 failures
expected: After 5 failed verification attempts (wrong code) for the same email, the OTP is invalidated. A 6th attempt even with the correct code fails.
result: skipped
reason: Проверка через API будет в Phase 3 (HTTP). Логика покрыта автотестами.

### 7. User auto-created on first verification
expected: First successful OTP verification for an email creates a user record with that email and appropriate role. Subsequent verifications for the same email update last_login_at and do not create a duplicate user.
result: skipped
reason: Проверка через API будет в Phase 3 (HTTP). Логика покрыта автотестами.

## Summary

total: 7
passed: 1
issues: 0
pending: 0
skipped: 6

## Gaps

[none yet]
