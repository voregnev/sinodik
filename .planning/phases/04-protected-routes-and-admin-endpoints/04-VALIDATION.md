---
phase: 04
slug: protected-routes-and-admin-endpoints
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-03-14"
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project) |
| **Config file** | pyproject.toml [tool.pytest.ini_options], testpaths = ["tests"] |
| **Quick run command** | `docker compose run --rm api pytest tests/ -v -x` |
| **Full suite command** | `docker compose run --rm api pytest tests/ -v` |
| **Estimated runtime** | ~60 seconds (quick), ~90s (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -v -x` (or targeted test file)
- **After every plan wave:** Run `docker compose run --rm api pytest tests/ -v`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-* | * | * | USER-01, ADMN-* | integration | `pytest tests/test_*_auth.py tests/test_admin_routes.py -v -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_orders_auth.py` (or equivalent) — GET/POST orders auth and scope
- [ ] `tests/test_admin_routes.py` — GET/PATCH admin/users, last-admin guard
- [ ] `tests/test_commemorations_auth.py` — GET list scope, PATCH/DELETE/bulk-update admin only
- [ ] `tests/test_upload_auth.py` or part of existing — POST /upload/csv require_admin
- [ ] `tests/test_names_by_user_auth.py` (or equivalent) — by-user scope and admin ?email=
- [ ] Shared fixtures: authenticated user (user + admin), DB with orders/commemorations
- Framework: pytest already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (None) | — | All phase behaviors have automated verification | — |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
