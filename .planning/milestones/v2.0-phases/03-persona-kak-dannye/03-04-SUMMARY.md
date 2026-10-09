---
phase: 03-persona-kak-dannye
plan: 04
subsystem: persona
tags: [persona, synthetic-persona, converter, persona-tokens, gate, drift-sha256, test-db]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-03: полная схема персоны, load_persona, seed-CLI, фикстура persona_session_db, /persona/current"
provides:
  - "synthetic_to_config() и SYNTHETIC_TELEGRAM_ENV в обеих байт-в-байт копиях synthetic_persona.py (stdlib, без импортов)"
  - "БД тестов chat-app с двумя персонами (по умолчанию и синтетической) через тот же seed-CLI"
  - "persona_tokens.py (пара копий): owner_tokens(config) и token_classes_in_line(line, tokens)"
  - "Строка гейта «токены персоны (дрейф SHA-256)»; persona_drift_check(..., name=...)"
affects: [03-05, 03-06, 03-07, 03-08, 03-09, 03-10]

actuals:
  tokens: 9094
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Вторая персона проходит те же load_persona / seed-CLI / DatabaseService без ветвления по id"
    - "Токены профиля вычисляются из данных персоны одной функцией; пара копий под контролем SHA-256"

key-files:
  created:
    - backend/tests/persona_tokens.py
    - /opt/assistant-core/tests/persona_tokens.py
  modified:
    - backend/tests/synthetic_persona.py
    - /opt/assistant-core/tests/synthetic_persona.py
    - backend/tests/conftest.py
    - backend/tests/test_persona_api.py
    - /opt/assistant-core/tests/test_persona_loader.py
    - scripts/gate.py
    - backend/tests/test_gate.py

key-decisions:
  - "Конвертер приспосабливается к схеме, словарь SYNTHETIC_PERSONA и test_synthetic_persona.py Фазы 1 не тронуты (D-06)"
  - "persona_drift_check получил необязательный параметр name; подсказка о синхронизации строится из путей аргументов (для прежней пары текст не изменился)"
  - "owner_tokens принимает как корень persona, так и плоский словарь полей (форма model_dump и config_json)"

requirements-completed: [PER-09, PER-08, BCK-01]

coverage:
  - id: F1
    description: "Синтетическая персона загружается из YAML и JSON теми же кодовыми путями, модели равны; Telegram-плейсхолдер разворачивается в 100000001 при заданной переменной и в пусто без неё; слоты уроков преобразованы в [{number,start,end}]"
    requirement: "PER-09"
    verification:
      - kind: unit
        ref: "/opt/assistant-core/tests/test_persona_loader.py::test_synthetic_persona_loads_from_yaml_via_env, ::test_synthetic_persona_loads_from_json"
        status: pass
    human_judgment: false
  - id: F2
    description: "В БД тестов chat-app две персоны; /persona/current для синтетической отдаёт её имя и область, отличные от персоны по умолчанию"
    requirement: "PER-09"
    verification:
      - kind: unit
        ref: "backend/tests/test_persona_api.py::test_synthetic_persona_current_differs"
        status: pass
    human_judgment: false
  - id: F3
    description: "Токены профиля из данных персоны по умолчанию покрывают весь прежний denylist Фазы 1 (8 строк)"
    requirement: "PER-08"
    verification:
      - kind: other
        ref: "команда из verify Задачи 2 (owner_tokens(load_persona()) покрывает 8 строк denylist), код 0"
        status: pass
    human_judgment: false
  - id: F4
    description: "Гейт следит за дрейфом обеих пар; прежняя строка и её тесты не изменены"
    requirement: "BCK-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_gate.py::test_persona_drift_check_uses_given_name, ::test_gate_checks_persona_tokens_pair (44 passed)"
        status: pass
      - kind: other
        ref: "python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ, обе строки дрейфа присутствуют"
        status: pass
    human_judgment: false

plan_head_before: ddabba16809ad3f3edba084c6b140a75d0d2198e
plan_head_after: 32df7eca1d38e183dfc846a8080a9d6e4f876edd
plan_head_before_core: d4fbefb67ae067072c22ac8b4ece085d740e04d1
plan_head_after_core: cfb829a2d432de8a4e00dcacfb2d77813b0a646d
duration: 8min
completed: 2026-10-03
status: complete
---

# Phase 3 Plan 04: вторая синтетическая персона на тех же путях и токены профиля из данных Summary

**`synthetic_to_config()` превращает словарь каркаса Фазы 1 в структуру `persona.yaml`, вторая персона засевается в БД тестов chat-app тем же seed-CLI, а `owner_tokens()` вычисляет токены профиля владельца из данных персоны; обе пары файлов под контролем гейта.**

## Performance

- **Duration:** около 8 мин
- **Tasks:** 2 из 2
- **Репозитории:** assistant-core (`main`, 2 коммита) и chat-app (`master`, 2 коммита), без push

## Accomplishments

- В обеих копиях `synthetic_persona.py` (байт-в-байт, `cmp` совпал) добавлены `SYNTHETIC_TELEGRAM_ENV` и `synthetic_to_config(d, prompts=None)`; модуль остался без импортов, `SYNTHETIC_PERSONA` не изменён (в диффе с базовой точкой нет ни одной удалённой строки).
- Фикстура `persona_session_db` засевает БД копии дважды: персона по умолчанию, затем синтетическая из временного JSON через `--persona-config`. Константа `SYNTHETIC_PERSONA_ID` добавлена в conftest.
- Тесты: YAML через `PERSONA_CONFIG_PATH`, JSON и равенство `model_dump()`; разворачивание Telegram-плейсхолдера с переменной и без неё; `/persona/current` для синтетической персоны.
- `persona_tokens.py`: классы `name`, `organization`, `account`, `path`, `domain`; токены короче 3 символов отбрасываются, сравнение через `casefold`. Для персоны по умолчанию набор включает ГУАП, GUAP, Тидекс, Tydex, Попов, Дмитрий Александрович, DimaMuhannad, guap.ru, оба закрытых пути и бот.
- Гейт: `CHAT_TOKENS`/`CORE_TOKENS`, параметр `name` у `persona_drift_check`, новая строка «токены персоны (дрейф SHA-256)» после прежней строки.

## Task Commits

1. **Задача 1, assistant-core:** `9c2b3c7` (feat) - конвертер и два теста загрузки
2. **Задача 1, chat-app:** `65fa76e` (feat) - копия `synthetic_persona.py`, conftest, тест API
3. **Задача 2, assistant-core:** `cfb829a` (feat) - `persona_tokens.py`
4. **Задача 2, chat-app:** `32df7ec` (feat) - `persona_tokens.py`, гейт, два теста гейта

Метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS) коммитятся в chat-app отдельно. Измеренное число коммитов: chat-app 2 (`ddabba1..HEAD`), assistant-core 2 (`d4fbefb..HEAD`).

## TDD-заметка

Задача 1 помечена `tdd="true"`, но тесты и конвертер писались вместе (как в 03-02 и 03-03): красной фазы отдельным прогоном и отдельным коммитом не было. Поведение из `<behavior>` покрыто тестами (YAML, JSON, равенство моделей, плейсхолдер с переменной и без, слоты, API).

## Deviations from Plan

None - plan executed exactly as written.

Уточнения без отклонения от смысла: для `persona_drift_check` добавлен вспомогательный `_rel_to`, чтобы подсказка о синхронизации строилась из путей аргументов (для прежней пары текст остался дословно прежним); отдельные тесты на `owner_tokens` не добавлялись (в плане не предусмотрены, первые потребители - 03-06 и 03-10; сейчас функция проверена командой покрытия denylist).

## Authentication Gates

None.

## Verification Results

- `cmp` для `synthetic_persona.py` и `persona_tokens.py`: копии совпадают.
- `backend/tests/test_persona_api.py` + `test_synthetic_persona.py`: 10 passed (порог 9); `test_gate.py`: 44 passed (порог 44); assistant-core `test_persona_loader.py` + `test_synthetic_persona.py`: 29 passed.
- Покрытие прежнего denylist Фазы 1 данными персоны: код 0.
- Гейт `python3 scripts/gate.py`: **ИТОГ: ЗЕЛЁНЫЙ**; chat-app 73 теста, assistant-core 268; обе строки дрейфа ✓; `lint-imports` и shield `--all` ✓; боевая БД не изменена.
- `test_synthetic_persona.py` не изменялся (`git diff --quiet` с базовой точкой - код 0); в `test_gate.py` против базовой точки удалены только две строки из 03-03 (переименование теста на 18), прежние тесты дрейфа не менялись.
- Гигиена секретов (`check_file_content`) для `persona_tokens.py`, `gate.py`, `test_gate.py`, `synthetic_persona.py`: нарушений 0.
- Сервисы не запускались (assistant-worker `failed`, chat-app и dev-bridge `inactive`, как и до плана).

## Threat Model Status

- T-03-35 (дрейф копий): митигирована - две строки гейта, `cmp` в verify.
- T-03-36 (ослабление каркаса Фазы 1): митигирована - словарь и `test_synthetic_persona.py` не менялись.
- T-03-37 (токены в выводе): принята - токены профиля не секреты, NDA-слова в набор не входят (только пути и аккаунты).
- T-03-SC: установок пакетов не было.

## Known Stubs

None.

## Threat Flags

None.

## Next Phase Readiness

03-05 и далее могут обращаться к двум персонам в БД тестов chat-app и к `load_persona` на синтетическом файле; 03-06 (статика index.html) и 03-10 (сканер хардкода) берут токены из `owner_tokens`. Блокеров нет.

## Self-Check: PASSED

- Файлы `backend/tests/persona_tokens.py` и `/opt/assistant-core/tests/persona_tokens.py` найдены на диске.
- Коммиты `65fa76e`, `32df7ec` (chat-app) и `9c2b3c7`, `cfb829a` (assistant-core) найдены в `git log`.
