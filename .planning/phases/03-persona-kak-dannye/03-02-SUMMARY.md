---
phase: 03-persona-kak-dannye
plan: 02
subsystem: persona
tags: [persona, yaml, pydantic, sqlite, seed-cli, import-linter, fastapi, tracer]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-01: эталоны системных промптов (src/ не менялся)"
provides:
  - "config/persona.yaml с персоной popov-da-default и пакет src/persona (модели extra=forbid, загрузчик на safe_load, seed-CLI)"
  - "таблицы personas, workspaces, connector_bindings в Database.init_db() и методы upsert_persona (атомарный), get_persona_record, list_persona_workspaces, list_connector_bindings"
  - "контракт import-linter persona-is-leaf (5 контрактов)"
  - "GET /api/v1/persona/current (белый список, 503 без персоны), DatabaseService.get_persona, Settings.PERSONA_ID"
  - "сессионная фикстура persona_session_db: копия БД из mode=ro, засеянная seed-CLI"
affects: [03-03, 03-04, 03-05, 03-06, 03-07, 03-08, 03-09, 03-10]

actuals:
  tokens: 8533
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Один загрузчик YAML (assistant-core), chat-app читает только таблицы общей БД"
    - "Тесты chat-app работают на копии БД с засеянной персоной; боевая БД не открывается на запись"
    - "Отказ seed-CLI на боевом пути до создания Database"

key-files:
  created:
    - /opt/assistant-core/config/persona.yaml
    - /opt/assistant-core/src/persona/__init__.py
    - /opt/assistant-core/src/persona/models.py
    - /opt/assistant-core/src/persona/loader.py
    - /opt/assistant-core/src/persona/seed.py
    - /opt/assistant-core/tests/test_persona_loader.py
    - /opt/assistant-core/tests/test_persona_storage.py
    - backend/app/api/v1/persona.py
    - backend/tests/test_persona_api.py
  modified:
    - /opt/assistant-core/src/storage/db.py
    - /opt/assistant-core/.importlinter
    - /opt/assistant-core/requirements.txt
    - backend/app/core/config.py
    - backend/app/db.py
    - backend/app/api/v1/router.py
    - backend/tests/conftest.py

key-decisions:
  - "seed-CLI сначала загружает и проверяет файл персоны, и только потом открывает БД: сбой файла не оставляет следов в БД (уточнение порядка шагов плана)"
  - "persona_public_view принимает снимок и с обёрткой persona, и плоский (model_dump_json хранит плоский вид)"
  - "Требование PER-02 закрыто полностью; PER-01, PER-05 и BCK-01 остаются открытыми до следующих планов фазы"

requirements-completed: [PER-02]

coverage:
  - id: C1
    description: "Персона по умолчанию грузится из config/persona.yaml без PERSONA_CONFIG_PATH; переменная и явный путь подменяют файл; схема строгая, YAML безопасный, ошибки без значений"
    requirement: "PER-01"
    verification:
      - kind: unit
        ref: "tests/test_persona_loader.py (6 passed)"
        status: pass
    human_judgment: false
  - id: C2
    description: "Три таблицы создаёт init_db(); загрузка идемпотентна и атомарна; пользовательские таблицы не затрагиваются; seed-CLI отказывает на боевой БД"
    requirement: "PER-02"
    verification:
      - kind: unit
        ref: "tests/test_persona_storage.py (7 passed)"
        status: pass
    human_judgment: false
  - id: C3
    description: "GET /api/v1/persona/current отдаёт только белый список из таблицы копии БД; без строки отвечает 503"
    requirement: "PER-05"
    verification:
      - kind: unit
        ref: "backend/tests/test_persona_api.py (2 passed)"
        status: pass
    human_judgment: false
  - id: C4
    description: "Боевая assistant.db не менялась (SHA-256 726c4e99...), гейт ЗЕЛЁНЫЙ: assistant-core 247, chat-app 70, lint-imports 5 kept"
    requirement: "BCK-01"
    verification:
      - kind: other
        ref: "python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ"
        status: pass
    human_judgment: false

plan_head_before: b491005116493d4a1a65b880058513333a5cc488
plan_head_after: f2fe4d7f2126d9fdbaa24f687363e42cb2d9914c
plan_head_before_core: caf4789d163810b9d52d39bb92b8af26b708003b
plan_head_after_core: ec28d69e7b9a0c6e2642912bae334277ebfab5c3
duration: 10min
completed: 2026-10-02
status: complete
---

# Phase 3 Plan 02: сквозной путь персоны (tracer) Summary

**Персона popov-da-default проходит путь config/persona.yaml, Pydantic-загрузчик (safe_load, extra=forbid), таблицы personas/workspaces/connector_bindings из init_db(), seed-CLI, копия БД в тестах chat-app, DatabaseService и GET /api/v1/persona/current; боевая БД не тронута, гейт зелёный.**

## Performance

- **Duration:** около 10 мин
- **Tasks:** 2 из 2
- **Репозитории:** assistant-core (`main`, 2 коммита) и chat-app (`master`, 1 коммит), без push

## Accomplishments

- Tracer прошёл все слои за один план: вопрос по D-04 владельцу не понадобился, путь «YAML в assistant-core, таблицы, chat-app» работает и под гейтом, и при ручном запуске pytest chat-app (фикстура копирует БД из `mode=ro`).
- Схема таблиц создана полностью (составной ключ `(persona_id, id)`, `position`, `account`, `clearance_label`, `remote`, `remote_violation_message`, `ON DELETE CASCADE`, 6 ролей привязок); наполнение пространств и привязок остаётся за 03-03.
- Контракт `persona-is-leaf` запрещает `src.persona` импортировать `src.config` и адаптеры; `src.persona` внесён в `core-is-pure`: `lint-imports` показывает «5 kept, 0 broken».
- Боевая БД: SHA-256 `726c4e9970b2352b4dab97842e4ea89f24938b807a5ac6744018bee781cb7168` до и после; seed-CLI на `data/assistant.db` вернул код 2.

## Task Commits

1. **Задача 1 (tracer), assistant-core:** `a138f0d` (feat) — persona.yaml, `src/persona/*`, DDL и методы в `db.py`, `.importlinter`, `requirements.txt`
2. **Задача 1 (tracer), chat-app:** `f2fe4d7` (feat) — `PERSONA_ID`, `get_persona`, `persona.py`, `router.py`, фикстура `persona_session_db`, `test_persona_api.py`
3. **Задача 2, assistant-core:** `ec28d69` (test) — `test_persona_loader.py` (6) и `test_persona_storage.py` (7)

Метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS, WINDOWS) коммитятся в chat-app отдельно.

## TDD-заметка (Задача 2)

Реализация загрузчика, хранилища и seed-CLI уже существовала после Задачи 1 (tracer), поэтому 13 тестов сразу прошли; красной фазы не было. Чтобы убедиться, что тесты не пустые, выполнена одноразовая мутация: убран `rollback()` в `upsert_persona` — `test_upsert_is_atomic_on_failure` упал; правка откатана через `git checkout -- src/storage/db.py`. Расхождений с Задачей 1, требующих правок `loader.py`, `seed.py`, `db.py`, тесты не вскрыли.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Тесты seed-CLI, вызывающие `main()` из async-теста**
- **Found during:** Задача 2, написание тестов
- **Issue:** `main()` вызывает `asyncio.run`, что нельзя из работающего цикла событий (`asyncio_mode = auto`).
- **Fix:** три теста seed-CLI сделаны синхронными, проверка БД через `asyncio.run(...)`. Утверждения не ослаблены.
- **Files modified:** /opt/assistant-core/tests/test_persona_storage.py
- **Commit:** ec28d69

### Уточнения без отклонения от смысла плана

- В `seed.py` `load_persona` вызывается до открытия БД (в плане после `init_db()`): неверный файл персоны не создаёт и не меняет БД.
- Явный `PERSONA_CONFIG_PATH` из пустой строки или пробелов трактуется как «не задана».
- Из 4 требований плана отмечено выполненным только PER-02. PER-01 (подстановка идентификаторов Telegram из окружения, D-05), PER-05 (поля интерфейса, 03-06) и BCK-01 (поведение 1:1 по всей фазе) требуют следующих планов; план сам помечает PER-05 как «срез».
- Делегирование agy не использовалось (архитектурный срез, D-20).

**Total deviations:** 1 auto-fixed (Rule 1, только в тестах). **Impact:** на артефакты плана не влияет.

## Authentication Gates

None.

## Verification Results

- `load_persona()` без `PERSONA_CONFIG_PATH`: `id == popov-da-default`, источник `config/persona.yaml`.
- `lint-imports` assistant-core: «Contracts: 5 kept, 0 broken».
- `backend/tests/test_persona_api.py`: 2 passed. `tests/test_persona_loader.py` + `tests/test_persona_storage.py`: 13 passed.
- Гейт `python3 /opt/chat-app/scripts/gate.py`: ИТОГ ЗЕЛЁНЫЙ после каждой задачи; итог: assistant-core 247 тестов (было 234, +13), chat-app 70 (было 68, +2); import-linter, security_shield (--all), дрейф синтетической персоны, неизменность боевой БД зелёные.
- Критерии приёмки: нет импортов `src.config` в `src/persona`; нет YAML в chat-app (`backend/app`, `backend/tests`, `backend/requirements.txt`); `pyyaml>=6.0` в `requirements.txt`; гигиена секретов (`check_file_content`) — нарушений 0 для всех новых файлов; существующие тесты assistant-core не изменены (в `tests/` только добавления).
- Сервисы не запускались: assistant-worker `failed`, chat-app и dev-bridge `inactive`, как и до плана.

## Threat Model Status

- T-03-04 (запись в боевую БД): митигирована — отказ CLI (код 2, `test_seed_cli_refuses_live_db`), фикстура на копии из `mode=ro`, строка гейта о неизменности БД.
- T-03-05 (исполнение кода из YAML): митигирована — только `yaml.safe_load`, `test_unsafe_yaml_tag_rejected`.
- T-03-06 (раскрытие через API): митигирована — `persona_public_view` с явным белым списком, тест на множество ключей.
- T-03-07 (значения в текстах ошибок): митигирована — только loc и msg, `test_unknown_key_rejected_without_echoing_value`.
- T-03-08 (нет таблицы): митигирована — `OperationalError` даёт `None` и 503.
- T-03-SC: установок пакетов не было.

## Known Stubs

- `/opt/assistant-core/src/persona/seed.py`, `persona_rows`: возвращает два пустых списка намеренно; рабочие пространства и привязки коннекторов заполняет план 03-03. Занесено в `.planning/WINDOWS.md`.

## Threat Flags

None (новый сетевой маршрут `/api/v1/persona/current` предусмотрен моделью угроз, T-03-06).

## Next Phase Readiness

Таблицы, загрузчик, seed-CLI и фикстура готовы для 03-03 (рабочие пространства, NDA-правила и привязки в данных персоны и в `persona_rows`). Блокеров нет. Побочный эффект для владельца: ручной запуск pytest chat-app по CLAUDE.md больше не пишет в боевую БД.

## Self-Check: PASSED

- Файлы: все созданные файлы найдены на диске.
- Коммиты a138f0d, ec28d69 (assistant-core) и f2fe4d7 (chat-app) найдены в `git log`.
- Измеренное число коммитов плана: 3 (chat-app 1 по `b491005..HEAD`, assistant-core 2 по `caf4789..HEAD`).
