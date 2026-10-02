---
phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
plan: 02
subsystem: architecture
tags: [ports, protocol, adapters, asyncio, conformance-test, hitl-marker]

requires:
  - phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
    provides: "src/core (домен, BaseConnector, BaseTimesheetProvider), AadhkTimesheetProvider, composition root"
provides:
  - "порты BaseScheduleProvider, BaseCalendarSink, BaseLMSProvider (все методы async, роли разделены)"
  - "адаптеры ScheduleParserSource, GoogleCalendarSink, GuapLmsProvider поверх неизменённых конкретных классов"
  - "декларативная пометка BaseLMSProvider.REQUIRES_CONFIRMATION = {submit_grade, delete_task}"
  - "DI-протоколы существующих клиентов LmsClientLike, EmailSenderLike, DriveClientLike (src/core/ports/clients.py)"
  - "tests/test_ports_conformance.py: Protocol-проверка четырёх пар порт - адаптер"
affects: [02-03, 02-04, 03-persona, 05-plugins, 06-isolation]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: bc5b2c913d3d7e64315c2f1b7089a9b04e39f7d6
plan_head_after: 7410deb4062abb878cbed74fba042478b66b3590

tech-stack:
  added: []
  patterns:
    - "адаптер-обёртка закрывает несовпадение сигнатур: синхронный разбор парсера оборачивается в async, синхронный клиент ЛК уходит в поток через asyncio.to_thread"
    - "порт нейтрален к поставщику: event_id вместо google_event_id, адаптер передаёт аргумент позиционно"
    - "conformance = isinstance + inspect.iscoroutinefunction по членам Protocol (isinstance один проверяет только имена)"
    - "health_check читает только атрибуты: без сети и файлов учётных данных"

key-files:
  created:
    - /opt/assistant-core/src/core/ports/clients.py
    - /opt/assistant-core/src/parser/provider.py
    - /opt/assistant-core/src/calendar/provider.py
    - /opt/assistant-core/src/connectors/guap_lms/provider.py
    - /opt/assistant-core/tests/test_ports_conformance.py
  modified:
    - /opt/assistant-core/src/core/ports/connectors.py

key-decisions:
  - "Все методы портов async, включая parse_json_payload и parse_html_payload (у ScheduleParser они синхронные): буква PRT-02 важнее исследования, несовпадение закрывает адаптер"
  - "Порт календаря назван BaseCalendarSink; идентификатор события в порту - event_id, не google_event_id"
  - "submit_grade в адаптере ЛК бросает NotImplementedError без обращения к клиенту; REQUIRES_CONFIRMATION только декларативна до Фазы 5"
  - "Адаптер ЛК не подключён к bot_handler, brain, main, composition (проверяет test_lms_provider_not_wired_into_production)"
  - "Протоколы клиентов clients.py без названий организаций и классов в docstrings: тест ядра сканирует токены профиля"

requirements-completed: [PRT-02, PRT-03]

coverage:
  - id: D1
    description: "Пять портов PRT-02 объявлены как runtime_checkable Protocol, все методы async"
    requirement: PRT-02
    verification:
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_port_methods_are_coroutines_on_adapter"
        status: pass
    human_judgment: false
  - id: D2
    description: "Четыре адаптера соответствуют портам (isinstance + корутины), роли расписания разделены в обе стороны"
    requirement: PRT-03
    verification:
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_adapter_conforms_to_port"
        status: pass
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_schedule_roles_are_separated"
        status: pass
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_adapter_roles_and_ids"
        status: pass
    human_judgment: false
  - id: D3
    description: "Порт ЛК помечает submit_grade и delete_task как требующие подтверждения; submit_grade не выполняет действий; адаптер не подключён к боевым потокам"
    requirement: PRT-02
    verification:
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_lms_confirmation_markers"
        status: pass
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_lms_submit_grade_not_implemented"
        status: pass
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_lms_provider_not_wired_into_production"
        status: pass
    human_judgment: false
  - id: D4
    description: "health_check всех адаптеров работает без сети; адаптеры не копируют дефолты профиля"
    requirement: PRT-03
    verification:
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_health_check_is_offline"
        status: pass
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_adapters_do_not_duplicate_profile_defaults"
        status: pass
    human_judgment: false
  - id: D5
    description: "Существующие клиенты структурно удовлетворяют DI-протоколам бота; отображение заданий ЛК в AcademicSubmission"
    requirement: PRT-03
    verification:
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_existing_clients_match_di_protocols"
        status: pass
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_lms_list_tasks_maps_to_academic_submission"
        status: pass
      - kind: unit
        ref: "tests/test_ports_conformance.py#test_lms_delete_task_runs_in_thread_and_forwards_args"
        status: pass
    human_judgment: false
  - id: D6
    description: "Полный гейт качества зелёный, import-linter 3 kept, 0 broken"
    verification:
      - kind: other
        ref: "env -u PYTEST_ADDOPTS python3 /opt/chat-app/scripts/gate.py (ИТОГ: ЗЕЛЁНЫЙ, assistant-core 192 теста)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-02
status: complete
---

# Phase 2 Plan 02: Порты расписания, календаря и личного кабинета Summary

**Три async-порта (BaseScheduleProvider, BaseCalendarSink, BaseLMSProvider) с адаптерами поверх неизменённых клиентов, пометка REQUIRES_CONFIRMATION для submit_grade и delete_task, DI-протоколы клиентов бота и единый conformance-тест всех четырёх пар порт - адаптер с проверкой разделения ролей.**

## Performance

- **Duration:** 8 min
- **Completed:** 2026-10-02T09:55:21Z
- **Tasks:** 2
- **Files modified:** 6 (5 новых, 1 изменённый в assistant-core)

## Accomplishments

- Порты источника расписания и приёмника календаря (роли schedule_source и calendar_sync разделены, проверка isinstance в обе стороны); синхронный разбор payload парсера закрыт адаптером.
- Порт личного кабинета с `REQUIRES_CONFIRMATION = frozenset({"submit_grade", "delete_task"})`; адаптер объявляет ту же пометку, `submit_grade` бросает `NotImplementedError` и клиента не трогает; `list_tasks` отображает строки клиента в `AcademicSubmission` с терпимым разбором срока.
- `src/core/ports/clients.py`: `LmsClientLike` (синхронный), `EmailSenderLike`, `DriveClientLike` - готовы для DI бота в плане 02-03; существующие клиенты им соответствуют структурно.
- `tests/test_ports_conformance.py`: 29 тестов вместе с `test_core_architecture.py` (conformance-файл - 25 с параметризацией), все зелёные; гейт «ИТОГ: ЗЕЛЁНЫЙ», assistant-core 192 теста (было 167), `lint-imports` 3 kept, 0 broken.

## Task Commits

Все коммиты в `/opt/assistant-core` (ветка main, без push):

1. **Task 1: порты расписания и календаря, адаптеры, conformance-тест** - `0ead83a` (feat)
2. **Task 2: порт ЛК, clients.py, адаптер GuapLmsProvider** - `7410deb` (feat)

**Plan metadata:** коммит docs в /opt/chat-app (см. git log, `docs(02-02)`).

## Files Created/Modified

- `/opt/assistant-core/src/core/ports/connectors.py` - добавлены BaseScheduleProvider, BaseCalendarSink, BaseLMSProvider
- `/opt/assistant-core/src/core/ports/clients.py` - LmsClientLike, EmailSenderLike, DriveClientLike
- `/opt/assistant-core/src/parser/provider.py` - ScheduleParserSource (schedule_site)
- `/opt/assistant-core/src/calendar/provider.py` - GoogleCalendarSink (google_calendar)
- `/opt/assistant-core/src/connectors/guap_lms/provider.py` - GuapLmsProvider (lms_portal), `_parse_deadline`
- `/opt/assistant-core/tests/test_ports_conformance.py` - Protocol-проверка PRT-03 и тесты безопасности ЛК

## Decisions Made

- Все методы портов async (буква PRT-02), включая разбор payload: у конкретного парсера они синхронные, несовпадение закрывает адаптер, поведение не меняется (адаптер нигде не используется).
- Порт календаря нейтрален к поставщику: `event_id` вместо `google_event_id`.
- Пометка подтверждения декларативна; механизм появится в Фазе 5, а HITL-диалог удаления в боте остаётся единственным путём удаления.
- Делегирование Antigravity не использовалось: объём малый, тесты и адаптеры написаны напрямую.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None. `submit_grade` намеренно бросает `NotImplementedError` (у клиента нет такой операции, D-09): это защитное поведение, а не заглушка данных; механизм подтверждения - Фаза 5.

## Threat Flags

None - новых сетевых точек и путей аутентификации нет: адаптеры не подключены к боевым потокам, health_check читает только атрибуты; `T-02-SC` не применим, пакеты не устанавливались.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- DI-протоколы `LmsClientLike`, `EmailSenderLike`, `DriveClientLike` готовы для плана 02-03 (внедрение зависимостей в bot_handler, снижение долга ignore_imports до 0).
- Флаги допущений edge-probe PRT-02 и PRT-03 трактованы как в плане (async-порты, пометка = константа + тест, разделение ролей = разные role и isinstance в обе стороны); требуют ручной проверки на верификации.
- Блокеров нет.

## Self-Check: PASSED

- Файлы существуют: connectors.py, clients.py, три provider.py, test_ports_conformance.py (проверено при запуске тестов и коммитах).
- Коммиты найдены: `0ead83a`, `7410deb`; `git rev-list --count` от `bc5b2c9` до HEAD = 2.
- Критерии приёмки обеих задач выполнены; конкретные классы, бот и main.py не тронуты, в `tests/` только строки `A`.

---
*Phase: 02-porty-i-domen-bez-izmeneniya-povedeniya*
*Completed: 2026-10-02*
