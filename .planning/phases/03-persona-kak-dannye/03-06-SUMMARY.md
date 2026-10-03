---
phase: 03-persona-kak-dannye
plan: 06
subsystem: web-ui
tags: [white-label, persona-api, index-html, default-area, whitelist, xss, node-check]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-02/03-03: таблица personas, /persona/current (базовый белый список), данные task_areas и ui.texts; 03-04: owner_tokens и вторая персона в БД тестов"
provides:
  - "/api/v1/persona/current: полный белый список (id, display_name, short_name, title, organizations{name}, default_area, task_areas[], ui.texts)"
  - "DatabaseService.resolve_default_area(), PersonaNotLoadedError и обработчик 503 в app/main.py"
  - "ProjectBase.area и TaskBase.area необязательны; пустая или отсутствующая область заменяется default_area персоны"
  - "index.html без токенов владельца: loadPersona/applyPersona, PERSONA_DEFAULT_AREA"
  - "test_index_whitelabel.py (6 тестов), 4 новых теста в test_persona_api.py, 2 в test_dashboard_api.py"
affects: [03-07, 03-08, 03-09, 03-10, phase-04, phase-06]

actuals:
  tokens: 15000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Публичное представление персоны - явное перечисление ключей, вложенные словари не копируются целиком"
    - "Нет персоны - 503 (одно исключение уровня БД и один обработчик), а не строка владельца"
    - "Данные персоны попадают в DOM только через textContent, setAttribute, createElement и Option"
    - "Проверка статики на токены профиля берёт их из данных персоны (owner_tokens), а не из списка в тесте"

key-files:
  created:
    - backend/tests/test_index_whitelabel.py
  modified:
    - backend/app/api/v1/persona.py
    - backend/app/db.py
    - backend/app/models/dashboard_schemas.py
    - backend/app/main.py
    - backend/app/static/index.html
    - backend/tests/test_persona_api.py
    - backend/tests/test_dashboard_api.py

key-decisions:
  - "Область по умолчанию берётся из персоны при создании (data.get('area') or resolve_default_area()); явно заданная область персоне не требует, существующие строки БД не трогаются"
  - "DDL assistant-core DEFAULT 'ГУАП' и Python-дефолты assistant-core не менялись (D-13): остаётся долгом в baseline сканера 03-10, перенос не позже Фазы 6"
  - "filterTasks(area, el) принимает необязательный элемент кнопки: кнопки, созданные скриптом, не зависят от глобального event"

requirements-completed: [PER-05, BCK-01, BCK-02]

coverage:
  - id: H1
    description: "/persona/current отдаёт ровно белый список ключей (включая task_areas и ui.texts) и не содержит слов NDA, подстрок remote, путей пространств и плейсхолдеров ${…}"
    requirement: "PER-05"
    verification:
      - kind: unit
        ref: "backend/tests/test_persona_api.py::test_persona_current_whitelist_only"
        status: pass
    human_judgment: false
  - id: H2
    description: "Задача или проект без области (поле отсутствует или пустая строка) получает default_area текущей персоны, синтетическая персона даёт свою; без персоны - 503, явная область сохраняется"
    requirement: "PER-05"
    verification:
      - kind: unit
        ref: "backend/tests/test_dashboard_api.py::test_task_without_area_gets_persona_default_area, ::test_project_without_area_gets_persona_default_area; backend/tests/test_persona_api.py::test_synthetic_persona_default_area_and_areas_differ, ::test_create_without_area_and_without_persona_is_503"
        status: pass
    human_judgment: false
  - id: H3
    description: "Значения областей проходят API и БД без изменений, без нормализации Unicode (кириллица, эмодзи, амперсанд, Ё и Е с диакритикой различаются)"
    requirement: "PER-05"
    verification:
      - kind: unit
        ref: "backend/tests/test_persona_api.py::test_task_areas_roundtrip_exact_unicode"
        status: pass
    human_judgment: false
  - id: H4
    description: "В статике index.html нет токенов владельца (ФИО, организации, аккаунт, пути, домены); токены вычисляются из данных персоны"
    requirement: "PER-05"
    verification:
      - kind: unit
        ref: "backend/tests/test_index_whitelabel.py::test_static_index_has_no_owner_tokens"
        status: pass
    human_judgment: false
  - id: H5
    description: "Для персоны по умолчанию 7 текстов, 5 кнопок фильтра и 6 опций формы совпадают с прежней статикой дословно; встроенный скрипт проходит node --check; applyPersona не использует innerHTML; loadPersona стоит перед refreshAll"
    requirement: "BCK-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_index_whitelabel.py::test_persona_values_equal_previous_static_strings, ::test_inline_script_passes_node_check, ::test_apply_persona_does_not_use_inner_html, ::test_index_loads_persona_before_render, ::test_fill_targets_present_once"
        status: pass
    human_judgment: false
  - id: H6
    description: "test_dashboard_api.py проверяет область через персону, пять исходных тестов сохранены, ассерты не ослаблены"
    requirement: "BCK-02"
    verification:
      - kind: unit
        ref: "backend/tests/test_dashboard_api.py (7 passed)"
        status: pass
      - kind: other
        ref: "python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ, chat-app 124, assistant-core 268"
        status: pass
    human_judgment: false
  - id: H7
    description: "Визуальный вид страницы в браузере для персоны по умолчанию (отрисовка шапки, фильтров, формы) не проверялся глазами: сервис не запускался; сверка выполнена по данным и эталонным строкам, applyPersona прогнан в node на заглушке DOM"
    requirement: "BCK-01"
    verification: []
    human_judgment: true
    rationale: "Сервисы заморожены (OPS-06), открыть страницу в браузере без запуска chat-app нельзя; эквивалентность текстов закрыта тестом, вёрстка - нет"

plan_head_before: 2fbaa6699971ca9f7df170311dd60df1ec11fc57
plan_head_after: 0fd8fc2a85e4b4b40b4b05805b5c98544f778870
duration: 6min
completed: 2026-10-03
status: complete
---

# Phase 3 Plan 06: white-label интерфейс и область по умолчанию из персоны Summary

**`/api/v1/persona/current` отдаёт полный белый список (с `task_areas` и `ui.texts`), новые задачи и проекты без области получают `default_area` персоны (без персоны - 503), а `index.html` не содержит ни одного токена владельца и заполняется из API через `loadPersona`/`applyPersona` только через textContent и Option.**

## Performance

- **Duration:** около 6 мин
- **Tasks:** 2 из 2
- **Репозиторий:** только chat-app (`master`, 2 коммита, без push); assistant-core не менялся

## Accomplishments

- **API (коммит `e7a3eca`):** `persona_public_view` перечисляет ключи явно: `task_areas` (value, label, filter_label, show_in_filter) и `ui: {texts}`. `DatabaseService.resolve_default_area()` читает персону `settings.PERSONA_ID`; нет строки - `PersonaNotLoadedError`, один обработчик в `app/main.py` отвечает 503 «Персона не загружена в базу данных». `create_project` и `create_task` берут `data.get("area") or await resolve_default_area()`; в `db.py` и `dashboard_schemas.py` литерала области больше нет, `area` в схемах - `Optional[str] = None`.
- **Тесты API:** `test_persona_current_whitelist_only` (ключи ровно из белого списка; слова NDA из shield, подстроки remote и пути пространств из БД проверяются булевыми флагами, без вывода значений, плюс `${`), `test_task_areas_roundtrip_exact_unicode` (значения персоны, эмодзи и амперсанд, «Ё» против «Е + диакритика» - разные значения, фильтр `?area=`), синтетическая персона (свой `default_area` и набор областей), 503 без персоны (задача, проект, пустая область) и сохранение явной области без персоны. `test_dashboard_api.py`: `test_tasks_crud` берёт область из `/persona/current` и дополнительно проверяет `task["area"] == default_area`; добавлены два теста на отсутствие и пустую область (задачи и проекты удаляются в `finally`).
- **Статика (коммит `0fd8fc2`):** из `index.html` убраны шапка, заголовок расписания, 5 кнопок фильтра, абзац и три подписи Security Tile, 6 опций формы и подсказка напоминания; на их месте пустые элементы с id. Добавлены `PERSONA_DEFAULT_AREA`, `loadPersona()` (не-200 или сеть - `console.warn`, поля остаются пустыми) и `applyPersona()`; `DOMContentLoaded` вызывает `await loadPersona()` перед `await refreshAll()`; `openNewTaskModal` и `editTask` используют `PERSONA_DEFAULT_AREA`. В `grep -ci` для ГУАП, Тидекс, tydex - 0.
- **Тесты статики:** шесть тестов `test_index_whitelabel.py` (токены из `owner_tokens` по config_json копии БД, порядок загрузки, id ровно по одному разу, эталон прежней статики дословно, `node --check` последнего встроенного скрипта с лимитом памяти, отсутствие innerHTML в `applyPersona`).
- Дополнительная проверка: `applyPersona` выполнен в node на заглушке DOM (заполнение текста, placeholder, только `show_in_filter`-кнопки, опции по всем областям).

## Task Commits

1. **Задача 1:** `e7a3eca` (feat) - полный белый список, дефолт области из персоны, 503, переписанные и новые тесты API
2. **Задача 2:** `0fd8fc2` (feat) - white-label `index.html` и `test_index_whitelabel.py`

Метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS) коммитятся отдельно. Измеренное число коммитов: 2 (`2fbaa66..HEAD`).

## TDD-заметка

Задача 1 (`tdd="true"`): тесты записаны до кода и прогнаны на неизменённом коде - 7 failed, 7 passed (красная фаза); после правки 14 passed. Отдельным коммитом красная фаза не оформлялась (тесты и код в одном `feat`-коммите, как в 03-02..03-05). Задача 2 без `tdd`: тесты написаны после разметки.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Область выводилась в разметку без экранирования**
- **Found during:** Задача 2 (запрет «данные персоны в DOM только через textContent/Option»)
- **Issue:** значение области из персоны через select попадает в `task.area`, а карточки задач и список проектов вставляли `t.area` и `p.area` через innerHTML без `escapeHtml`; область персоны с разметкой исполнилась бы как HTML (T-03-19).
- **Fix:** в трёх местах вывода (`${t.area}` в двух шаблонах карточек и `[${p.area}]` в списке проектов) использован существующий `escapeHtml`; для значений по умолчанию отображение прежнее (`AI & Dev Projects` отображается как раньше).
- **Files modified:** backend/app/static/index.html
- **Commit:** 0fd8fc2

### Уточнения без отклонения от смысла плана

- `filterTasks(area, el)` получил необязательный второй параметр: кнопки, созданные скриптом, передают себя и не зависят от глобального `event`; служебная кнопка «Все сферы» работает как прежде.
- В `test_persona_current_returns_seeded_persona` проверка `set(data) <= PUBLIC_KEYS` усилена до `==` (набор ключей расширен, ассерт стал строже, а не слабее).
- Тестов больше порога: 14 в двух API-файлах (порог 14), chat-app 124 в гейте (порог 109).
- Делегирование agy не использовалось (мелкие правки разметки, ревью всё равно полное).

**Total deviations:** 1 auto-fixed (Rule 2). **Impact:** вывод расширен только экранированием, поведение не меняется.

## Authentication Gates

None.

## Verification Results

- Предусловие OPS-06: `systemctl is-active` - `failed`, `inactive`, `inactive` (ни одной строки `active`); сервисы не запускались.
- `test_persona_api.py` + `test_dashboard_api.py`: 14 passed (порог 14); `test_index_whitelabel.py`: 6 passed (порог 6).
- Acceptance Задачи 1: `grep -cE '"ГУАП"'` для `db.py` и `dashboard_schemas.py` - 0 и 0; `resolve_default_area()` в `create_project` и `create_task`; `PersonaNotLoadedError` в `main.py`; в `test_dashboard_api.py` 7 тестов, пять исходных с прежними именами.
- Acceptance Задачи 2: `grep -ci` ГУАП, Тидекс, tydex в `index.html` - 0, 0, 0; `await loadPersona();` на строке 728; `owner_tokens(` в тесте; `check_file_content` для `index.html` и `test_index_whitelabel.py` - нарушений 0.
- Гейт `python3 scripts/gate.py` после Задачи 1: ИТОГ ЗЕЛЁНЫЙ, chat-app 118, assistant-core 268; после Задачи 2: **ИТОГ: ЗЕЛЁНЫЙ**, chat-app 124 (порог 109), assistant-core 268 (порог 259), строка «токены персоны (дрейф SHA-256)» присутствует, боевая `assistant.db` не изменена.

## Threat Model Status

- T-03-18 (раскрытие через /persona/current): митигирована - явный белый список, тест на ключи, NDA-слова, remote, пути, `${`.
- T-03-19 (XSS): митигирована - `applyPersona` без innerHTML (тест), плюс экранирование области в существующих шаблонах (отклонение 1).
- T-03-20 (отказ при создании без персоны): митигирована - 503 с понятным текстом.
- T-03-21 (эталон прежней статики в тестах): принята по плану; тесты - класс allowlist сканера, ужесточает Фаза 6.
- T-03-SC: установок пакетов не было.
- Параллельные запросы `/persona/current` (backstop): эндпоинт только читает, отдельного теста конкурентности нет.

## Known Stubs

None. Пустые id-элементы в статике до ответа API - намеренное поведение (D-12), а не заглушки; данные приходят из `/persona/current`.

## Threat Flags

None.

## Deferred Items

- `DEFAULT 'ГУАП'` в DDL assistant-core (`src/storage/db.py`) и Python-дефолты `create_project/create_task` assistant-core не менялись (D-13); остаточный долг в baseline сканера (03-10), перенос не позже Фазы 6.
- Визуальная проверка страницы в браузере не выполнялась (сервисы заморожены) - см. пункт H7 покрытия.

## Next Phase Readiness

03-07 и далее могут опираться на `/persona/current` с `task_areas` и `ui.texts` и на отсутствие профиля владельца в статике chat-app; 03-10 берёт токены из `owner_tokens` для сканера хардкода. Блокеров нет.

## Self-Check: PASSED

- Файлы `backend/tests/test_index_whitelabel.py`, `backend/app/api/v1/persona.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/static/index.html` найдены на диске.
- Коммиты `e7a3eca` и `0fd8fc2` найдены в `git log`; измеренное число коммитов плана: 2.
