---
phase: 5
slug: frontend-auth-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-03-15"
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend); no frontend test runner (Babel-in-browser, single JSX file) |
| **Config file** | pyproject.toml / pytest (existing) |
| **Quick run command** | `docker compose run --rm api pytest tests/ -v -x` |
| **Full suite command** | `docker compose run --rm api pytest tests/ -v` |
| **Estimated runtime** | ~30–60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose run --rm api pytest tests/ -v -x` (relevant auth/orders tests)
- **After every plan wave:** Run full suite `docker compose run --rm api pytest tests/ -v`
- **Before `$gsd-verify-work`:** Full suite must be green; manual UAT for FRNT-01–04, FRNT-07
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-* | 01 | 1 | FRNT-05, FRNT-06 | integration | `pytest tests/test_auth_routes.py tests/test_orders_auth.py -v` | ✅ | ⬜ pending |
| 05-02-* | 02 | 1 | FRNT-01, FRNT-07 | manual UAT | — | N/A | ⬜ pending |
| 05-03-* | 03 | 2 | FRNT-02 | manual UAT + backend | Backend: `pytest tests/test_orders.py tests/test_names.py -v` | ✅ | ⬜ pending |
| 05-04-* | 04 | 2 | FRNT-03, FRNT-04 | manual UAT | — | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend: if new endpoint or change to get_by_user (order_id) — add/update tests in existing test files
- [ ] No frontend test framework (by design; manual UAT covers login, Мои заказы, admin tabs, Податели)

*Existing backend tests cover auth routes, orders auth/scope, admin users, upload 403.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Login flow (email → OTP, token stored, user UI) | FRNT-01 | No Jest/Vitest in repo | Open app → Войти → email → OTP → verify UI and Выйти/Мои заказы |
| "Мои заказы" shows user's orders/commemorations | FRNT-02 | Frontend-only UI | Login → Мои заказы → check cards (type, period, expiry, names/count) |
| Admin sees all tabs + Податели in БД | FRNT-03 | Frontend-only UI | Login as admin → see Сегодня, Поиск, CSV, Стат., БД, Податели |
| CSV tab hidden for non-admin | FRNT-04 | Frontend-only UI | Login as user (non-admin) → no CSV/Стат./БД/Сегодня/Поиск |
| Admin UI visible only when role=admin (from /me) | FRNT-07 | Frontend conditional render | Verify tabs and Податели only for admin role |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: backend suite after each wave
- [ ] Wave 0 covers any new backend changes (order_id in get_by_user)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter after manual UAT checklist done

**Approval:** pending
