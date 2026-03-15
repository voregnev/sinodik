---
phase: 2
slug: auth-service-core
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pytest.ini (existing) |
| **Quick run command** | `pytest tests/test_auth_service.py -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_auth_service.py -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | AUTH-02 | unit | `pytest tests/test_auth_service.py::test_request_otp -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | AUTH-03 | integration | `pytest tests/test_email_service.py::test_send_otp_email -x` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | AUTH-04 | unit | `pytest tests/test_auth_service.py::test_verify_otp -x` | ❌ W0 | ⬜ pending |
| 2-01-04 | 01 | 1 | AUTH-05 | integration | `pytest tests/test_auth_service.py::test_account_auto_creation -x` | ❌ W0 | ⬜ pending |
| 2-01-05 | 01 | 1 | AUTH-06 | unit | `pytest tests/test_auth_service.py::test_otp_expiry -x` | ❌ W0 | ⬜ pending |
| 2-01-06 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_service.py::test_otp_single_use -x` | ❌ W0 | ⬜ pending |
| 2-01-07 | 01 | 1 | AUTH-08 | integration | `pytest tests/test_auth_service.py::test_otp_rate_limiting -x` | ❌ W0 | ⬜ pending |
| 2-01-08 | 01 | 1 | AUTH-09 | unit | `pytest tests/test_auth_service.py::test_jwt_claims_structure -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_auth_service.py` — stubs for AUTH-02, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09
- [ ] `tests/test_email_service.py` — stubs for AUTH-03
- [ ] `framework install` — if no framework detected

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending