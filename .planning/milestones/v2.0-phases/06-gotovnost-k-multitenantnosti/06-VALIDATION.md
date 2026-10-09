---
phase: "06"
slug: "gotovnost-k-multitenantnosti"
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-10-04"
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (Python 3.12.3) |
| **Config file** | `pytest.ini` / setup in each repo |
| **Quick run command** | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_key_rotator.py -q` |
| **Full suite command** | `python3 /opt/chat-app/scripts/gate.py` |
| **Estimated runtime** | ~5 seconds (focused) / ~90 seconds (full gate) |

---

## Sampling Rate

- **After every task commit:** Run focused pytest command for modified module/test
- **After every plan wave:** Run `python3 /opt/chat-app/scripts/gate.py`
- **Before `/gsd-verify-work`:** Full suite must be green (Exit code 0, ЗЕЛЁНЫЙ)
- **Max feedback latency:** 10 seconds (unit) / 120 seconds (gate)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | ISO-01 | T-06-01 | No global mutation of `config.GEMINI_API_KEY` | unit | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_key_rotator.py -q` | ✅ | ⬜ pending |
| 06-02-01 | 02 | 2 | ISO-02 | T-06-02 | NDA bodies/attachments never sent to LLM | unit | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_airgap_trap.py -q` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 3 | ISO-03 | T-06-03 | Connectors fail-fast without required scope; zero LMS creds in chat-app | integration | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_credentials_isolation.py -q && /opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_ports_conformance.py -q` | ❌ W0 | ⬜ pending |
| 06-04-01 | 04 | 4 | ISO-04 | T-06-04 | Concurrent execution of 2 personas has zero cross-talk | integration | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_concurrency_isolation.py -q` | ❌ W0 | ⬜ pending |
| 06-05-01 | 05 | 5 | FIN-01 | T-06-05 | Core `src/` free of hardcoded tokens | unit/regression | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/ -q` | ✅ | ⬜ pending |
| 06-06-01 | 06 | 6 | FIN-01 | T-06-06 | `HARDCODE_BASELINE = {}` in both repos; Quality Gate is green | gate | `python3 /opt/chat-app/scripts/gate.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `/opt/assistant-core/tests/test_airgap_trap.py` — Stubs & SpyGenAIClient for ISO-02
- [ ] `/opt/chat-app/backend/tests/test_credentials_isolation.py` — LMS credentials isolation check for ISO-03
- [ ] `/opt/assistant-core/tests/test_concurrency_isolation.py` — Concurrent persona run for ISO-04

---

## Manual-Only Verifications

*None: All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-04
