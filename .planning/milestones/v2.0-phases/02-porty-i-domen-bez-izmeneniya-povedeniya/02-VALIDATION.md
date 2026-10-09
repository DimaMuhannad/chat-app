---
phase: "2"
slug: "porty-i-domen-bez-izmeneniya-povedeniya"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-02"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = auto`) |
| **Config file** | `/opt/assistant-core/pytest.ini` (`testpaths = tests`, `pythonpath = .`) |
| **Quick run command** | `cd /opt/assistant-core && .venv/bin/pytest tests/test_core_domain.py tests/test_core_events.py tests/test_ports_conformance.py tests/test_composition_di.py tests/test_core_architecture.py tests/test_architecture_contract.py -q && .venv/bin/lint-imports --no-logo --no-cache` |
| **Full suite command** | `python3 /opt/chat-app/scripts/gate.py` (ожидается «ИТОГ: ЗЕЛЁНЫЙ», exit 0) |
| **Estimated runtime** | ~45 seconds (assistant-core), гейт целиком ~90 s |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run `python3 /opt/chat-app/scripts/gate.py`
- **Before `/gsd-verify-work`:** Full suite must be green; `git -C /opt/assistant-core diff --name-status <базовый>..HEAD -- tests/` без `M`/`D` для существующих файлов
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-xx | TBD | TBD | PRT-01 | — | N/A | unit | `.venv/bin/pytest tests/test_core_domain.py -q` | ❌ W0 | ⬜ pending |
| 2-xx | TBD | TBD | PRT-02, PRT-03 | — | `submit_grade` требует подтверждения (HITL) | unit | `.venv/bin/pytest tests/test_ports_conformance.py -q` | ❌ W0 | ⬜ pending |
| 2-xx | TBD | TBD | PRT-04 | — | N/A | unit + lint | `.venv/bin/pytest tests/test_composition_di.py tests/test_core_architecture.py -q && .venv/bin/lint-imports --no-logo --no-cache` | ❌ W0 | ⬜ pending |
| 2-xx | TBD | TBD | PRT-05 | — | N/A | unit (async) | `.venv/bin/pytest tests/test_core_events.py -q` | ❌ W0 | ⬜ pending |
| 2-xx | TBD | TBD | SC1 | — | N/A | gate | `python3 /opt/chat-app/scripts/gate.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs заполняются после планирования (см. 02-RESEARCH.md § Validation Architecture).*

---

## Wave 0 Requirements

- [ ] `tests/test_core_domain.py` — PRT-01 (+ D-05)
- [ ] `tests/test_core_events.py` — PRT-05
- [ ] `tests/test_ports_conformance.py` — PRT-02/03 (D-10)
- [ ] `tests/test_composition_di.py` — PRT-04, характеризационные тесты непокрытых путей пишутся ДО рефакторинга отдельным коммитом
- [ ] `tests/test_core_architecture.py` — `core-is-pure` в рантайме + «долг ignore_imports = 0»

Фреймворк и конфиг уже есть; установка не нужна.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
