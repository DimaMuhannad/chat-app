---
phase: "07"
slug: "git-istochniki-i-dashbordy-notion"
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-10-04"
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (Python 3.12.3) |
| **Config file** | `pytest.ini` / setup in each repo |
| **Quick run command** | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_git_connector.py -q` |
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
| 07-01-01 | 01 | 1 | GIT-01, GIT-02 | T-07-02 | BaseGitSourceProvider port & SshGitProvider with git.read only | unit | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_git_connector.py -q` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 2 | GIT-03, GIT-04 | T-07-01 | NDA commits/diffs/files never passed to LLM; Russian semantic summary | unit/trap | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_git_airgap_trap.py -q` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 3 | NTN-01, NTN-02 | T-07-04 | Notion log_project_activity & individual HITL confirmation cards in Telegram | integration | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_notion_git_hitl.py -q` | ❌ W0 | ⬜ pending |
| 07-04-01 | 04 | 4 | ALL (GIT, NTN) | T-07-03 | End-to-end composition, zero-drift persona tests and 100% Quality Gate | gate | `python3 /opt/chat-app/scripts/gate.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `/opt/assistant-core/tests/test_git_connector.py` — Stubs & test harness for SshGitProvider
- [ ] `/opt/assistant-core/tests/test_git_airgap_trap.py` — SpyGenAIClient trap for Git NDA Air-Gap
- [ ] `/opt/assistant-core/tests/test_notion_git_hitl.py` — Mock Notion API client & Telegram HITL flow test

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
