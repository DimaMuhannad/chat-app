---
phase: 03-persona-kak-dannye
plan: 03
subsystem: persona
tags: [persona, yaml, pydantic, workspaces, nda, connectors, telegram-env, shield-exception, seed]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-02: загрузчик, таблицы personas/workspaces/connector_bindings, seed-CLI, /api/v1/persona/current"
provides:
  - "Полная схема персоны (extra=forbid): workspaces, name_forms, telegram, task_areas, ui.texts, connectors (6 ролей), methodist, prompts"
  - "config/persona.yaml с полными данными владельца: 4 пространства, NDA-правила, привязки, области, тексты интерфейса, каталог методиста"
  - "current_persona(), use_persona(), reset_persona_cache(); PersonaConfig.to_domain(), unresolved_env_vars(), resolve_authorized_user_ids()"
  - "Засев персоны демоном после init_db(); persona_rows отдаёт пространства и привязки"
  - "Тест паритета P01 между правилами security_shield и данными персоны"
  - "Единственное исключение shield для config/persona.yaml (3 находки); закреплённое число 18"
affects: [03-04, 03-05, 03-06, 03-07, 03-08, 03-09, 03-10]

actuals:
  tokens: 11247
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Правила NDA как данные пространства с fail-closed валидацией (restricted_nda без обоих списков не загружается)"
    - "Идентификаторы Telegram только плейсхолдерами ${VAR}; разворачивание в момент вызова, пустое значение не попадает в результат"
    - "Тест сравнивает NDA-слова через булеву переменную: слова не попадают в вывод pytest"

key-files:
  created:
    - /opt/assistant-core/src/persona/current.py
    - /opt/assistant-core/tests/test_nda_script_parity.py
  modified:
    - /opt/assistant-core/config/persona.yaml
    - /opt/assistant-core/src/persona/models.py
    - /opt/assistant-core/src/persona/seed.py
    - /opt/assistant-core/src/core/domain/entities.py
    - /opt/assistant-core/src/main.py
    - /opt/assistant-core/tests/test_persona_loader.py
    - /opt/assistant-core/tests/test_persona_storage.py
    - scripts/gate.py
    - backend/tests/test_gate.py
    - docs/BASELINE.md

key-decisions:
  - "task_areas, methodist обязательны в схеме (а не необязательны с пустыми значениями): default_area должен входить в task_areas всегда, поэтому минимальные персоны в тестах получили эти блоки"
  - "Данные верхнего блока YAML (4 пространства с дословными строками реестра, 6 областей, 7 текстов, каталог из 7 файлов, оба списка слов методиста) перенесены скриптами из исходников (ast, импорт констант), а не набраны вручную"
  - "Раскрытие плейсхолдеров Telegram живёт в методах PersonaConfig, снимок config_json хранит плейсхолдер без отдельной логики"

requirements-completed: [PER-01, PER-04]

coverage:
  - id: E1
    description: "restricted_nda без forbidden_remote_substrings или forbidden_keywords не загружается; дубли id пространств и повтор id привязки в роли отвергаются; значения clearance совпадают с WorkspaceClearance"
    requirement: "PER-04"
    verification:
      - kind: unit
        ref: "tests/test_persona_loader.py (test_restricted_nda_requires_rules x4, test_workspace_ids_unique, test_clearance_values_match_domain_enum)"
        status: pass
    human_judgment: false
  - id: E2
    description: "NDA-слова и подстрока remote в данных персоны равны правилам scripts/security_shield.py; слова в выводе не печатаются"
    requirement: "PER-04"
    verification:
      - kind: unit
        ref: "tests/test_nda_script_parity.py (2 passed)"
        status: pass
    human_judgment: false
  - id: E3
    description: "Telegram-ID в файле только плейсхолдеры; незаданная или пустая переменная никогда не становится пустой строкой; strict называет переменную; config_json хранит плейсхолдер"
    requirement: "PER-01"
    verification:
      - kind: unit
        ref: "tests/test_persona_loader.py::test_resolve_authorized_user_ids_never_returns_empty_string, tests/test_persona_storage.py::test_config_json_keeps_env_placeholders"
        status: pass
    human_judgment: false
  - id: E4
    description: "Привязки 6 ролей (git_source и notion пустые), несколько на роль, position внутри роли; засев пространств в порядке реестра"
    requirement: "PER-02"
    verification:
      - kind: unit
        ref: "tests/test_persona_storage.py::test_multiple_bindings_per_role_are_stored, test_seed_writes_workspaces_in_order"
        status: pass
    human_judgment: false
  - id: E5
    description: "Гейт ЗЕЛЁНЫЙ с одной новой одобренной записью shield; число известных находок 18 закреплено тестом"
    requirement: "PER-04"
    verification:
      - kind: other
        ref: "python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ; backend/tests/test_gate.py::test_known_shield_false_positives_total_is_eighteen"
        status: pass
    human_judgment: false

plan_head_before: 5f4b3de0b9b0979fe274f401d23fb11cc4257707
plan_head_after: ff1c871e3ca1f9a358816215d80c72a9a52a2929
plan_head_before_core: ec28d69e7b9a0c6e2642912bae334277ebfab5c3
plan_head_after_core: d4fbefb67ae067072c22ac8b4ece085d740e04d1
duration: 9min
completed: 2026-10-02
status: complete
---

# Phase 3 Plan 03: полная схема персоны и данные владельца Summary

**Схема персоны утверждена целиком (4 рабочих пространства с NDA-правилами, 6 ролей коннекторов с несколькими привязками, Telegram только плейсхолдерами `${VAR}`, 6 областей задач, 7 текстов интерфейса, формы имени, каталог методиста), `config/persona.yaml` содержит все сегодняшние значения владельца, демон засевает персону в БД при старте, shield получил одно одобренное исключение (18 известных находок).**

## Performance

- **Duration:** около 9 мин
- **Tasks:** 2 из 2
- **Репозитории:** assistant-core (`main`, 2 коммита) и chat-app (`master`, 1 коммит), без push

## Accomplishments

- NDA-правила стали данными пространства: `WorkspaceConfig` для `restricted_nda` требует и `forbidden_remote_substrings`, и `forbidden_keywords`; пустые данные не могут молча выключить блокировку (fail-closed, T-03-09). Тест P01 сверяет слова и подстроку remote с `scripts/security_shield.py`; слова в вывод не попадают.
- Идентификаторы Telegram: литерал числа отвергается валидатором, `resolve_authorized_user_ids` разворачивает `${TELEGRAM_USER_ID}` в момент вызова (пропуск пустого и незаданного, strict называет переменную, нечисловое отвергается). Снимок `personas.config_json` хранит плейсхолдер (T-03-10, T-03-12).
- Данные владельца: 4 пространства в порядке реестра с дословными строками, 6 областей (две подписи, `Финансы` вне фильтра), 7 текстов интерфейса (каждый найден в `index.html` дословно), 9 форм имени, привязки `schedule_source` (слоты 09:30..20:20, 4 предмета), `calendar_sync`, `timesheet` (норма 8.5), `lms`, каталог методиста (7 файлов, оба списка слов, причина отказа). Значения извлечены из исходников скриптами.
- `current_persona()` читает персону при вызове с кэшем по пути, `use_persona()` подменяет через `ContextVar`, `reset_persona_cache()` перечитывает файл. `ConnectorRole` расширен до 6 членов (`git_source`, `notion` только объявлены).
- `main.py` после `init_db()` вызывает `seed_persona(db, current_persona())` и логирует только id и числа; незаданные переменные окружения персоны попадают в `warning` по именам. Боевая БД при выполнении плана не затрагивалась (сервисы не запускались).
- Исключение shield: `("config/persona.yaml", "nda-keyword"): 3` с комментарием о решении владельца (OQ1) в `gate.py`; число известных находок 15 -> 18, тест переименован; `BASELINE.md` отражает таблицу (chat-app 6, assistant-core 12, всего 18) и правило 4.

## Task Commits

1. **Задача 1, assistant-core:** `3a6e6b1` (feat) - `WorkspaceConfig`, 4 пространства в `persona.yaml`, seed, тест паритета P01
2. **Задача 1, chat-app:** `ff1c871` (feat) - запись исключения shield, тест на 18, `BASELINE.md`
3. **Задача 2, assistant-core:** `d4fbefb` (feat) - полная схема, `current.py`, `entities.py`, `main.py`, данные владельца, тесты

Метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS, WINDOWS) коммитятся в chat-app отдельно. Между `3a6e6b1` и `ff1c871` гейт был бы красным (новая находка shield), поэтому гейт запускался только после обоих.

## TDD-заметка

Тесты Задач 1 и 2 писались вместе с реализацией, поэтому красной фазы отдельным прогоном не было (как и в 03-02). Покрытие поведения проверялось по сценариям `<behavior>`: отказ restricted_nda при каждом из 4 вариантов отсутствия правил, литерал Telegram-ID, пустые значения окружения, дубли id, расхождение `default_area`, подмена и сброс кэша.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Минимальные персоны в существующих тестах**
- **Found during:** Задача 2 (после введения обязательных `task_areas` и `methodist`)
- **Issue:** `MINIMAL_TEMPLATE` в `test_persona_loader.py` и встроенная персона в `test_seed_cli_uses_persona_config_argument` не содержали обязательных блоков и перестали загружаться.
- **Fix:** в оба шаблона добавлены `task_areas` из одной области и минимальный `methodist`; ассерты не менялись.
- **Files modified:** /opt/assistant-core/tests/test_persona_loader.py, /opt/assistant-core/tests/test_persona_storage.py
- **Commit:** d4fbefb

**2. [Rule 1 - Bug] Собственный тест Задачи 1 после появления привязок**
- **Found during:** Задача 2
- **Issue:** `test_seed_writes_workspaces_in_order` (Задача 1) утверждал `binding_rows == []`, что верно было только до заполнения привязок.
- **Fix:** утверждение заменено на проверку списка ролей привязок по умолчанию.
- **Commit:** d4fbefb

### Уточнения без отклонения от смысла плана

- Первая генерация блока данных в `persona.yaml` (flow-стиль) дала плохо читаемый файл и из-за неверного маркера дублировала блок; файл восстановлен из коммита и сгенерирован заново в блочном стиле. Итоговый файл разобран и сверен с данными исходных скриптов.
- Тесты `test_restricted_nda_requires_rules` параметризованы (4 варианта), поэтому тестов больше, чем строк в плане: assistant-core 266 (было 247), chat-app 70.
- Делегирование agy не использовалось: объём малый, значения извлекались скриптами прямо из исходников.

**Total deviations:** 2 auto-fixed (Rule 3, Rule 1, обе в тестах). **Impact:** на артефакты плана не влияет.

## Authentication Gates

None.

## Verification Results

- `tests/test_persona_loader.py`, `test_persona_storage.py`, `test_nda_script_parity.py`, `test_core_domain.py`, `test_ports_conformance.py`: 77 passed (три первых файла: 23 на конец Задачи 1).
- Гейт `python3 /opt/chat-app/scripts/gate.py`: ИТОГ ЗЕЛЁНЫЙ после Задачи 1 (assistant-core 257, chat-app 70) и после Задачи 2 (assistant-core 266, chat-app 70); `lint-imports`: 5 kept, 0 broken; shield `--all`, дрейф синтетической персоны, неизменность боевой БД зелёные.
- Порядок пространств и clearance `['chat-app','assistant-core','tydex-optics','guap-physics']` / `['public','public','restricted_nda','internal']`; в `persona.yaml` 3 находки shield по NDA-словам, как в записи исключения.
- `grep -nE '[0-9]{6,}' config/persona.yaml` пусто; `${TELEGRAM_USER_ID}` присутствует.
- Тексты интерфейса и подписи областей найдены в `index.html` дословно (проверка скриптом, все 7 + 6 + 5).
- Гигиена секретов (`check_file_content`) для `models.py`, `current.py`, `seed.py`, `entities.py`, `main.py` и трёх тестов: нарушений 0.
- NDA-слова не печатались в консоль, коммит-сообщения и этот документ.
- Сервисы не запускались: assistant-worker `failed`, chat-app и dev-bridge `inactive`, как и до плана.

## Threat Model Status

- T-03-09 (сужение NDA-правил): митигирована - валидатор требует оба списка, P01 сверяет с скриптом; полный чек-лист N/S/P/D в 03-05.
- T-03-10 (подмена Telegram-ID): митигирована - только плейсхолдеры, пустое значение не превращается в строку, `bot_handler` не менялся.
- T-03-11 (NDA-слова в выводе): митигирована - булевы сравнения, ошибки загрузчика без значений.
- T-03-12 (ID в `config_json`): митигирована - тест `test_config_json_keeps_env_placeholders`.
- T-03-13 (тихое расширение списка shield): митигирована - одна запись, число 18 закреплено тестом, срок снятия записан в BASELINE.
- T-03-SC: установок пакетов не было.

## Known Stubs

None. Заглушка `persona_rows` из 03-02 закрыта (запись WINDOWS.md 1 отмечена исправленной).

## Threat Flags

None.

## Next Phase Readiness

Схема утверждена целиком: 03-04 загружает вторую персону на этой схеме, 03-05 делает полный чек-лист NDA, 03-06..03-09 только потребляют поля. Боевая БД получит персону при следующем запуске демона (решение владельца о разморозке). Блокеров нет.

## Self-Check: PASSED

- Файлы `current.py`, `test_nda_script_parity.py`, обновлённые `persona.yaml`, `models.py`, `seed.py`, `main.py` найдены на диске.
- Коммиты 3a6e6b1, d4fbefb (assistant-core) и ff1c871 (chat-app) найдены в `git log`.
- Измеренное число коммитов плана: 3 (chat-app 1 по `5f4b3de..HEAD`, assistant-core 2 по `ec28d69..HEAD`).
