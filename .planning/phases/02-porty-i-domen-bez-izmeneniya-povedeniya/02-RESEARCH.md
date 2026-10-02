# Phase 2: Порты и домен без изменения поведения - Research

**Researched:** 2026-10-02
**Domain:** Python 3.12, гексагональное ядро (dataclass-домен, `typing.Protocol`-порты, адаптеры-обёртки, DI через конструктор), import-linter/grimp, внутрипроцессная шина событий на asyncio
**Confidence:** HIGH (весь объём — код репозитория и stdlib; поведение Protocol/dataclass/StrEnum проверено запуском на Python 3.12.3 в venv assistant-core)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Владелец (не специалист) снова делегировал технические решения Claude: «реши сам». Все решения ниже — по усмотрению Claude по KISS/YAGNI и CLAUDE.md; это НЕ решения уровня W1–W10. Планировщик обязан им следовать, если исследование не опровергнет их фактами; при опровержении — вернуть вопрос владельцу простыми словами с вариантами (опрос AskUserQuestion, по-русски).

**Раскладка ядра (PRT-01, PRT-02, PRT-05)**
- **D-01:** Новый пакет `src/core/` (с `__init__.py`): `src/core/domain/` (сущности, enum, доменные события), `src/core/ports/` (Protocol-порты), `src/core/events.py` или `src/core/events/bus.py` (реализация `EventBus`) — точное имя файла на усмотрение планировщика, ориентир blueprint 2.4. Ядро импортирует только stdlib и `src.core.*`.
- **D-02:** Новый контракт import-linter `core-is-pure` в `/opt/assistant-core/.importlinter`: `src.core` не импортирует `src.connectors`, `src.calendar`, `src.parser`, `src.sender`, `src.collector`, `src.notifier`, `src.brain`, `src.storage`, `src.models`, `src.main`. Контракт добавляется с пустым `ignore_imports`. Тест «доказанно падает» из Фазы 1 (`test_architecture_contract.py`) уже покрывает механизм — новый тест на механизм не нужен.

**Доменные сущности (PRT-01)**
- **D-03:** Сущности — `@dataclass(frozen=True, slots=True)`: `ScheduleEvent`, `WorkRecord` (поле `project_tag: str`, без названия компании по умолчанию), `AcademicSubmission`, `Task` (область — свободная `str`), `EmailMessage`, `Workspace`, `Persona`; `WorkspaceClearance` — `StrEnum` ровно со значениями `public`, `internal`, `restricted_nda` (совпадают с допустимыми значениями синтетической персоны Фазы 1). Коллекции внутри — `tuple`/`frozenset`, не `list`.
- **D-04:** Сущности в этой фазе ТОЛЬКО объявляются и используются портами/адаптерами. Существующие модели (`src/models/schedule.py`: `Lesson`, `SchedulePayload`; `src/models/message.py`; `src/models/second_brain.py`) не удаляются и не переписываются; потребители в `brain`/`notifier` на новые сущности не переводятся. Перевод — по мере надобности в Фазах 3+. `src.models` считается допустимой зависимостью use-cases наравне с `src.core` (это pydantic-модели данных, не адаптеры) — критерий 4 ROADMAP читать так.
- **D-05:** Поля `Persona`/`Workspace` — минимальные (id, название, clearance, путь, remote для Workspace; имя, список рабочих пространств для Persona). Полная схема персоны — Фаза 3 (PER-01); здесь её не предвосхищать. Новый тест: рабочие пространства синтетической персоны (фикстура `synthetic_persona`) собираются в `Workspace` с корректным `WorkspaceClearance` — без изменения `synthetic_persona.py`.

**Порты и адаптеры (PRT-02, PRT-03)**
- **D-06:** Порты — `typing.Protocol` с `@runtime_checkable` (структурная совместимость: существующие классы и `MagicMock` в тестах не обязаны наследоваться). Имена как в требованиях: `BaseConnector` (`connector_id`, `required_scopes`, `async health_check`), `BaseScheduleProvider` (роль `schedule_source`), порт приёмника календаря (роль `calendar_sync`, имя на усмотрение — напр. `BaseCalendarSink`), `BaseTimesheetProvider`, `BaseLMSProvider`. Сигнатуры — ориентир blueprint разд. 2.2, но методы порта приёмника и прочих портов выводятся из ФАКТИЧЕСКИХ публичных методов существующих классов (`GoogleCalendarClient.sync_schedule/create_event/patch_event/delete_event/find_existing_event`, `AadhkIngestionService.get_timesheet_report/get_monthly_pacing/...`, `ScheduleParser.fetch_schedule_raw`, `GuapLmsClient.list_tasks/...`), а не придумываются заново.
- **D-07:** Несовпадения сигнатур закрываются адаптерами-обёртками рядом с конкретным классом (напр. `src/connectors/guap_lms/provider.py`), сам конкретный класс не переписывается. `GuapLmsClient` синхронный (requests/скрейпер) — НЕ переписывать на async: адаптер `BaseLMSProvider` вызывает его через `asyncio.to_thread` (тот же приём, что уже применяет `bot_handler`). — **Reversibility:** reversible.
- **D-08:** `health_check` в адаптерах — без сетевых вызовов (проверка конфигурации, по образцу `is_configured`); тесты не ходят во внешние сервисы и не читают `.env`/`credentials.json`/`token.json`/`*.session` (как D-18 Фазы 1).
- **D-09:** «Требует подтверждения» для `submit_grade` и `delete_task` в этой фазе — только декларативная пометка в порту (напр. константа `REQUIRES_CONFIRMATION = frozenset({"submit_grade", "delete_task"})` у `BaseLMSProvider`) и тест, что пометка есть. Механизма `@requires_confirmation` нет до Фазы 5; текущий HITL-диалог удаления в боте (`delete_task` через кнопку подтверждения) остаётся как есть. Если у `GuapLmsClient` нет выставления оценки, адаптер реализует `submit_grade` как `NotImplementedError` с понятным сообщением — сегодня его никто не вызывает, поведение не меняется.
- **D-10:** Protocol-проверка (PRT-03) — новый тест `tests/test_ports_conformance.py`: для каждой пары «порт ↔ класс/адаптер» проверяет `isinstance` (runtime_checkable) И что методы порта у реализации есть и являются корутинами там, где порт async (`inspect.iscoroutinefunction`), т.к. `isinstance` с Protocol проверяет только наличие имён. Отдельный тест — роли расписания разделены: парсер сайта соответствует `schedule_source`, но не `calendar_sync`; Google Calendar — наоборот.

**Внедрение зависимостей (PRT-04)**
- **D-11:** Ключевое ограничение, найденное при разведке: `bot_handler` уже вызывает клиент ЛК синхронно через `asyncio.to_thread(self.lms_client.list_tasks, 28)`, а тесты (`tests/test_lms_bot_workflow.py`) передают `lms_client=MagicMock()` с синхронными методами. Поэтому в этой фазе `bot_handler` НЕ переводится на async `BaseLMSProvider`: он продолжает принимать «сырой» клиент ЛК, аннотированный синхронным Protocol из `src/core/ports/` (напр. `LmsClientLike` с методами, которые бот реально вызывает: `list_tasks`, `get_task_details`, `create_task`, `delete_task`, `set_task_visibility`, `get_disciplines`). Перевод бота на async-порт с доменными сущностями — когда появится HITL-примитив (Фаза 5) или раньше по необходимости.
- **D-12:** Конструкторы сохраняют сигнатуры и необязательные параметры с `None` по умолчанию (тесты создают `EmailBotHandler(db=test_db, allowed_user_id=123)` без клиентов). Значения по умолчанию создаёт новый модуль-сборщик `src/composition.py` (фабрики `default_lms_client()`, `default_email_sender()`, `default_timesheet_service(db)`, `default_drive_client()` и т. п.), который `bot_handler` и `secretary_dialog` вызывают вместо прямого импорта коннекторов. `src/composition.py` не входит в source/forbidden контрактов (как `src/main.py`); `main.py` по возможности использует те же фабрики. Это совместимо с `allow_indirect_imports = True`, установленным в Фазе 1, — непрямой импорт через сборщик осознанно разрешён; цель PRT-04 — убрать прямые знания use-cases о конкретных классах. — **Reversibility:** reversible.
- **D-13:** Inline-импорты коннекторов в функциях (`secretary_dialog.py:139`, `bot_handler.py:1052,1095,1143,1144`) заменяются на зависимости, переданные в конструктор (по образцу `MethodistService` в `SecretaryDialogEngine.__init__`), с ленивым дефолтом из `src/composition.py`. Top-level импорты `GuapLmsClient` и `EmailSender` в `bot_handler.py` убираются; аннотации типов — через Protocol из `src/core/ports/`.
- **D-14:** Если какой-либо существующий тест патчит путь вида `src.notifier.bot_handler.GuapLmsClient` / `...AadhkIngestionService` (разведка таких не нашла, исследователь обязан перепроверить, включая `patch.object` и строки в `monkeypatch.setattr`), — сохранить совместимость без правки теста; если невозможно — остановиться и вынести владельцу.
- **D-15:** Итог PRT-04: оба списка `ignore_imports` в `.importlinter` assistant-core пусты (строки удаляются вместе с комментариями «долг»), `lint-imports` зелёный на реальных модулях, гейт `python3 /opt/chat-app/scripts/gate.py` — «ЗЕЛЁНЫЙ».

**EventBus (PRT-05)**
- **D-16:** Минимальная реализация на asyncio без зависимостей: `subscribe(event_type, handler)`, `async publish(event)`; доставка подписчикам точного типа события, последовательно, в порядке подписки. Исключение подписчика логируется и не прерывает ни публикатора, ни остальных подписчиков (иначе будущая публикация могла бы сломать боевой поток). Доменные события — frozen dataclass по blueprint 2.4 (`DomainEvent` с `event_id`, `occurred_at` в UTC через `datetime.now(timezone.utc)`, не устаревший `utcnow`; `ScheduleChanged`, `TimesheetSynced`, `TaskCreated`, `SecurityViolationDetected`, `DialogMemoryCleared`, `DelegatedToSpecialist`).
- **D-17:** В этой фазе шина НЕ подключается к боевым потокам (ни одного `publish` в `brain`/`notifier`/`main`) — ноль изменения поведения, YAGNI: потребители появятся в следующих фазах. Тесты: доставка подписчику, изоляция упавшего подписчика, отсутствие доставки неподписанным типам.

**Процесс**
- **D-18:** Коммиты атомарные, в `main` assistant-core (локально, без push) и в `master` chat-app только для `.planning/`; каждый шаг — гейт зелёный. Порядок рекомендуемый: домен → порты → адаптеры + conformance-тест → сборщик и DI → опустошение `ignore_imports` → EventBus. Сервисы остаются остановленными, перезапусков нет.
- **D-19:** Шаблонный код (dataclass-сущности, черновики тестов) допускается делегировать Antigravity только через `scripts/agy_task.sh` (skill `agy-delegate`) с ревью патча Claude; запускать `agy` напрямую запрещено.

### Claude's Discretion

Все области отданы владельцем на усмотрение Claude. Планировщик дополнительно вправе выбрать: точные имена файлов внутри `src/core/`, имя порта приёмника календаря и sync-Protocol клиента ЛК, состав фабрик в `src/composition.py`, набор полей сущностей сверх минимума D-03/D-05, разбиение на планы — если это не нарушает D-01..D-19.

### Deferred Ideas (OUT OF SCOPE)

- Перевод `bot_handler` на async `BaseLMSProvider` и доменную `AcademicSubmission` — Фаза 5 (вместе с `@requires_confirmation`) или по необходимости раньше.
- Публикация доменных событий в боевых потоках (очистка памяти, синхронизация табеля, создание задачи) — по мере появления подписчиков в следующих фазах.
- Перевод use-cases с `src/models` (`Lesson`, `SchedulePayload`) на доменные сущности — Фаза 3+.
- Выставление оценок в ЛК (`submit_grade`) как реальная функция — новая возможность, не в этой миграции.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRT-01 | Доменные сущности как неизменяемые dataclass в `core/domain`; enum `WorkspaceClearance` | Раздел «Code Examples» (сущности, `frozen+slots+StrEnum` проверены запуском); тест D-05 по `synthetic_persona` собирает `Workspace` в самом тесте, без production-загрузчика |
| PRT-02 | Async-порты в `core/ports/` (`BaseConnector`, `BaseScheduleProvider`, порт приёмника календаря, `BaseTimesheetProvider`, `BaseLMSProvider`); роли расписания разделены | Таблица «Фактические публичные методы → порты»; атрибут `role: ClassVar[ConnectorRole]` делает разделение ролей проверяемым фактом; `REQUIRES_CONFIRMATION` как ClassVar проверен запуском |
| PRT-03 | Четыре класса соответствуют портам напрямую или через адаптер; Protocol-проверка (тест); фикстуры существующих тестов не изменены | Ни у одного из четырёх классов нет `connector_id`/`required_scopes`/`health_check` → нужны адаптеры-обёртки (D-07); ловушки `isinstance` (Pitfalls 1-3); безопасные способы конструирования классов в тесте |
| PRT-04 | Зависимости `secretary_dialog.py` и `bot_handler.py` через конструктор; inline-импорты убраны; `ignore_imports` пуст | Полная карта 8 мест импорта/создания конкретных классов; правило «строка `ignore_imports` удаляется в том же коммите»; характеризационные тесты ДО рефакторинга (4 непокрытых пути); `src/composition.py` с ленивыми импортами сохраняет патчируемость |
| PRT-05 | Внутрипроцессный `EventBus` на asyncio с шестью доменными событиями | Эскиз реализации (точный тип, последовательно, изоляция исключений, sync+async обработчики); `CancelledError` не глотать |
</phase_requirements>

## Summary

Фаза — чистый рефакторинг по границам без изменения поведения: в assistant-core вводится слой `src/core/` (домен, порты, шина), у каждого из четырёх коннекторов появляется тонкий адаптер-обёртка, `bot_handler` и `secretary_dialog` перестают импортировать конкретные коннекторы и получают их через конструктор с ленивым дефолтом из `src/composition.py`, а пять записей `ignore_imports` обнуляются. Внешних пакетов не нужно: всё на stdlib (`typing.Protocol`, `dataclasses`, `enum.StrEnum`, `asyncio`, `inspect`), import-linter 2.15 и grimp 3.17 уже установлены в Фазе 1 [VERIFIED: `.venv/bin/pip list` в /opt/assistant-core].

Главная находка исследования: ни один из четырёх существующих классов НЕ имеет `connector_id`, `required_scopes`, `health_check` — поэтому напрямую порт `BaseConnector` не удовлетворяется ни одним из них, и все четыре PRT-03-соответствия идут через адаптеры-обёртки (D-07 это и предписывает). Второе: ядро по D-02 не вправе импортировать `src.models`/`src.storage`, а реальные методы принимают `Lesson`, `ScheduleDiff`, `Database` — значит в сигнатурах портов эти параметры типизируются как `Any` (D-02/D-06 не опровергаются, это рабочий компромисс). Третье: на Python 3.12 `isinstance(MagicMock(), <runtime_checkable Protocol>)` возвращает `False` — это не мешает тестам (они не делают `isinstance` по моку), но запрещает fail-fast проверки `isinstance` внутри конструкторов `bot_handler`/`secretary_dialog`.

Ключевой риск нулевой регрессии — четыре пути `bot_handler`/`secretary_dialog`, не покрытые ни одним тестом (`handle_cmd_timesheet`, `cb_timesheet_sync`, ветка AADHk в `handle_user_document`, `_get_tydex_context`; тесты подменяют `handle_cmd_timesheet` через `AsyncMock`). Рекомендация: ПЕРЕД рефакторингом написать для них новые характеризационные тесты, патча `src.connectors.aadhk.parser.AadhkIngestionService` (inline-импорт разрешает атрибут в момент вызова, поэтому патч работает и до, и после рефакторинга, если `src/composition.py` импортирует класс лениво внутри фабрики).

**Primary recommendation:** Идти по D-18 в четыре плана: (1) домен + контракт `core-is-pure`; (2) порты + 4 адаптера + `test_ports_conformance.py`; (3) характеризационные тесты → `src/composition.py` → DI в `bot_handler`/`secretary_dialog` (и, решением планировщика, `live_ticker`) с удалением каждой строки `ignore_imports` В ТОМ ЖЕ КОММИТЕ, что и убираемый импорт; (4) `EventBus` + события + финальный гейт. Адаптеры пробрасывают `*args, **kwargs` для методов с «зашитыми» дефолтами (`"Тидекс"`, `8.5`, длинное описание задачи ЛК), чтобы не плодить новые копии хардкода перед сканером PER-08.

## Architectural Responsibility Map

Проект — Python-демон (не веб-стек), поэтому «уровни» адаптированы под гексагональную раскладку.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Доменные сущности, `WorkspaceClearance`, доменные события | Ядро (`src/core/domain`) | — | Чистые данные без зависимостей; общий язык для портов и будущих use-cases |
| Контракты портов (Protocol) | Ядро (`src/core/ports`) | — | Определяют, что нужно use-cases от внешнего мира; не знают реализаций |
| Реализация портов (GUAP/AADHk/Google/сайт расписания) | Адаптеры (`src/connectors/*`, `src/calendar`, `src/parser`) | — | Единственное место, знающее конкретные сайты/API; обёртки лежат рядом с классом (D-07) |
| Сборка зависимостей по умолчанию | Корень композиции (`src/composition.py`, `src/main.py`) | — | Единственные модули, вправе знать конкретные классы; вне source/forbidden контрактов |
| Use-cases (диалог секретаря, роутер, методист, обработчик бота) | Use-cases (`src/brain`, `src/notifier/bot_handler.py`) | — | Зависят от портов/Protocol и `src.models`/`src.storage`; конкретных коннекторов не импортируют |
| Внутрипроцессная доставка событий | Ядро (`src/core/events`) | — | asyncio без брокера (W9); в боевые потоки не подключается (D-17) |
| Проверка архитектурных границ | Инструментарий (`.importlinter`, `tests/`, `scripts/gate.py`) | chat-app (гейт) | Линтер + тесты фиксируют границу, гейт — единственная команда приёмки |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing.Protocol` + `@runtime_checkable` | stdlib, Python 3.12.3 | Порты (структурная типизация) | Решение D-06; существующие классы не наследуются |
| `dataclasses` (`frozen=True, slots=True`; `kw_only=True` для событий) | stdlib | Неизменяемые сущности и события | Решение D-03; `slots` + `frozen` + наследование проверены на 3.12.3 |
| `enum.StrEnum` | stdlib (3.11+) | `WorkspaceClearance`, `ConnectorRole` | Решение D-03; `C("public") is C.PUBLIC` и `C.PUBLIC == "public"` проверены |
| `asyncio`, `inspect` | stdlib | `EventBus`, `to_thread`-адаптер ЛК, проверка корутин в тесте | Тот же приём уже в `bot_handler` (`asyncio.to_thread`) |
| import-linter | 2.15 | Контракты `forbidden` | Уже установлен в Фазе 1 [VERIFIED: pip list, assistant-core venv] |
| grimp | 3.17 | Граф импортов для страж-теста | Уже установлен в Фазе 1 [VERIFIED: pip list, assistant-core venv] |
| pytest / pytest-asyncio | 9.1.1 / 1.4.0 (`asyncio_mode = auto`) | Тесты | Уже в проекте [VERIFIED: pip list; `/opt/assistant-core/pytest.ini`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`) | stdlib | Фейки в характеризационных тестах | Как в существующих тестах |
| `logging` | stdlib | Лог исключений подписчиков `EventBus` | `logger.exception`, без вывода содержимого события |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Адаптеры-обёртки (D-07) | Добавить `connector_id`/`required_scopes`/`health_check` прямо в 3 существующих класса | Меньше шаблонного кода, но правит конкретные классы и теряет симметрию с ЛК (там обёртка обязательна из-за sync→async); держаться D-07 |
| `pyee`, `blinker`, `aiopubsub` для шины | — | Запрещено W9/D-16: «без зависимостей»; шина ~40 строк |
| `abc.ABC` для портов | — | Мок и существующие классы пришлось бы наследовать — противоречит D-06 |

**Installation:**
```bash
# Новых пакетов нет. Dev-зависимости (import-linter, grimp) установлены в Фазе 1.
```

**Version verification:** новых внешних пакетов фаза не вводит, `npm view`/`pip index` не требовались. Установленные версии прочитаны из `.venv/bin/pip list` (import-linter 2.15, grimp 3.17, pytest 9.1.1, pytest-asyncio 1.4.0, pydantic 2.13.5, anyio 4.15.1).

## Package Legitimacy Audit

Фаза не устанавливает внешних пакетов. Все рекомендации — stdlib и уже установленные в Фазе 1 (после одобрения владельцем) import-linter/grimp.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — (новых пакетов нет) | — | — | — | — | — | Проверка не требуется |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────── src/main.py (корень композиции, не меняется) ───────────────────┐
                        │  создаёт ScheduleParser / GoogleCalendarClient / GuapLmsClient / EmailSender         │
                        └──────────────────────────────────────────────────────────────────────────────────────┘
                                                      │ передаёт готовые клиенты в конструктор (как сегодня)
                                                      ▼
Telegram ──► EmailBotHandler (src/notifier/bot_handler.py)                      SecretaryDialogEngine (src/brain)
                │  lms_client: LmsClientLike (sync Protocol)                          │ timesheet_service: BaseTimesheetProvider
                │  email_sender: EmailSenderLike (async Protocol)                     │ (по умолчанию — лениво из composition)
                │  timesheet_service: BaseTimesheetProvider | None                    │
                │  drive_client_factory: Callable[[], DriveClientLike] | None         │
                │  значение None ──► src/composition.default_*()  (ленивый импорт     │
                ▼                    конкретных классов ВНУТРИ фабрики)               ▼
        src/core/ports (Protocol, только stdlib + src.core)  ◄──── структурно ───── адаптеры-обёртки
          BaseConnector ─┬─ BaseScheduleProvider  (role=schedule_source) ◄── src/parser/provider.py        ── ScheduleParser
                         ├─ BaseCalendarSink      (role=calendar_sync)   ◄── src/calendar/provider.py      ── GoogleCalendarClient
                         ├─ BaseTimesheetProvider (role=timesheet)       ◄── src/connectors/aadhk/provider.py ── AadhkIngestionService
                         └─ BaseLMSProvider       (role=lms)             ◄── src/connectors/guap_lms/provider.py ── GuapLmsClient (sync, to_thread)
        src/core/domain: ScheduleEvent, WorkRecord, AcademicSubmission, Task, EmailMessage, Workspace, Persona,
                         WorkspaceClearance(StrEnum), доменные события (DomainEvent + 6 наследников)
        src/core/events/bus.py: EventBus.subscribe(type, handler) / await publish(event)   ── НЕ подключена к боевым потокам (D-17)

Проверки границ:  .importlinter [brain-no-adapters | bot-handler-no-adapters | core-is-pure]  ─►  lint-imports  ─►  scripts/gate.py
```

### Recommended Project Structure

```
/opt/assistant-core/
├── src/
│   ├── core/                      # НОВОЕ: обычный пакет с __init__.py (D-01); импортирует только stdlib и src.core.*
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py        # реэкспорт
│   │   │   ├── entities.py        # WorkspaceClearance, ConnectorRole, ScheduleEvent, WorkRecord, AcademicSubmission, Task, EmailMessage, Workspace, Persona
│   │   │   └── events.py          # DomainEvent + ScheduleChanged, TimesheetSynced, TaskCreated, SecurityViolationDetected, DialogMemoryCleared, DelegatedToSpecialist
│   │   ├── ports/
│   │   │   ├── __init__.py
│   │   │   ├── connectors.py      # BaseConnector, BaseScheduleProvider, BaseCalendarSink, BaseTimesheetProvider, BaseLMSProvider
│   │   │   └── clients.py         # DI-only Protocol: LmsClientLike (sync), EmailSenderLike, DriveClientLike
│   │   └── events/
│   │       ├── __init__.py
│   │       └── bus.py             # EventBus
│   ├── composition.py             # НОВОЕ: default_lms_client(), default_email_sender(), default_timesheet_service(db), default_drive_client()
│   ├── parser/provider.py         # НОВОЕ: ScheduleParserSource (обёртка)
│   ├── calendar/provider.py       # НОВОЕ: GoogleCalendarSink (обёртка)
│   ├── connectors/aadhk/provider.py       # НОВОЕ: AadhkTimesheetProvider (обёртка)
│   └── connectors/guap_lms/provider.py    # НОВОЕ: GuapLmsProvider (обёртка, asyncio.to_thread)
├── tests/                         # ТОЛЬКО новые файлы; существующие не правятся (SC1)
│   ├── test_core_domain.py        # PRT-01 + D-05 (Workspace из synthetic_persona)
│   ├── test_core_events.py        # PRT-05
│   ├── test_ports_conformance.py  # PRT-02/03 (D-10)
│   ├── test_composition_di.py     # PRT-04 (внедрение, дефолты, характеризация непокрытых путей)
│   └── test_core_architecture.py  # core-is-pure в рантайме + «долг ignore_imports = 0»
└── .importlinter                  # + контракт core-is-pure; оба списка ignore_imports пусты
```

### Фактические публичные методы → порты (источник истины для D-06)

Сигнатуры прочитаны из исходников в этой сессии ([VERIFIED: чтение файлов], строки указаны):

| Класс (файл:строка) | Публичная поверхность (дословно) |
|---------------------|----------------------------------|
| `ScheduleParser` (`src/parser/schedule_parser.py:22`) | `async def fetch_schedule_raw(self, target_id: str, endpoint: str = "", param_name: str = "pr") -> FetchResult` (:53); `def parse_json_payload(self, raw_json: str, group_or_teacher_id: str) -> SchedulePayload` (:117); `def parse_html_payload(self, html_content: str, group_or_teacher_id: str, target_date: date \| None = None) -> SchedulePayload` (:156). `main.py` (:66, :76, :81) вызывает все три |
| `GoogleCalendarClient` (`src/calendar/client.py:37`) | `__init__(self, credentials_file: str = "./credentials.json", token_file: str = "./token.json", timezone_str: str = "Europe/Moscow", dry_run: bool = False)` — **читает `token.json` в конструкторе**, если файл есть (:129-:245 методы): `async def find_existing_event(self, calendar_id: str, lesson: Lesson) -> dict[str, Any] \| None` (:129); `async def create_event(self, calendar_id: str, lesson: Lesson) -> str` (:162); `async def patch_event(self, calendar_id: str, google_event_id: str, lesson: Lesson) -> bool` (:198); `async def delete_event(self, calendar_id: str, google_event_id: str) -> bool` (:231); `async def sync_schedule(self, calendar_id: str, diff: ScheduleDiff, db: Database) -> dict[str, int]` (:245). Классметоды `format_summary`/`format_description` — форматирование, в порт не входят |
| `AadhkIngestionService` (`src/connectors/aadhk/parser.py:55`) | `__init__(self, db: Database) -> None` (:58); `async def ingest_backup_file(self, backup_file_path: str \| Path, default_project: str = "Тидекс") -> dict[str, Any]` (:61); `async def reconcile_all_conflicts(self) -> dict[str, Any]` (:358); `async def get_timesheet_report(self, start_date: str \| None = None, end_date: str \| None = None, project_name: str \| None = "Тидекс") -> dict[str, Any]` (:405); `async def get_monthly_pacing(self, year: int \| None = None, month: int \| None = None, daily_norm: float = 8.5, project_name: str \| None = "Тидекс") -> dict[str, Any]` (:428) |
| `GuapLmsClient` (`src/connectors/guap_lms/client.py:16`), **все методы синхронные** | `__init__(self, email: str \| None = None, password: str \| None = None, timeout: float = 20.0)`; `@property is_configured -> bool` (:46); `is_authenticated() -> bool` (:50, делает сетевой GET); `list_tasks(self, semester: int \| str = 28) -> list[dict[str, Any]]` (:124); `get_task_details(self, task_id: int \| str) -> dict[str, Any]` (:221); `create_task(self, name, subject_id, group_ids, semester_id=28, task_type_id=2, description="…", markpoint=10, ordernum=1, harddeadline="2026-12-31", is_public=False, report_required=True, extensions=None) -> dict[str, Any]` (:296); `delete_task(self, task_id: int \| str, semester_id: int \| str = 28) -> bool` (:390); `set_task_visibility(self, task_id: int \| str, is_public: bool, semester_id: int \| str = 28) -> bool` (:431); `download_student_report(...)` (:526); `get_disciplines(self) -> list[dict[str, Any]]` (:551). Метода выставления оценки НЕТ (`grep -i grade` по файлу пуст) |
| `GoogleDriveClient` (`src/connectors/gdrive/client.py:30`) | `is_configured` property (читает `token.json`, :43-:51); `async def sync_aadhk_from_drive(self, db: Database) -> dict[str, Any]` (:242). Конструктор путей не читает |
| `EmailSender` (`src/sender/email_sender.py:13`) | `async def send_reply(self, to_email: str, subject: str, body: str, account_id: str = "mailru", in_reply_to: str \| None = None, references: str \| None = None, cc: list[str] \| None = None) -> dict[str, Any]` (:97) |

`list_tasks` отдаёт словари с ключами `id, ordernum, subject, title, task_type, deadline, is_public, updated_at, link` (:184-:193); `deadline` — строка, в тестовой разметке `15.10.2026` (`tests/test_guap_lms.py:43`).

### Pattern 1: Порты — Protocol с ролью и ClassVar

**What:** `BaseConnector` фиксирует ровно три члена из PRT-02; специализированные порты добавляют `role: ClassVar[ConnectorRole]` (делает W8 «роли расписания разделены» проверяемым фактом, а не только набором имён методов) и свои методы.
**When to use:** все 5 портов PRT-02.
**Example:**
```python
# Source: проверено запуском на Python 3.12.3 (venv assistant-core); структура — blueprint разд. 2.2
from __future__ import annotations
from typing import Any, ClassVar, Protocol, runtime_checkable
from src.core.domain.entities import AcademicSubmission, ConnectorRole

@runtime_checkable
class BaseConnector(Protocol):
    connector_id: str
    required_scopes: tuple[str, ...]
    async def health_check(self) -> bool: ...

@runtime_checkable
class BaseCalendarSink(BaseConnector, Protocol):
    role: ClassVar[ConnectorRole] = ConnectorRole.CALENDAR_SYNC
    # Lesson/ScheduleDiff/Database — из src.models/src.storage, ядру они запрещены (D-02) -> Any
    async def find_existing_event(self, calendar_id: str, lesson: Any) -> dict[str, Any] | None: ...
    async def create_event(self, calendar_id: str, lesson: Any) -> str: ...
    async def patch_event(self, calendar_id: str, google_event_id: str, lesson: Any) -> bool: ...
    async def delete_event(self, calendar_id: str, google_event_id: str) -> bool: ...
    async def sync_schedule(self, calendar_id: str, diff: Any, db: Any) -> dict[str, int]: ...

@runtime_checkable
class BaseLMSProvider(BaseConnector, Protocol):
    role: ClassVar[ConnectorRole] = ConnectorRole.LMS
    REQUIRES_CONFIRMATION: ClassVar[frozenset[str]] = frozenset({"submit_grade", "delete_task"})
    async def list_tasks(self, semester: int | str = 28) -> list[AcademicSubmission]: ...
    async def get_task_details(self, task_id: int | str) -> dict[str, Any]: ...
    async def create_task(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...
    async def delete_task(self, task_id: int | str, semester_id: int | str = 28) -> bool: ...
    async def set_task_visibility(self, task_id: int | str, is_public: bool, semester_id: int | str = 28) -> bool: ...
    async def get_disciplines(self) -> list[dict[str, Any]]: ...
    async def submit_grade(self, submission_id: str, grade: Any) -> None: ...
```
Результат проверки запуском: `isinstance(Impl(), Lms) == True`, `isinstance(Impl(), Sink) == False` (роли не смешиваются), `Lms.REQUIRES_CONFIRMATION == frozenset({'delete_task', 'submit_grade'})`, при отсутствии `connector_id`/`required_scopes`/`role` `isinstance` даёт `False`.

### Pattern 2: Адаптер-обёртка (композиция, пробрасывающая дефолты)

**What:** тонкий класс рядом с конкретным; хранит экземпляр, объявляет `connector_id`, `required_scopes`, `role`, `async health_check` (без сети, D-08) и делегирует. Для методов с зашитыми дефолтами — `*args, **kwargs`, чтобы дефолты (`"Тидекс"`, `8.5`, текст описания задачи) оставались только в конкретном классе и не множились перед сканером PER-08 (Фаза 3).
**Example:**
```python
# src/connectors/guap_lms/provider.py  (эскиз; идентификаторы connector_id/scopes — выбор планировщика)
import asyncio
from datetime import datetime
from typing import Any
from src.core.domain.entities import AcademicSubmission, ConnectorRole
from src.core.ports.clients import LmsClientLike

class GuapLmsProvider:
    connector_id = "lms_portal"
    required_scopes = ("lms.read", "lms.write")
    role = ConnectorRole.LMS
    REQUIRES_CONFIRMATION = frozenset({"submit_grade", "delete_task"})

    def __init__(self, client: LmsClientLike) -> None:
        self._client = client

    async def health_check(self) -> bool:            # без сети: только конфигурация (D-08)
        return bool(self._client.is_configured)

    async def list_tasks(self, semester: int | str = 28) -> list[AcademicSubmission]:
        rows = await asyncio.to_thread(self._client.list_tasks, semester)
        return [AcademicSubmission(submission_id=str(r["id"]), title=r["title"],
                                   deadline=_parse_deadline(r.get("deadline")), is_public=bool(r["is_public"]))
                for r in rows]

    async def delete_task(self, task_id, semester_id=28) -> bool:
        return await asyncio.to_thread(self._client.delete_task, task_id, semester_id)

    async def submit_grade(self, submission_id: str, grade: Any) -> None:
        raise NotImplementedError("Выставление оценок в личном кабинете пока не реализовано")
```

### Pattern 3: DI с ленивым дефолтом и сохранением патчируемости

**What:** конструктор принимает `X | None = None`; при `None` дефолт создаётся в момент использования через `src.composition`, который импортирует конкретный класс ВНУТРИ фабрики. Тогда `patch("src.connectors.aadhk.parser.AadhkIngestionService", Fake)` подменяет класс и до рефакторинга (inline-импорт в `bot_handler`), и после (inline-импорт в `composition`) — одни и те же характеризационные тесты проходят в обоих состояниях.
**Example:**
```python
# src/composition.py  (не входит в source/forbidden контрактов; грузит конкретику лениво)
from typing import Any

def default_lms_client():
    from src.connectors.guap_lms.client import GuapLmsClient
    return GuapLmsClient()

def default_email_sender():
    from src.sender.email_sender import EmailSender
    return EmailSender()

def default_timesheet_service(db: Any):
    from src.connectors.aadhk.parser import AadhkIngestionService
    from src.connectors.aadhk.provider import AadhkTimesheetProvider
    return AadhkTimesheetProvider(AadhkIngestionService(db))

def default_drive_client():
    from src.connectors.gdrive.client import GoogleDriveClient
    return GoogleDriveClient()
```
```python
# src/notifier/bot_handler.py  (фрагмент): per-call дефолт = ровно сегодняшнее поведение
def __init__(self, db, ..., lms_client: LmsClientLike | None = None,
             timesheet_service: BaseTimesheetProvider | None = None,
             drive_client_factory: Callable[[], DriveClientLike] | None = None):
    self.email_sender = email_sender if email_sender is not None else default_email_sender()
    self.lms_client = lms_client if lms_client is not None else default_lms_client()
    self._timesheet_service = timesheet_service
    self._drive_client_factory = drive_client_factory or default_drive_client

def _timesheet(self) -> BaseTimesheetProvider:
    return self._timesheet_service or default_timesheet_service(self.db)
```
`GoogleDriveClient` кэширует `_service`, а сегодня на каждый колбэк создаётся новый клиент; поэтому для Drive внедряется ФАБРИКА (сохраняет «свежий клиент на вызов»), для табеля — экземпляр или per-call дефолт (`AadhkIngestionService` хранит только `db`).

### Pattern 4: EventBus

**Example:**
```python
# src/core/events/bus.py
import inspect, logging
from collections import defaultdict
from typing import Any, Callable
from src.core.domain.events import DomainEvent

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Callable[[Any], Any]]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: Callable[[Any], Any]) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in tuple(self._handlers.get(type(event), ())):   # точный тип (D-16), копия списка
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:                                         # CancelledError — BaseException, не глотается
                logger.exception("EventBus: подписчик %r упал на %s", handler, type(event).__name__)
```

### Anti-Patterns to Avoid

- **`isinstance(dep, Protocol)` в конструкторах use-cases:** `isinstance(MagicMock(), P)` на 3.12 даёт `False` — сломает 7 тестов `test_lms_bot_workflow.py`, передающих `MagicMock()`. Protocol — только для аннотаций; `isinstance` допустим лишь в `test_ports_conformance.py` на настоящих адаптерах.
- **`issubclass()` с Protocol, у которого есть не-методные члены:** бросает `TypeError: Protocols with non-method members don't support issubclass()` (проверено). Использовать `isinstance` на экземплярах.
- **Импорт `src.models`/`src.storage` в `src.core` ради точных типов (в т.ч. под `TYPE_CHECKING`):** grimp считает и такие импорты → `core-is-pure` покраснеет. Использовать `Any`.
- **Дублирование зашитых дефолтов в адаптерах** (`"Тидекс"`, `8.5`): новые копии хардкода — долг перед PER-08/PER-06.
- **Eager-создание `GoogleDriveClient`/клиента календаря в конструкторе бота:** меняет поведение (`GoogleCalendarClient.__init__` читает `token.json`) и нарушает D-08/D-18 Фазы 1 в тестах.
- **Публикация событий в `brain`/`notifier`/`main`:** запрещено D-17.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Проверка архитектурных границ | Собственный сканер импортов (`ast`/`grep`) | import-linter `forbidden` + grimp (уже в проекте) | Видит и inline-импорты внутри функций; Phase 1 доказала, что падает на нарушении |
| Неизменяемые сущности | Ручные `__slots__`/`__setattr__` | `@dataclass(frozen=True, slots=True)` | Корректные `eq`/`hash`/`repr`, `FrozenInstanceError` |
| Enum со строковыми значениями | Класс констант | `enum.StrEnum` | `C("public") is C.PUBLIC`, сравнение со строкой, валидация значения |
| Структурная совместимость | ABC + регистрация | `typing.Protocol` + `runtime_checkable` | Мокам и существующим классам не нужно наследоваться |
| Потокобезопасный вызов sync-клиента | Свой пул потоков | `asyncio.to_thread` | Уже применяется в `bot_handler` |
| Шина событий | Внешняя библиотека/брокер | ~40 строк на asyncio (Pattern 4) | W9: без брокера и без зависимостей |

**Key insight:** вся фаза — «переложить зависимости», а не «написать новое»: поведение уже есть в классах, задача — тонкие обёртки и аккуратный порядок коммитов, при котором линтер и тесты зелёные на каждом шаге.

## Runtime State Inventory

Фаза — рефакторинг границ (без переименований данных); категории проверены явно.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Нет: имена таблиц, ключи БД и строки данных не меняются; сущности `src/core/domain` только объявляются (D-04). Боевая `assistant.db` не затрагивается (гейт контролирует SHA-256) | None — подтверждено чтением D-04/D-17 |
| Live service config | Нет: сервисы заморожены (`STATE.md`: assistant-worker failed/disabled), конфигурация во внешних системах не меняется | None |
| OS-registered state | Нет: systemd-юниты не меняются, перезапусков нет (D-18) | None |
| Secrets/env vars | Нет: имена переменных (`config.GUAP_EMAIL`, `config.GUAP_LK_PASSWORD` и т.д.) остаются; `composition.default_lms_client()` вызывает `GuapLmsClient()` без аргументов — как сегодня | None |
| Build artifacts / installed packages | Нет egg-info/бинарников; новые каталоги `src/core/**` — обычный пакет. Устаревшие `__pycache__` безвредны | None |

## Common Pitfalls

### Pitfall 1: `isinstance(MagicMock(), Protocol)` == False на Python 3.12
**What goes wrong:** любая runtime-проверка Protocol на моке возвращает `False` (даже для Protocol только из методов).
**Why it happens:** в 3.12 `runtime_checkable` использует `inspect.getattr_static`, а `MagicMock` создаёт атрибуты динамически через `__getattr__` [VERIFIED: запуск на 3.12.3 — `MagicMock isinstance method-only proto: False`].
**How to avoid:** D-06 («`MagicMock` не обязан наследоваться») верно только для статической типизации; в рантайме `isinstance` по зависимостям не делать, в conformance-тесте проверять настоящие адаптеры.
**Warning signs:** `test_lms_bot_workflow.py` падает на конструировании `EmailBotHandler(... lms_client=mock_lms)`.

### Pitfall 2: `isinstance` проверяет только имена — sync-метод проходит как async
**What goes wrong:** класс с обычным `def health_check` проходит `isinstance(…, BaseConnector)` [VERIFIED: запуск — `sync-method-instance-isinstance: True`].
**How to avoid:** D-10: дополнительно `inspect.iscoroutinefunction(getattr(impl, name))` для каждого async-метода порта; для sync-методов `parse_json_payload`/`parse_html_payload` — `not iscoroutinefunction`.

### Pitfall 3: Не-методные члены Protocol требуют атрибут на экземпляре или классе
**What goes wrong:** `connector_id`, `required_scopes`, `role`, `REQUIRES_CONFIRMATION` отсутствуют → `isinstance` = `False` [VERIFIED: запуск — `missing data attrs: False`].
**How to avoid:** объявлять их как атрибуты класса адаптера (не в `__init__`, чтобы тест видел их и на классе).

### Pitfall 4: Конструкторы читают файлы учётных данных
**What goes wrong:** `GoogleCalendarClient(...)` без `dry_run=True` открывает `token.json`, `GoogleDriveClient.is_configured` читает `token.json` — тест нарушит D-08 / D-18 Фазы 1.
**How to avoid:** в conformance-тесте — `GoogleCalendarClient(dry_run=True)` (так уже делает `tests/test_phase1.py:291`), `GuapLmsClient(email="", password="")` (как `tests/test_guap_lms.py:9`), `AadhkIngestionService(db=MagicMock())`, `ScheduleParser()` (сети не трогает при конструировании); `health_check` адаптеров не вызывать `is_authenticated()`/`is_configured` Drive.

### Pitfall 5: Устаревшая запись `ignore_imports` красит линтер
**What goes wrong:** если импорт убран, а строка `ignore_imports` осталась (или наоборот), `lint-imports` сообщает об устаревшей записи [CITED: `docs/BASELINE.md:123` — «запись удаляется в том же коммите, что и рефакторинг, иначе lint-imports сообщит об устаревшей записи»].
**How to avoid:** каждый коммит DI удаляет строку вместе с убираемым импортом. Пары не делимы: `bot_handler -> connectors.aadhk.parser` — это три inline-импорта (:1052, :1095, :1144) одной записью, убирать все три одним коммитом.

### Pitfall 6: Четыре пути без тестового покрытия
**What goes wrong:** рефакторинг `handle_cmd_timesheet`, `cb_timesheet_sync`, ветки AADHk в `handle_user_document` и `SecretaryDialogEngine._get_tydex_context` ничем не проверяется (в `tests/` есть лишь `handler.handle_cmd_timesheet = AsyncMock()`: `test_fast_intent_router.py:133,163`; `ingest_backup_file` вызывается только напрямую в `test_aadhk_parser.py`).
**How to avoid:** до рефакторинга добавить характеризационные тесты с `patch("src.connectors.aadhk.parser.AadhkIngestionService", Fake)` и `patch("src.connectors.gdrive.client.GoogleDriveClient", Fake)`; зафиксировать текст ответа; после рефакторинга те же тесты обязаны остаться зелёными без правок. Отрицательная проверка D-14 выполнена: патчей путей `src.notifier.bot_handler.*` и `...secretary_dialog.*` в `tests/` нет — единственные `patch("src.…")` — `src.connectors.gdrive.client.build`/`.Credentials` (`tests/test_gdrive_client.py:43-44`), и модуль gdrive-клиента остаётся нетронутым.

### Pitfall 7: Контракт ссылается на несуществующий модуль
**What goes wrong:** страж-тест `test_real_contract_modules_exist_in_graph` требует, чтобы каждый модуль из source/forbidden существовал в графе grimp. Контракт `core-is-pure` с `source_modules = src.core` упадёт, если `src/core/__init__.py` ещё нет; запрет на `src.composition` — если файла ещё нет.
**How to avoid:** контракт добавляется в том же коммите, что создаёт `src/core/__init__.py`; `src.composition` дописывается в `forbidden_modules` в коммите, создающем `composition.py`.

### Pitfall 8: Shield и «Generic Bearer»
**What goes wrong:** `scripts/security_shield.py --all` (режим гейта) красит итог на новой находке; паттерн `Generic Bearer Secret` срабатывает на `api_key|secret_key|auth_token = "<16+ символов>"` [VERIFIED: чтение `scripts/security_shield.py`]. Замороженный список ложных срабатываний assistant-core — только `test_debrief_parser.py`, `test_notion_client.py`, `test_voice.py` и сам shield (`scripts/gate.py:60-68`).
**How to avoid:** в новых тестах не писать присваивания вида `api_key="…16+ символов…"`; использовать короткие значения (`"test-key"`) или `""` (так уже в `SecretaryDialogEngine(db=db, api_key="")`).

### Pitfall 9: Наследование frozen-dataclass событий со значениями по умолчанию
**What goes wrong:** будущее событие с обязательным полем после полей с дефолтом из `DomainEvent` вызовет `TypeError: non-default argument follows default argument`.
**How to avoid:** `@dataclass(frozen=True, slots=True, kw_only=True)` на `DomainEvent` и наследниках [VERIFIED: запуск — `Req(task_id="1")` с обязательным полем работает, `occurred_at.tzinfo == UTC`, присваивание даёт `FrozenInstanceError`, `type(e) is Req`].

### Pitfall 10: `datetime.utcnow` в blueprint
**What goes wrong:** blueprint 2.4 использует `field(default_factory=datetime.utcnow)` — на 3.12 это `DeprecationWarning` [VERIFIED: `python -W error -c "…utcnow()"` → «DeprecationWarning: datetime.datetime.utcnow() is deprecated…»]; гейт чувствителен к предупреждениям не будет, но D-16 предписывает `datetime.now(timezone.utc)`.

## Code Examples

### Сущности и enum (D-03, D-05)
```python
# src/core/domain/entities.py  — только stdlib
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

class WorkspaceClearance(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED_NDA = "restricted_nda"

class ConnectorRole(StrEnum):               # роли привязок PER-02 (здесь только те, для которых есть порт)
    SCHEDULE_SOURCE = "schedule_source"
    CALENDAR_SYNC = "calendar_sync"
    TIMESHEET = "timesheet"
    LMS = "lms"

@dataclass(frozen=True, slots=True)
class ScheduleEvent:
    external_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    location: str | None = None

@dataclass(frozen=True, slots=True)
class WorkRecord:
    shift_date: datetime
    hours: float
    project_tag: str                         # без значения по умолчанию: названия компании в ядре нет

@dataclass(frozen=True, slots=True)
class AcademicSubmission:
    submission_id: str
    title: str
    deadline: datetime | None                # LMS отдаёт строку; адаптер парсит терпимо, None при неудаче
    is_public: bool

@dataclass(frozen=True, slots=True)
class Task:
    title: str
    area: str                                # свободная строка (PRT-01)
    status: str

@dataclass(frozen=True, slots=True)
class EmailMessage:                          # только объявление; правило NDA-почты — Фаза 6 (ISO-02)
    message_id: str
    subject: str
    sender: str
    received_at: datetime
    body: str = ""
    workspace_id: str | None = None

@dataclass(frozen=True, slots=True)
class Workspace:
    id: str
    name: str
    clearance: WorkspaceClearance
    path: str
    remote: str | None = None

@dataclass(frozen=True, slots=True)
class Persona:
    id: str
    name: str
    workspaces: tuple[Workspace, ...] = ()
```

### Тест D-05: рабочие пространства синтетической персоны (сборка — в самом тесте)
```python
# tests/test_core_domain.py  (фрагмент; поля persona взяты из tests/synthetic_persona.py: "id", "label", "path", "clearance", "remote")
from src.core.domain.entities import Persona, Workspace, WorkspaceClearance

def test_synthetic_workspaces_map_to_clearance(synthetic_persona):
    spaces = tuple(
        Workspace(id=w["id"], name=w["label"], clearance=WorkspaceClearance(w["clearance"]),
                  path=w["path"], remote=w.get("remote"))
        for w in synthetic_persona["workspaces"]
    )
    persona = Persona(id=synthetic_persona["id"], name=synthetic_persona["display_name"], workspaces=spaces)
    assert {w.clearance for w in persona.workspaces} == set(WorkspaceClearance)
    assert len(WorkspaceClearance) == 3
```
Значения `clearance` в синтетической персоне — `"public"`, `"internal"`, `"restricted_nda"` ([VERIFIED: `/opt/assistant-core/tests/synthetic_persona.py`, блок `"workspaces"`]); боевой загрузчик персоны — Фаза 3, поэтому в production-коде конструктора `Workspace.from_dict` быть не должно.

### Conformance-тест (D-10)
```python
# tests/test_ports_conformance.py  (эскиз)
import inspect
from unittest.mock import MagicMock
import pytest
from src.calendar.client import GoogleCalendarClient
from src.calendar.provider import GoogleCalendarSink
from src.connectors.aadhk.parser import AadhkIngestionService
from src.connectors.aadhk.provider import AadhkTimesheetProvider
from src.connectors.guap_lms.client import GuapLmsClient
from src.connectors.guap_lms.provider import GuapLmsProvider
from src.core.ports.connectors import (BaseCalendarSink, BaseLMSProvider,
                                       BaseScheduleProvider, BaseTimesheetProvider)
from src.parser.provider import ScheduleParserSource
from src.parser.schedule_parser import ScheduleParser

def _impls():
    return [
        (BaseScheduleProvider, ScheduleParserSource(ScheduleParser())),
        (BaseCalendarSink, GoogleCalendarSink(GoogleCalendarClient(dry_run=True))),   # не читает token.json
        (BaseTimesheetProvider, AadhkTimesheetProvider(AadhkIngestionService(MagicMock()))),
        (BaseLMSProvider, GuapLmsProvider(GuapLmsClient(email="", password=""))),
    ]

@pytest.mark.parametrize("port,impl", _impls())
def test_impl_conforms(port, impl):
    assert isinstance(impl, port)
    for name in _async_methods(port):          # имена берём из аннотаций/членов Protocol, а не руками
        assert inspect.iscoroutinefunction(getattr(impl, name)), name

def test_schedule_roles_are_separated():
    src_side, sink_side = _impls()[0][1], _impls()[1][1]
    assert isinstance(src_side, BaseScheduleProvider) and not isinstance(src_side, BaseCalendarSink)
    assert isinstance(sink_side, BaseCalendarSink) and not isinstance(sink_side, BaseScheduleProvider)

def test_lms_confirmation_markers():
    assert BaseLMSProvider.REQUIRES_CONFIRMATION == frozenset({"submit_grade", "delete_task"})
```

### Контракт `core-is-pure` (D-02, расширяемый список)
```ini
# Source: формат — существующие контракты в /opt/assistant-core/.importlinter (прочитан в этой сессии)
[importlinter:contract:core-is-pure]
name = ядро (core) не зависит от адаптеров и use-cases
type = forbidden
source_modules =
    src.core
forbidden_modules =
    src.connectors
    src.calendar
    src.parser
    src.sender
    src.collector
    src.notifier
    src.brain
    src.storage
    src.models
    src.main
    src.detector
    src.config
allow_indirect_imports = True
ignore_imports =
```
Рекомендация: к списку D-02 добавить `src.detector` и `src.config` (оба существуют: `src/detector/__init__.py`, `src/config.py`) — иначе ядро могло бы импортировать их, не нарушая контракт, хотя D-01 говорит «только stdlib и `src.core.*`». Это надмножество D-02, не противоречит ему. Дополняющая рантайм-проверка: подпроцесс `python -c "import src.core, sys; assert not [m for m in sys.modules if m.startswith('src.') and not m.startswith('src.core')]"` ловит динамические импорты, которых grimp не видит (`src/__init__.py` содержит только докстринг и `__version__`, импорта не тянет).

### Конечное состояние `ignore_imports` (D-15)
Сегодняшний файл содержит ровно пять записей ([VERIFIED: чтение `/opt/assistant-core/.importlinter`]):
`src.brain.secretary_dialog -> src.connectors.aadhk.parser`; `src.notifier.bot_handler -> src.connectors.aadhk.parser`; `-> src.connectors.gdrive.client`; `-> src.connectors.guap_lms.client`; `-> src.sender.email_sender`. Итог — обе секции без строк `ignore_imports` (допустимо оставить ключ с пустым значением или убрать совсем; оба варианта разбираются `_ignored_pairs` в `test_architecture_contract.py` как пустой список).

## Карта мест, которые обязана закрыть PRT-04

Построено агентом Antigravity (`reader`, `gemini-3.8-flash-medium`) и выборочно перепроверено самим (`grep` и чтение строк 1035-1175 `bot_handler.py`, 125-160 `secretary_dialog.py`, 95-135 `live_ticker.py`, 133-136/227-230/555-600/655-658 `main.py`): расхождений не найдено.

| Место | Что сейчас | Новое (рекомендация) |
|-------|-----------|----------------------|
| `bot_handler.py:22` | `from src.sender.email_sender import EmailSender` (top-level) | аннотация `EmailSenderLike` из `src/core/ports/clients.py`; дефолт `default_email_sender()` |
| `bot_handler.py:23`, :56 | `from src.connectors.guap_lms.client import GuapLmsClient`; `lms_client or GuapLmsClient()` | аннотация `LmsClientLike` (sync, D-11); дефолт `default_lms_client()` |
| `bot_handler.py:1052-1054` | inline `AadhkIngestionService(self.db).ingest_backup_file(dest_path)` | `self._timesheet().ingest_backup_file(dest_path)` |
| `bot_handler.py:1095-1099` | inline `AadhkIngestionService(self.db)`; `reconcile_all_conflicts()`; `get_monthly_pacing(project_name="Тидекс")` | то же через `self._timesheet()` |
| `bot_handler.py:1143-1146` | inline `GoogleDriveClient()` + `is_configured` + `sync_aadhk_from_drive(self.db)` | фабрика `drive_client_factory()` на каждый колбэк |
| `bot_handler.py:1144, 1156` | inline `AadhkIngestionService(self.db)`; `reconcile_all_conflicts()` | через `self._timesheet()` |
| `bot_handler.py:67` | `SecretaryDialogEngine(db=self.db)` | передать `timesheet_service=self._timesheet_service` (None → дефолт в движке) |
| `secretary_dialog.py:139-141` | inline `AadhkIngestionService(self.db).get_monthly_pacing(project_name="Тидекс")` | параметр `timesheet_service: BaseTimesheetProvider \| None = None` (образец — `methodist`), дефолт лениво через `default_timesheet_service(self.db)` |
| `live_ticker.py:115-116` | inline `AadhkIngestionService(self.db)` — НЕ в `ignore_imports`, контракта на `live_ticker` нет | см. Open Question 1 |

`bot_handler` также вызывает `self.email_sender.send_reply` (:576) и `lms_client`-методы через `asyncio.to_thread` (:1621, :1645, :1672, :1694, :1724, :1916, :1933, :1936, :2009) — сигнатуры `LmsClientLike` должны покрывать ровно `list_tasks`, `get_task_details`, `create_task`, `delete_task`, `set_task_visibility`, `get_disciplines`.
`main.py` (:135, :229, :240, :295, :566, :568, :582, :586, :657) — корень композиции, в контрактах не участвует. Рекомендация: НЕ трогать `main.py` в Фазе 2 (D-12 «по возможности»; `tests/test_lms_bot_workflow.py` импортирует `src.main.run_lms_monitor_cycle` — лишний риск без выигрыша для критериев).
Остальные use-cases (`intent_router.py`, `methodist.py`) импортируют только `src.storage.db`, `src.config`, `src.models`, `google.genai` — адаптеров не импортируют: критерий 4 по сути выполнен для них уже сейчас, в плане нужна лишь проверка/фиксация (см. Open Question 2).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` (blueprint 2.4) | `datetime.now(timezone.utc)` | Python 3.12 (DeprecationWarning) | Использовать в `DomainEvent.occurred_at` (D-16) |
| `class X(str, Enum)` (blueprint 2.1) | `enum.StrEnum` | Python 3.11 | Предписано D-03 |
| `@dataclass(frozen=True)` | `@dataclass(frozen=True, slots=True, kw_only=True)` | `slots` 3.10, `kw_only` 3.10 | Меньше памяти, события расширяемы обязательными полями |

**Deprecated/outdated:**
- Указание blueprint «ближайший к `BaseScheduleProvider` — `calendar/client.py`»: устарело после W8, это приёмник (`calendar_sync`); `BaseScheduleProvider` ложится на `ScheduleParser` (ROADMAP, заметки для планирования).
- Сигнатуры blueprint `fetch_events(since)`, `diff_against`, `fetch_shifts`, `monthly_pacing`, `list_tasks() -> list[AcademicSubmission]` — ориентир; фактические методы другие (таблица выше), в порты идут фактические (D-06).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Имена scope (`schedule.read`, `calendar.write`, `timesheet.read`/`timesheet.write`, `lms.read`/`lms.write`) и `connector_id` (`schedule_site`, `google_calendar`, `aadhk_timesheet`, `lms_portal`) — выбор исследователя по аналогии с blueprint `git.read` (GIT-01) | Pattern 2, Standard Stack | Низкий: в Фазе 6 (ISO-03) персона выдаёт scopes — возможно переименование; в Фазе 2 они только декларативны |
| A2 | `AcademicSubmission.deadline: datetime \| None` с терпимым разбором формата `dd.mm.yyyy` (единственный формат, виденный в `tests/test_guap_lms.py:43`) | Code Examples | Низкий: адаптер возвращает `None` при неудаче, потребителей нет (D-04) |
| A3 | Атрибут `role: ClassVar[ConnectorRole]` на специализированных портах и enum `ConnectorRole` (4 значения) — добавление исследователя сверх PRT-02 | Pattern 1 | Низкий: делает W8 проверяемым; если владелец/планировщик считает избыточным — убрать, ролевое разделение останется по набору методов |
| A4 | Дефолтный экземпляр `AadhkTimesheetProvider(AadhkIngestionService(db))` создаётся per-call, а не один раз в конструкторе, как гарантия «ноль изменения поведения» | Pattern 3 | Низкий: сервис без состояния; если создавать один раз — поведение то же |
| A5 | Расширение контракта `core-is-pure` модулями `src.detector`, `src.config` (надмножество D-02) | Code Examples | Низкий: оба модуля не нужны ядру; при необходимости убрать из списка |

## Open Questions

1. **Расширять ли контракт на `live_ticker`?**
   - What we know: `docs/BASELINE.md:135` оставляет решение Фазе 2; нарушение — одно (`live_ticker.py:115`, inline); `LiveTickerService(db)` в тестах создаётся с `db=MagicMock()` (`tests/test_live_ticker.py:40,51,73,99,187`), `get_timesheet_metrics` в этих местах не патчится.
   - What's unclear: нужно ли это для критериев (нет — PRT-04 говорит о `secretary_dialog` и `bot_handler`).
   - Recommendation: сделать отдельной финальной задачей плана 3 (после основного DI): параметр `timesheet_service: BaseTimesheetProvider | None = None` в `LiveTickerService`, дефолт per-call через `default_timesheet_service`, новый контракт `live-ticker-no-adapters` с пустым `ignore_imports`, `bot_handler` пробрасывает сервис. Стоимость — ~10 строк; «сегодняшнее поведение» сохраняется тем же `try/except` с `logger.warning`. Если на этапе плана это перегрузит волну — зафиксировать в BASELINE как оставшийся долг.

2. **Как читать критерий 4 ROADMAP («use-cases зависят только от портов и домена») буквально?**
   - What we know: `brain` импортирует `src.config`, `src.storage.db.Database`, `src.models.*`, `google.genai`; D-04 легализует `src.models`, но ничего не говорит про `src.storage`/`src.config`.
   - What's unclear: считать ли `Database` допустимой зависимостью.
   - Recommendation: читать критерий как «нет импортов адаптеров» (контракт `brain-no-adapters`, проверяется линтером) и явно записать в плане и в VERIFICATION, что `src.storage`/`src.config` остаются известными зависимостями до Фазы 4 (владелец схемы БД) и Фазы 3 (персона). Вопрос владельцу не требуется — это уточнение формулировки, а не изменение объёма.

3. **Правка существующего `test_architecture_contract.py` (`MAX_IGNORED_IMPORTS = 5`)?**
   - What we know: комментарий в файле: «Фаза 2 (PRT-04) опускает её до 0»; при 0 записей существующий тест остаётся зелёным (`0 <= 5`). CONTEXT и сквозные критерии запрещают менять существующие тесты.
   - Recommendation: НЕ править старый файл; добавить новый тест «долг = 0» (в `tests/test_core_architecture.py`, переиспользуя `_read_real_config`, `_contracts`, `_ignored_pairs` из `tests/test_architecture_contract.py` — `tests/__init__.py` существует, `pythonpath = .`). Усиление, а не ослабление.

4. **Обновлять ли `docs/BASELINE.md` в chat-app?**
   - What we know: CONTEXT говорит «в chat-app меняются лишь документы `.planning/`»; BASELINE.md описывает «пять записей долга», `2 kept`, число тестов (127).
   - Recommendation: одна финальная документная правка BASELINE.md (раздел контрактов: три контракта, долг 0, новое число тестов) в `master` chat-app — документ, не код; если планировщик считает её вне объёма, отметить в SUMMARY как следующий шаг. Решение низкого риска.

5. **Замечание код-ревью Фазы 1 WR-03 (в гейте нет нижней границы числа тестов), рекомендованное к закрытию «до рефакторинга Фазы 2» (`STATE.md`).**
   - What we know: гейт красит прогон с 0 тестов/skip/xfail/deselect, но не защищает от сужения набора переменной `PYTEST_ADDOPTS`.
   - Recommendation: перед плановым рефакторингом (план 3) добавить в план отдельную маленькую задачу chat-app `scripts/gate.py` (нижняя граница: 127 + число новых тестов; игнорирование `PYTEST_ADDOPTS`) ИЛИ явно записать, что гейт запускается из чистого окружения (`env -u PYTEST_ADDOPTS`). Выбор — за планировщиком; без этого рефакторинг идёт под сетью с известной дырой.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv assistant-core) | Вся фаза | ✓ | 3.12.3 | — |
| pytest / pytest-asyncio | Тесты | ✓ | 9.1.1 / 1.4.0 (`asyncio_mode = auto`) | — |
| import-linter / grimp | Контракты, страж-тест | ✓ | 2.15 / 3.17 (`lint-imports --no-logo --no-cache` → «2 kept, 0 broken», 0.4 с) | — |
| `python3 /opt/chat-app/scripts/gate.py` | Приёмка шага | ✓ | — | — |
| `scripts/agy_task.sh` (Antigravity) | Делегирование шаблонного кода (D-19) | ✓ | — | Писать самому |
| Внешние сервисы (GUAP LMS, Google, AADHk-бэкап, Telegram) | — | не нужны | — | Тесты на фейках (D-08) |
| systemd-сервисы | — | остаются остановленными | — | Перезапусков нет (D-18) |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = auto`; `async def test_*` без маркеров) |
| Config file | `/opt/assistant-core/pytest.ini` (`testpaths = tests`, `pythonpath = .`) |
| Quick run command | `cd /opt/assistant-core && .venv/bin/pytest tests/test_core_domain.py tests/test_core_events.py tests/test_ports_conformance.py tests/test_composition_di.py tests/test_core_architecture.py tests/test_architecture_contract.py -q && .venv/bin/lint-imports --no-logo --no-cache` |
| Full suite command | `python3 /opt/chat-app/scripts/gate.py` (оба pytest + import-linter + shield + дрейф персоны; «ИТОГ: ЗЕЛЁНЫЙ») |

Базовое состояние: assistant-core 127 passed (`docs/BASELINE.md`), chat-app 14 + `test_gate.py`; прогон assistant-core ≈ 27-45 с.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRT-01 | Сущности frozen+slots, `WorkspaceClearance` ровно 3 значения, `Workspace` из `synthetic_persona` | unit | `.venv/bin/pytest tests/test_core_domain.py -q` | ❌ Wave 0 |
| PRT-01 | `WorkRecord.project_tag` обязателен, названия компании в ядре нет | unit | `.venv/bin/pytest tests/test_core_domain.py -q` | ❌ Wave 0 |
| PRT-02 | Порты объявлены, роли разные, `REQUIRES_CONFIRMATION` == `{"submit_grade","delete_task"}` | unit | `.venv/bin/pytest tests/test_ports_conformance.py -q` | ❌ Wave 0 |
| PRT-03 | `isinstance` + `iscoroutinefunction` для 4 пар порт↔адаптер; schedule_source ≠ calendar_sync | unit | `.venv/bin/pytest tests/test_ports_conformance.py -q` | ❌ Wave 0 |
| PRT-03 | `submit_grade` → `NotImplementedError`; `health_check` без сети (адаптеры на фейках) | unit | `.venv/bin/pytest tests/test_ports_conformance.py -q` | ❌ Wave 0 |
| PRT-04 | Характеризация `handle_cmd_timesheet`, `cb_timesheet_sync`, AADHk-ветка `handle_user_document`, `_get_tydex_context` — одинаковый вывод до и после рефакторинга | unit (фейки) | `.venv/bin/pytest tests/test_composition_di.py -q` | ❌ Wave 0 |
| PRT-04 | Внедрённые зависимости используются вместо дефолтов; `EmailBotHandler(db=..., allowed_user_id=123)` по-прежнему создаётся | unit | `.venv/bin/pytest tests/test_composition_di.py tests/test_fast_intent_router.py tests/test_lms_bot_workflow.py -q` | ❌ Wave 0 (новый) / ✅ (существующие) |
| PRT-04 | Оба `ignore_imports` пусты; `lint-imports` зелёный | unit + lint | `.venv/bin/pytest tests/test_core_architecture.py -q && .venv/bin/lint-imports --no-logo --no-cache` | ❌ Wave 0 |
| PRT-01/02 | `import src.core` не тянет ни одного `src.*` вне `src.core` (рантайм-страж к `core-is-pure`) | unit (подпроцесс) | `.venv/bin/pytest tests/test_core_architecture.py -q` | ❌ Wave 0 |
| PRT-05 | Доставка подписчику точного типа; порядок подписки; изоляция упавшего подписчика (лог, остальные получают); отсутствие доставки неподписанным; sync- и async-обработчики | unit (async) | `.venv/bin/pytest tests/test_core_events.py -q` | ❌ Wave 0 |
| PRT-05 | `occurred_at` — UTC-aware; события неизменяемы; ни одного `publish` в `brain`/`notifier`/`main` | unit | `.venv/bin/pytest tests/test_core_events.py -q` | ❌ Wave 0 |
| SC1 | 100% существующих тестов без правки файлов | gate | `python3 /opt/chat-app/scripts/gate.py` и `git -C /opt/assistant-core diff --stat <базовый>..HEAD -- tests/` показывает только новые файлы | ✅ |

### Sampling Rate
- **Per task commit:** быстрый набор новых тестов + `lint-imports` (секунды).
- **Per wave merge:** `python3 /opt/chat-app/scripts/gate.py` («ИТОГ: ЗЕЛЁНЫЙ»); волны последовательные (2 ГБ ОЗУ).
- **Phase gate:** гейт зелёный; `git diff --name-status <базовый>..HEAD -- tests/` не содержит `M`/`D` для существующих файлов; `lint-imports` без записей `ignore_imports`; сервисы не `active` (`systemctl is-active`, OPS-01).

### Wave 0 Gaps
- [ ] `tests/test_core_domain.py` — PRT-01 (+ D-05)
- [ ] `tests/test_core_events.py` — PRT-05
- [ ] `tests/test_ports_conformance.py` — PRT-02/03 (D-10)
- [ ] `tests/test_composition_di.py` — PRT-04, включая характеризационные тесты непокрытых путей (пишутся ДО рефакторинга и коммитятся отдельным коммитом)
- [ ] `tests/test_core_architecture.py` — `core-is-pure` в рантайме + «долг ignore_imports = 0»
- Фреймворк и конфиг уже есть; установка не нужна.

## Security Domain

`security_enforcement` в `.planning/config.json` не задан → включён. Фаза не добавляет сетевых поверхностей, эндпоинтов и хранения секретов.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Не затрагивается (проверка `allowed_user_id` в боте не меняется) |
| V3 Session Management | no | — |
| V4 Access Control | yes (декларативно) | `REQUIRES_CONFIRMATION` у `BaseLMSProvider`; существующий HITL-диалог `delete_task` в боте сохраняется без изменений (D-09); `WorkspaceClearance` объявлен, обеспечение air-gap — Фаза 6 |
| V5 Input Validation | no | Новых входов нет; `StrEnum(...)` отвергает неизвестный `clearance` значением `ValueError` |
| V6 Cryptography | no | — |
| V7 Error Handling/Logging | yes | `EventBus` логирует исключение подписчика с типом события и именем обработчика, не печатает содержимое события (в будущем там могут быть NDA-метаданные) |

### Known Threat Patterns for этого стека

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Тест читает/печатает `.env`, `credentials.json`, `token.json`, `*.session` | Information Disclosure | `GoogleCalendarClient(dry_run=True)`, фейки; `health_check` без сети и чтения файлов (D-08) |
| Новая находка shield красит гейт / утечка секрета в тестовые данные | Information Disclosure | Не использовать `api_key="<16+ символов>"` в новых тестах; в артефактах нет e-mail, телефонов, реальных ID (сквозной критерий 7) |
| Ослабление HITL при DI (обход подтверждения удаления) | Elevation of Privilege | Не трогать тела `cb_*`/`handle_*` кроме замены источника зависимости; `test_hitl_safety_guardrails.py` и `test_bot_group_isolation.py` проходят без правок |
| Преждевременное обещание air-gap через `EmailMessage` | Information Disclosure | `EmailMessage` только объявляется; в LLM-путь не подключается (ISO-02 — Фаза 6) |
| Персональные токены в новом коде (ФИО, ГУАП/Тидекс) | Information Disclosure | Новые файлы `src/core/**`, `composition.py`, адаптеры не содержат токенов профиля (кроме имён существующих пакетов `guap_lms`/`aadhk` в путях импортов) |

## Project Constraints (from CLAUDE.md)

- Тесты: `/opt/chat-app/backend/.venv/bin/pytest backend/tests` и `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests` — 100% зелёные; гейт `python3 /opt/chat-app/scripts/gate.py` (оба pytest, import-linter, security_shield; exit 0 = «ЗЕЛЁНЫЙ»).
- Zero Regression & Safety First: HITL для деструктивных действий, strict air-gap NDA, существующие тесты не удаляются и не ослабляются.
- Asyncio-first для I/O (`aiosqlite`, `httpx`, `aiohttp`); синхронный клиент ЛК — через `asyncio.to_thread`.
- KISS/YAGNI: типизированные dataclass/Pydantic, без избыточной инженерии (поэтому шина без подписок на подклассы, без unsubscribe, без реестров).
- Язык: код и комментарии на английском или русском, пользовательский вывод строго по-русски (в боте тексты не меняются).
- Делегирование Antigravity: только `scripts/agy_task.sh run --repo <path> --mode read|edit`; `agy` напрямую не запускать; патч ревьюит и применяет Claude; NDA-пространства скрипт отклоняет.
- Контекст ОЗУ VPS (2 ГБ + 4,5 ГБ swap): тяжёлые прогоны последовательно; для Node — `NODE_OPTIONS="--max-old-space-size=1536"` (в этой фазе Node не нужен).
- Перезапуск сервисов (`systemctl restart …`) в CLAUDE.md предписан «если изменено» — в этой фазе НЕ выполнять (D-18: сервисы заморожены).
- Из памяти пользователя: весь текст для пользователя — по-русски; вопросы владельцу — только через `AskUserQuestion` с вариантами.

**Что допустимо делегировать Antigravity в этой фазе (D-19):** черновики dataclass-сущностей (`entities.py`, `events.py` по образцу блока «Code Examples»), шаблонные делегирующие методы адаптеров, черновики параметризованных тестов `test_core_domain.py`/`test_core_events.py`. Профиль `test-writer`/`gsd-executor`, режим `edit`, с проверкой патча Claude. Не делегировать: контракты линтера, DI в `bot_handler`/`secretary_dialog`, характеризационные тесты (требуют запуска и подгонки под текущий вывод), HITL-логику.

## Sources

### Primary (HIGH confidence)
- Исходники assistant-core, прочитанные в этой сессии: `.importlinter`, `src/notifier/bot_handler.py` (1-60, 1035-1175), `src/brain/secretary_dialog.py` (1-30, 55-160), `src/notifier/live_ticker.py` (95-135), `src/main.py` (95-135, 555-600), `src/calendar/client.py`, `src/parser/schedule_parser.py`, `src/connectors/aadhk/parser.py`, `src/connectors/guap_lms/client.py`, `src/connectors/gdrive/client.py`, `src/sender/email_sender.py`, `src/models/schedule.py`, `tests/test_architecture_contract.py`, `tests/synthetic_persona.py`, `tests/conftest.py`, `scripts/security_shield.py`, `pytest.ini`, `requirements-dev.txt`
- chat-app: `.planning/phases/02-…/02-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` §2.1-2.4, `docs/BASELINE.md`, `scripts/gate.py` (1-110), `.claude/skills/agy-delegate/SKILL.md`, `.planning/phases/01-…/01-REVIEW-DISPOSITION.md`
- Эмпирические проверки на Python 3.12.3 (venv assistant-core): поведение `runtime_checkable` Protocol (включая `MagicMock`, `issubclass`, ClassVar, наследование портов), `dataclass(frozen, slots, kw_only)` с наследованием, `StrEnum`, `DeprecationWarning` у `utcnow`; `lint-imports --no-logo --no-cache` → «2 kept, 0 broken»
- Антигравити-инвентаризации (два задания `reader`, перепроверены выборочно, см. выше)

### Secondary (MEDIUM confidence)
- Нет.

### Tertiary (LOW confidence)
- Нет. Context7/веб-поиск не использовались: все вопросы касаются кода репозитория и stdlib, подтверждённых запуском; research-plan seam не вызывался (нет внешних библиотек и документации для запроса).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — только stdlib и уже установленные инструменты, версии прочитаны из venv
- Architecture: HIGH — раскладка следует D-01..D-19 и проверенному поведению Protocol/dataclass; единственное отклонение (`Any` в сигнатурах портов) вынужденное и объяснено
- Pitfalls: HIGH — шесть из десяти подтверждены запуском или чтением кода/конфигов; остальные следуют из прочитанных контрактов и гейта

**Research date:** 2026-10-02
**Valid until:** 2026-11-01 (стабильно; пересмотреть, если до планирования изменятся `.importlinter`, `bot_handler.py` или `gate.py`)

**Расход Antigravity (на эту фазу исследования):** 2 задания `reader` (`gemini-3.8-flash-medium`): сигнатуры 4 классов + gdrive/email/notion — вход 81 285, выход 38 821 токенов (126 с); инвентаризация зависимостей `brain`/`notifier`/`main` — вход 274 386, выход 18 185 токенов (83 с). Всего ≈ 355,7 тыс. входных и 57 тыс. выходных токенов.
