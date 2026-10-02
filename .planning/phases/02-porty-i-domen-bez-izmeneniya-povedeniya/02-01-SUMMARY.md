---
phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
plan: 01
subsystem: architecture
tags: [ports, protocol, dataclass, import-linter, dependency-injection, composition-root]

requires:
  - phase: 01-fundament
    provides: "контракты import-linter brain-no-adapters / bot-handler-no-adapters, гейт качества, синтетическая персона"
provides:
  - "пакет src/core (домен и порты), защищённый контрактом core-is-pure"
  - "Protocol-порты BaseConnector и BaseTimesheetProvider"
  - "адаптер AadhkTimesheetProvider и корень композиции src/composition.py"
  - "DI timesheet_service в SecretaryDialogEngine, долг ignore_imports 5 -> 4"
  - "ConnectorRole, WorkspaceClearance и 7 frozen+slots сущностей"
affects: [02-02, 02-03, 03-persona, 05-plugins, 06-isolation]

actuals:
  tokens: 6000
  tasks: 2
  commits: 3
plan_head_before: 06792b7cabd3d8d97c7aca5f5e61cd87734cbef2
plan_head_after: bc5b2c913d3d7e64315c2f1b7089a9b04e39f7d6

tech-stack:
  added: []
  patterns:
    - "структурные Protocol-порты (runtime_checkable) вместо ABC"
    - "корень композиции с ленивым импортом внутри фабрик (патчи модулей-источников продолжают работать)"
    - "DI: параметр X | None = None и ленивая фабрика по умолчанию"
    - "адаптер пробрасывает *args/**kwargs, дефолты профиля остаются в конкретном классе"
    - "строка долга ignore_imports удаляется в том же коммите, что и импорт"

key-files:
  created:
    - /opt/assistant-core/src/core/__init__.py
    - /opt/assistant-core/src/core/domain/__init__.py
    - /opt/assistant-core/src/core/domain/entities.py
    - /opt/assistant-core/src/core/ports/__init__.py
    - /opt/assistant-core/src/core/ports/connectors.py
    - /opt/assistant-core/src/connectors/aadhk/provider.py
    - /opt/assistant-core/src/composition.py
    - /opt/assistant-core/tests/test_composition_di.py
    - /opt/assistant-core/tests/test_core_domain.py
    - /opt/assistant-core/tests/test_core_architecture.py
  modified:
    - /opt/assistant-core/src/brain/secretary_dialog.py
    - /opt/assistant-core/.importlinter

key-decisions:
  - "Характеризационный тест _get_tydex_context закоммичен отдельно до правки src (cd54595), патчит модуль-источник parser.AadhkIngestionService"
  - "Порт BaseTimesheetProvider без хардкода профиля: дефолты project_name/default_project/daily_norm заменены многоточием, адаптер пробрасывает *args/**kwargs"
  - "core-is-pure запрещает ядру все 13 прочих модулей верхнего уровня src (надмножество D-02), полноту проверяет test_core_is_pure_forbids_every_other_src_module"
  - "ConnectorRole и атрибут role: ClassVar сделали разделение ролей проверяемым фактом"

requirements-completed: [PRT-01, PRT-02, PRT-03, PRT-04]

coverage:
  - id: D1
    description: "Ответ секретаря о табеле не изменился после переноса зависимости в конструктор (характеризационный тест написан до правки src)"
    requirement: PRT-04
    verification:
      - kind: unit
        ref: "tests/test_composition_di.py#test_tydex_context_text_characterization"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_tydex_context_fallback_on_error"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_secretary_uses_injected_timesheet_service"
        status: pass
    human_judgment: false
  - id: D2
    description: "AadhkTimesheetProvider соответствует порту BaseTimesheetProvider (isinstance, корутины, атрибуты класса)"
    requirement: PRT-03
    verification:
      - kind: unit
        ref: "tests/test_composition_di.py#test_default_timesheet_service_conforms_to_port"
        status: pass
    human_judgment: false
  - id: D3
    description: "Контракт core-is-pure kept, долг ignore_imports равен 4, инлайн-импорт секретаря убран"
    requirement: PRT-04
    verification:
      - kind: other
        ref: "cd /opt/assistant-core && .venv/bin/lint-imports --no-logo --no-cache (3 kept, 0 broken)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Семь frozen+slots сущностей и WorkspaceClearance с тремя значениями; рабочие пространства синтетической персоны собираются в Workspace"
    requirement: PRT-01
    verification:
      - kind: unit
        ref: "tests/test_core_domain.py#test_entities_are_frozen"
        status: pass
      - kind: unit
        ref: "tests/test_core_domain.py#test_synthetic_workspaces_map_to_clearance"
        status: pass
    human_judgment: false
  - id: D5
    description: "Ядро чисто: импортирует только stdlib и src.core.*, без токенов профиля владельца, список запретов полон"
    requirement: PRT-01
    verification:
      - kind: unit
        ref: "tests/test_core_architecture.py#test_core_imports_only_stdlib_and_core"
        status: pass
      - kind: unit
        ref: "tests/test_core_architecture.py#test_core_is_pure_forbids_every_other_src_module"
        status: pass
      - kind: unit
        ref: "tests/test_core_architecture.py#test_core_has_no_profile_tokens"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-02
status: complete
---

# Phase 2 Plan 01: Порты и домен, сквозной срез табеля Summary

**Вопрос о табеле идёт через Protocol-порт BaseTimesheetProvider, адаптер AadhkTimesheetProvider и корень композиции src/composition.py; ядро src/core защищено контрактом core-is-pure, долг ignore_imports снижен с 5 до 4, поведение секретаря закреплено тестом, написанным до правки.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-02T09:46:55Z
- **Completed:** 2026-10-02T09:50:45Z
- **Tasks:** 2 (tracer + auto)
- **Files modified:** 12 (10 новых, 2 изменённых в assistant-core)

## Accomplishments

- Tracer-срез: SecretaryDialogEngine → BaseTimesheetProvider → AadhkTimesheetProvider → AadhkIngestionService, зависимость приходит через конструктор (`timesheet_service`), по умолчанию лениво собирается `default_timesheet_service(self.db)` внутри существующего `try`.
- Контракт `core-is-pure` (13 запрещённых модулей, ignore_imports пуст): `lint-imports` — «3 kept, 0 broken»; запись secretary_dialog удалена в том же коммите, что и инлайн-импорт (долг 4).
- Домен PRT-01: `ConnectorRole`, `WorkspaceClearance` (ровно три значения) и 7 сущностей `frozen+slots`; `WorkRecord.project_tag` без значения по умолчанию.
- Чистота ядра доказана тремя способами: контракт grimp, рантайм-страж (подпроцесс, только stdlib и src.core.*), проверка полноты списка запретов; плюс тест отсутствия токенов профиля.
- Гейт: «ИТОГ: ЗЕЛЁНЫЙ», тестов assistant-core 167 (старт фазы 139).

## Task Commits

Все коммиты в `/opt/assistant-core` (ветка main, без push):

1. **Task 1 (tracer), шаг 1: характеризация до правки src** - `cd54595` (test)
2. **Task 1 (tracer), шаги 2-8: src/core, адаптер, composition, DI, core-is-pure** - `98f1c0f` (feat)
3. **Task 2: доменные сущности и тесты чистоты ядра** - `bc5b2c9` (feat)

**Plan metadata:** коммит docs в /opt/chat-app (см. git log, `docs(02-01)`).

## Files Created/Modified

- `/opt/assistant-core/src/core/ports/connectors.py` - порты BaseConnector и BaseTimesheetProvider (дефолты профиля заменены многоточием)
- `/opt/assistant-core/src/core/domain/entities.py` - ConnectorRole, WorkspaceClearance и 7 неизменяемых сущностей
- `/opt/assistant-core/src/connectors/aadhk/provider.py` - адаптер-обёртка AadhkTimesheetProvider (атрибуты на уровне класса)
- `/opt/assistant-core/src/composition.py` - корень композиции, `default_timesheet_service(db)` с ленивым импортом
- `/opt/assistant-core/src/brain/secretary_dialog.py` - параметр и атрибут `timesheet_service`, инлайн-импорт убран
- `/opt/assistant-core/.importlinter` - контракт core-is-pure, запись secretary_dialog удалена
- `/opt/assistant-core/tests/test_composition_di.py`, `test_core_domain.py`, `test_core_architecture.py` - 4 + 8 (24 с параметризацией) + 4 теста

## Decisions Made

- Характеризация закоммичена отдельно до правки src и патчит модуль-источник, поэтому один и тот же тест работает с инлайн-импортом и с внедрением (проверено порядком коммитов через `git log -S` и `merge-base`).
- В порте дефолты профиля заменены многоточием, адаптер пробрасывает `*args, **kwargs`: в ядре нет названия компании и нормы часов (подготовка к PER-06, PER-08).
- Список запретов core-is-pure взят шире D-02 (добавлены src.detector, src.config, src.composition) в соответствии с D-01.

## Deviations from Plan

None - plan executed exactly as written. Делегирование Antigravity (необязательное в задаче 2) не использовалось: объём малый, сущности и тесты написаны напрямую.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None - новых сетевых точек, путей аутентификации и обращений к файлам на границах доверия нет; `T-02-SC` (установки пакетов) не применим: пакеты не устанавливались.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Готовы шов `src/composition.py` и пакет `src/core` для планов 02-02 (порты LMS, расписание, календарь) и 02-03 (DI bot_handler, снижение долга до 0).
- Требования PRT-02..PRT-04 закрыты здесь только частично (срез табеля и секретаря); полное закрытие зависит от остальных планов фазы.
- Блокеров нет.

## Self-Check: PASSED

---
*Phase: 02-porty-i-domen-bez-izmeneniya-povedeniya*
*Completed: 2026-10-02*
