---
phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
plan: 03
subsystem: architecture
tags: [dependency-injection, composition-root, characterization-tests, import-linter, hitl]

requires:
  - phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
    provides: "src/core (домен, порты, DI-протоколы клиентов), src/composition.default_timesheet_service, DI timesheet_service в SecretaryDialogEngine"
provides:
  - "фабрики default_lms_client, default_email_sender, default_drive_client в src/composition.py (ленивые импорты)"
  - "EmailBotHandler: клиент ЛК, отправщик почты, сервис табеля и фабрика Drive приходят через конструктор; аннотации - протоколы портов"
  - "характеризационные тесты трёх ранее непокрытых путей бота (/timesheet, синхронизация с Google Drive, AADHk-ветка документа), закоммичены до правки bot_handler.py"
  - "пустой долг ignore_imports по всем контрактам (было 4 записи у bot-handler-no-adapters), lint-imports: 3 kept, 0 broken"
affects: [02-04, 03-persona, 05-plugins, 06-isolation]

actuals:
  tokens: 6950
  tasks: 2
  commits: 2
plan_head_before: 7410deb4062abb878cbed74fba042478b66b3590
plan_head_after: c5820eb9cdf0134527b05314292ccd3720aaf1cd

tech-stack:
  added: []
  patterns:
    - "характеризация до рефакторинга: отдельный коммит только с тестом, патчатся модули-источники, а не имена в модуле бота"
    - "ленивая сборка в корне композиции: use-case хранит ссылку на фабрику (default_drive_client) и вызывает её на каждый колбэк"
    - "семантика or сохранена для существующих параметров, is not None для новых"
    - "_timesheet(): внедрённый сервис или сервис по умолчанию на каждый вызов, как было до рефакторинга"

key-files:
  created: []
  modified:
    - /opt/assistant-core/src/composition.py
    - /opt/assistant-core/src/notifier/bot_handler.py
    - /opt/assistant-core/.importlinter
    - /opt/assistant-core/tests/test_composition_di.py
    - /opt/assistant-core/tests/test_core_architecture.py

key-decisions:
  - "Дефект /timesheet (NameError cur_m_name) не исправлен: решение владельца 2026-10-02, поведение заморожено тестом test_cmd_timesheet_characterization"
  - "Drive внедряется фабрикой, а не экземпляром: сохраняется «свежий клиент на колбэк», token.json не читается в конструкторе"
  - "main.py и live_ticker.py не менялись: DI живой сводки и контракт live-ticker-no-adapters - план 02-04, Задача 1"
  - "Непрямой путь use-case -> src.composition -> коннектор разрешён (D-12), комментарий добавлен над allow_indirect_imports"

requirements-completed: [PRT-04]

coverage:
  - id: D1
    description: "Три пути бота (/timesheet, синхронизация табеля с Google Drive, AADHk-ветка документа) и их неавторизованные ветки зафиксированы характеризацией до рефакторинга; тесты зелёные без изменений после него"
    requirement: PRT-04
    verification:
      - kind: unit
        ref: "tests/test_composition_di.py#test_cmd_timesheet_characterization"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_timesheet_sync_success_text"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_document_aadhk_branch_text"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_cmd_timesheet_unauthorized_does_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_timesheet_sync_unauthorized"
        status: pass
    human_judgment: false
  - id: D2
    description: "EmailBotHandler получает зависимости через конструктор, значения по умолчанию собирает src.composition; старый вызов EmailBotHandler(db=..., allowed_user_id=...) работает; секретарь получает тот же сервис табеля"
    requirement: PRT-04
    verification:
      - kind: unit
        ref: "tests/test_composition_di.py#test_bot_uses_injected_timesheet_service"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_bot_uses_injected_drive_client_factory"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_bot_defaults_come_from_composition"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_bot_passes_timesheet_service_to_secretary"
        status: pass
    human_judgment: false
  - id: D3
    description: "Модуль bot_handler не содержит имён конкретных коннекторов; суммарный долг ignore_imports равен 0; import-linter: 3 kept, 0 broken"
    requirement: PRT-04
    verification:
      - kind: unit
        ref: "tests/test_composition_di.py#test_bot_handler_has_no_concrete_connector_names"
        status: pass
      - kind: unit
        ref: "tests/test_core_architecture.py#test_ignore_imports_debt_is_zero"
        status: pass
      - kind: other
        ref: "cd /opt/assistant-core && .venv/bin/lint-imports --no-logo --no-cache (Contracts: 3 kept, 0 broken)"
        status: pass
    human_judgment: false
  - id: D4
    description: "HITL и авторизация бота не ослаблены: safety-тесты бота без правок и зелёные"
    requirement: PRT-04
    verification:
      - kind: unit
        ref: "tests/test_hitl_safety_guardrails.py, tests/test_bot_group_isolation.py, tests/test_lms_bot_workflow.py, tests/test_fast_intent_router.py (без правок, зелёные)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Полный гейт качества зелёный, assistant-core 207 тестов (было 192)"
    verification:
      - kind: other
        ref: "env -u PYTEST_ADDOPTS python3 /opt/chat-app/scripts/gate.py (ИТОГ: ЗЕЛЁНЫЙ)"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-10-02
status: complete
---

# Phase 2 Plan 03: DI бота и обнуление долга ignore_imports Summary

**EmailBotHandler получает клиент ЛК, отправщик почты, сервис табеля и фабрику Google Drive через конструктор (значения по умолчанию собирает src.composition), поведение трёх непокрытых путей бота заморожено характеризационными тестами, закоммиченными до рефакторинга, долг ignore_imports равен 0, import-linter: 3 kept, 0 broken.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-02T09:56:00Z
- **Completed:** 2026-10-02T10:01:30Z
- **Tasks:** 2
- **Files modified:** 5 (все в assistant-core)

## Accomplishments

- Задача 1: 9 характеризационных тестов в `tests/test_composition_di.py` пишутся и проходят на НЕизменённом `bot_handler.py` (коммит `02241b9` затрагивает только этот файл). Патчатся только модули-источники `src.connectors.aadhk.parser.AadhkIngestionService` и `src.connectors.gdrive.client.GoogleDriveClient`; загрузка файла замокана, `/opt/chat-app/uploads/synthetic_backup.db` не создаётся; `token.json` не читается.
- Задача 2: три фабрики в `src/composition.py` (ленивые импорты), DI в `EmailBotHandler` (`timesheet_service`, `drive_client_factory` добавлены в конец сигнатуры, `_timesheet()`), три места инлайн-импорта и два импорта верхнего уровня удалены; `SecretaryDialogEngine(db=self.db, timesheet_service=self.timesheet_service)`.
- Из контракта `bot-handler-no-adapters` удалены четыре записи долга, добавлен комментарий о разрешённом непрямом импорте через `src.composition`; новый `test_ignore_imports_debt_is_zero`.
- Старые тесты бота (`test_lms_bot_workflow`, `test_fast_intent_router`, `test_hitl_safety_guardrails`, `test_bot_group_isolation`, `test_bot_menu`, `test_email_reply_workflow`, `test_secretary_dialog`, `test_live_ticker`) прошли без правок; в `tests/` относительно `06792b7` только строки `A`.

## Task Commits

Все коммиты в `/opt/assistant-core` (ветка main, без push):

1. **Task 1: характеризация трёх путей бота до DI** - `02241b9` (test)
2. **Task 2: DI в EmailBotHandler, фабрики сборщика, долг = 0** - `c5820eb` (feat)

**Plan metadata:** коммит docs в /opt/chat-app (см. git log, `docs(02-03)`).

## Files Created/Modified

- `/opt/assistant-core/src/composition.py` - `default_lms_client`, `default_email_sender`, `default_drive_client`
- `/opt/assistant-core/src/notifier/bot_handler.py` - DI, `_timesheet()`, аннотации протоколами, без имён конкретных коннекторов
- `/opt/assistant-core/.importlinter` - пустой долг, комментарий над `allow_indirect_imports`
- `/opt/assistant-core/tests/test_composition_di.py` - 9 тестов характеризации и 5 тестов внедрения, фикстура `in_memory_db`
- `/opt/assistant-core/tests/test_core_architecture.py` - `test_ignore_imports_debt_is_zero`

## Decisions Made

- Дефект `/timesheet` оставлен как есть (решение владельца 2026-10-02); тест-фиксатор `test_cmd_timesheet_characterization` ожидает `NameError`.
- Drive внедряется фабрикой: сохраняется «свежий клиент на колбэк», `is_configured` (читает token.json) в конструкторе не вызывается.
- `main.py` не менялся (корень композиции вне контрактов, тесты импортируют `src.main.run_lms_monitor_cycle`); `live_ticker.py` не менялся - план 02-04, Задача 1.
- Делегирование Antigravity не использовалось: характеризация требует подгонки литералов под вывод, а DI затрагивает границу HITL.

## Deviations from Plan

None - plan executed exactly as written.

Замечание по числам: план говорил о «пяти записях» долга Фазы 1; после 02-01 осталось четыре (запись для секретаря снята в 02-01), все четыре сняты здесь.

## Issues Encountered

None.

## Backlog (для владельца)

1. **Дефект команды /timesheet.** `handle_cmd_timesheet` (`/opt/assistant-core/src/notifier/bot_handler.py`, f-строка заголовка табеля, примерно строка 1107 в исходном файле) ссылается на неопределённое имя `cur_m_name` (определён только список `month_names`) и падает с `NameError` после расчёта, ничего не отправляя. Решение владельца 2026-10-02: не чинить в Фазе 2. Нужна отдельная задача на исправление. Тест-фиксатор `test_cmd_timesheet_characterization` (`pytest.raises(NameError, match="cur_m_name")`) при исправлении переписывают в той же задаче.
2. **docs/BASELINE.md в chat-app устарел** (долг «5 записей», «2 kept»): после 02-03 долг 0, контрактов 3, после 02-04 станет 4; число тестов assistant-core 207. Обновление вне D-18 - следующий шаг владельца.

## Known Stubs

None. Известный дефект `/timesheet` - не заглушка, а сознательно замороженное поведение (см. Backlog).

## Threat Flags

None - новых сетевых точек, путей аутентификации и доступа к файлам нет. Проверки угроз: T-02-10 (HITL/авторизация) - safety-тесты без правок зелёные, неавторизованные пути табеля покрыты; T-02-11 - характеризация в отдельном коммите, предшествует первой правке `bot_handler.py` (`git merge-base --is-ancestor`); T-02-12 - `download_file` замокан, файла в uploads нет; T-02-13 - `test_ignore_imports_debt_is_zero`; T-02-14 - Drive фабрикой, клиенты в конструкторе не создаются; T-02-SC - пакеты не устанавливались.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 02-04: DI `LiveTickerService` и контракт `live-ticker-no-adapters` (в `bot_handler` строка `LiveTickerService(db=self.db)` оставлена без изменений).
- Флаг допущений edge-probe PRT-04 трактован как в плане (необязательные параметры с `None`, контракты без `ignore_imports`, непрямой импорт через `src.composition` разрешён); требует ручной проверки на верификации.
- Блокеров нет.

## Self-Check: PASSED

- Файлы существуют: composition.py, bot_handler.py, .importlinter, test_composition_di.py, test_core_architecture.py (изменены в коммитах `02241b9`, `c5820eb`).
- Коммиты найдены: `02241b9`, `c5820eb`; `git rev-list --count 7410deb..HEAD` = 2.
- Критерии приёмки: долг = 0, `lint-imports` 3 kept, 0 broken, характеризация предшествует правке бота, существующие тесты не изменены (в `tests/` только `A`), `test_composition_di.py` 18 тестов, гигиена секретов «нарушений: 0», гейт «ИТОГ: ЗЕЛЁНЫЙ», assistant-core 207 тестов (порог 183).

---
*Phase: 02-porty-i-domen-bez-izmeneniya-povedeniya*
*Completed: 2026-10-02*
