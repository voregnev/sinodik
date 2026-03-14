---
phase: 04-protected-routes-and-admin-endpoints
verified: "2026-03-14T00:00:00Z"
status: passed
score: 5/5 Success Criteria; all plan must-haves and requirements verified
---

# Phase 4: Protected Routes and Admin Endpoints — Verification Report

**Phase Goal:** Authenticated users can access their own data, admins can manage all data, and unauthenticated access to protected operations is rejected.

**Verified:** 2026-03-14  
**Status:** passed  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|--------|--------|----------|
| 1 | Authenticated user calling GET /api/v1/names/by-user sees only commemorations linked to their email | ✓ VERIFIED | `app/api/routes/names.py`: `get_current_user`, `effective_email = current_user.email` (or `email` for admin); `get_by_user(db, user_email=effective_email, ...)`. `query_service.get_by_user` filters by `Order.user_email`. |
| 2 | POST /api/v1/upload/csv returns 403 for non-admin, succeeds for admin | ✓ VERIFIED | `app/api/routes/upload.py`: `Depends(require_admin)` on `upload_csv`. Tests: `test_upload_auth.py` — 401 no token, 403 user token, 200 admin (mocked). |
| 3 | Admin calling GET /api/v1/admin/users sees all accounts with email, role, active status, created date | ✓ VERIFIED | `app/api/routes/admin.py`: `list_users` returns `id`, `email`, `role`, `is_active`, `created_at`, `orders_count`, `active_commemoration_count`. Router registered in `main.py`. |
| 4 | Admin can promote, demote, disable via PATCH /api/v1/admin/users/{id}; disabled user's JWT rejected on next request | ✓ VERIFIED | `admin.py`: `patch_user` with `role`/`is_active`; last-admin check returns 400. `app/api/deps.py`: `get_current_user` checks `if not user or not user.is_active` → 401. Tests: promote, demote when another admin, demote last admin 400, disable user, disable last admin 400. |
| 5 | Admin can edit and delete any commemoration via PATCH/DELETE /api/v1/commemorations/{id} | ✓ VERIFIED | `app/api/routes/commemorations.py`: `update_commemoration` and `delete_commemoration` use `Depends(require_admin)`; body updates and delete implemented. |

**Score:** 5/5 Success Criteria verified

### Plan must-haves (truths)

| Plan | Truth | Status | Evidence |
|------|--------|--------|----------|
| 04-01 | Test modules for Phase 4 auth and scope exist and are collectible | ✓ VERIFIED | `tests/test_orders_auth.py`, `test_names_by_user_auth.py`, `test_upload_auth.py`, `test_commemorations_auth.py`, `test_admin_routes.py` exist with real tests (401/403/scope/last-admin). |
| 04-02 | Authenticated user sees only own data on GET /names/by-user and GET /orders | ✓ VERIFIED | names: `effective_email = current_user.email`; orders: `stmt.where(Order.user_email == current_user.email)` when not admin. |
| 04-02 | Admin sees all orders; optional ?email= on by-user for admin | ✓ VERIFIED | orders: no filter when `current_user.role == "admin"`. names: `if current_user.role == "admin" and email is not None: effective_email = email`. |
| 04-02 | POST /orders with JWT sets user_email from token; without JWT anonymous allowed | ✓ VERIFIED | `link_email = current_user.email if current_user is not None else body.user_email`; `get_current_user_optional`. |
| 04-02 | GET /orders/{id}, PATCH/DELETE order require admin | ✓ VERIFIED | `get_order`, `update_order`, `delete_order` use `Depends(require_admin)`. |
| 04-03 | POST /upload/csv returns 403 for non-admin | ✓ VERIFIED | `Depends(require_admin)` on `upload_csv`. |
| 04-03 | GET /commemorations requires auth; user sees own, admin sees all | ✓ VERIFIED | `Depends(get_current_user)`; `effective_email = None if current_user.role == "admin" else current_user.email`; `get_commemorations(..., user_email=effective_email)`. |
| 04-03 | PATCH/DELETE /commemorations/{id} and POST bulk-update require admin | ✓ VERIFIED | All three handlers use `Depends(require_admin)`. |
| 04-04 | Admin can list all user accounts with orders_count and active_commemoration_count | ✓ VERIFIED | `list_users` with scalar_subquery for both counts. |
| 04-04 | Admin can PATCH /admin/users/{id} (role, is_active) with last-admin protection | ✓ VERIFIED | `patch_user`; 400 when demoting/disabling last active admin. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/api/deps.py` | get_current_user_optional, get_current_user, require_admin | ✓ VERIFIED | All present; is_active check in get_current_user. |
| `app/api/routes/names.py` | GET /names/by-user with get_current_user and scope | ✓ VERIFIED | Depends(get_current_user), effective_email logic, get_by_user(db, ...). |
| `app/api/routes/orders.py` | GET/POST/GET id/PATCH/DELETE with auth and scope | ✓ VERIFIED | list_orders get_current_user + scope; create get_current_user_optional; get/patch/delete require_admin. |
| `app/api/routes/upload.py` | POST /upload/csv with require_admin | ✓ VERIFIED | Depends(require_admin). |
| `app/api/routes/commemorations.py` | GET list auth+scope; mutate require_admin | ✓ VERIFIED | get_commemorations(..., user_email=effective_email); PATCH/DELETE/bulk-update require_admin. |
| `app/api/routes/admin.py` | GET /admin/users, PATCH /admin/users/{id} | ✓ VERIFIED | list_users with counts; patch_user with last-admin guard. |
| `app/main.py` | include_router(admin.router) | ✓ VERIFIED | `app.include_router(admin.router, prefix="/api/v1", tags=["admin"]). |
| `app/services/query_service.py` | get_commemorations with optional user_email | ✓ VERIFIED | Signature `user_email: str \| None = None`; `if user_email is not None: stmt = stmt.where(Order.user_email == user_email)`. |
| `tests/test_orders_auth.py` | Scaffold + auth/scope tests | ✓ VERIFIED | 401, user scope, admin all, POST optional auth, by-id 403. |
| `tests/test_names_by_user_auth.py` | by-user scope and admin ?email= | ✓ VERIFIED | 401, user own data, admin ?email=. |
| `tests/test_upload_auth.py` | 401, 403, 200 admin | ✓ VERIFIED | No token 401; user 403; admin 200 mocked. |
| `tests/test_commemorations_auth.py` | GET auth+scope; mutate 403/200 | ✓ VERIFIED | 401, user scope, admin all, PATCH/DELETE 403 non-admin. |
| `tests/test_admin_routes.py` | GET 401/403/200; PATCH promote/demote/disable/last-admin | ✓ VERIFIED | List tests + async PATCH tests with get_db override. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| orders.py | deps.py | Depends(get_current_user_optional), get_current_user, require_admin | ✓ WIRED | Imports and used on POST, GET list, GET id, PATCH, DELETE. |
| names.py | deps.py | Depends(get_current_user) | ✓ WIRED | Import and used on by-user. |
| names.py | query_service | get_by_user(db, user_email=effective_email, active_only) | ✓ WIRED | Called with effective_email. |
| upload.py | deps.py | Depends(require_admin) | ✓ WIRED | Used on upload_csv. |
| commemorations.py | deps.py | get_current_user, require_admin | ✓ WIRED | GET list get_current_user; mutate require_admin. |
| commemorations.py | query_service | get_commemorations(db, user_email=effective_email, ...) | ✓ WIRED | effective_email set from current_user. |
| admin.py | deps.py | Depends(require_admin) | ✓ WIRED | On list_users and patch_user. |
| admin.py | models | User, Order, Commemoration for list and counts | ✓ WIRED | select(User), scalar_subquery with Order/Commemoration. |
| main.py | admin router | include_router(admin.router, prefix="/api/v1") | ✓ WIRED | Line 54. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| USER-01 | 04-01, 04-02 | Authenticated user can view their own orders (matched by email) | ✓ SATISFIED | GET /orders scoped by current_user.email for non-admin; GET /names/by-user returns get_by_user(effective_email). |
| ADMN-01 | 04-02 | Admin can view all orders across all users | ✓ SATISFIED | list_orders: no user filter when current_user.role == "admin". |
| ADMN-02 | 04-04 | Admin can view all user accounts (email, role, active status, created date) | ✓ SATISFIED | GET /admin/users returns list with id, email, role, is_active, created_at, orders_count, active_commemoration_count. |
| ADMN-03 | 04-04 | Admin can promote a user to admin role | ✓ SATISFIED | PATCH /admin/users/{id} body.role = "admin"; test_patch_promote_user_to_admin_200. |
| ADMN-04 | 04-04 | Admin can demote an admin to user role | ✓ SATISFIED | PATCH role = "user"; last-admin returns 400; test_patch_demote_*. |
| ADMN-05 | 04-04 | Admin can disable user (is_active = false; JWT rejected) | ✓ SATISFIED | PATCH is_active = False; get_current_user checks is_active → 401. test_patch_disable_*. |
| ADMN-06 | 04-03 | Admin can edit any commemoration record | ✓ SATISFIED | PATCH /commemorations/{id} with require_admin; body updates fields. |
| ADMN-07 | 04-03 | Admin can delete any commemoration record | ✓ SATISFIED | DELETE /commemorations/{id} with require_admin. |
| ADMN-08 | 04-03 | CSV upload restricted to admin role only | ✓ SATISFIED | POST /upload/csv Depends(require_admin); test_upload_user_token_returns_403. |

No orphaned requirements: every Phase 4 requirement (USER-01, ADMN-01..08) is claimed by at least one plan and implemented.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None | — | No TODO/FIXME/placeholder or empty stubs in app/api. |

### Human Verification Required

Optional end-to-end checks (automated tests already cover 401/403/scope and last-admin):

1. **E2E disabled user** — Disable a user via PATCH /admin/users/{id} with is_active: false; on next request with that user's JWT, expect 401. (Code path: deps.get_current_user → is_active check.)
2. **E2E by-user scope** — As a non-admin user, call GET /names/by-user and GET /orders; confirm only that user's data. As admin, call with ?email=other@example.com on by-user and confirm other user's data.

### Gaps Summary

None. All Success Criteria, plan truths, artifacts, key links, and requirements are satisfied. Phase goal achieved.

---

_Verified: 2026-03-14_  
_Verifier: Claude (gsd-verifier)_
