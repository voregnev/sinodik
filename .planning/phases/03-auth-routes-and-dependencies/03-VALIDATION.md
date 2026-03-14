---
phase: 03
slug: auth-routes-and-dependencies
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-03-14"
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (asyncio_mode = "auto") |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/test_auth_routes.py -v -x` |
| **Full suite command** | `docker compose run --rm api pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds (quick), ~60s (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_auth_routes.py -v -x`
- **After every plan wave:** Run `docker compose run --rm api pytest tests/ -v`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-* | 01 | 1 | USER-03 | integration | `pytest tests/test_auth_routes.py -v -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_auth_routes.py` — auth endpoints (request-otp 202/429/400, verify-otp 200/401, /auth/me 200/401) and USER-03 (401 without token / expired)
- [ ] Optional: `tests/test_auth_deps.py` — unit tests for get_current_user / require_admin
- [ ] Existing `tests/test_auth_service.py` — no change for Phase 3
- [ ] conftest.py — add if shared fixtures (client, db) needed for auth route tests

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (None) | — | All phase behaviors have automated verification | — |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
