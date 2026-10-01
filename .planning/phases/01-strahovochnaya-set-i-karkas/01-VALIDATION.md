---
phase: "01"
slug: "strahovochnaya-set-i-karkas"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-01"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (chat-app: плагин anyio; assistant-core: pytest-asyncio, `asyncio_mode = auto`) |
| **Config file** | chat-app: нет (`rootdir=/opt/chat-app`); assistant-core: `/opt/assistant-core/pytest.ini` |
| **Quick run command** | chat-app: `cd /opt/chat-app && SQLITE_DB_PATH=<копия> backend/.venv/bin/pytest backend/tests/test_synthetic_persona.py backend/tests/test_architecture_contract.py -q`; assistant-core: `cd /opt/assistant-core && .venv/bin/pytest tests/test_synthetic_persona.py tests/test_architecture_contract.py -q` |
| **Full suite command** | `python3 /opt/chat-app/scripts/gate.py` (после появления гейта); до этого — две команды из CLAUDE.md |
| **Estimated runtime** | ~60 seconds (chat-app ≈2 с, assistant-core ≈45 с) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (быстрые тесты нового файла + соответствующий шаг гейта)
- **After every plan wave:** Run full gate (`python3 /opt/chat-app/scripts/gate.py`)
- **Before `/gsd-verify-work`:** Full gate must be «ЗЕЛЁНЫЙ»
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Заполняется планировщиком по итоговым PLAN.md; исходная карта требований:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-xx-xx | — | — | FND-01 | T-1-xx | боевая БД не изменена (SHA-256 до/после) | gate | `python3 /opt/chat-app/scripts/gate.py` | ❌ W0 | ⬜ pending |
| 1-xx-xx | — | — | FND-02 | T-1-xx | контракт не «пустой» (все модули контракта есть в графе) | unit | `…/pytest …/test_architecture_contract.py -q` | ❌ W0 | ⬜ pending |
| 1-xx-xx | — | — | FND-02 | — | контракт падает на нарушении, зелёный на чистом пакете | unit | `…/pytest …/test_architecture_contract.py -q` | ❌ W0 | ⬜ pending |
| 1-xx-xx | — | — | FND-03 | T-1-xx | персона без токенов владельца, отличается от дефолта, ровно 3 clearance | unit | `…/pytest …/test_synthetic_persona.py -q` | ❌ W0 | ⬜ pending |
| 1-xx-xx | — | — | FND-04 | — | итог «ЗЕЛЁНЫЙ»/«КРАСНЫЙ», код возврата 0/1 | unit | `backend/.venv/bin/pytest backend/tests/test_gate.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `/opt/chat-app/scripts/gate.py`, `/opt/chat-app/docs/BASELINE.md`, `/opt/chat-app/docs/baseline/*.txt`
- [ ] `.importlinter` и `requirements-dev.txt` в обоих репозиториях; установка `import-linter` в оба `.venv` (чекпойнт человека, вердикт SUS)
- [ ] `backend/tests/{conftest.py, synthetic_persona.py, test_synthetic_persona.py, test_architecture_contract.py}` и аналоги в `/opt/assistant-core/tests/`
- [ ] `backend/tests/test_gate.py` — чистые функции: агрегирование итога, разбор вывода shield, сравнение хешей

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Контракт доказанно падает на реальном коде | FND-02 | Требует временной правки `ignore_imports` | Временно убрать одну запись `ignore_imports` → `lint-imports` красный → вернуть; записать в SUMMARY |
| Гейт даёт «КРАСНЫЙ» при красном шаге | FND-04 | Нужно намеренно сломать шаг | `ASSISTANT_CORE_DIR=/nonexistent python3 scripts/gate.py` → итог «КРАСНЫЙ», код 1 |
| Установка import-linter (SUS) | FND-02 | Решение владельца о supply chain | Чекпойнт `human-verify` перед `pip install` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
