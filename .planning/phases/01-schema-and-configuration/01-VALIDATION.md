---
phase: 1
slug: schema-and-configuration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in pyproject.toml) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` with `pythonpath = ["app"]`, `testpaths = ["tests"]` |
| **Quick run command** | `docker compose run --rm api pytest tests/test_phase1.py -x` |
| **Full suite command** | `docker compose run --rm api pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose run --rm api pytest tests/test_phase1.py -x`
- **After every plan wave:** Run `docker compose run --rm api pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | USER-02 | unit | `docker compose run --rm api pytest tests/test_phase1.py::test_order_user_email_exists -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | AUTH-01 | integration | `docker compose run --rm api pytest tests/test_phase1.py::test_anonymous_order_unaffected -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | BOOT-01 | unit | `docker compose run --rm api pytest tests/test_phase1.py::test_admin_emails_config -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | BOOT-01 | unit | `docker compose run --rm api pytest tests/test_phase1.py::test_jwt_secret_required -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase1.py` — stubs for AUTH-01, USER-02, BOOT-01 (new file, does not exist yet)

*Note: Existing `tests/test_name_extractor.py` covers NLP pipeline only and is unaffected by Phase 1 changes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `users` and `otp_codes` tables exist after `alembic upgrade head` | Phase success criterion #1 | Requires live DB inspection | Run `docker compose exec db psql -U sinodik -c "\dt"` and verify both tables appear |
| `User` and `OtpCode` models importable in service code | Phase success criterion #2 | Import smoke test via Python REPL | `docker compose exec api python -c "from models.models import User, OtpCode; print('OK')"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
