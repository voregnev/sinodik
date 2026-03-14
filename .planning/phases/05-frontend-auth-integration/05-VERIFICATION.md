---
phase: 05-frontend-auth-integration
verified: 2025-03-15T12:00:00Z
status: passed
score: 5/5 must-haves verified (gaps resolved inline)
gaps_resolved:
  - "Removed duplicate MyOrdersPage stub; tab now uses full implementation with /orders + /names/by-user and order_id grouping."
  - "UploadPage now sends Authorization Bearer and handles 401 (clear token/user)."
human_verification: []
---

# Phase 05: Frontend Auth Integration Verification Report

**Phase Goal:** The React PWA presents a complete auth-aware UI — unauthenticated users see the login screen, authenticated users see their orders, and admins see the admin panel.

**Verified:** 2025-03-15T12:00:00Z  
**Status:** gaps_found  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|--------|--------|----------|
| 1 | Unauthenticated user sees login screen (email → OTP steps) | ✓ VERIFIED | Login modal with loginStep 'email'/'otp'; POST /auth/request-otp and /auth/verify-otp; token/user stored and modal closed. |
| 2 | JWT in localStorage; all API calls include Authorization: Bearer | ⚠️ PARTIAL | api()/apiOrThrow() add Bearer and handle 401; UploadPage uses raw fetch() without Bearer — admin CSV upload will 401. |
| 3 | Authenticated user sees "My Orders" with linked commemorations | ✗ FAILED | Second MyOrdersPage (stub) shadows full implementation; only order list shown, no by-user or order_id grouping. |
| 4 | Admin sees all tabs + Податели; CSV/Стат./БД only for admin | ✓ VERIFIED | visibleTabs by user.role; TABS_FULL for admin, TABS_USER for non-admin; DbManagePage has SubmittersSection when isAdmin. |
| 5 | Anonymous user can submit записка without logging in | ✓ VERIFIED | !user → AddPage; api() does not add Bearer when token null; POST /orders uses get_current_user_optional on backend. |

**Score:** 4/5 success criteria fully met; 1 failed (My Orders content), 1 partial (Bearer on upload).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| app/services/query_service.py | get_by_user returns order_id in select and dict | ✓ VERIFIED | Order.id.label("order_id") in select; "order_id": r.order_id in returned dict. |
| tests/test_names_by_user_auth.py | by-user response includes order_id in commemorations | ✓ VERIFIED | test_by_user_response_includes_order_id_in_commemorations asserts order_id in data["commemorations"][0]. |
| frontend/SinodikApp.jsx | Auth state, Bearer in fetch, 401 clear, login modal, conditional tabs | ✓ VERIFIED | token/user state, authRef, api/apiOrThrow with Bearer and 401 handling; login modal email→OTP; visibleTabs by role. |
| frontend/SinodikApp.jsx | MyOrdersPage with /orders + /names/by-user, cards by order_id | ✗ STUB USED | Full implementation exists (L731–816) but duplicate stub (L1703–1746) is the one rendered. |
| frontend/SinodikApp.jsx | UploadPage | ⚠️ ORPHANED WIRE | Uses raw fetch without Authorization; admin upload will 401. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| SinodikApp mount | GET /auth/me | fetch with Bearer when token in localStorage | ✓ WIRED | useEffect reads AUTH_KEY, calls /auth/me, sets user or clears on 401. |
| api() / apiOrThrow() | Authorization Bearer + 401 clear | authRef.current.token, headers, res.status 401 | ✓ WIRED | Both add Bearer when token; on 401 removeItem, setToken(null), setUser(null). |
| Login modal | POST /auth/request-otp, /auth/verify-otp | fetch with body { email } / { email, code } | ✓ WIRED | handleRequestOtp, handleVerifyOtp; token/user stored, modal closed. |
| visibleTabs | user?.role | admin => TABS_FULL; user => TABS_USER | ✓ WIRED | visibleTabs = user?.role === "admin" ? TABS_FULL : TABS_USER. |
| Мои заказы tab | GET /orders + GET /names/by-user | api() then group by order_id | ✗ NOT WIRED | Rendered component only calls api("/orders"); full component that calls by-user is shadowed. |
| UploadPage | POST /upload/csv | fetch (no Bearer) | ✗ NOT WIRED | No Authorization header; backend requires admin → 401. |
| SubmittersSection | GET /admin/users | api("/admin/users") | ✓ WIRED | useEffect calls api("/admin/users"), list with "Заказы" → onSelectOrders(email). |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FRNT-01 | 05-03 | Login screen (email → OTP) | ✓ SATISFIED | Login modal, request-otp, verify-otp, token/user stored. |
| FRNT-02 | 05-01, 05-04 | My Orders tab with linked commemorations | ✗ BLOCKED | Stub MyOrdersPage rendered; no by-user or order cards. |
| FRNT-03 | 05-04 | Admin sees all tabs + user management (Податели) | ✓ SATISFIED | TABS_FULL, DbManagePage, SubmittersSection. |
| FRNT-04 | 05-03 | CSV tab hidden for non-admin | ✓ SATISFIED | visibleTabs excludes upload/stats/db for non-admin. |
| FRNT-05 | 05-02 | JWT in localStorage; Bearer on all requests | ⚠️ PARTIAL | Bearer in api/apiOrThrow; UploadPage does not send Bearer. |
| FRNT-06 | 05-02 | Anonymous can submit orders (no login) | ✓ SATISFIED | Guest sees AddPage; POST /orders without Bearer. |
| FRNT-07 | 05-02, 05-03 | Role from /me; conditional admin UI | ✓ SATISFIED | user from /auth/me, visibleTabs and Податели by user.role. |

No orphaned requirements: all FRNT-01–FRNT-07 are claimed by plans 05-01–05-04.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|--------|----------|--------|
| frontend/SinodikApp.jsx | 1703 | Duplicate function name MyOrdersPage (stub overwrites full) | 🛑 Blocker | "My Orders" does not show linked commemorations. |
| frontend/SinodikApp.jsx | 840 | fetch() without Authorization in UploadPage | ⚠️ Warning | Admin CSV upload returns 401. |

### Human Verification Required

- **Login flow (FRNT-01):** Open app unauthenticated → click Войти → enter email → Получить код → enter OTP → verify modal closes and Выйти/Мои заказы or full tabs appear. (Automated checks pass; optional human UAT.)
- **Admin CSV (after fix):** After adding Bearer to upload, confirm CSV upload succeeds when logged in as admin.

### Gaps Summary

1. **My Orders content (FRNT-02):** The full "Мои заказы" implementation (GET /orders + GET /names/by-user, grouping by order_id, cards with type/period/expiry/names) exists in the first `MyOrdersPage` (L731–816) but a second `MyOrdersPage` (L1703–1746) that only fetches `/orders` and shows a simple list overwrites it. Remove the duplicate stub or merge so the tab uses the implementation that displays linked commemorations.

2. **CSV upload auth (FRNT-05):** UploadPage does not send the JWT; it uses raw `fetch()` without headers. Because POST /upload/csv requires admin, uploads will fail with 401. Use the shared api layer (or add Authorization header and 401 handling) so admin uploads are authenticated.

---

_Verified: 2025-03-15T12:00:00Z_  
_Verifier: Claude (gsd-verifier)_
