# Requirements: Sinodic — User Management Milestone

**Defined:** 2026-03-14
**Core Value:** A submitter who logs in with their email sees exactly their commemorations — past and present — without accessing anyone else's data.

## v1 Requirements

### Authentication

- [x] **AUTH-01**: Anonymous user can submit an order with names only (no email required)
- [ ] **AUTH-02**: User can request a one-time code by providing their email address
- [ ] **AUTH-03**: User receives the OTP via email (SMTP); code is returned in the API response when SMTP is not configured
- [ ] **AUTH-04**: User can verify the OTP code and receive a JWT session token
- [ ] **AUTH-05**: Account is created automatically on first successful OTP verification (no separate registration step)
- [ ] **AUTH-06**: OTP codes expire after 10 minutes
- [x] **AUTH-07**: OTP codes are single-use (invalidated immediately on successful verification)
- [x] **AUTH-08**: OTP requests are rate-limited per email to prevent brute-force
- [x] **AUTH-09**: JWT encodes user email, role, and expiry (stateless — no server-side session store)

### User Features

- [x] **USER-01**: Authenticated user can view their own orders (matched by email — includes historical CSV orders)
- [x] **USER-02**: Authenticated user's new orders are automatically linked to their account email
- [x] **USER-03**: User can log out (client-side: discard JWT)

### Admin Features

- [x] **ADMN-01**: Admin can view all orders across all users
- [x] **ADMN-02**: Admin can view all user accounts (email, role, active status, created date)
- [x] **ADMN-03**: Admin can promote a user to admin role
- [x] **ADMN-04**: Admin can demote an admin to user role
- [x] **ADMN-05**: Admin can disable a user account (is_active = false; disabled user's JWT is rejected)
- [x] **ADMN-06**: Admin can edit any commemoration record
- [x] **ADMN-07**: Admin can delete any commemoration record
- [x] **ADMN-08**: CSV upload is restricted to admin role only

### Bootstrap

- [x] **BOOT-01**: First admin account is seeded via `SINODIK_ADMIN_EMAILS` env var (checked at account creation time)

### Frontend

- [ ] **FRNT-01**: Login screen shown when user is not authenticated (email entry → OTP code entry)
- [x] **FRNT-02**: Authenticated user sees a "My Orders" tab showing their linked commemorations
- [ ] **FRNT-03**: Admin sees an "Admin" tab with all orders and user management UI
- [ ] **FRNT-04**: CSV upload tab is hidden for non-admin users
- [ ] **FRNT-05**: JWT stored client-side (localStorage); sent as `Authorization: Bearer` header on all authenticated requests
- [ ] **FRNT-06**: Anonymous users can still submit orders via the "Записка" tab (no login required)
- [ ] **FRNT-07**: App decodes JWT role claim client-side to conditionally render admin UI

## v2 Requirements

### Notifications

- **NOTF-01**: User receives email notification when their commemoration is about to expire
- **NOTF-02**: User can configure notification preferences

### Audit

- **AUDT-01**: Admin can view an audit log of changes to commemorations

### Account Management

- **ACCT-01**: User can delete their own account (GDPR)
- **ACCT-02**: User can update their notification email

## Out of Scope

| Feature | Reason |
|---------|--------|
| Password-based login | OTP-only by design — simpler, no password storage or reset flow |
| OAuth / social login | Not needed for this user base (church administrators) |
| Refresh token rotation | Single JWT with 30-day expiry; re-auth via OTP when expired |
| TOTP authenticator app | Out of scope — email OTP covers the use case |
| Granular permissions beyond two roles | Two roles (user/admin) cover all defined requirements |
| Account deletion | Not requested this milestone |
| Real-time notifications | Not requested this milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| AUTH-06 | Phase 2 | Pending |
| AUTH-07 | Phase 2 | Complete |
| AUTH-08 | Phase 2 | Complete |
| AUTH-09 | Phase 2 | Complete |
| USER-01 | Phase 4 | Complete |
| USER-02 | Phase 1 | Complete |
| USER-03 | Phase 3 | Complete |
| ADMN-01 | Phase 4 | Complete |
| ADMN-02 | Phase 4 | Complete |
| ADMN-03 | Phase 4 | Complete |
| ADMN-04 | Phase 4 | Complete |
| ADMN-05 | Phase 4 | Complete |
| ADMN-06 | Phase 4 | Complete |
| ADMN-07 | Phase 4 | Complete |
| ADMN-08 | Phase 4 | Complete |
| BOOT-01 | Phase 1 | Complete |
| FRNT-01 | Phase 5 | Pending |
| FRNT-02 | Phase 5 | Complete |
| FRNT-03 | Phase 5 | Pending |
| FRNT-04 | Phase 5 | Pending |
| FRNT-05 | Phase 5 | Pending |
| FRNT-06 | Phase 5 | Pending |
| FRNT-07 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after roadmap creation (5-phase structure, corrected count from 24 to 28)*
