---
phase: "3"
slug: "persona-kak-dannye"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-02"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1; assistant-core: pytest-asyncio 1.4.0 (`asyncio_mode = auto`); chat-app: `pytest.mark.anyio`, `ASGITransport` + `AsyncClient` |
| **Config file** | `/opt/assistant-core/pytest.ini`; chat-app: `backend/tests/conftest.py` (без `pytest.ini`) |
| **Quick run command** | assistant-core: `cd /opt/assistant-core && .venv/bin/pytest <файлы задачи> -q -p no:cacheprovider && .venv/bin/lint-imports --no-logo --no-cache`; chat-app: `cd /opt/chat-app && backend/.venv/bin/pytest <файлы задачи> -q -p no:cacheprovider` |
| **Full suite command** | `python3 /opt/chat-app/scripts/gate.py` (ожидается «ИТОГ: ЗЕЛЁНЫЙ») |
| **Estimated runtime** | ~60 seconds (быстрый набор), гейт — несколько минут |

Нижние границы числа тестов на старте фазы: assistant-core ≥ 223, chat-app ≥ 68; после каждой волны число только растёт.

---

## Sampling Rate

- **After every task commit:** быстрый набор своего репозитория + `lint-imports`
- **After every plan wave:** `python3 /opt/chat-app/scripts/gate.py`
- **Before `/gsd-verify-work`:** гейт зелёный, `docs/BASELINE.md` обновлён, сервисы не запускались, SHA-256 боевой БД равен стартовому
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Заполняется по планам (карта «требование → тест → команда» — в `03-RESEARCH.md`, раздел Validation Architecture).

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| PER-07 | Шаблон с дефолтной персоной = эталон побайтно | unit | `.venv/bin/pytest tests/test_prompt_snapshot.py -q` | ❌ W0 | ⬜ pending |
| PER-01 | Загрузка дефолта без `PERSONA_CONFIG_PATH`, strict, `extra=forbid` | unit | `.venv/bin/pytest tests/test_persona_loader.py -q` | ❌ W0 | ⬜ pending |
| PER-02 | Таблицы персон через `init_db()`, несколько привязок на роль | unit | `.venv/bin/pytest tests/test_persona_storage.py -q` | ❌ W0 | ⬜ pending |
| PER-03 | `/security/overview` из таблиц, 4 записи, без `PROJECTS_REGISTRY` | integration | `backend/.venv/bin/pytest backend/tests/test_security_api.py -q` | ✅ | ⬜ pending |
| PER-04 | NDA-чек-лист N01–N09, S01–S09, P01–P03, D01–D03 | integration | `backend/.venv/bin/pytest backend/tests/test_nda_equivalence.py -q` | ❌ W0 | ⬜ pending |
| PER-05 | `/persona/current`, `index.html` без токенов, дефолт области | integration + static | `backend/.venv/bin/pytest backend/tests/test_persona_api.py backend/tests/test_index_whitelabel.py -q` | ❌ W0 | ⬜ pending |
| PER-06 | Параметры коннекторов из привязок | unit | `.venv/bin/pytest tests/test_connector_params.py tests/test_composition_di.py -q` | ❌ W0 | ⬜ pending |
| PER-08 | Сканер хардкода с baseline-allowlist | unit | `tests/test_hardcode_scanner.py` (оба репозитория) | ❌ W0 | ⬜ pending |
| PER-09 | Синтетическая персона даёт другие результаты | integration | `.venv/bin/pytest tests/test_persona_config.py -q` | ❌ W0 | ⬜ pending |
| BCK-01 | 1:1 для персоны по умолчанию | сводный | `python3 /opt/chat-app/scripts/gate.py` | ✅ | ⬜ pending |
| BCK-02 | Переписанные тесты не слабее, ни один не удалён | диф-проверка | `git diff --name-status <база>..HEAD -- tests/` без `D` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/prompts_snapshot/*.txt` + `MANIFEST.json` + `tests/test_prompt_snapshot.py` — PER-07 (первый коммит фазы)
- [ ] характеризационный `backend/tests/test_nda_equivalence.py` на текущем коде — PER-04 (до замены реестра)
- [ ] эталон вывода `/security/overview` — PER-03
- [ ] `tests/test_persona_loader.py`, `test_persona_storage.py`, `test_persona_config.py`, `test_connector_params.py`, `test_nda_script_parity.py`, `test_hardcode_scanner.py` (assistant-core)
- [ ] `backend/tests/{test_persona_api,test_index_whitelabel,test_hardcode_scanner}.py`, фикстуры копии БД в `conftest.py`
- [ ] установка Jinja2 (чекпоинт), версии в `docs/BASELINE.md`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Установка Jinja2/MarkupSafe в venv | PER-07 | Пакетный аудит дал SUS («unknown downloads») | Владелец подтверждает установку через `checkpoint:human-verify` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
