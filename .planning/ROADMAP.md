# Roadmap: Sinodic — User Management Milestone

## Overview

This milestone adds OTP-based authentication, JWT sessions, and two-role RBAC to Sinodic. The build order follows hard dependency boundaries: schema first (ORM models and DB tables must exist before any service references them), then auth service logic (independently testable), then auth HTTP layer (routes and dependency injection), then protected routes and admin endpoints (require deps.py to exist), then frontend (requires all backend endpoints to be stable).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)
- Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Schema and Configuration** - Add users and otp_codes tables, ORM models, and auth config settings (completed 2026-03-14)
- [ ] **Phase 2: Auth Service Core** - OTP generation, verification, JWT issuance, and email delivery
- [ ] **Phase 3: Auth Routes and Dependencies** - HTTP endpoints, FastAPI dependency injection, and logout flow
- [ ] **Phase 4: Protected Routes and Admin Endpoints** - Guard existing routes, add user-scoped and admin endpoints
- [ ] **Phase 5: Frontend Auth Integration** - Login screen, My Orders tab, admin panel, and auth state management

## Phase Details

### Phase 1: Schema and Configuration
**Goal**: The database and configuration foundation for auth exists — tables are created, models are importable, and all auth settings are validated at startup
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, USER-02, BOOT-01
**Success Criteria** (what must be TRUE):
  1. `users` and `otp_codes` tables exist in the database after running migrations
  2. `User` and `OtpCode` ORM models can be imported and used in service code
  3. Application startup fails with a clear error if `SINODIK_JWT_SECRET` is unset
  4. Anonymous order submission still works without authentication (existing behavior preserved)
  5. New orders are stored with `user_email` from the submission (linkage field ready for auth)
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Auth config fields in Settings + Phase 1 test scaffold
- [ ] 01-02-PLAN.md — User and OtpCode ORM models + migration 0006

### Phase 2: Auth Service Core
**Goal**: The complete OTP-to-JWT flow works as tested business logic, independent of HTTP — OTPs are generated, hashed, sent via email, verified securely, and accounts are created automatically
**Depends on**: Phase 1
**Requirements**: AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09
**Success Criteria** (what must be TRUE):
  1. Calling the auth service with a valid email produces a 6-digit OTP stored as a SHA-256 hash in otp_codes
  2. Submitting the correct OTP returns a JWT encoding email, role, and expiry; the code is marked used and rejected on reuse
  3. An OTP expires after 10 minutes and is rejected after expiry
  4. After 5 failed OTP attempts the code is invalidated and further attempts are rejected
  5. A user account is auto-created on first successful OTP verification; subsequent verifications update last_login_at
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Basic auth service with OTP generation and JWT issuance
- [ ] 02-02-PLAN.md — Email service with SMTP delivery and fallback mechanism
- [ ] 02-03-PLAN.md — Auth-email integration and OTP lifecycle management

### Phase 3: Auth Routes and Dependencies
**Goal**: The auth API is reachable over HTTP — OTP request and verify endpoints are live, JWT verification and role-checking dependencies exist and are importable by any route
**Depends on**: Phase 2
**Requirements**: USER-03
**Success Criteria** (what must be TRUE):
  1. POST /auth/request-otp accepts an email and returns 202; OTP delivery (or dev fallback) occurs
  2. POST /auth/verify-otp with a valid code returns a JWT; with an invalid code returns 401
  3. GET /auth/me with a valid JWT returns the current user's email and role
  4. A user can log out by discarding the JWT client-side; the /auth/me endpoint rejects expired or missing tokens
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — JWT and role dependencies (app/api/deps.py) + minimal test
- [ ] 03-02-PLAN.md — Auth routes (request-otp, verify-otp, me), router registration, integration tests

### Phase 4: Protected Routes and Admin Endpoints
**Goal**: Authenticated users can access their own data, admins can manage all data, and unauthenticated access to protected operations is rejected
**Depends on**: Phase 3
**Requirements**: USER-01, ADMN-01, ADMN-02, ADMN-03, ADMN-04, ADMN-05, ADMN-06, ADMN-07, ADMN-08
**Success Criteria** (what must be TRUE):
  1. Authenticated user calling GET /api/v1/names/by-user sees only commemorations linked to their email, including historical CSV orders
  2. POST /api/v1/upload/csv returns 403 for non-admin callers and succeeds for admin callers
  3. Admin calling GET /api/v1/admin/users sees all accounts with email, role, active status, and created date
  4. Admin can promote, demote, and disable user accounts via PATCH /api/v1/admin/users/{id}; disabled user's JWT is rejected on next request
  5. Admin can edit and delete any commemoration record via PATCH/DELETE /api/v1/commemorations/{id}
**Plans**: 4 plans

Plans:
- [ ] 04-01-PLAN.md — Test scaffolds and shared auth fixtures (Wave 0)
- [ ] 04-02-PLAN.md — Optional auth dependency, names/by-user and orders guard and scope
- [ ] 04-03-PLAN.md — Upload and commemorations guard and scope
- [ ] 04-04-PLAN.md — Admin users API (GET/PATCH with last-admin protection)

### Phase 5: Frontend Auth Integration
**Goal**: The React PWA presents a complete auth-aware UI — unauthenticated users see the login screen, authenticated users see their orders, and admins see the admin panel
**Depends on**: Phase 4
**Requirements**: FRNT-01, FRNT-02, FRNT-03, FRNT-04, FRNT-05, FRNT-06, FRNT-07
**Success Criteria** (what must be TRUE):
  1. An unauthenticated user opening the app sees the login screen with email entry and OTP code entry steps
  2. After login, the JWT is stored in localStorage and all subsequent API calls include the Authorization: Bearer header
  3. An authenticated user sees a "My Orders" tab showing their linked commemorations
  4. An admin sees an "Admin" tab with all orders and user management UI; the CSV upload tab is visible only to admins
  5. An anonymous user can still submit a записка via the order form without logging in
**Plans**: 4 plans

Plans:
- [ ] 05-01-PLAN.md — Backend: add order_id to get_by_user and by-user response for Мои заказы grouping
- [ ] 05-02-PLAN.md — Auth state, localStorage, fetch wrapper with Bearer and 401 handling
- [ ] 05-03-PLAN.md — Login modal (email → OTP) and conditional tabs/header by role
- [ ] 05-04-PLAN.md — Мои заказы screen and Податели section in БД tab

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Schema and Configuration | 2/2 | Complete   | 2026-03-14 |
| 2. Auth Service Core | 0/3 | Not started | - |
| 3. Auth Routes and Dependencies | 0/2 | Not started | - |
| 4. Protected Routes and Admin Endpoints | 3/4 | In Progress|  |
| 5. Frontend Auth Integration | 1/4 | In Progress|  |