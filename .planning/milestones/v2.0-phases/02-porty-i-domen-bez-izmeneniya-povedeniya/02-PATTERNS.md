# Фаза 2: Порты и домен без изменения поведения - Карта паттернов

**Составлено:** 2026-10-02
**Файлов проанализировано:** 24 (новых 21, изменяемых 3 кода + 2 документа)
**Аналоги найдены:** 21 / 24 (3 файла без прямого аналога, опираются на RESEARCH.md)

Все пути ниже относительно `/opt/assistant-core`, если не сказано иное. Все аналоги проверены: это отслеживаемые git-файлы (`git ls-files`), зеркал/установленных копий нет.

## Классификация файлов

| Новый/изменяемый файл | Роль | Поток данных | Ближайший аналог | Качество |
|---|---|---|---|---|
| `src/core/__init__.py`, `src/core/*/__init__.py` | config (пакет) | - | `src/models/__init__.py`, `src/calendar/__init__.py` | role-match |
| `src/core/domain/entities.py` | model | transform | `src/models/schedule.py` (данные) + RESEARCH "Сущности" | role-match |
| `src/core/domain/events.py` | model | event-driven | нет в коде; RESEARCH Pitfall 9 / blueprint 2.4 | no analog |
| `src/core/ports/connectors.py` | port (Protocol) | request-response | нет Protocol в коде; RESEARCH Pattern 1 | no analog |
| `src/core/ports/clients.py` | port (sync Protocol) | request-response | реальная поверхность `GuapLmsClient`, `EmailSender` | partial |
| `src/core/events/bus.py` | service | pub-sub | нет; RESEARCH Pattern 4 | no analog |
| `src/connectors/guap_lms/provider.py` | adapter | request-response (sync->async) | `bot_handler.py` приём `asyncio.to_thread` | role-match |
| `src/connectors/aadhk/provider.py` | adapter | CRUD (async) | `src/connectors/aadhk/parser.py` (делегируемый класс) | role-match |
| `src/calendar/provider.py` | adapter | request-response | `src/calendar/client.py` | role-match |
| `src/parser/provider.py` | adapter | request-response | `src/parser/schedule_parser.py` | role-match |
| `src/composition.py` | config (корень композиции) | - | inline-импорты `bot_handler.py:1052,1143`, `secretary_dialog.py:139` | exact (переносит их) |
| `src/notifier/bot_handler.py` (изм.) | use-case | event-driven | сам файл + `SecretaryDialogEngine.__init__` (образец DI) | exact |
| `src/brain/secretary_dialog.py` (изм.) | use-case | request-response | `SecretaryDialogEngine.__init__` параметр `methodist` | exact |
| `src/notifier/live_ticker.py` (изм., по Open Question 1) | use-case | request-response | `secretary_dialog.py:139` | exact |
| `.importlinter` (изм.) | config | - | контракты `brain-no-adapters`, `bot-handler-no-adapters` | exact |
| `tests/test_core_domain.py` | test | transform | `tests/test_synthetic_persona.py`, `tests/conftest.py` | role-match |
| `tests/test_core_events.py` | test | pub-sub | `tests/test_methodist.py`/`test_lms_bot_workflow.py` (async-стиль) | partial |
| `tests/test_ports_conformance.py` | test | request-response | `tests/test_phase1.py:291` (конструирование клиентов) | partial |
| `tests/test_composition_di.py` | test | request-response | `tests/test_lms_bot_workflow.py` | role-match |
| `tests/test_core_architecture.py` | test | file-I/O (конфиг) | `tests/test_architecture_contract.py` | exact |
| `/opt/chat-app/scripts/gate.py` (по Open Question 5, опц.) | config | batch | сам файл | exact |
| `/opt/chat-app/docs/BASELINE.md` (изм., док) | docs | - | сам файл | exact |

## Назначение паттернов

### `src/core/domain/entities.py` и `events.py` (model)

**Аналог:** нет ни одного frozen-dataclass в кодовой базе (используются pydantic-модели в `src/models/*`); берите готовые эскизы из `02-RESEARCH.md`, раздел "Code Examples / Сущности и enum" (строки 442-510) и "Pattern 4" для `DomainEvent`. Правила: `@dataclass(frozen=True, slots=True)`, для событий дополнительно `kw_only=True`, `occurred_at` через `datetime.now(timezone.utc)` (не `utcnow`), `WorkspaceClearance(StrEnum)` ровно 3 значения. Импортировать только stdlib. Pydantic-модели из `src/models` не трогать и не импортировать (контракт `core-is-pure`).

---

### `src/core/ports/connectors.py` и `clients.py` (port)

**Аналога-Protocol нет.** Источник - RESEARCH "Pattern 1" (строки 221-254) и таблица "Фактические публичные методы" (строки 205-212). Сигнатуры брать из реальных классов, `Lesson`/`ScheduleDiff`/`Database` в ядре типизировать как `Any`.

Реальная поверхность для `LmsClientLike` (sync) - `src/connectors/guap_lms/client.py`:
```python
@property
def is_configured(self) -> bool:                       # строка 46
def list_tasks(self, semester: int | str = 28) -> list[dict[str, Any]]    # :124
def get_task_details(self, task_id: int | str) -> dict[str, Any]           # :221
def delete_task(self, task_id: int | str, semester_id: int | str = 28) -> bool   # :390
def set_task_visibility(self, task_id, is_public, semester_id=28) -> bool  # :431
def get_disciplines(self) -> list[dict[str, Any]]                          # :551
```
`LmsClientLike` - только sync-методы без `async` (тесты передают `MagicMock()`; `isinstance(MagicMock(), Protocol)` на 3.12 даёт `False`, поэтому `isinstance` в конструкторах use-cases НЕ использовать).

---

### `src/connectors/guap_lms/provider.py` (adapter, sync->async)

**Аналог:** `02-RESEARCH.md` Pattern 2 (строки 262-292) + существующий приём `asyncio.to_thread` в `src/notifier/bot_handler.py` (`asyncio.to_thread(self.lms_client.list_tasks, 28)`, строки около 1621, 2009).

Особенности: атрибуты `connector_id`, `required_scopes`, `role`, `REQUIRES_CONFIRMATION` объявлять на уровне КЛАССА (не в `__init__`); `health_check` - только `bool(self._client.is_configured)` (образец `GuapLmsClient.is_configured`, `client.py:46-48`, без сети); `submit_grade` -> `NotImplementedError("...")`.

---

### `src/connectors/aadhk/provider.py`, `src/calendar/provider.py`, `src/parser/provider.py` (adapter)

**Аналог:** оборачиваемые классы (`AadhkIngestionService` `parser.py:55-61,405,428`, `GoogleCalendarClient` `client.py:37,129-245`, `ScheduleParser` `schedule_parser.py:22,53`). Копировать сигнатуры методов дословно, для методов с зашитыми дефолтами (`"Тидекс"`, `8.5`) пробрасывать `*args, **kwargs`, не плодить копии хардкода. Роли: `ScheduleParserSource` - `schedule_source` (`fetch_schedule_raw`, `parse_json_payload`, `parse_html_payload`, sync-методы остаются sync), `GoogleCalendarSink` - `calendar_sync`. `health_check` без чтения `token.json`/сети (D-08).

---

### `src/composition.py` (корень композиции)

**Аналог:** переносит существующие inline-импорты. Текущее состояние:

`src/notifier/bot_handler.py:1048-1054` (`handle_user_document`):
```python
try:
    from src.connectors.aadhk.parser import AadhkIngestionService
    ingestion = AadhkIngestionService(self.db)
    res = await ingestion.ingest_backup_file(dest_path)
```
`bot_handler.py:1142-1148` (`cb_timesheet_sync`):
```python
from src.connectors.gdrive.client import GoogleDriveClient
from src.connectors.aadhk.parser import AadhkIngestionService
client = GoogleDriveClient()
if not client.is_configured:
```
Шаблон результата - RESEARCH Pattern 3 (строки 299-318): фабрики с ЛЕНИВЫМ импортом внутри функции (`default_lms_client()`, `default_email_sender()`, `default_timesheet_service(db)`, `default_drive_client()`), чтобы `patch("src.connectors.aadhk.parser.AadhkIngestionService", Fake)` продолжал работать. `src.composition` дописать в `forbidden_modules` контрактов в том же коммите, где создаётся файл (Pitfall 7).

---

### `src/notifier/bot_handler.py` (use-case, изменение)

**Аналог:** собственный конструктор и `SecretaryDialogEngine.__init__`.

Убираемые импорты (строки 22-23):
```python
from src.sender.email_sender import EmailSender
from src.connectors.guap_lms.client import GuapLmsClient
```
Текущий конструктор (строки 40-57), который нужно сохранить по сигнатуре:
```python
email_sender: EmailSender | None = None,
...
lms_client: GuapLmsClient | None = None,
...
self.email_sender = email_sender or EmailSender()
self.lms_client = lms_client or GuapLmsClient()
```
Заменить на аннотации `EmailSenderLike`/`LmsClientLike` и `default_*()` из `src.composition` (RESEARCH строки 320-331). Параметры оставить `... | None = None`: тесты вызывают `EmailBotHandler(db=in_memory_db, notifier=notifier, allowed_user_id=12345)` и `lms_client=mock_lms` (`tests/test_lms_bot_workflow.py:91,116`). Строка 67 `SecretaryDialogEngine(db=self.db)` - пробросить `timesheet_service`. Для Drive внедрять ФАБРИКУ (свежий клиент на колбэк).

Группа строк `ignore_imports` для `bot_handler -> connectors.aadhk.parser` (3 inline-импорта: 1052, 1095, 1144) убирать ОДНИМ коммитом.

---

### `src/brain/secretary_dialog.py` (use-case, изменение)

**Аналог (образец DI):** `src/brain/secretary_dialog.py:66-76`:
```python
def __init__(self, db: Database, api_key: str | None = config.GEMINI_API_KEY,
             model: str = config.GEMINI_MODEL,
             methodist: MethodistService | None = None) -> None:
    ...
    self.methodist = methodist or MethodistService(db, api_key=api_key, model=model)
```
Применить так же: добавить `timesheet_service: BaseTimesheetProvider | None = None`; в `_get_tydex_context` (строки 136-141) заменить inline-импорт `AadhkIngestionService(self.db).get_monthly_pacing(project_name="Тидекс")` на вызов через сервис с ленивым дефолтом `default_timesheet_service(self.db)`. Тело форматирования ответа и `try/except` не менять.

---

### `src/notifier/live_ticker.py` (опционально, Open Question 1)

**Аналог:** `src/notifier/live_ticker.py:112-120` (`get_timesheet_metrics`) - тот же inline-импорт `AadhkIngestionService`, обёрнут в `try/except` с `logger.warning("LiveTicker: error fetching timesheet pacing: %s", e)`. Сохранить `try/except` как есть, поменять только источник сервиса. Тесты создают `LiveTickerService(db=MagicMock())` (`tests/test_live_ticker.py:40,...`) - сигнатуру не ломать.

---

### `.importlinter` (config)

**Аналог:** существующие контракты, формат такой (файл целиком читан):
```ini
[importlinter:contract:bot-handler-no-adapters]
name = bot_handler не импортирует адаптеры
type = forbidden
source_modules =
    src.notifier.bot_handler
forbidden_modules =
    src.connectors
    ...
allow_indirect_imports = True
ignore_imports =
    # долг, только убывает: ...
    src.notifier.bot_handler -> src.sender.email_sender
```
Новый контракт `core-is-pure` - полный текст в `02-RESEARCH.md` строки 572-592 (с `ignore_imports =` пустым; рекомендовано добавить `src.detector`, `src.config`). В `root_packages` (`src`, `src.connectors`, `src.sender`) ничего добавлять не надо: `src/core` - обычный пакет внутри `src`. Итог D-15: строки и комментарии "долг" удаляются парно с убираемым импортом.

---

### `tests/test_core_architecture.py` (test)

**Аналог:** `tests/test_architecture_contract.py` - переиспользовать хелперы (импортируются, `tests/__init__.py` существует, `pythonpath = .`).

Хелперы (строки 67-91):
```python
def _lines(value: str) -> list[str]: ...
def _read_real_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(REAL_CONFIG, encoding="utf-8")
    return parser
def _contracts(parser) -> list[configparser.SectionProxy]:
    return [parser[s] for s in parser.sections() if s.startswith("importlinter:contract:")]
def _ignored_pairs(contract) -> list[tuple[str, str]]: ...
```
Шаблон проверки долга (строки 132-137):
```python
def test_ignore_imports_debt_only_shrinks():
    parser = _read_real_config()
    total = sum(len(_ignored_pairs(contract)) for contract in _contracts(parser))
    assert total <= MAX_IGNORED_IMPORTS
```
Новый тест: то же с `== 0`. Старый файл НЕ править (`MAX_IGNORED_IMPORTS = 5` остаётся, 0 <= 5). Рантайм-страж: `subprocess` с `python -c "import src.core, sys; ..."` (RESEARCH строка 593). Подпроцессы - только на синтетике/копиях (как `_run_lint` строки 41-51).

---

### `tests/test_core_domain.py` (test)

**Аналог:** фикстура `tests/conftest.py`:
```python
from .synthetic_persona import SYNTHETIC_PERSONA

@pytest.fixture
def synthetic_persona() -> dict:
    return copy.deepcopy(SYNTHETIC_PERSONA)
```
Тест D-05 - готовый фрагмент в `02-RESEARCH.md` строки 517-525 (ключи `w["id"]`, `w["label"]`, `w["path"]`, `w["clearance"]`, `w.get("remote")`). `synthetic_persona.py` не менять.

---

### `tests/test_ports_conformance.py` (test)

**Аналог:** безопасное конструирование клиентов уже есть в тестах - `tests/test_phase1.py:291` `GoogleCalendarClient(dry_run=True)`, `tests/test_guap_lms.py:9` `GuapLmsClient(email="", password="")`. Каркас - RESEARCH строки 531-567. Помнить: `isinstance` проверяет только имена, поэтому добавлять `inspect.iscoroutinefunction`; не писать присваиваний вида `api_key="<16+ символов>"` (shield).

---

### `tests/test_composition_di.py` (test)

**Аналог:** `tests/test_lms_bot_workflow.py` - фикстура и стиль:
```python
@pytest.fixture
async def in_memory_db():
    db = Database(":memory:")
    await db.init_db()
    yield db
    await db.close()
...
handler = EmailBotHandler(db=in_memory_db, notifier=notifier, allowed_user_id=12345, lms_client=mock_lms)
```
Характеризационные тесты 4 непокрытых путей пишутся и коммитятся ДО рефакторинга; патчить `src.connectors.aadhk.parser.AadhkIngestionService` и `src.connectors.gdrive.client.GoogleDriveClient` (как `tests/test_gdrive_client.py:43-44` патчит модули-источники). `asyncio_mode = auto`.

---

### `tests/test_core_events.py` (test)

Прямого аналога нет, брать `async def test_*` без маркеров (`asyncio_mode = auto`). Кейсы - из D-17: доставка, порядок, изоляция упавшего подписчика (`caplog`), отсутствие доставки неподписанным, sync+async обработчик, `occurred_at.tzinfo` UTC, `FrozenInstanceError`. Дополнительно grep-страж "ни одного `publish` в `src/brain`, `src/notifier`, `src/main.py`".

---

## Общие паттерны

### Нулевая регрессия при DI
**Источник:** `bot_handler.py:40-57`, `secretary_dialog.py:66-76`
**Применять к:** `bot_handler.py`, `secretary_dialog.py`, `live_ticker.py`
Параметры остаются `X | None = None`; дефолт - ленивая фабрика из `src.composition`; тела `cb_*`/`handle_*` меняются только в источнике зависимости (HITL-тесты `test_hitl_safety_guardrails.py`, `test_bot_group_isolation.py` без правок).

### Структурные Protocol вместо ABC
**Источник:** RESEARCH Pattern 1
**Применять к:** `src/core/ports/*`, адаптеры. Только аннотации; `isinstance` только в `test_ports_conformance.py` на настоящих адаптерах.

### Чистота ядра
**Источник:** контракт `core-is-pure`
**Применять к:** все файлы `src/core/**`: только stdlib и `src.core.*`; `Any` вместо `Lesson`/`ScheduleDiff`/`Database`.

### Тесты без боевых данных
**Источник:** `tests/test_phase1.py:291`, `tests/test_guap_lms.py:9`
**Применять к:** все новые тесты: `dry_run=True`, пустые учётные данные, `MagicMock()` для `Database`; не читать `.env`/`token.json`/`credentials.json`/`*.session`.

### Порядок коммитов (D-18)
домен (+ контракт `core-is-pure` в том же коммите, где появляется `src/core/__init__.py`) -> порты -> адаптеры + conformance -> характеризационные тесты -> `composition.py` + DI (строка `ignore_imports` удаляется в том же коммите) -> EventBus. После каждого шага: `python3 /opt/chat-app/scripts/gate.py`.

## Аналог не найден

| Файл | Роль | Поток | Причина |
|---|---|---|---|
| `src/core/domain/events.py` | model | event-driven | В кодовой базе нет frozen-dataclass/событий; брать RESEARCH Pitfall 9 и blueprint 2.4 (`docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md`) |
| `src/core/ports/connectors.py` | port | request-response | Protocol-классов в проекте нет; RESEARCH Pattern 1 |
| `src/core/events/bus.py` | service | pub-sub | Шины нет; RESEARCH Pattern 4 (~25 строк, `CancelledError` не глотать) |

## Метаданные

**Область поиска аналогов:** `/opt/assistant-core/src` (brain, notifier, connectors, calendar, parser, sender, models, storage), `/opt/assistant-core/tests`, `.importlinter`
**Дополнительно:** RESEARCH.md и инвентаризация Antigravity из исследования использованы повторно; новых вызовов `agy` не было
**Дата извлечения паттернов:** 2026-10-02
