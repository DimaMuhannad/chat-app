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

Заполнено планировщиком по 01-01..01-04-PLAN.md. Команды chat-app выполняются из `/opt/chat-app`. Волны последовательные (01 → 02 → 03 → 04): планы делят `scripts/gate.py`, `backend/tests/test_gate.py`, `docs/BASELINE.md` и проверяются полным прогоном двух pytest (ограничение 2 ГБ ОЗУ).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | FND-01, FND-04 | T-01-01, T-01-02, T-01-03, T-01-05, T-01-06 | pytest chat-app только на копии БД; SHA-256 боевой БД до/после; 0 тестов/skip/xfail/deselect = красный; красный путь без трассировки | gate (e2e) + unit | `bash -o pipefail -c 'python3 scripts/gate.py \| grep -F "ИТОГ: ЗЕЛЁНЫЙ"'`; `ASSISTANT_CORE_DIR=/nonexistent python3 scripts/gate.py` → код 1; `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_gate.py -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | FND-02 (пререквизит) | T-01-SC | пакеты SUS одобрены владельцем до установки | checkpoint (blocking-human) | — (решение владельца) | — | ⬜ pending |
| 1-01-03 | 01 | 1 | FND-01, FND-04 | T-01-SC, T-01-04 | установлены ровно import-linter 2.15 / grimp 3.17; BASELINE без секретов, с разделом «Правила» | env + doc | `/opt/chat-app/backend/.venv/bin/python -c "…m.version('import-linter')…"` (и в assistant-core); проверка гигиены `check_file_content` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | FND-02, FND-04 | T-01-07, T-01-08 | контракт не «пустой» (страж графа); падает на синтетическом нарушении и на копии реального кода; долг ≤ 5 | lint + unit + gate | `cd /opt/assistant-core && .venv/bin/lint-imports --no-logo --no-cache` («2 kept, 0 broken»); `cd /opt/assistant-core && .venv/bin/pytest tests/test_architecture_contract.py -q` (5 passed) | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | FND-02, FND-04 | T-01-07, T-01-09 | app ↛ src; страж графа; падает на внедрённом импорте src; долг = 0 | lint + unit + gate | `PYTHONPATH=backend /opt/chat-app/backend/.venv/bin/lint-imports --no-logo --no-cache` («1 kept, 0 broken»); `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_architecture_contract.py backend/tests/test_gate.py -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 3 | FND-03 | T-01-11, T-01-12 | без токенов владельца, e-mail и реальных NDA-слов; каждое поле отличается от хардкода; ровно 3 clearance; без skip/xfail | unit + gate | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_synthetic_persona.py -q` (7 passed) | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 3 | FND-03, FND-04 | T-01-13 | копии персоны байт-в-байт; дрейф SHA-256 ловит гейт | unit + gate | `cmp` трёх пар файлов; `cd /opt/assistant-core && .venv/bin/pytest tests/test_synthetic_persona.py -q` (7 passed); гейт со строкой «дрейф SHA-256» | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 4 | FND-04 | T-01-14, T-01-15, T-01-16 | вывод shield (remote, e-mail, текст NDA-слов) не печатается; новая/устаревшая находка или сбой = красный | unit + gate | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_gate.py -q`; гейт с двумя строками «security_shield» и без remote/e-mail в выводе | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 4 | FND-04 | T-01-15 | режим shield выбран владельцем | checkpoint:decision (blocking-human) | — (решение владельца) | — | ⬜ pending |
| 1-04-03 | 04 | 4 | FND-04, FND-01 | T-01-17 | финальный гейт: 8 строк ✓; продакшен-код не изменён; сервисы не active; SHA-256 боевой БД = стартовому; CLAUDE.md +1 строка | gate + git + doc | `python3 scripts/gate.py`; `git log 7925190..HEAD -- backend/app` и `git -C /opt/assistant-core log 6e0850b..HEAD -- src` пусты; `/usr/bin/systemctl is-active` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `/opt/chat-app/scripts/gate.py`, `/opt/chat-app/backend/tests/test_gate.py`, `/opt/chat-app/docs/baseline/*.txt` (план 01-01, задача 1)
- [ ] `requirements-dev.txt` в обоих репозиториях, установка import-linter 2.15 / grimp 3.17 в оба `.venv` после чекпойнта владельца (вердикт SUS), `/opt/chat-app/docs/BASELINE.md` (план 01-01, задачи 2–3)
- [ ] `.importlinter` и `test_architecture_contract.py` в обоих репозиториях (план 01-02)
- [ ] `{conftest.py, synthetic_persona.py, test_synthetic_persona.py}` в `backend/tests/` и `/opt/assistant-core/tests/` (план 01-03)
- [ ] шаг shield в гейте и тесты разбора его вывода в `test_gate.py` (план 01-04)

---

## Manual-Only Verifications

Ручная проверка «контракт падает на реальном коде» заменена автоматическим `test_real_contract_fails_on_injected_violation` (копия реального пакета во временном каталоге + внедрённый запрещённый импорт), а «гейт даёт КРАСНЫЙ» — автоматической командой задачи 1-01-01 (`ASSISTANT_CORE_DIR=/nonexistent`).

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Установка import-linter и grimp (SUS) | FND-02 | Решение владельца о supply chain | Чекпойнт 1-01-02 (`checkpoint:human-verify`, gate="blocking-human") перед `pip install` |
| Режим запуска security_shield в гейте | FND-04 | Политика безопасности — решение владельца | Чекпойнт 1-04-02 (`checkpoint:decision`, gate="blocking-human") |
| Изменение CLAUDE.md (одна строка) | FND-04 | Файл инструкций агентов, ревью владельца (D-05) | Проверить строку «Run Quality Gate» в SUMMARY 01-04 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
