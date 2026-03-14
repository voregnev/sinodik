# Sinodic — User Management Milestone

## What This Is

Sinodic is a church commemoration management system that processes CSV uploads and form submissions to track prayer requests (записки) for living and deceased individuals. This milestone adds a user authentication and role system so submitters can log in to view their own orders, while admins get full oversight and management capabilities.

## Core Value

A submitter who logs in with their email sees exactly their commemorations — past and present — without accessing anyone else's data.

## Requirements

### Validated

- ✓ CSV upload pipeline — parses Russian church names from payment CSVs
- ✓ Order creation via web form (POST /api/v1/orders)
- ✓ Commemoration tracking with period types (разовое, сорокоуст, полгода, год)
- ✓ Three-level name search (exact, trigram, vector similarity)
- ✓ Today's active names view (GET /api/v1/names/today)
- ✓ Stats endpoint (GET /api/v1/names/stats)
- ✓ React PWA frontend (SinodikApp.jsx, no build toolchain)

### Active

- [ ] User can request a one-time code sent to their email address
- [ ] User can verify the OTP and receive a session token (JWT)
- [ ] Account created automatically on first successful OTP verification
- [ ] User can view their own orders (matched by email — CSV history + future form submissions)
- [ ] Admin can view all orders across all users
- [ ] Admin can view all user accounts
- [ ] Admin can promote/demote users to admin role, disable accounts
- [ ] Admin can edit and delete commemorations
- [ ] CSV upload restricted to admin role
- [ ] Frontend: login screen, "My Orders" tab for users, admin panel tab for admins
- [ ] OTP delivered via email (SMTP); code exposed in API response as fallback when SMTP not configured

### Out of Scope

- Password-based authentication — OTP-only by design (simpler, no password storage)
- OAuth/social login — not needed for this user base
- Self-serve role requests — admin assigns roles
- Mobile app — web PWA only

## Context

- Orders already store `user_email` on the `Order` model — the ownership link exists in the DB
- Frontend is a single `SinodikApp.jsx` served with in-browser Babel transform — editable directly, no build step
- SMTP is optional; if `SINODIK_SMTP_*` vars are unset, OTP is returned in the API response
- The existing `/api/v1/upload/csv` endpoint has no auth today — it needs an admin guard

## Constraints

- **Tech stack**: Must stay Python/FastAPI/SQLAlchemy async — no new frameworks
- **Frontend**: Edit `SinodikApp.jsx` only (no Node.js toolchain available)
- **Migrations**: Alembic for all schema changes (new `users` table, OTP codes table)
- **Sessions**: JWT (stateless) — no server-side session store

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| OTP-only auth (no passwords) | Simpler, no password hashing/reset flow; fits infrequent login pattern | — Pending |
| Auto-create account on first OTP | Removes admin friction for onboarding submitters | — Pending |
| JWT for sessions | Stateless, no Redis dependency, fits existing stack | — Pending |
| OTP in API response as SMTP fallback | Enables dev/demo without SMTP config | — Pending |
| Admin role seeded via env var or DB flag | First admin bootstrapped without chicken-and-egg problem | — Pending |

---
*Last updated: 2026-03-14 after initialization*
