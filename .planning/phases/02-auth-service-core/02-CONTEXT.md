# Phase 2: Auth Service Core - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the complete OTP-to-JWT flow as tested business logic, independent of HTTP. This includes OTP generation, hashing, email delivery, verification, JWT signing, and account creation. All AUTH-02 through AUTH-09 requirements will be implemented in service layer code.

</domain>

<decisions>
## Implementation Decisions

### OTP Generation Mechanism
- Generate 6-digit numeric codes using random algorithm (not with checksum)
- Codes are issued when user requests OTP via email address
- Codes stored as SHA-256 hash in the otp_codes table (per Phase 1 schema)

### Email Delivery Implementation
- Use aiosmtplib for async SMTP delivery (matches existing async patterns in codebase)
- When SMTP fails and SINODIK_OTP_PLAINTEXT_FALLBACK is enabled, return OTP in API response
- When SMTP fails but plaintext fallback is disabled, fail the request gracefully

### JWT Signing Approach
- Use PyJWT library for JWT signing and verification
- Basic claims structure: sub (email), role, exp (expiration)
- Use HS256 algorithm with the jwt_secret from config

### Claude's Discretion
- Exact retry logic and timeout configurations for SMTP delivery
- Specific error handling and logging patterns for email delivery failures
- How to handle race conditions during account creation
- Exact structure of service layer functions and their interfaces

</decisions>

<specifics>
## Specific Ideas

- OTP codes should be generated with cryptographically secure random number generation
- Email delivery should handle connection timeouts gracefully with appropriate error messages
- JWT expiration should respect the jwt_ttl_days setting from config (7 days by default)
- Account creation should check if email exists in settings.admin_emails for auto-admin assignment

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/config.py` - Settings already includes jwt_secret, jwt_ttl_days, admin_emails, otp_plaintext_fallback
- `app/models/models.py` - User and OtpCode models are ready for use (from Phase 1)
- `app/database.py` - AsyncSession factory available for database operations
- Existing services in `app/services/` follow async patterns and error handling

### Established Patterns
- All database operations use async/await with AsyncSession dependency injection
- Services return `list[dict]` for query results, not ORM objects
- Error handling uses savepoints (`begin_nested()`) for operations that might fail
- Logging uses standard `logging` module with module-level loggers

### Integration Points
- New auth_service.py module will contain OTP and JWT business logic
- Service functions will be testable independently of HTTP layer
- Database transactions will be handled through FastAPI dependency injection pattern

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-auth-service-core*
*Context gathered: 2026-03-14*