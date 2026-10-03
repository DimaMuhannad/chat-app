---
phase: 03-persona-kak-dannye
plan: 09
subsystem: connector-params
tags: [persona, connector-bindings, timesheet, schedule, methodist, lms, PER-06, PER-09]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-03: схема персоны, привязки connector_bindings и блок methodist; 03-04: synthetic_to_config; 03-08: все 8 промптов - шаблоны персоны"
provides:
  - "src/persona/bindings.py: TimesheetSettings, LessonSlot, ScheduleSourceSettings, LmsSettings; binding, timesheet_settings, schedule_source_settings, lms_settings, methodist_settings, format_hours"
  - "Проект учёта и норма часов читаются из привязки timesheet в момент вызова (AadhkIngestionService.settings, сентинел _FROM_PERSONA); все места вызова и тексты «по N ч» берут значения из персоны"
  - "Слоты пар и короткие названия предметов - один источник (привязка schedule_source): lesson_slot_numbers(), subject_short_names(); дубль в calendar/client.py удалён"
  - "schedule_site_url() в корне композиции: SCHEDULE_URL из окружения сильнее персоны; ScheduleParser без аргумента берёт адрес из персоны"
  - "Методист (каталоги, правила области, причина отказа), каталог файлов секретаря и адрес личного кабинета - данные персоны"
affects: [03-10, phase-06]

actuals:
  tokens: 14000
  tasks: 3
  commits: 0
  # commits: 0 - chat-app (репозиторий SUMMARY): изменений кода в этом репозитории нет (docs-only). Код - в assistant-core: 6 коммитов, см. ниже.

tech-stack:
  added: []
  patterns:
    - "Параметры коннекторов берутся из привязки текущей персоны в момент вызова; явный аргумент сильнее; необязательный параметр настроек - шов для явной инъекции (Фаза 6)"
    - "Сентинел _FROM_PERSONA отличает «не передано» от явного None (project_name=None - «все проекты»)"
    - "Окружение сильнее персоны: пустая SCHEDULE_URL - адрес из привязки"

key-files:
  created:
    - /opt/assistant-core/src/persona/bindings.py
    - /opt/assistant-core/tests/test_connector_params.py
  modified:
    - /opt/assistant-core/src/connectors/aadhk/parser.py
    - /opt/assistant-core/src/main.py
    - /opt/assistant-core/src/notifier/live_ticker.py
    - /opt/assistant-core/src/notifier/bot_handler.py
    - /opt/assistant-core/src/brain/secretary_dialog.py
    - /opt/assistant-core/src/brain/methodist.py
    - /opt/assistant-core/src/models/schedule.py
    - /opt/assistant-core/src/calendar/client.py
    - /opt/assistant-core/src/parser/schedule_parser.py
    - /opt/assistant-core/src/config.py
    - /opt/assistant-core/src/composition.py
    - /opt/assistant-core/src/connectors/guap_lms/client.py
    - /opt/assistant-core/tests/test_secretary_dialog.py

key-decisions:
  - "Слоты календаря: локальный словарь из 6 слотов в GoogleCalendarClient.format_description заменён на lesson_slot_numbers() (один источник). Побочный эффект для персоны по умолчанию: у пары 20:20 в описании события появляется строка «Пара: 7» (раньше седьмой слот в календаре отсутствовал)"
  - "Адрес ЛК нормализуется rstrip('/') в GuapLmsClient и в ссылке main.py: адрес персоны с завершающим «/» не даёт двойной слэш; для адреса по умолчанию поведение то же"
  - "Конструкторы и сигнатуры композиции не менялись (D-18): шов - необязательный параметр settings у AadhkIngestionService и base_url у GuapLmsClient"

requirements-completed: [PER-06, BCK-01, BCK-02]

coverage:
  - id: I1
    description: "Проект учёта и норма читаются из привязки timesheet; для персоны по умолчанию значения прежние («Тидекс», 8.5), для синтетической - свои (6 ч); явный аргумент и явный None сильнее персоны"
    requirement: "PER-06"
    verification:
      - kind: unit
        ref: "tests/test_connector_params.py::test_timesheet_settings_default_persona, ::test_timesheet_settings_follow_active_persona, ::test_aadhk_monthly_pacing_uses_persona_norm_and_project, ::test_aadhk_explicit_arguments_beat_persona"
        status: pass
    human_judgment: false
  - id: I2
    description: "Секретарь и живая сводка передают project_name из персоны и форматируют норму из персоны; характеризация Фазы 2 (kwargs, текст «по 8.5 ч») не изменена и зелёная"
    requirement: "BCK-01"
    verification:
      - kind: unit
        ref: "tests/test_connector_params.py::test_secretary_and_ticker_pass_persona_project_and_norm; tests/test_composition_di.py, test_aadhk_parser.py, test_live_ticker.py без правок: 43 passed вместе с test_connector_params"
        status: pass
    human_judgment: false
  - id: I3
    description: "Слоты пар и короткие названия предметов - один источник; допуск ±15 минут сохранён; строки расписания test_brain не изменились; календарь и живая сводка используют ту же функцию; собственных словарей коротких названий в модулях нет"
    requirement: "PER-06"
    verification:
      - kind: unit
        ref: "tests/test_connector_params.py::test_lesson_slots_and_subjects_default_persona, ::test_lesson_slots_and_subjects_from_persona, ::test_calendar_formatting_follows_persona, ::test_calendar_and_ticker_have_no_own_subject_dicts, ::test_ticker_uses_persona_subject_names; test_brain.py, test_phase1.py, test_bot_menu.py без правок"
        status: pass
    human_judgment: false
  - id: I4
    description: "SCHEDULE_URL из окружения сильнее персоны; без неё - base_url привязки; ScheduleParser() без аргумента берёт адрес из персоны"
    requirement: "PER-06"
    verification:
      - kind: unit
        ref: "tests/test_connector_params.py::test_schedule_site_url_env_wins_over_persona, ::test_schedule_parser_default_base_url_from_persona"
        status: pass
    human_judgment: false
  - id: I5
    description: "Каталоги методиста, каталог файлов секретаря и правила области (слова и причина отказа) - данные персоны; для персоны по умолчанию списки и причина равны прежним литералам; test_search_local_files_catalog проверяет то же поведение через персону"
    requirement: "BCK-02"
    verification:
      - kind: unit
        ref: "tests/test_connector_params.py::test_methodist_dirs_and_catalog_from_persona, ::test_default_file_catalog_text_unchanged, ::test_check_scope_decisions_follow_persona; tests/test_secretary_dialog.py::test_search_local_files_catalog"
        status: pass
      - kind: other
        ref: "скрипт: списки out_of_scope/academic и причина из persona.yaml == литералы из HEAD:src/brain/methodist.py - True True True"
        status: pass
    human_judgment: false
  - id: I6
    description: "Провайдеры и scopes привязок персоны по умолчанию равны connector_id и required_scopes адаптеров (W8); адрес ЛК из привязки lms"
    requirement: "PER-06"
    verification:
      - kind: unit
        ref: "tests/test_connector_params.py::test_bindings_match_adapter_ids_and_scopes, ::test_lms_base_url_from_persona"
        status: pass
    human_judgment: false
  - id: I7
    description: "Гейт зелёный, lint-imports 5 kept, 0 broken; сервисы не запускались"
    requirement: "BCK-01"
    verification:
      - kind: other
        ref: "python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ, chat-app 124 (порог 109), assistant-core 315 (порог 292); shield, дрейф SHA-256, неизменность assistant.db - все ✓"
        status: pass
    human_judgment: false

plan_head_before: ccbafac1ba3f2f70dc8643495ffd0f5fc7cfbd0c
plan_head_after: ccbafac1ba3f2f70dc8643495ffd0f5fc7cfbd0c
assistant_core_head_before: b004f668f86b1be3d0617a86233b311e451b5a5b
assistant_core_head_after: 8f61982
assistant_core_commits: 6
duration: около 12 мин
completed: 2026-10-03
status: complete
---

# Phase 3 Plan 09: параметры коннекторов из персоны Summary

**Проект учёта и норма часов, слоты пар и короткие названия предметов, адреса сайта расписания и личного кабинета, каталоги методиста, каталог файлов секретаря и правила области методиста читаются из привязок персоны в момент вызова (новый `src/persona/bindings.py`); для персоны по умолчанию значения и тексты прежние, синтетическая персона на тех же кодовых путях получает свои.**

## Performance

- **Duration:** около 12 мин
- **Tasks:** 3 из 3
- **Репозитории:** assistant-core (`main`, 6 коммитов, без push); chat-app (`master`) - только метаданные плана. Сервисы не запускались (OPS-06): `systemctl is-active` до и после - `failed`, `inactive`, `inactive`.

## Accomplishments

- **Аксессоры привязок:** `src/persona/bindings.py` (лист зависимостей, контракт persona-is-leaf): frozen dataclass для настроек табеля, расписания и ЛК, `binding(role)` (нет привязки или ключа - `PersonaConfigError` с названием роли и ключа, без значений), `methodist_settings()`, `format_hours` (8.5 -> «8.5», 6.0 -> «6»).
- **Табель:** `AadhkIngestionService.__init__(db, settings=None)` (позиционный вызов `AadhkIngestionService(db)` прежний), свойство `settings` читает привязку при каждом обращении; сентинел `_FROM_PERSONA` для `default_project`, `project_name`, `daily_norm`; явный `None` у `project_name` по-прежнему «все проекты». Литералы «Тидекс» и 8.5 из `parser.py` убраны. Места вызова (`main.py`, `live_ticker.py`, `bot_handler.py` x2, `secretary_dialog.py`) передают `timesheet_settings().default_project`, тексты «по N ч» форматируют норму персоны. Заголовки «Табель ... «Тидекс»» остались текстами интерфейса (остаточный долг).
- **Расписание:** `models/schedule.py` вместо словарей `GUAP_BELL_SCHEDULE` и `SUBJECT_SHORT_NAMES` - функции `lesson_slot_numbers()` и `subject_short_names()`; `calendar/client.py` и `live_ticker.py` пользуются ими (дубль словаря удалён, локальный словарь слотов календаря тоже). `ScheduleParser(base_url=None)` берёт адрес из персоны; `config.SCHEDULE_URL` без адреса по умолчанию; `composition.schedule_site_url()` (окружение сильнее персоны), `main.py` использует её в двух местах.
- **Методист и ЛК:** `MethodistService` берёт `raw_dir`/`kb_dir` из персоны при `None`, `check_scope` читает слова и причину отказа из `scope_rules`; `_search_local_files_context` строит каталог из `file_catalog`; `GuapLmsClient(base_url=None)` берёт адрес из привязки `lms`, ссылка на задание в `main.py` строится из `lms_settings()`. Проверкой скриптом списки и причина в `persona.yaml` равны прежним литералам.
- **Тесты:** `tests/test_connector_params.py` - 21 тест (порог плана 12) для обеих персон; `test_search_local_files_catalog` переписан через каталог персоны с сохранением трёх проверок.

## Task Commits

Репозиторий assistant-core (`b004f66..8f61982`, измерено `git rev-list --count`: 6 коммитов):

1. **Задача 1, RED:** `7df0765` - 8 упавших тестов (`8 failed, 2 passed`).
2. **Задача 1, GREEN:** `586b76c` - `bindings.py`, табель, места вызова; `43 passed` по четырём файлам.
3. **Задача 2, RED:** `dab522a` - 7 упавших тестов (`7 failed, 10 passed`).
4. **Задача 2, GREEN:** `fe2fe39` - слоты, предметы, `schedule_site_url`; `49 passed` по пяти файлам.
5. **Задача 3, RED:** `e65eccb` - 3 упавших теста (`3 failed, 24 passed`), переписан `test_search_local_files_catalog`.
6. **Задача 3, GREEN:** `8f61982` - методист, каталог секретаря, ЛК; `47 passed` по пяти файлам.

chat-app: код не менялся (`plan_head_before` = `plan_head_after`, `commits: 0` - docs-only для этого репозитория); метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS) коммитятся отдельно.

## TDD Gate Compliance

- **RED (3 коммита):** тесты поведения падали на утверждениях (`assert ... == ...`: проект и норма, слоты, каталоги, причина отказа, адрес ЛК). Тесты самих аксессоров `bindings` в первом RED падали с `ModuleNotFoundError` (модуля ещё нет), поэтому по строгому правилу `check tdd-red-evidence` они дали бы INVALID_RED; ценность RED обеспечили поведенческие тесты (`test_aadhk_monthly_pacing_uses_persona_norm_and_project`, `test_secretary_and_ticker_pass_persona_project_and_norm`). Файл `check tdd-red-evidence` не оформлялся (как в 03-07, 03-08).
- **GREEN (3 коммита):** все целевые тесты зелёные, характеризационные тесты Фазы 2 без правок.
- **REFACTOR:** не требовался.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Локальный словарь слотов в `GoogleCalendarClient.format_description`**
- **Found during:** Задача 2 (аудит дублей слотов)
- **Issue:** кроме `SUBJECT_SHORT_NAMES`, в `calendar/client.py` был второй зашитый словарь слотов (6 слотов, точное совпадение времени, без седьмого). Он оставил бы слоты владельца в коде и нарушил бы «один источник» (Pitfall 8) и PER-09 для календаря.
- **Fix:** замена на `lesson_slot_numbers()` (точное совпадение по `HH:MM`). Эффект для персоны по умолчанию: у пары 20:20 в описании события календаря появляется строка «Пара: 7 (...)» (раньше её не было); слоты 1-6 без изменений (`test_phase1.py` без правок, зелёный).
- **Files modified:** /opt/assistant-core/src/calendar/client.py
- **Commit:** fe2fe39
- **Требует внимания владельца:** единственное отличие поведения персоны по умолчанию в плане; для уже созданных событий 20:20 описание изменится при следующей синхронизации календаря (после разморозки).

**2. [Rule 2 - Missing critical functionality] Нормализация адреса ЛК**
- **Found during:** Задача 3
- **Issue:** адрес в данных персоны может оканчиваться на «/» (так в синтетической персоне), тогда адреса запросов получили бы двойной слэш.
- **Fix:** `.rstrip("/")` при присвоении `GuapLmsClient.base_url` и в ссылке на задание `main.py`; для адреса по умолчанию (без завершающего «/») поведение то же.
- **Files modified:** /opt/assistant-core/src/connectors/guap_lms/client.py, /opt/assistant-core/src/main.py
- **Commit:** 8f61982

### Уточнения без отклонения от смысла плана

- **Адрес `ScheduleParser()` без аргумента** меняется с литерала `https://rasp.guap.ru/` на `base_url` привязки (`https://guap.ru/rasp`) - так предписано планом; боевой код всегда передаёт адрес явно через `schedule_site_url()`, а тесты соответствия портам адрес не проверяют.
- **Гейт запущен дважды:** после Задачи 1 (assistant-core 304, порог 285) и после Задачи 3 (315, порог 292); отдельного прогона после Задачи 2 не было - итоговый гейт покрывает порог 289.
- **`tests/test_secretary_dialog.py`:** кроме переписанного теста добавлены импорты `Path` и `methodist_settings`; остальные тесты файла не менялись.
- **Делегирование agy не использовалось** (значения владельца в данных, объём небольшой).

**Total deviations:** 2 auto-fixed (Rule 2 x2). **Impact:** критерии плана выполнены; одно изменение поведения персоны по умолчанию (седьмой слот в описании календаря) вынесено на внимание владельца.

## Authentication Gates

None.

## Verification Results

- Acceptance Задачи 1: `grep -rn 'project_name="Тидекс"' src` - пусто; `grep -cE "8\.5" parser.py` - 0; `timesheet_settings().default_project` найден в `main.py`, `live_ticker.py`, `bot_handler.py` (2), `secretary_dialog.py`; `git diff --quiet 150e9b3..HEAD -- src/connectors/aadhk/provider.py` - код 0; `test_composition_di.py`, `test_aadhk_parser.py`, `test_live_ticker.py` без изменений относительно 150e9b3.
- Acceptance Задачи 2: `grep -rn "SUBJECT_SHORT_NAMES\|GUAP_BELL_SCHEDULE" src` - пусто; `rasp.guap.ru|guap.ru/rasp` в `schedule_parser.py` и `config.py` - 0 и 0; `schedule_site_url()` в `main.py` - 2 строки; `test_brain.py`, `test_phase1.py`, `test_bot_menu.py` без изменений.
- Acceptance Задачи 3: `/opt/assistant-core/data/methodist` в `methodist.py` и `secretary_dialog.py` - 0 и 0; `Форма_отчета_эффективный_контракт` в `secretary_dialog.py` - 0; `self.base_url = "https://pro.guap.ru"` - 0; удалённых тестов нет (`D` - 0); `test_methodist.py`, `test_guap_lms.py`, `test_lms_bot_workflow.py` без изменений.
- `lint-imports`: «5 kept, 0 broken».
- Гейт `python3 scripts/gate.py`: **ИТОГ: ЗЕЛЁНЫЙ**, chat-app 124 (порог 109), assistant-core 315 (порог 292).
- Сервисы: `systemctl is-active assistant-worker chat-app dev-bridge` - `failed`, `inactive`, `inactive` (ни одного `active`).

## Threat Model Status

- T-03-29 (подмена характеризованного поведения табеля и расписания): митигирована - тесты Фазы 2, `test_brain`, `test_phase1`, `test_bot_menu` не менялись (`git diff --quiet`); списки и причина методиста равны прежним литералам (проверено скриптом); значения персоны по умолчанию = прежние литералы. Единственное осознанное отличие - строка «Пара: 7» (см. отклонение 1).
- T-03-30 (подмена хоста ЛК/расписания данными): принята - файл персоны доверенный; проверка хоста при входе и SSO не менялись; приоритет окружения для `SCHEDULE_URL` закреплён тестом.
- T-03-31 (пути каталога методиста): принята - пути в `config/persona.yaml`, в API chat-app не отдаются.
- T-03-SC (установка пакетов): митигирована - установок нет.

## Known Stubs

None.

## Threat Flags

None.

## Deferred Items (остаточный долг, запись в BASELINE - 03-10, затем Фаза 6)

- `SCHEDULE_TARGET_ID` (окружение и `config.py`, на нём построены id источников `rasp_guap_<id>`), имена функций с «guap», хост в проверке входа и SSO-хост ЛК (часть протокола), тексты интерфейса Telegram и подписи ссылок (заголовки «Табель ... «Тидекс»», «pro.guap.ru» в подписях), текст отказа методиста в `ask` (его проверяет `test_methodist.py`), DDL-дефолты и стартовые данные `storage/db.py`, `get_timesheet_summary` без фильтра проекта в ряде мест.
- Закрыть при необходимости: пробрасывание `PersonaConfigError` из внешних `try` (дайджесты, `_get_tydex_context` ловит исключение и отдаёт запасной текст) - решение к 03-10 или Фазе 6.

## Next Phase Readiness

Все параметры коннекторов из перечня аудита PER-06 - данные персоны; адаптеры принимают явные настройки (шов для Фазы 6). Готово для 03-10 (сканер хардкода, PER-08, запись остаточного долга в BASELINE). Блокеров нет.

## Self-Check: PASSED

- Файлы `src/persona/bindings.py`, `tests/test_connector_params.py`, `src/composition.py` (`schedule_site_url`) найдены на диске.
- Коммиты assistant-core `7df0765`, `586b76c`, `dab522a`, `fe2fe39`, `e65eccb`, `8f61982` найдены в `git log`.
- Измеренное число коммитов плана: assistant-core 6 (`b004f66..8f61982`), chat-app 0 до коммита метаданных.
