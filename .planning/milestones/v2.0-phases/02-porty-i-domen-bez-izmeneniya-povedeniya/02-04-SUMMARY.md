---
phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
plan: 04
subsystem: architecture
tags: [dependency-injection, event-bus, domain-events, import-linter, characterization-tests, asyncio]

requires:
  - phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
    provides: "src/core (домен, порты), src/composition.default_timesheet_service, DI в EmailBotHandler с атрибутом timesheet_service, долг ignore_imports = 0 после 02-03"
provides:
  - "LiveTickerService(db, timesheet_service=None): сервис табеля через конструктор, дефолт лениво из src.composition внутри try"
  - "контракт live-ticker-no-adapters с пустым ignore_imports; lint-imports: 4 kept, 0 broken"
  - "src/core/domain/events.py: DomainEvent и шесть доменных событий (frozen, slots, kw_only, UTC)"
  - "src/core/events/bus.py: EventBus (subscribe, async publish), доставка по точному типу, изоляция сбоя подписчика"
  - "отчёт приёмки фазы 2 (гейт зелёный, 223 теста assistant-core)"
affects: [03-persona, 05-plugins, 06-isolation, 07-integrations]

actuals:
  tokens: 4690
  tasks: 3
  commits: 3
plan_head_before: c5820eb9cdf0134527b05314292ccd3720aaf1cd
plan_head_after: 150e9b3b0698a1dc1c92599bcc61038ec10b3e6e

tech-stack:
  added: []
  patterns:
    - "характеризация до рефакторинга: отдельный коммит только с тестом (live_ticker, a973c2b), патчится модуль-источник AadhkIngestionService"
    - "новый параметр DI в конце сигнатуры, None по умолчанию, выбор через is not None, дефолт собирается внутри существующего try"
    - "шина: словарь подписчиков по точному type(event), обход копии списка, перехват только Exception, в журнал только qualname обработчика и имя типа события"
    - "события: frozen+slots+kw_only dataclass, occurred_at = datetime.now(timezone.utc)"

key-files:
  created:
    - /opt/assistant-core/src/core/domain/events.py
    - /opt/assistant-core/src/core/events/__init__.py
    - /opt/assistant-core/src/core/events/bus.py
    - /opt/assistant-core/tests/test_core_events.py
  modified:
    - /opt/assistant-core/src/notifier/live_ticker.py
    - /opt/assistant-core/src/notifier/bot_handler.py
    - /opt/assistant-core/.importlinter
    - /opt/assistant-core/tests/test_composition_di.py
    - /opt/assistant-core/tests/test_core_architecture.py

key-decisions:
  - "Одна конкретная шина EventBus без отдельного Protocol (KISS/YAGNI): потребителей нет, порт появится со второй реализацией"
  - "Доставка по точному типу: подписка на DomainEvent не получает TaskCreated; отписок и подписки на подклассы нет"
  - "Шина не подключена к боевым потокам (D-17), охраняется тестом test_bus_not_wired_into_production_flows"
  - "main.py не менялся: LiveTickerService(db) в main.py получает дефолт из src.composition"

requirements-completed: [PRT-04, PRT-05]

coverage:
  - id: D1
    description: "LiveTickerService получает сервис табеля через конструктор; поведение get_timesheet_metrics (успех и словарь-заглушка с предупреждением) зафиксировано характеризацией до правки и не изменилось"
    requirement: PRT-04
    verification:
      - kind: unit
        ref: "tests/test_composition_di.py#test_live_ticker_timesheet_characterization"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_live_ticker_timesheet_fallback_on_error"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_live_ticker_uses_injected_timesheet_service"
        status: pass
      - kind: unit
        ref: "tests/test_composition_di.py#test_bot_passes_timesheet_service_to_ticker"
        status: pass
      - kind: unit
        ref: "tests/test_live_ticker.py (без правок)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Контракт live-ticker-no-adapters без записей ignore_imports; суммарный долг 0; import-linter 4 kept, 0 broken"
    requirement: PRT-04
    verification:
      - kind: unit
        ref: "tests/test_core_architecture.py#test_use_case_contracts_not_weakened"
        status: pass
      - kind: unit
        ref: "tests/test_core_architecture.py#test_ignore_imports_debt_is_zero"
        status: pass
      - kind: other
        ref: "cd /opt/assistant-core && .venv/bin/lint-imports --no-logo --no-cache (Contracts: 4 kept, 0 broken)"
        status: pass
    human_judgment: false
  - id: D3
    description: "EventBus доставляет событие подписчику точного типа последовательно, поддерживает sync и async обработчики, без брокера и сторонних зависимостей"
    requirement: PRT-05
    verification:
      - kind: unit
        ref: "tests/test_core_events.py#test_publish_delivers_to_subscriber"
        status: pass
      - kind: unit
        ref: "tests/test_core_events.py#test_handlers_called_in_subscription_order"
        status: pass
      - kind: unit
        ref: "tests/test_core_events.py#test_dispatch_is_exact_type_only"
        status: pass
      - kind: unit
        ref: "tests/test_core_events.py#test_sync_and_async_handlers"
        status: pass
      - kind: unit
        ref: "tests/test_core_architecture.py#test_core_imports_only_stdlib_and_core"
        status: pass
    human_judgment: false
  - id: D4
    description: "Сбой подписчика изолирован и журналируется без содержимого события; CancelledError не глотается"
    requirement: PRT-05
    verification:
      - kind: unit
        ref: "tests/test_core_events.py#test_failing_subscriber_is_isolated"
        status: pass
      - kind: unit
        ref: "tests/test_core_events.py#test_failure_log_has_no_payload"
        status: pass
      - kind: unit
        ref: "tests/test_core_events.py#test_cancelled_error_propagates"
        status: pass
    human_judgment: false
  - id: D5
    description: "Шесть доменных событий: неизменяемые dataclass-наследники DomainEvent, UTC и уникальный event_id; шина не подключена к боевым потокам"
    requirement: PRT-05
    verification:
      - kind: unit
        ref: "tests/test_core_events.py#test_six_domain_event_types"
        status: pass
      - kind: unit
        ref: "tests/test_core_events.py#test_events_are_frozen"
        status: pass
      - kind: unit
        ref: "tests/test_core_events.py#test_event_defaults_utc_and_unique_id"
        status: pass
      - kind: unit
        ref: "tests/test_core_events.py#test_bus_not_wired_into_production_flows"
        status: pass
    human_judgment: false
  - id: D6
    description: "Трактовка PRT-05 (edge-probe, unclassified): «без брокера» = только stdlib и src.core, «без межпроцессной передачи» = словарь в объекте без потоков и очередей, «доставляет» = тот же объект события"
    requirement: PRT-05
    verification: []
    human_judgment: true
    rationale: "Флаг допущений edge-probe помечен unresolved: трактовку формулировки требования подтверждает человек на верификации"
  - id: D7
    description: "Приёмка фазы 2: гейт зелёный, тесты не сужены, существующие тесты не тронуты, сервисы не активны"
    verification:
      - kind: other
        ref: "env -u PYTEST_ADDOPTS python3 /opt/chat-app/scripts/gate.py (ИТОГ: ЗЕЛЁНЫЙ)"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-02
status: complete
---

# Phase 2 Plan 04: DI живой сводки, EventBus и приёмка фазы Summary

**LiveTickerService получает сервис табеля через конструктор (контракт live-ticker-no-adapters без долга, lint-imports 4 kept, 0 broken), добавлены шесть неизменяемых доменных событий и внутрипроцессный EventBus на asyncio с изоляцией сбоя подписчика и без утечки содержимого события в журнал; фаза 2 принята: гейт «ИТОГ: ЗЕЛЁНЫЙ», 223 теста assistant-core.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-02T10:03:13Z
- **Completed:** 2026-10-02T10:07:00Z
- **Tasks:** 3
- **Files modified:** 9 (все в assistant-core)

## Accomplishments

- Задача 1: характеризация `get_timesheet_metrics` (успех и заглушка с предупреждением) закоммичена отдельно (`a973c2b`, только `tests/test_composition_di.py`) до первой правки `live_ticker.py`; затем DI в `LiveTickerService`, передача `timesheet_service` из `EmailBotHandler`, контракт `live-ticker-no-adapters` с пустым `ignore_imports`, обновлён комментарий над `allow_indirect_imports` в `brain-no-adapters`, расширен `test_use_case_contracts_not_weakened`. `tests/test_live_ticker.py` и `main.py` не менялись.
- Задача 2: `src/core/domain/events.py` (`DomainEvent` + 6 наследников, `frozen+slots+kw_only`, `datetime.now(timezone.utc)`), `src/core/events/bus.py` (`EventBus`), 12 тестов PRT-05. Рантайм-страж ядра и контракт core-is-pure приняли новые модули без правок.
- Задача 3: приёмка фазы (отчёт ниже). Делегирование Antigravity не использовалось: объём малый, `bus.py` по плану пишет исполнитель сам.

## Task Commits

Все коммиты в `/opt/assistant-core` (ветка main, без push):

1. **Task 1a: характеризация живой сводки до DI** - `a973c2b` (test)
2. **Task 1b: DI в LiveTickerService, контракт live-ticker-no-adapters** - `4cf3695` (feat)
3. **Task 2: доменные события и EventBus** - `150e9b3` (feat)
4. **Task 3:** изменяемых файлов нет, только проверки

**Plan metadata:** коммит docs в /opt/chat-app (см. git log, `docs(02-04)`).

## Files Created/Modified

- `/opt/assistant-core/src/notifier/live_ticker.py` - параметр и атрибут `timesheet_service`, дефолт `default_timesheet_service(self.db)` внутри try
- `/opt/assistant-core/src/notifier/bot_handler.py` - `LiveTickerService(db=self.db, timesheet_service=self.timesheet_service)`
- `/opt/assistant-core/.importlinter` - контракт `live-ticker-no-adapters`, обновлённый комментарий
- `/opt/assistant-core/src/core/domain/events.py` - `DomainEvent` и шесть событий
- `/opt/assistant-core/src/core/events/__init__.py`, `bus.py` - `EventBus`
- `/opt/assistant-core/tests/test_composition_di.py` - 4 новых теста (было 18 после 02-03, стало 22)
- `/opt/assistant-core/tests/test_core_architecture.py` - расширен `test_use_case_contracts_not_weakened`
- `/opt/assistant-core/tests/test_core_events.py` - 12 тестов PRT-05

## Decisions Made

- Одна конкретная шина `EventBus` без отдельного Protocol (KISS/YAGNI, потребителей нет, D-17).
- Доставка по точному `type(event)`, без отписок и подписки на подклассы.
- События без полезной нагрузки, кроме `DelegatedToSpecialist`; поля добавят фазы с публикаторами.
- В журнал сбоя подписчика попадают только `__qualname__` обработчика и имя типа события; `logger.exception` пишет трассировку самого исключения обработчика, содержимое события не передаётся.

## Deviations from Plan

None - plan executed exactly as written.

Замечания по числам и проверкам (не отклонения):
- Пороги тестов в плане (≥ 187, ≥ 199) нижние границы; фактически 223, так как 02-03 закончился на 207.
- Четвёртая проверка Задачи 3 (`git status --porcelain -- . ":(exclude).planning"` в chat-app пуст) формально выдаёт `?? .gsd/`. Это неотслеживаемый каталог, существовавший до фазы (виден в gitStatus на старте), не создан и не изменён этим планом; изменений отслеживаемых файлов chat-app вне `.planning/` нет (`git diff --name-only f977191..HEAD -- . ":(exclude).planning"` пуст).

## Issues Encountered

None.

## Отчёт приёмки фазы 2

- **Гейт** `env -u PYTEST_ADDOPTS python3 /opt/chat-app/scripts/gate.py`: «ИТОГ: ЗЕЛЁНЫЙ», код 0. chat-app: 68 тестов; assistant-core: 223 теста (порог 199). import-linter обоих репозиториев, security_shield (--all) обоих, дрейф SHA-256 синтетической персоны, боевая assistant.db не изменена: все зелёные.
- **lint-imports (assistant-core):** «Contracts: 4 kept, 0 broken» (brain-no-adapters, bot-handler-no-adapters, live-ticker-no-adapters, core-is-pure); долг `ignore_imports` = 0 (`test_ignore_imports_debt_is_zero`, `tests/test_architecture_contract.py` зелёные: 6 passed).
- **Существующие тесты не тронуты:** `git diff --name-status 06792b7..HEAD -- tests/` в assistant-core — только строки `A` (test_composition_di.py, test_core_architecture.py, test_core_domain.py, test_core_events.py, test_ports_conformance.py).
- **Границы репозиториев:** в chat-app нет изменений отслеживаемых файлов вне `.planning/` (см. замечание про `.gsd/`); `git status --porcelain` в assistant-core пуст.
- **Сервисы (`systemctl is-active`):** assistant-worker `failed`, chat-app `inactive`, dev-bridge `inactive`: ни один не active, заморозка сохранена; сервисы не запускались и не перезапускались.

### Критерии успеха ROADMAP Фазы 2 и тесты-доказательства

1. **Поведение прежнее, 100% pytest:** гейт «ИТОГ: ЗЕЛЁНЫЙ» (chat-app 68, assistant-core 223); существующие тесты неизменны (в `tests/` только `A`); характеризации `test_tydex_context_*`, `test_cmd_timesheet_characterization`, `test_timesheet_sync_*`, `test_document_aadhk_branch_*`, `test_live_ticker_timesheet_*` закоммичены до правок src.
2. **Коннекторы соответствуют портам:** `tests/test_ports_conformance.py`.
3. **Use-cases бота не импортируют адаптеры:** `test_ignore_imports_debt_is_zero`, `lint-imports` (4 контракта, включая `live-ticker-no-adapters`), `test_bot_handler_has_no_concrete_connector_names`, `test_live_ticker_uses_injected_timesheet_service`, `test_bot_passes_timesheet_service_to_ticker`.
4. **Домен и ядро чисты:** `tests/test_core_domain.py`, `tests/test_core_architecture.py` (рантайм-страж, core-is-pure, отсутствие профильных токенов).
5. **EventBus без внешних зависимостей и брокера:** `tests/test_core_events.py` (12 тестов) плюс рантайм-страж ядра.

## Backlog (для владельца)

1. **Дефект команды /timesheet** (`handle_cmd_timesheet`, `/opt/assistant-core/src/notifier/bot_handler.py`, f-строка заголовка табеля, строка ~1107 в исходном файле): ссылается на неопределённое имя `cur_m_name` и падает с `NameError` после расчёта, ничего не отправляя. Решение владельца 2026-10-02: не чинить в Фазе 2; нужна отдельная задача на исправление (backlog). Тест-фиксатор `test_cmd_timesheet_characterization` (`pytest.raises(NameError, match="cur_m_name")`) при исправлении переписывают в той же задаче.
2. **Открытый вопрос владельцу: docs/BASELINE.md в chat-app устарел** (долг «5 записей», «2 kept»): фактически долг 0, контрактов 4, тестов assistant-core 223. Обновление вне D-18 (chat-app вне `.planning/` не менялся) — решение владельца.
3. **Ручная проверка флага edge-probe PRT-05** (unresolved) на верификации: трактовка формулировок «без брокера», «без межпроцессной передачи», «доставляет» (см. coverage D6).

## Known Stubs

None. Шина сознательно не подключена к боевым потокам (D-17): это не заглушка, а граница фазы; публикаторы появятся в следующих фазах.

## Threat Flags

None - новых сетевых точек, путей аутентификации и доступа к файлам нет. Проверки угроз: T-02-15 - `test_failure_log_has_no_payload`; T-02-16 - `test_failing_subscriber_is_isolated`, `test_cancelled_error_propagates`; T-02-17 - `test_bus_not_wired_into_production_flows`; T-02-18 - `env -u PYTEST_ADDOPTS`, нижняя граница по строке гейта, дифф `tests/` без `M`/`D`; T-02-19 - характеризация в отдельном коммите `a973c2b`, предшествует правке `live_ticker.py` (`4cf3695`); T-02-20 - контракт `live-ticker-no-adapters` проверен через configparser, расширен `test_use_case_contracts_not_weakened`; T-02-SC - пакеты не устанавливались, шина на stdlib.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Фаза 2 принята, готова к верификации (`/gsd-verify-work`) и переходу к Фазе 3 (персона в данных).
- Блокеров нет. Открытые пункты владельцу: backlog /timesheet, обновление BASELINE.md, ручная проверка трактовки PRT-05.

## Self-Check: PASSED

- Файлы существуют: events.py, events/__init__.py, events/bus.py, test_core_events.py, live_ticker.py, bot_handler.py, .importlinter, test_composition_di.py, test_core_architecture.py (в коммитах `a973c2b`, `4cf3695`, `150e9b3`).
- Коммиты найдены; `git rev-list --count c5820eb..HEAD` = 3.
- Критерии приёмки Задач 1-3 выполнены; гигиена секретов (`check_file_content`) «нарушений: 0»; гейт «ИТОГ: ЗЕЛЁНЫЙ»; lint-imports «4 kept, 0 broken».

---
*Phase: 02-porty-i-domen-bez-izmeneniya-povedeniya*
*Completed: 2026-10-02*
