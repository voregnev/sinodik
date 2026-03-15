# Phase 5: Frontend Auth Integration — Research

**Researched:** 2026-03-15
**Domain:** React PWA auth state, JWT in localStorage, conditional UI (guest/user/admin), OTP login flow
**Confidence:** HIGH

## Summary

Phase 5 integrates authentication into the existing React PWA (`frontend/SinodikApp.jsx`). The frontend is a single-file app loaded via Babel in the browser (no build step); all API calls go through `api()`/`apiOrThrow()` which currently do not send `Authorization: Bearer`. The backend already provides: POST `/api/v1/auth/request-otp`, POST `/api/v1/auth/verify-otp`, GET `/api/v1/auth/me`, GET `/api/v1/orders` (auth, user-scoped), GET `/api/v1/names/by-user` (auth, user-scoped), GET/PATCH `/api/v1/admin/users` (admin-only), POST `/api/v1/upload/csv` (admin-only). The research establishes: (1) wrap all fetch calls to add Bearer from localStorage and handle 401 by clearing token and switching to guest; (2) on load, read token from localStorage and call GET `/auth/me` to get user/role (or clear token on 401); (3) render guest vs user vs admin UI from that state; (4) implement login popup (email → OTP in same modal), "Мои заказы" screen (GET /orders + GET /names/by-user or orders with commemorations), and admin-only tabs plus "Податели" section in БД tab.

**Primary recommendation:** Add auth state (token, user { email, role } | null) in SinodikApp; centralize fetch in one helper that adds `Authorization: Bearer ${token}` when token exists and on 401 clears token and sets user to null; on mount read token and call GET /auth/me to hydrate user (or clear token); conditional TABS and header (Войти / Выйти, Мои заказы) and admin-only visibility from user.role; login modal with two steps (email submit → OTP submit), errors at top of modal; "Мои заказы" page listing user's orders with type, period, expiry, names/count from existing API shapes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Вход (модалка):** Один попап с двумя шагами подряд: email → OTP в том же окне. Ошибки (неверный код, истёкший OTP, сеть) — вверху попапа. Подсказку «Код отправлен на …» не показывать. Кнопки «Назад» / «Изменить email» на шаге OTP нет.
- **«Мои заказы»:** Ссылка ведёт на отдельный экран со списком записок пользователя. Пустое состояние — просто пустой список, без текста «Пока нет записок». В карточке записки минимум: тип (здравие/упокоение), период, дата окончания, имена или количество имён. Размещение ссылки «Мои заказы» в шапке — на усмотрение реализации.
- **Админ и видимость разделов:** Управление пользователями в зоне вкладки «БД», раздел называется **«Податели»** (не «Пользователи»). На экране «Податели» — только список подателей; у каждой строки — ссылка на заказы этого пользователя (отфильтрованные). CSV, Стат., БД, «Сегодня», «Поиск» — только для админа. Обычный пользователь после входа видит только форму записки и «Мои заказы».
- **Выход:** По нажатию «Выйти» — сразу сброс токена и показ гостевого вида, без диалога подтверждения. После выхода всегда показывается форма записки (главная страница гостя).
- **Терминология в UI:** Везде «Записки», не «заказы».

### Claude's Discretion
- Точное размещение ссылки «Мои заказы» (справа в шапке, под шапкой и т.п.).
- Детали оформления попапа входа и экрана «Мои заказы» в рамках существующих стилей (T, компоненты).

### Deferred Ideas (OUT OF SCOPE)
None — обсуждение в рамках фазы 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FRNT-01 | Login screen when not authenticated (email → OTP code entry) | Single modal with step state (email \| otp); POST /auth/request-otp then POST /auth/verify-otp; store token and user from verify response; call GET /auth/me on app load to restore session. |
| FRNT-02 | Authenticated user sees "My Orders" tab with their linked commemorations | Backend verified: GET /orders returns id, user_email, source_channel, need_receipt, ordered_at, created_at (no commemorations). GET /names/by-user returns { user_email, commemorations, count }; each comm has commemoration_id, canonical_name, prefix, order_type, period_type, ordered_at, starts_at, expires_at, is_active — **no order_id**. So frontend cannot group commemorations by order from current API. **Planner must either:** (A) Extend get_by_user to include order_id in each comm (and names route to return it) so frontend can group by order_id and show one card per order with type/period/expiry/count; or (B) Add backend endpoint e.g. GET /orders?summary=1 for current user returning orders with nested or aggregated comm summary (order_type, period_type, expires_at, count). Option A is minimal: add order_id (and optionally order position) to get_by_user select and to the dict returned; frontend then groups by order_id. |
| FRNT-03 | Admin sees "Admin" tab with all orders and user management UI | Admin sees full TABS (Сегодня, Поиск, Записка, CSV, Стат., БД); БД tab includes section "Податели" (list from GET /admin/users; link to orders filtered by user). So no separate "Admin" tab — admin sees all tabs; CSV/Стат./БД/Сегодня/Поиск only for admin; "Мои заказы" for non-admin user. CONTEXT says: "Админ: видит полный интерфейс — все разделы (Сегодня, Поиск, Записка, CSV, Стат., БД). Управление пользователями — в том же месте, где вкладка «БД», раздел называется «Податели»." So FRNT-03 satisfied by admin seeing all tabs + Податели inside БД. |
| FRNT-04 | CSV upload tab hidden for non-admin users | Conditional TABS: when user?.role !== 'admin', exclude upload, stats, db from tab bar; show only Записка and "Мои заказы" (and header Выйти). |
| FRNT-05 | JWT in localStorage; Authorization Bearer on all authenticated requests | Store token in localStorage (e.g. key 'sinodik_token'); in api()/apiOrThrow() add headers['Authorization'] = `Bearer ${token}` when token present; on 401 clear token and set user to null, then re-render. |
| FRNT-06 | Anonymous users can still submit orders via "Записка" tab (no login required) | Guest sees form (AddPage) and "Войти"; POST /orders without Bearer already supported (get_current_user_optional); keep showing AddPage for guest and send no Authorization. |
| FRNT-07 | App decodes JWT role client-side to conditionally render admin UI | Either decode JWT payload (base64url middle part) for role or rely on GET /auth/me response (id, email, role, is_active). Prefer GET /auth/me on load and after login — single source of truth; no need to decode JWT for role. |
</phase_requirements>

## Standard Stack

### Core
| Library / Asset | Version | Purpose | Why Standard |
|-----------------|---------|---------|--------------|
| React | 18 (vendor) | Components, useState, useEffect | Already in frontend; no build |
| fetch | — | API calls | Native; existing api()/apiOrThrow() |
| localStorage | — | Persist JWT | REQUIREMENTS FRNT-05; no extra lib |
| Babel (browser) | — | JSX transform in index.html | Current setup; no Node toolchain |

### Supporting
| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| GET /auth/me | Hydrate user/role on load and after login | On app mount if token exists; after verify-otp success store token + user from response (verify returns user); on 401 clear token and user. |
| Single fetch wrapper | Add Bearer, handle 401 | Replace or wrap existing api/apiOrThrow so every request gets Authorization when token present and 401 → clear token + set user null. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Decode JWT for role | GET /auth/me for role | GET /auth/me is authoritative (server checks is_active); decoding JWT only for role is possible but redundant if we call /me on load. |
| Separate "Admin" tab | Admin sees all tabs (Сегодня, Поиск, CSV, Стат., БД) | CONTEXT: admin sees full interface; "Admin" tab not required — visibility by role suffices. |

**Installation:** No new frontend packages. Backend already in place (Phase 2–4).

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── index.html          # Loads React, Babel, SinodikApp.jsx (unchanged)
├── SinodikApp.jsx      # Auth state, fetch wrapper, conditional TABS, login modal, Мои заказы, Податели
├── vendor/             # react, react-dom, babel (unchanged)
└── (no dist/ or build)
```

### Pattern 1: Auth state and fetch wrapper
**What:** One top-level state: `token` (string | null), `user` ({ id, email, role, is_active } | null). On mount: read token from localStorage; if present, GET /auth/me and set user (or clear token on 401). All API calls go through a wrapper that adds `Authorization: Bearer ${token}` when token is set; on response 401 remove token from localStorage and set user to null.
**When to use:** Every authenticated request; initial hydration.
**Example:**
```javascript
const AUTH_KEY = "sinodik_token";

async function apiAuth(path, opts = {}, { token, setToken, setUser } = {}) {
  const headers = { "Content-Type": "application/json", ...opts.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) {
    localStorage.removeItem(AUTH_KEY);
    setToken?.(null);
    setUser?.(null);
    throw new Error("Unauthorized");
  }
  if (!res.ok) throw new Error(/* ... */);
  return res.json();
}
```

### Pattern 2: Conditional tabs by role
**What:** Build TABS array from role: guest → no tabs (or only content); user → Записка + "Мои заказы" (no tab bar or minimal); admin → full TABS (Сегодня, Поиск, Записка, CSV, Стат., БД). Header: guest → "Войти"; user → "Мои заказы" link + "Выйти"; admin → same + full tabs.
**When to use:** Render tab bar and header.
**Example:** `const tabs = user?.role === 'admin' ? TABS_FULL : (user ? TABS_USER : TABS_GUEST);` with TABS_USER = [{ add, myOrders }], TABS_GUEST = [add only or single view].

### Pattern 3: Login modal (two steps)
**What:** Modal state: `loginStep: 'email' | 'otp'`, `loginEmail: string`, `loginError: string`. Step email: input email, submit → POST /auth/request-otp; on 202 set step 'otp', clear error; on 4xx set error. Step otp: input code, submit → POST /auth/verify-otp; on 200 store token + user, close modal; on 401 set error. No "Back" on OTP step; errors at top of modal.
**When to use:** "Войти" click opens modal.
**Example:** Single modal component with step and error state; two forms (email form, OTP form) rendered by step.

### Anti-Patterns to Avoid
- **Sending Bearer for anonymous POST /orders:** When guest submits записка, do not add Authorization; backend accepts optional auth.
- **Relying only on JWT decode for role:** Server may have disabled the user; GET /auth/me reflects is_active and current role.
- **Showing "Код отправлен на …" in login modal:** CONTEXT explicitly says not to show this hint.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT validation on client | Verify signature in browser | GET /auth/me or decode payload for display only | Secret is server-only; client only needs role for UI. Trust /me for auth state. |
| Custom auth protocol | New token format or flow | Existing POST request-otp, verify-otp, Bearer | Backend already implements; stay aligned. |

**Key insight:** Auth is enforced by the backend; frontend only stores token, sends it, and shows/hides UI based on role from /auth/me.

## Common Pitfalls

### Pitfall 1: 401 on every request after refresh
**What goes wrong:** Token in localStorage but expired; first API call returns 401; if not handled globally, user appears logged in until that call.
**Why it happens:** No initial GET /auth/me on load, or 401 not clearing token.
**How to avoid:** On mount, if token exists call GET /auth/me; on 401 clear token and set user null. In fetch wrapper, on 401 always clear token and set user null so one failed request logs out.
**Warning signs:** User sees "Мои заказы" then gets 401 and content disappears.

### Pitfall 2: Upload/CSV still visible to non-admin
**What goes wrong:** TABS built once and not filtered by role.
**Why it happens:** Forgetting to derive tab list from user.role.
**How to avoid:** Compute visible tabs from `user?.role === 'admin'`; for non-admin user show only Записка and Мои заказы (no Сегодня, Поиск, CSV, Стат., БД).
**Warning signs:** Regular user sees CSV tab and gets 403 on upload.

### Pitfall 3: "Мои заказы" empty or wrong data
**What goes wrong:** GET /orders returns list but card needs type, period, expires_at, names; GET /names/by-user currently does not include order_id in each comm, so frontend cannot group by order.
**Why it happens:** get_by_user does not select/return order_id.
**How to avoid:** Add order_id to get_by_user result (query_service) and return it in GET /names/by-user; frontend then GET /orders + GET /names/by-user?active_only=false and group commemorations by order_id to build one card per order.
**Warning signs:** Cards show only order id/date without type/period/expiry.

### Pitfall 4: Form POST /orders without token when user is logged in
**What goes wrong:** Logged-in user submits записка but request is sent without Bearer, so order is created as anonymous.
**Why it happens:** AddPage or submit path doesn't use the auth-aware fetch or doesn't pass token.
**How to avoid:** All API calls (including POST /orders) go through the same wrapper that adds Bearer when token is set.
**Warning signs:** After login, new записки don't appear under "Мои заказы".

## Code Examples

### GET /auth/me on load and 401 handling
```javascript
useEffect(() => {
  const t = localStorage.getItem(AUTH_KEY);
  if (!t) { setUser(null); return; }
  fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${t}` } })
    .then(res => {
      if (res.status === 401) { localStorage.removeItem(AUTH_KEY); setToken(null); setUser(null); return; }
      if (!res.ok) return;
      return res.json();
    })
    .then(data => { if (data) { setToken(t); setUser(data); } })
    .catch(() => { setUser(null); });
}, []);
```

### Decode JWT payload (optional, for role before /me returns)
```javascript
function parseJwtPayload(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(decodeURIComponent(atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''));
  } catch { return null; }
}
```
Use only for optional display; rely on GET /auth/me for auth decisions.

### Login: request OTP then verify
```javascript
// Step 1
const res = await fetch(`${API}/auth/request-otp`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: loginEmail.trim() }),
});
if (res.status === 429) { setLoginError('Слишком много запросов'); return; }
if (!res.ok) { const d = await res.json().catch(() => ({})); setLoginError(d.detail || 'Ошибка'); return; }
setLoginStep('otp');

// Step 2
const res2 = await fetch(`${API}/auth/verify-otp`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: loginEmail, code: otpCode }),
});
if (!res2.ok) { setLoginError('Неверный или истёкший код'); return; }
const { token: newToken, user: userData } = await res2.json();
localStorage.setItem(AUTH_KEY, newToken);
setToken(newToken);
setUser(userData);
closeLoginModal();
```

## Backend API Summary (for frontend)

| Endpoint | Auth | Purpose |
|----------|------|---------|
| POST /api/v1/auth/request-otp | No | Body: { email }; 202 + message; 429 rate limit |
| POST /api/v1/auth/verify-otp | No | Body: { email, code }; 200 → { token, user }; 401 invalid/expired |
| GET /api/v1/auth/me | Bearer | 200 → { id, email, role, is_active }; 401 |
| GET /api/v1/orders | Bearer | User: own orders; admin: all. List with id, user_email, source_channel, need_receipt, ordered_at, created_at |
| GET /api/v1/orders/{id} | Admin | Order detail + commemorations (admin only) |
| GET /api/v1/names/by-user | Bearer | ?email= (admin only). Returns { user_email, commemorations, count }. Commemorations: check if order_id present for grouping. |
| GET /api/v1/admin/users | Admin | List users with orders_count, active_commemoration_count |
| PATCH /api/v1/admin/users/{id} | Admin | role, is_active |
| POST /api/v1/upload/csv | Admin | multipart file |

**Мои заказы data:** GET /orders gives order list. get_by_user (query_service) currently does **not** return order_id; it returns commemoration_id, canonical_name, prefix, order_type, period_type, ordered_at, starts_at, expires_at, is_active. So frontend cannot group by order. **Recommendation:** Add order_id to get_by_user select and to the response dict in query_service, and expose it in GET /names/by-user response. Then frontend can GET /orders + GET /names/by-user?active_only=false, group commemorations by order_id, and for each order show a card with type, period, expiry (from first or representative comm), and names or count.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No auth in frontend | JWT in localStorage, Bearer on requests, /auth/me for role | Phase 5 | Single-file React stays; no new framework. |

**Deprecated/outdated:** N/A.

## Open Questions

1. **GET /names/by-user commemorations: do they include order_id?**
   - What we know: get_by_user (query_service) returns list of dicts without order_id; names route returns that as { user_email, commemorations, count }.
   - Resolved: order_id is **not** in response. Recommendation: Add order_id to get_by_user (select Commemoration.order_id, include in returned dict) and keep names route returning same structure; frontend can then group by order_id for "Мои заказы" cards.

2. **Податели: link to "orders filtered by user"**
   - What we know: GET /admin/users returns list; GET /orders for admin returns all orders (filter by user_email in UI or backend support).
   - What's unclear: Whether we need GET /orders?user_email= for admin to show orders of selected submitter.
   - Recommendation: Backend GET /orders already filters by current_user.email for non-admin; for admin, optional ?user_email= could filter. Check orders route: admin sees all. So frontend can list all orders and filter by selected user_email, or backend can add ?user_email= for admin. Planner to decide (frontend filter vs backend param).

## Validation Architecture

`workflow.nyquist_validation` is true in `.planning/config.json`. Frontend is a single JSX file with no Node/test runner in repo; backend tests cover auth and scope. Validation for Phase 5 is therefore manual/browser UAT plus backend regression.

### Test Framework
| Property | Value |
|----------|--------|
| Frontend unit/integration | None (no Jest/Vitest in repo; Babel-in-browser setup) |
| Backend | pytest (existing) |
| Config file | pyproject.toml / pytest (existing) |
| Quick run command | `docker compose run --rm api pytest tests/ -v -x` |
| Full suite command | `docker compose run --rm api pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FRNT-01 | Login flow (email → OTP, store token, show user UI) | manual UAT | — | N/A |
| FRNT-02 | "Мои заказы" shows user's orders/commemorations | manual UAT | — | N/A |
| FRNT-03 | Admin sees all tabs + Податели in БД | manual UAT | — | N/A |
| FRNT-04 | CSV tab hidden for non-admin | manual UAT | — | N/A |
| FRNT-05 | JWT in localStorage; Bearer on requests; 401 clears token | manual UAT / backend | Backend: `pytest tests/test_auth_routes.py tests/test_orders_auth.py -v` | ✅ |
| FRNT-06 | Anonymous can POST /orders (no login) | integration | `pytest tests/test_orders_auth.py -v -k "anonymous\|post"` | ✅ |
| FRNT-07 | Admin UI visible only when role=admin (from /me) | manual UAT | — | N/A |

### Sampling Rate
- **Per task commit:** Run relevant backend tests (auth, orders) to ensure no regression.
- **Per wave merge:** Full backend suite: `docker compose run --rm api pytest tests/ -v`.
- **Phase gate:** Manual UAT for FRNT-01–04, FRNT-07; backend suite green; 05-VALIDATION.md checklist.

### Wave 0 Gaps
- No frontend automated tests in repo (by design; no Node toolchain). Manual UAT covers login, "Мои заказы", admin vs user tabs, Податели, anonymous submit.
- Backend tests already cover: auth routes (request-otp, verify-otp, me), orders auth and scope, admin users, upload 403. No new test file required for Phase 5 unless adding a backend endpoint for "my orders summary"; then add tests for that endpoint.

## Sources

### Primary (HIGH confidence)
- Project code: `frontend/SinodikApp.jsx`, `frontend/index.html`, `app/api/routes/auth.py`, `app/api/deps.py`, `app/api/routes/orders.py`, `app/api/routes/admin.py`, `app/api/routes/upload.py`, `app/api/routes/names.py` (GET /names/by-user).
- REQUIREMENTS.md, CONTEXT.md 05-frontend-auth-integration, STATE.md, CLAUDE.md.

### Secondary (MEDIUM confidence)
- WebSearch: JWT decode client-side without library (atob base64url payload) — standard approach; security note: client decode is for display only, not for auth decisions.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing frontend and backend code reviewed.
- Architecture: HIGH — patterns follow CONTEXT and existing SinodikApp structure.
- Pitfalls: HIGH — 401 handling and role-based tabs are standard; "Мои заказы" data shape depends on backend response (one open question).

**Research date:** 2026-03-15
**Valid until:** ~30 days (backend API stable; frontend patterns unchanged).

---

## RESEARCH COMPLETE

**Phase:** 5 — Frontend Auth Integration
**Confidence:** HIGH

### Key Findings
- Frontend: single-file React (SinodikApp.jsx), Babel in browser, no build; add auth state (token, user) and one fetch wrapper that adds Bearer and clears token on 401.
- Backend auth API is ready: request-otp, verify-otp, me, orders (auth/scoped), names/by-user, admin/users, upload/csv (admin).
- GET /names/by-user does not return order_id per comm; add order_id to get_by_user so "Мои заказы" can group by order and show one card per order with type/period/expiry/count.
- Login: one modal, two steps (email → OTP), errors at top, no "code sent" hint, no Back on OTP. Logout: immediate token clear, no confirm.
- Admin sees all tabs (Сегодня, Поиск, Записка, CSV, Стат., БД); БД tab includes section "Податели" (GET /admin/users, link to orders per user). Non-admin user sees only Записка + "Мои заказы".

### File Created
`.planning/phases/05-frontend-auth-integration/05-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Existing frontend and backend code reviewed; no new libs |
| Architecture | HIGH | Patterns follow CONTEXT and current SinodikApp |
| Pitfalls | HIGH | 401 handling, role-based tabs, order_id for "Мои заказы" documented |

### Open Questions
- Податели: filter orders by selected user on frontend vs backend GET /orders?user_email= for admin — planner can choose.

### Ready for Planning
Research complete. Planner can create PLAN.md files. Include one backend task: add order_id to get_by_user (and to GET /names/by-user response) for "Мои заказы" grouping.
