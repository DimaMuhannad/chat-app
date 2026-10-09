---
phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
verified: 2026-10-02T12:00:00Z
status: passed
score: 4/5 must-haves verified
covered_files:
  - .planning/phases/02-porty-i-domen-bez-izmeneniya-povedeniya/02-01-PLAN.md
  - .planning/phases/02-porty-i-domen-bez-izmeneniya-povedeniya/02-01-SUMMARY.md
  - .planning/phases/02-porty-i-domen-bez-izmeneniya-povedeniya/02-02-PLAN.md
  - .planning/phases/02-porty-i-domen-bez-izmeneniya-povedeniya/02-02-SUMMARY.md
  - .planning/phases/02-porty-i-domen-bez-izmeneniya-povedeniya/02-03-PLAN.md
  - .planning/phases/02-porty-i-domen-bez-izmeneniya-povedeniya/02-03-SUMMARY.md
  - .planning/phases/02-porty-i-domen-bez-izmeneniya-povedeniya/02-04-PLAN.md
  - .planning/phases/02-porty-i-domen-bez-izmeneniya-povedeniya/02-04-SUMMARY.md
covered_digest: "v2:sha256:918a4a3d5f3e0a4d91bd7e90b5d470ffd972f4000ff68606a3aa735cf268688b"
behavior_unverified: 0
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
human_verification:
  - test: "SC4: подтвердить трактовку «use-cases зависят только от портов и домена» (D-04)"
    expected: "Владелец принимает, что use-cases (IntentRouter, Methodist, SecretaryDialog) могут зависеть от src.storage.db.Database, src.models.* и src.config наравне с src.core, а перевод на доменные сущности откладывается на Фазу 3+. Если нужна буквальная трактовка, это новый объём работ"
    why_human: "Решение D-04 сужает формулировку критерия 4. Код: brain/intent_router.py и methodist.py импортируют src.storage.db, secretary_dialog.py ещё и src.models.schedule и src.composition. Доменные сущности use-cases не используют, их потребляют только порты и адаптеры. Контракт линтера запрещает только конкретные адаптеры"
  - test: "PRT-02/PRT-03: подтвердить допущения edge-probe (все методы портов async, пометка подтверждения только декларативная)"
    expected: "Принято: sync-разбор ScheduleParser оборачивается async-адаптером; BaseLMSProvider.REQUIRES_CONFIRMATION = {submit_grade, delete_task} - константа плюс тест, механизм @requires_confirmation приходит в Фазе 5; GuapLmsClient соответствует порту через адаптер, а не напрямую"
    why_human: "Формулировка PRT-02 «помечены как требующие подтверждения» допускает и декларативное, и исполняемое толкование. Код реализует декларативное (см. WR-02). Safety-вопрос: принять риск до Фазы 5 или добавить параметр confirmed в адаптер сейчас"
  - test: "PRT-04: подтвердить допущения edge-probe (необязательные параметры None, непрямой импорт через src.composition разрешён)"
    expected: "Принято: «через конструктор» = параметры X | None = None с ленивым дефолтом из src.composition; use-cases (brain, bot_handler, live_ticker) непрямо достигают коннекторов через src.composition (allow_indirect_imports = True); путь Google Drive всё ещё сам создаёт AadhkIngestionService внутри GoogleDriveClient.sync_aadhk_from_drive (WR-03), так что подмена timesheet_service не затрагивает ингест на этом пути"
    why_human: "Трактовка формулировки требования. Поведение сохранено (характеризационные тесты зелёные), но полнота DI на пути Drive зависит от того, считает ли владелец это достаточным до появления второго провайдера табеля"
  - test: "PRT-05: подтвердить допущения edge-probe (трактовка «без брокера», «без межпроцессной передачи», «доставляет»)"
    expected: "Принято: «без брокера» = только stdlib и src.core; «без межпроцессной передачи» = словарь подписчиков в объекте шины; «доставляет» = подписчику передаётся тот же объект события (проверено: got[0] is event); доставка только по точному типу, без unsubscribe и таймаута (IN-02)"
    why_human: "Трактовка формулировки требования; ограничения шины (точный тип, нет отписки, нет таймаута, traceback в журнале может содержать текст исключения обработчика) нужно принять осознанно"
  - test: "Живой запуск бота и демона после снятия остановки сервиса"
    expected: "После ручного перезапуска assistant-worker (не выполнялся, сервис failed с 2026-10-01 до фазы) команды /today, живая сводка, секретарь с вопросом о табеле и синхронизация табеля с Google Drive отвечают как раньше"
    why_human: "Верификатору запрещено перезапускать сервисы. Эквивалентность подтверждена характеризационными тестами и ревью диффа, но не живым прогоном"
---

# Phase 2: Порты и домен без изменения поведения - Отчёт верификации

**Phase Goal:** Ядро ассистента зависит от абстрактных портов, а не от конкретных классов GUAP/AADHk/Google, при этом бот и демон ведут себя ровно как раньше.
**Verified:** 2026-10-02
**Status:** human_needed
**Re-verification:** Нет, первичная верификация

Вывод: код фазы соответствует цели. Блокирующих расхождений нет, все автоматически проверяемые условия выполнены. Статус human_needed из-за пяти пунктов, где решает человек: четыре допущения edge-probe и одна трактовка критерия 4. Живой прогон бота не выполнялся: сервис остановлен до фазы, перезапуск запрещён.

## Достижение цели

### Наблюдаемые истины (контракт ROADMAP)

| # | Истина | Статус | Доказательства |
|---|--------|--------|----------------|
| 1 | Все существующие тесты проходят без изменения фикстур (100% pytest в обоих репозиториях) | VERIFIED | `git diff --name-status 06792b7..HEAD -- tests/` даёт только пять строк `A` (test_composition_di, test_core_architecture, test_core_domain, test_core_events, test_ports_conformance); ни одного `M`/`D`. Свой прогон: assistant-core `223 passed`; гейт `env -u PYTEST_ADDOPTS python3 scripts/gate.py`: chat-app 68 passed, assistant-core 223 passed, ИТОГ: ЗЕЛЁНЫЙ |
| 2 | Protocol-проверка подтверждает соответствие ScheduleParser, GoogleCalendarClient, AadhkIngestionService, GuapLmsClient своим портам; роли разделены (schedule_source, calendar_sync, lms) | VERIFIED (через адаптеры) | `tests/test_ports_conformance.py`: `test_adapter_conforms_to_port[schedule/calendar/timesheet/lms]` (isinstance), `test_port_methods_are_coroutines_on_adapter` (iscoroutinefunction по каждому методу порта), `test_schedule_roles_are_separated` (isinstance в обе стороны отрицателен, роли разные). Соответствие через адаптеры-обёртки допускает PRT-03. Допущение edge-probe: см. human_verification 2 |
| 3 | `secretary_dialog.py` и `bot_handler.py` получают зависимости через конструктор; `ignore_imports` пуст; import-linter зелёный на реальных модулях | VERIFIED | Диф: `SecretaryDialogEngine(..., timesheet_service=None)`, `EmailBotHandler(..., timesheet_service=None, drive_client_factory=None)`, `LiveTickerService(db, timesheet_service=None)`. В `.importlinter` четыре строки `ignore_imports =` пусты. `lint-imports`: `4 kept, 0 broken`. Мутационная проба на копии (в scratchpad добавлены прямые импорты коннекторов в brain, bot_handler, live_ticker и импорт src.storage в ядро): `0 kept, 4 broken`, значит контракты реально ловят нарушения. Inline-импортов коннекторов в brain/bot_handler/live_ticker нет |
| 4 | Домен: неизменяемые dataclass, `WorkspaceClearance` с тремя значениями; use-cases (IntentRouter, SecretaryDialog, Methodist) зависят только от портов и домена | UNCERTAIN (WARNING, решение человека) | Домен подтверждён: `entities.py`: семь `@dataclass(frozen=True, slots=True)`, `WorkspaceClearance` = `['public','internal','restricted_nda']` (проверено запуском), тесты frozen/slots/clearance/synthetic_workspaces зелёные. Но use-cases зависят от `src.storage.db.Database`, `src.models.schedule`, `src.config`, а не только от портов и домена; доменные сущности use-cases не используют. Это закреплено решением D-04 (замена трактовки критерия). Вердикт за владельцем, см. human_verification 1 |
| 5 | Внутрипроцессный EventBus доставляет событие подписчику без внешних зависимостей и брокера | VERIFIED | Собственный запуск: после импорта новых top-level модулей только stdlib (`_datetime, copy, dataclasses, datetime, platform, uuid`) и `src`; `publish(DialogMemoryCleared())` отдаёт подписчику тот же объект (`got[0] is e`), `occurred_at.tzinfo == UTC`. Тесты: `test_publish_delivers_to_subscriber`, `test_failing_subscriber_is_isolated`, `test_cancelled_error_propagates`, `test_dispatch_is_exact_type_only`, `test_core_imports_only_stdlib_and_core`. Шина нигде не подключена: `grep` по `src` не находит `.publish(`, `EventBus` или `core.events` вне `src/core` |

**Счёт:** 4/5 истин подтверждено, 0 behavior-unverified, 1 UNCERTAIN (трактовка, не провал).

### Дополнительные истины из PLAN (выборочно, поверх ROADMAP)

| Истина | Статус | Доказательства |
|--------|--------|----------------|
| Характеризационные тесты закоммичены ДО правки src | VERIFIED | `cd54595` (test, секретарь) раньше `98f1c0f`; `02241b9` (test, бот) раньше `c5820eb`; `a973c2b` (test, живая сводка) раньше `4cf3695`. Каждый коммит меняет только `tests/test_composition_di.py` |
| Контракт `core-is-pure`: 13 запрещённых модулей, долг 0 | VERIFIED | `.importlinter` строки core-is-pure; `test_core_is_pure_forbids_every_other_src_module`, `test_ignore_imports_debt_is_zero` зелёные |
| Адаптер ЛК и шина не подключены к боевым потокам | VERIFIED (слабая защита) | grep: `GuapLmsProvider`, `GoogleCalendarSink`, `ScheduleParserSource` встречаются только в собственных модулях; `AadhkTimesheetProvider` только в `composition.py`. Защита тестами подстрочная (IN-04) |
| Поведение `/timesheet` заморожено (NameError `cur_m_name` не исправлен) | VERIFIED | `bot_handler.py:1122` по-прежнему использует `cur_m_name`; решение владельца 2026-10-02; `test_cmd_timesheet_characterization` |
| Профиль владельца не вшит в ядро | VERIFIED | `test_core_has_no_profile_tokens`; `WorkRecord.project_tag` без значения по умолчанию; в портах `...` вместо дефолтов |
| Изменений вне `.planning/` в chat-app нет | VERIFIED | `git status` chat-app: только untracked `.gsd/`, `.planning/config.json`, `.planning/milestone.lock`, `.planning/state.json` |
| Сервисы не перезапускались | VERIFIED | `assistant-worker`: failed (как до фазы), `chat-app`: inactive |

### Необходимые артефакты

| Артефакт | Ожидание | Статус | Детали |
|----------|----------|--------|--------|
| `src/core/domain/entities.py` | 7 сущностей, `ConnectorRole`, `WorkspaceClearance` | VERIFIED | frozen+slots, только stdlib |
| `src/core/domain/events.py` | `DomainEvent` + 6 событий | VERIFIED | frozen+slots+kw_only, UTC |
| `src/core/events/bus.py` | `EventBus` | VERIFIED | подписчики по `type(event)`, изоляция `Exception`, `CancelledError` не перехватывается |
| `src/core/ports/connectors.py` | 5 портов PRT-02 | VERIFIED | `runtime_checkable`, все методы `async`, `REQUIRES_CONFIRMATION` |
| `src/core/ports/clients.py` | `LmsClientLike`, `EmailSenderLike`, `DriveClientLike` | VERIFIED | синхронный Protocol клиента ЛК; `test_existing_clients_match_di_protocols` |
| `src/composition.py` | Фабрики с ленивыми импортами | VERIFIED | 4 фабрики; патчи модулей-источников работают |
| Адаптеры (aadhk, parser, calendar, guap_lms `provider.py`) | Обёртки под порты | VERIFIED | substantive, делегируют без копирования дефолтов профиля |
| `.importlinter` | 4 контракта, пустой долг | VERIFIED | `4 kept, 0 broken` |
| Тесты (5 новых файлов, 84 теста) | Покрытие PRT-01..05 | VERIFIED | все зелёные, ни один существующий файл не изменён |

### Проверка ключевых связей

| От | К | Через | Статус |
|----|---|-------|--------|
| `secretary_dialog._get_tydex_context` | `composition.default_timesheet_service` | `self.timesheet_service` или дефолт внутри существующего `try` | WIRED |
| `bot_handler.__init__` | `SecretaryDialogEngine`, `LiveTickerService` | `timesheet_service=self.timesheet_service` | WIRED |
| `bot_handler` (`_timesheet()`, документ, `/timesheet`, sync) | `composition` | `default_*` фабрики | WIRED |
| `live_ticker.get_timesheet_metrics` | `composition.default_timesheet_service` | дефолт внутри `try` | WIRED |
| `composition.default_timesheet_service` | `AadhkTimesheetProvider(AadhkIngestionService(db))` | ленивый импорт | WIRED |
| `bot_handler.cb_timesheet_sync` | внедрённый `timesheet_service` для ингеста | через `GoogleDriveClient.sync_aadhk_from_drive(db)` | PARTIAL (WR-03): ингест идёт мимо внедрённого провайдера, `reconcile` через него |

### Трассировка потока данных (Уровень 4)

Фаза не добавляет рендеринга новых динамических данных. Данные от `AadhkIngestionService` проходят через адаптер без преобразования (`*args/**kwargs`, `await self._service...`); дефолты не подменяются. Статус: FLOWING.

### Поведенческие проверки

| Поведение | Команда | Результат | Статус |
|-----------|---------|-----------|--------|
| Полный набор assistant-core | `.venv/bin/pytest tests -q` | `223 passed` | PASS |
| Контракты линтера | `.venv/bin/lint-imports --no-logo --no-cache` | `4 kept, 0 broken` | PASS |
| Контракты ловят нарушения | копия src в scratchpad с 4 мутациями | `0 kept, 4 broken` | PASS |
| Гейт качества | `env -u PYTEST_ADDOPTS python3 scripts/gate.py` | ИТОГ: ЗЕЛЁНЫЙ | PASS |
| EventBus без внешних зависимостей | прямой запуск (см. SC5) | доставка тем же объектом, только stdlib | PASS |

### Проверка проб (Step 7c)

В PLAN/SUMMARY нет путей `probe-*.sh`; в `scripts/*/tests/` пробы не заявлены для этой фазы. Шаг не применим.

### Покрытие требований

| Требование | План | Описание | Статус | Доказательства |
|------------|------|----------|--------|----------------|
| PRT-01 | 02-01 | Неизменяемые сущности, `WorkspaceClearance` | SATISFIED | `entities.py`, `test_core_domain.py` (20 тестов) |
| PRT-02 | 02-01, 02-02 | Async-порты, разделённые роли, пометка подтверждения | SATISFIED (допущение: пометка декларативная) | `connectors.py`, `test_lms_confirmation_markers`; см. human_verification 2 |
| PRT-03 | 02-01, 02-02 | Соответствие четырёх классов портам, фикстуры не тронуты | SATISFIED (через адаптеры) | `test_ports_conformance.py`, диф тестов только `A` |
| PRT-04 | 02-01, 02-03, 02-04 | DI через конструктор, `ignore_imports` пуст | SATISFIED (допущение: дефолт из composition; WR-03) | диф `secretary_dialog`, `bot_handler`, `live_ticker`; `lint-imports` |
| PRT-05 | 02-04 | `EventBus` на asyncio, шесть событий, без брокера | SATISFIED (допущение: трактовка формулировок) | `bus.py`, `events.py`, `test_core_events.py` |

Все пять ID объявлены в `requirements:` планов и сопоставлены в REQUIREMENTS.md с Фазой 2 (в таблице трассировки `Complete`). Осиротевших требований нет: других ID, привязанных к Фазе 2, в REQUIREMENTS.md нет.

### Запреты (prohibitions, test-tier)

Все запреты из PLAN помечены `verification: test` и имеют подключённое исполнение (тест), то есть не падают в «unverified-fail-closed».

| Запрет | Исполнение | Оценка |
|--------|-----------|--------|
| Профиль владельца в ядре (02-01) | `test_core_has_no_profile_tokens` | OK |
| Менять текст ответа секретаря (02-01) | `test_tydex_context_text_characterization` | OK |
| Ослаблять контракты вместо удаления импортов (02-01) | `test_use_case_contracts_not_weakened`, `test_ignore_imports_debt_is_zero`; мутационная проба | OK |
| Деструктив ЛК в обход подтверждения (02-02) | не подключён + `test_lms_provider_not_wired_into_production` | OK, но слабо (WR-02: гейт декларативный, проверка подстрочная) |
| Сеть и учётные данные в `health_check` (02-02) | `test_health_check_is_offline` | OK (IN-01: проверка тавтологична) |
| Дефолты профиля в адаптерах (02-02) | `test_adapters_do_not_duplicate_profile_defaults` | OK |
| HITL и авторизация бота (02-03) | существующие safety-тесты без правок, зелёные; `test_cmd_timesheet_unauthorized_does_nothing` | OK |
| Писать характеризацию после рефакторинга; чинить `/timesheet` (02-03/04) | порядок коммитов, `cur_m_name` на месте | OK |
| Содержимое события в журнале (02-04) | `test_failure_log_has_no_payload` | OK с оговоркой IN-02: проверяется поле события, но `logger.exception` пишет traceback с текстом исключения обработчика |
| Шина в боевых потоках (02-04) | `test_bus_not_wired_into_production_flows` + grep | OK |

Прокси-флагов `unverified-prohibition` нет: judgment-tier запретов в планах нет.

### Найденные антипаттерны

| Файл | Строка | Паттерн | Серьёзность | Влияние |
|------|--------|---------|-------------|---------|
| `src/connectors/guap_lms/provider.py` | 46 | `str(row["id"])` даёт `"None"` для заданий без id (WR-01) | Warning | Латентно: адаптер не подключён, но станет дефектом в Фазе 5 |
| `src/connectors/guap_lms/provider.py` | 68-72 | `delete_task` без гейта; `REQUIRES_CONFIRMATION` декларативна (WR-02) | Warning | Латентно: адаптер не подключён; закрывается Фазой 5 (`@requires_confirmation`) |
| `src/notifier/bot_handler.py` | 1158-1168 | ингест Drive идёт мимо внедрённого провайдера (WR-03) | Warning | DI на пути Drive частичный; поведение прежнее |
| `src/core/domain/*`, `guap_lms/provider.py` | - | смешение naive и aware datetime (WR-04) | Warning | Латентно: сущности не потребляются use-cases |
| `src/core/events/bus.py` | 25-43 | нет `unsubscribe`, нет таймаута, traceback в журнале (IN-02) | Info | Ограничения шины до появления подписчиков |

Маркеров TBD/FIXME/XXX/TODO/HACK в изменённых файлах нет (grep по `src/core`, адаптерам, `composition.py`, новым тестам пуст). Заглушек нет: все адаптеры делегируют реальным классам. `submit_grade` намеренно бросает `NotImplementedError` (D-09, зафиксировано контекстом).

Все десять замечаний ревью 02-REVIEW.md в `02-REVIEW-DISPOSITION.md` имеют статус `open` (не разобраны). Критических нет; ни одно не нарушает контракт ROADMAP, поэтому они не блокируют, но их нужно разобрать до Фазы 5 (WR-01, WR-02) и Фазы 3 (WR-04).

### Требуется проверка человеком

1. **SC4: трактовка «только порты и домен» (D-04).** Тест: решить, принимается ли зависимость use-cases от `src.storage`, `src.models`, `src.config` и непрямая через `src.composition`. Ожидание: подтверждение D-04 либо заказ буквального перевода (новый объём).
2. **PRT-02/03: допущения edge-probe.** Тест: подтвердить async-обёртки над sync-разбором, декларативную пометку подтверждения, соответствие через адаптеры. Ожидание: принять до Фазы 5 либо добавить параметр `confirmed` в адаптер ЛК (WR-02).
3. **PRT-04: допущения edge-probe.** Тест: подтвердить DI с `None` по умолчанию, непрямой импорт через `composition`, частичность DI на пути Drive (WR-03).
4. **PRT-05: допущения edge-probe.** Тест: подтвердить трактовку «без брокера / без межпроцессной передачи / доставляет» и ограничения шины (IN-02).
5. **Живой прогон.** Тест: после ручного снятия остановки сервиса проверить `/today`, живую сводку, вопрос секретарю о табеле, синхронизацию Drive. Ожидание: ответы как до фазы. Почему человек: верификатору запрещён перезапуск сервисов.

### Резюме расхождений

Расхождений, блокирующих цель, нет: gaps пуст. Цель фазы (ядро зависит от портов, а не от конкретных классов GUAP/AADHk/Google, поведение прежнее) достигнута в части, проверяемой кодом, тестами и линтером. Остаются решения владельца по трактовкам и список открытых замечаний ревью (WR-01..WR-04), которые не разобраны в disposition.

---

_Verified: 2026-10-02_
_Verifier: Claude (gsd-verifier)_
