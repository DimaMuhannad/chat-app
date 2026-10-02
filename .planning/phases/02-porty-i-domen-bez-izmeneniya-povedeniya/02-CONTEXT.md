# Phase 2: Порты и домен без изменения поведения - Context

**Gathered:** 2026-10-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Только assistant-core (в chat-app меняются лишь документы `.planning/`). Фаза вводит слой ядра — неизменяемые доменные сущности, async-порты (Protocol) и внутрипроцессный `EventBus` — и разрывает прямые зависимости use-cases (`src.brain`) и `bot_handler` от конкретных коннекторов (GUAP LMS, AADHk, Google Drive, e-mail). Наблюдаемое поведение бота и демона не меняется ни в одном сценарии; тестовые файлы (фикстуры и тела тестов) не меняются, добавляются только новые тесты. Требования: PRT-01..PRT-05.

Не входит: перенос персоны в данные (Фаза 3), HITL-примитив `@requires_confirmation` (Фаза 5), правило «NDA-почта не уходит в LLM» (Фаза 6), публикация событий в боевых потоках.

</domain>

<decisions>
## Implementation Decisions

Владелец (не специалист) снова делегировал технические решения Claude: «реши сам». Все решения ниже — по усмотрению Claude по KISS/YAGNI и CLAUDE.md; это НЕ решения уровня W1–W10. Планировщик обязан им следовать, если исследование не опровергнет их фактами; при опровержении — вернуть вопрос владельцу простыми словами с вариантами (опрос AskUserQuestion, по-русски).

### Раскладка ядра (PRT-01, PRT-02, PRT-05)
- **D-01:** Новый пакет `src/core/` (с `__init__.py`): `src/core/domain/` (сущности, enum, доменные события), `src/core/ports/` (Protocol-порты), `src/core/events.py` или `src/core/events/bus.py` (реализация `EventBus`) — точное имя файла на усмотрение планировщика, ориентир blueprint 2.4. Ядро импортирует только stdlib и `src.core.*`.
- **D-02:** Новый контракт import-linter `core-is-pure` в `/opt/assistant-core/.importlinter`: `src.core` не импортирует `src.connectors`, `src.calendar`, `src.parser`, `src.sender`, `src.collector`, `src.notifier`, `src.brain`, `src.storage`, `src.models`, `src.main`. Контракт добавляется с пустым `ignore_imports`. Тест «доказанно падает» из Фазы 1 (`test_architecture_contract.py`) уже покрывает механизм — новый тест на механизм не нужен.

### Доменные сущности (PRT-01)
- **D-03:** Сущности — `@dataclass(frozen=True, slots=True)`: `ScheduleEvent`, `WorkRecord` (поле `project_tag: str`, без названия компании по умолчанию), `AcademicSubmission`, `Task` (область — свободная `str`), `EmailMessage`, `Workspace`, `Persona`; `WorkspaceClearance` — `StrEnum` ровно со значениями `public`, `internal`, `restricted_nda` (совпадают с допустимыми значениями синтетической персоны Фазы 1). Коллекции внутри — `tuple`/`frozenset`, не `list`.
- **D-04:** Сущности в этой фазе ТОЛЬКО объявляются и используются портами/адаптерами. Существующие модели (`src/models/schedule.py`: `Lesson`, `SchedulePayload`; `src/models/message.py`; `src/models/second_brain.py`) не удаляются и не переписываются; потребители в `brain`/`notifier` на новые сущности не переводятся. Перевод — по мере надобности в Фазах 3+. `src.models` считается допустимой зависимостью use-cases наравне с `src.core` (это pydantic-модели данных, не адаптеры) — критерий 4 ROADMAP читать так.
- **D-05:** Поля `Persona`/`Workspace` — минимальные (id, название, clearance, путь, remote для Workspace; имя, список рабочих пространств для Persona). Полная схема персоны — Фаза 3 (PER-01); здесь её не предвосхищать. Новый тест: рабочие пространства синтетической персоны (фикстура `synthetic_persona`) собираются в `Workspace` с корректным `WorkspaceClearance` — без изменения `synthetic_persona.py`.

### Порты и адаптеры (PRT-02, PRT-03)
- **D-06:** Порты — `typing.Protocol` с `@runtime_checkable` (структурная совместимость: существующие классы и `MagicMock` в тестах не обязаны наследоваться). Имена как в требованиях: `BaseConnector` (`connector_id`, `required_scopes`, `async health_check`), `BaseScheduleProvider` (роль `schedule_source`), порт приёмника календаря (роль `calendar_sync`, имя на усмотрение — напр. `BaseCalendarSink`), `BaseTimesheetProvider`, `BaseLMSProvider`. Сигнатуры — ориентир blueprint разд. 2.2, но методы порта приёмника и прочих портов выводятся из ФАКТИЧЕСКИХ публичных методов существующих классов (`GoogleCalendarClient.sync_schedule/create_event/patch_event/delete_event/find_existing_event`, `AadhkIngestionService.get_timesheet_report/get_monthly_pacing/...`, `ScheduleParser.fetch_schedule_raw`, `GuapLmsClient.list_tasks/...`), а не придумываются заново.
- **D-07:** Несовпадения сигнатур закрываются адаптерами-обёртками рядом с конкретным классом (напр. `src/connectors/guap_lms/provider.py`), сам конкретный класс не переписывается. `GuapLmsClient` синхронный (requests/скрейпер) — НЕ переписывать на async: адаптер `BaseLMSProvider` вызывает его через `asyncio.to_thread` (тот же приём, что уже применяет `bot_handler`). — **Reversibility:** reversible.
- **D-08:** `health_check` в адаптерах — без сетевых вызовов (проверка конфигурации, по образцу `is_configured`); тесты не ходят во внешние сервисы и не читают `.env`/`credentials.json`/`token.json`/`*.session` (как D-18 Фазы 1).
- **D-09:** «Требует подтверждения» для `submit_grade` и `delete_task` в этой фазе — только декларативная пометка в порту (напр. константа `REQUIRES_CONFIRMATION = frozenset({"submit_grade", "delete_task"})` у `BaseLMSProvider`) и тест, что пометка есть. Механизма `@requires_confirmation` нет до Фазы 5; текущий HITL-диалог удаления в боте (`delete_task` через кнопку подтверждения) остаётся как есть. Если у `GuapLmsClient` нет выставления оценки, адаптер реализует `submit_grade` как `NotImplementedError` с понятным сообщением — сегодня его никто не вызывает, поведение не меняется.
- **D-10:** Protocol-проверка (PRT-03) — новый тест `tests/test_ports_conformance.py`: для каждой пары «порт ↔ класс/адаптер» проверяет `isinstance` (runtime_checkable) И что методы порта у реализации есть и являются корутинами там, где порт async (`inspect.iscoroutinefunction`), т.к. `isinstance` с Protocol проверяет только наличие имён. Отдельный тест — роли расписания разделены: парсер сайта соответствует `schedule_source`, но не `calendar_sync`; Google Calendar — наоборот.

### Внедрение зависимостей (PRT-04)
- **D-11:** Ключевое ограничение, найденное при разведке: `bot_handler` уже вызывает клиент ЛК синхронно через `asyncio.to_thread(self.lms_client.list_tasks, 28)`, а тесты (`tests/test_lms_bot_workflow.py`) передают `lms_client=MagicMock()` с синхронными методами. Поэтому в этой фазе `bot_handler` НЕ переводится на async `BaseLMSProvider`: он продолжает принимать «сырой» клиент ЛК, аннотированный синхронным Protocol из `src/core/ports/` (напр. `LmsClientLike` с методами, которые бот реально вызывает: `list_tasks`, `get_task_details`, `create_task`, `delete_task`, `set_task_visibility`, `get_disciplines`). Перевод бота на async-порт с доменными сущностями — когда появится HITL-примитив (Фаза 5) или раньше по необходимости.
- **D-12:** Конструкторы сохраняют сигнатуры и необязательные параметры с `None` по умолчанию (тесты создают `EmailBotHandler(db=test_db, allowed_user_id=123)` без клиентов). Значения по умолчанию создаёт новый модуль-сборщик `src/composition.py` (фабрики `default_lms_client()`, `default_email_sender()`, `default_timesheet_service(db)`, `default_drive_client()` и т. п.), который `bot_handler` и `secretary_dialog` вызывают вместо прямого импорта коннекторов. `src/composition.py` не входит в source/forbidden контрактов (как `src/main.py`); `main.py` по возможности использует те же фабрики. Это совместимо с `allow_indirect_imports = True`, установленным в Фазе 1, — непрямой импорт через сборщик осознанно разрешён; цель PRT-04 — убрать прямые знания use-cases о конкретных классах. — **Reversibility:** reversible.
- **D-13:** Inline-импорты коннекторов в функциях (`secretary_dialog.py:139`, `bot_handler.py:1052,1095,1143,1144`) заменяются на зависимости, переданные в конструктор (по образцу `MethodistService` в `SecretaryDialogEngine.__init__`), с ленивым дефолтом из `src/composition.py`. Top-level импорты `GuapLmsClient` и `EmailSender` в `bot_handler.py` убираются; аннотации типов — через Protocol из `src/core/ports/`.
- **D-14:** Если какой-либо существующий тест патчит путь вида `src.notifier.bot_handler.GuapLmsClient` / `...AadhkIngestionService` (разведка таких не нашла, исследователь обязан перепроверить, включая `patch.object` и строки в `monkeypatch.setattr`), — сохранить совместимость без правки теста; если невозможно — остановиться и вынести владельцу.
- **D-15:** Итог PRT-04: оба списка `ignore_imports` в `.importlinter` assistant-core пусты (строки удаляются вместе с комментариями «долг»), `lint-imports` зелёный на реальных модулях, гейт `python3 /opt/chat-app/scripts/gate.py` — «ЗЕЛЁНЫЙ».

### EventBus (PRT-05)
- **D-16:** Минимальная реализация на asyncio без зависимостей: `subscribe(event_type, handler)`, `async publish(event)`; доставка подписчикам точного типа события, последовательно, в порядке подписки. Исключение подписчика логируется и не прерывает ни публикатора, ни остальных подписчиков (иначе будущая публикация могла бы сломать боевой поток). Доменные события — frozen dataclass по blueprint 2.4 (`DomainEvent` с `event_id`, `occurred_at` в UTC через `datetime.now(timezone.utc)`, не устаревший `utcnow`; `ScheduleChanged`, `TimesheetSynced`, `TaskCreated`, `SecurityViolationDetected`, `DialogMemoryCleared`, `DelegatedToSpecialist`).
- **D-17:** В этой фазе шина НЕ подключается к боевым потокам (ни одного `publish` в `brain`/`notifier`/`main`) — ноль изменения поведения, YAGNI: потребители появятся в следующих фазах. Тесты: доставка подписчику, изоляция упавшего подписчика, отсутствие доставки неподписанным типам.

### Процесс
- **D-18:** Коммиты атомарные, в `main` assistant-core (локально, без push) и в `master` chat-app только для `.planning/`; каждый шаг — гейт зелёный. Порядок рекомендуемый: домен → порты → адаптеры + conformance-тест → сборщик и DI → опустошение `ignore_imports` → EventBus. Сервисы остаются остановленными, перезапусков нет.
- **D-19:** Шаблонный код (dataclass-сущности, черновики тестов) допускается делегировать Antigravity только через `scripts/agy_task.sh` (skill `agy-delegate`) с ревью патча Claude; запускать `agy` напрямую запрещено.

### Claude's Discretion
Все области отданы владельцем на усмотрение Claude. Планировщик дополнительно вправе выбрать: точные имена файлов внутри `src/core/`, имя порта приёмника календаря и sync-Protocol клиента ЛК, состав фабрик в `src/composition.py`, набор полей сущностей сверх минимума D-03/D-05, разбиение на планы — если это не нарушает D-01..D-19.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Требования и границы
- `.planning/REQUIREMENTS.md` — PRT-01..PRT-05, сквозные критерии приёмки
- `.planning/ROADMAP.md` §«Phase 2» — критерии успеха и заметки для планирования (объём переделки по коннекторам, устаревшее указание про calendar после W8)
- `.planning/PROJECT.md` §Key Decisions — EventBus только внутрипроцессный (W9), коммиты в master/main
- `.planning/intel/user-resolutions.md` — решения владельца W1–W10 (особенно W8: разделение ролей расписания, W9: без брокера)

### Архитектура
- `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` §2.2 (порты, сигнатуры-ориентир), §2.3 (requires_confirmation — только пометка в этой фазе), §2.4 (EventBus и события)

### Наследие Фазы 1
- `.planning/phases/01-strahovochnaya-set-i-karkas/01-CONTEXT.md` — D-08 (границы контракта), D-10 (`ignore_imports` как убывающий долг), D-11 (тест механизма линтера), D-18 (тесты без боевых учётных данных)
- `docs/BASELINE.md` — baseline тестов и правила (100% pytest, атомарные коммиты)
- `scripts/gate.py` — гейт качества (оба pytest, import-linter, security_shield)
- `/opt/assistant-core/.importlinter` — текущие контракты и список долга

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SecretaryDialogEngine.__init__` (`/opt/assistant-core/src/brain/secretary_dialog.py:66`) — готовый образец DI: `methodist: MethodistService | None = None` с дефолтом.
- `EmailBotHandler.__init__` (`/opt/assistant-core/src/notifier/bot_handler.py:40`) — уже принимает `email_sender`, `lms_client`, `summarizer` и т. п. опционально; нужно лишь убрать конкретные дефолты/импорты.
- Фикстура `synthetic_persona` (`/opt/assistant-core/tests/conftest.py`, `tests/synthetic_persona.py`) — источник рабочих пространств всех трёх clearance для теста D-05.

### Established Patterns
- Синхронный блокирующий код вызывается через `asyncio.to_thread` (`bot_handler.py:1620`, `:2009`) — тот же приём для адаптера ЛК.
- Тесты передают `MagicMock()` вместо клиентов (`tests/test_lms_bot_workflow.py`, 7 мест) — поэтому структурные Protocol, а не ABC, и синхронный интерфейс клиента ЛК в боте.
- `src/connectors` и `src/sender` — namespace-каталоги без `__init__.py`, перечислены в `root_packages` `.importlinter`; новый `src/core` делать обычным пакетом с `__init__.py`.

### Integration Points
- Inline-импорты коннекторов: `secretary_dialog.py:139` (AADHk), `bot_handler.py:1052,1095,1144` (AADHk), `:1143` (Google Drive); top-level: `bot_handler.py:22` (EmailSender), `:23` (GuapLmsClient).
- Конкретные классы под порты: `src/parser/schedule_parser.py:22` `ScheduleParser`, `src/calendar/client.py:37` `GoogleCalendarClient`, `src/connectors/aadhk/parser.py:55` `AadhkIngestionService`, `src/connectors/guap_lms/client.py:16` `GuapLmsClient` (синхронный).
- Корень композиции: `src/main.py:569` (создание `EmailBotHandler`).

</code_context>

<specifics>
## Specific Ideas

Владелец просил объяснять развилки простыми словами и аналогиями, а при сложности — решать самому. Любой вопрос, который всё же придётся вынести владельцу на следующих шагах, задавать опросом по-русски, без жаргона, с рекомендуемым вариантом первым.

</specifics>

<deferred>
## Deferred Ideas

- Перевод `bot_handler` на async `BaseLMSProvider` и доменную `AcademicSubmission` — Фаза 5 (вместе с `@requires_confirmation`) или по необходимости раньше.
- Публикация доменных событий в боевых потоках (очистка памяти, синхронизация табеля, создание задачи) — по мере появления подписчиков в следующих фазах.
- Перевод use-cases с `src/models` (`Lesson`, `SchedulePayload`) на доменные сущности — Фаза 3+.
- Выставление оценок в ЛК (`submit_grade`) как реальная функция — новая возможность, не в этой миграции.

</deferred>

---

*Phase: 02-porty-i-domen-bez-izmeneniya-povedeniya*
*Context gathered: 2026-10-02*
