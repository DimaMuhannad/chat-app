# Фаза 3: Персона как данные - карта паттернов

**Составлено:** 2026-10-02
**Файлов проанализировано:** 38 (новых и изменяемых, два репозитория)
**Аналоги найдены:** 32 / 38 (6 без прямого аналога)

Префиксы: `AC:` = `/opt/assistant-core`, `CA:` = `/opt/chat-app`. Все аналоги проверены как отслеживаемые git файлы (`git ls-files`), зеркал `.gsd/capabilities` нет. NDA-каталоги (`/opt/work-tydex`, `/opt/personal/guap-physics`) не читались.

## Классификация файлов

| Файл (новый/изменяемый) | Роль | Поток данных | Ближайший аналог | Качество |
|---|---|---|---|---|
| `AC:src/persona/models.py` | model (Pydantic v2) | transform | `AC:src/core/domain/entities.py` + `CA:backend/app/core/config.py` | role-match |
| `AC:src/persona/loader.py` | service/utility | file-I/O | нет (подстановка `${ENV}`: набросок RESEARCH) | нет |
| `AC:src/persona/current.py` | utility (ContextVar) | request-response | нет | нет |
| `AC:src/persona/prompts.py` | utility | transform | нет (Jinja2 набросок в RESEARCH) | нет |
| `AC:src/persona/seed.py` | CLI/service | batch + CRUD | `CA:scripts/gate.py` (`make_db_copy`, `run_cmd`) | partial |
| `AC:config/persona.yaml`, `AC:config/prompts/*.jinja2` | config/data | file-I/O | константы промптов `AC:src/brain/*.py` | data-source |
| `AC:src/storage/db.py` (+3 DDL, upsert/get persona) | storage | CRUD | сам файл: `Database.init_db()` | exact |
| `AC:src/core/domain/entities.py` (+2 роли) | model | transform | сам файл (`ConnectorRole`, `Persona`, `Workspace`) | exact |
| `AC:src/composition.py` (фабрики с binding-конфигом) | composition root | request-response | сам файл | exact |
| `AC:src/brain/{secretary_dialog,intent_router,methodist,reply_generator,debrief_parser,summarizer}.py` | service | request-response (LLM) | `AC:src/brain/secretary_dialog.py:37,698` | exact |
| `AC:src/models/schedule.py`, `AC:src/calendar/client.py` | model/adapter | transform | `AC:src/models/schedule.py:76-99` | exact |
| `AC:src/main.py`, `AC:src/notifier/{bot_handler,live_ticker}.py`, `AC:src/connectors/aadhk/parser.py` | wiring | request-response | `AC:src/main.py:296` | exact |
| `AC:.importlinter` | config | - | сам файл (`core-is-pure`) | exact |
| `AC:requirements.txt`, `AC:docs/BASELINE.md` (в CA) | config/docs | - | запись import-linter Фазы 1 | role-match |
| `AC:tests/fixtures/prompts_snapshot/*` + `MANIFEST.json` | test data | file-I/O | нет (в `tests/data/` нельзя: игнор) | нет |
| `AC:tests/test_prompt_snapshot.py` | test | transform | `AC:tests/test_composition_di.py` (характеризация + fake клиент) | role-match |
| `AC:tests/test_persona_loader.py`, `test_persona_storage.py` | test | CRUD | `AC:tests/test_composition_di.py` (`in_memory_db`) | role-match |
| `AC:tests/test_persona_config.py` | test | transform | `AC:tests/test_synthetic_persona.py` | role-match |
| `AC:tests/test_connector_params.py` | test | request-response | `AC:tests/test_composition_di.py:235-255` | exact |
| `AC:tests/test_nda_script_parity.py` | test | file-I/O | `CA:backend/tests/test_gate.py` | partial |
| `AC:tests/test_hardcode_scanner.py`, `AC:tests/hardcode_baseline.py` | test + data | batch | `CA:scripts/gate.py:354-368` (`compare_shield_findings`) | role-match |
| `AC:tests/synthetic_persona.py` и `CA:backend/tests/synthetic_persona.py` (+конвертер) | test fixture | transform | сами файлы (две копии, SHA-256) | exact |
| `AC:tests/test_core_architecture.py` | test | - | сам файл (полнота `core-is-pure`) | exact |
| `CA:backend/app/api/v1/persona.py` | route | request-response | `CA:backend/app/api/v1/security.py` + `router.py` | exact |
| `CA:backend/app/api/v1/router.py` | route | - | сам файл | exact |
| `CA:backend/app/api/v1/security.py` (реестр из БД) | route | request-response | сам файл | exact |
| `CA:backend/app/db.py` (`get_persona`, `list_workspaces`, `resolve_default_area`) | service | CRUD | `CA:backend/app/db.py` (`DatabaseService`) | exact |
| `CA:backend/app/models/dashboard_schemas.py` | model | request-response | сам файл (убрать `"ГУАП"`) | exact |
| `CA:backend/app/core/config.py` (+`PERSONA_ID`) | config | - | сам файл | exact |
| `CA:backend/app/static/index.html` | component (UI) | request-response | сам файл | exact |
| `CA:backend/tests/conftest.py` (+фикстура копии БД, `persona_db`) | test fixture | file-I/O | `CA:scripts/gate.py:97-113` `make_db_copy` | exact |
| `CA:backend/tests/test_persona_api.py`, `test_index_whitelabel.py` | test | request-response | `CA:backend/tests/test_security_api.py` | exact |
| `CA:backend/tests/test_nda_equivalence.py` | test | file-I/O (git) | `CA:backend/tests/test_security_api.py` + RESEARCH `make_repo` | partial |
| `CA:backend/tests/test_hardcode_scanner.py` | test | batch | `AC:tests/test_hardcode_scanner.py` | exact (пара) |
| `CA:backend/tests/test_security_api.py`, `test_dashboard_api.py` | test | request-response | сами файлы (переписать на персону, BCK-02) | exact |
| `CA:scripts/gate.py` (опц. шаг seed на копии, `persona_drift_check`) | script | batch | сам файл | exact |

## Назначение паттернов

### `AC:src/storage/db.py` - три таблицы персоны (storage, CRUD)

**Аналог:** этот же файл. `init_db()` объявлен в строке 45, внутри `executescript` стоят `CREATE TABLE IF NOT EXISTS` (например `projects`, строка 145), после коммита вызывается `_seed_initial_data_if_empty` (строка 411). `Database.__init__(db_path)` принимает путь аргументом; файл не импортирует `src.config`.

**Паттерн соединения** (строки 12-30, 45-52):
```python
class Database:
    def __init__(self, db_path: str = "./data/assistant.db"):
        self.db_path = db_path
    ...
    async def init_db(self) -> None:
        async with self.connection() as conn:
            await conn.executescript("""CREATE TABLE IF NOT EXISTS monitored_sources (...); ...""")
            await conn.commit()
            await self._seed_initial_data_if_empty(conn)
```
Копировать: добавить DDL `personas/workspaces/connector_bindings` (из RESEARCH) в тот же `executescript` ДО `_seed_initial_data_if_empty`; методы `upsert_persona`/`get_persona` писать через `async with self.connection() as conn`, одна транзакция DELETE+INSERT; `PRAGMA foreign_keys = ON` уже включён в `connection()` (строки 32, 37).

### `AC:src/core/domain/entities.py` - расширение enum и сущностей (model)

**Аналог:** этот же файл, строки 12-27 и 80-97.
```python
class ConnectorRole(StrEnum):
    SCHEDULE_SOURCE = "schedule_source"
    CALENDAR_SYNC = "calendar_sync"
    TIMESHEET = "timesheet"
    LMS = "lms"
class WorkspaceClearance(StrEnum):
    PUBLIC = "public"; INTERNAL = "internal"; RESTRICTED_NDA = "restricted_nda"
@dataclass(frozen=True, slots=True)
class Workspace:
    id: str; name: str; clearance: WorkspaceClearance; path: str; remote: str | None = None
```
Добавить `GIT_SOURCE = "git_source"`, `NOTION = "notion"` (только объявление). Pydantic-модели `src/persona/models.py` держать вне `src/core` (ядро чистое), `Literal` допуска должен совпадать со значениями `WorkspaceClearance`. Стиль настроек: `CA:backend/app/core/config.py` (`BaseSettings`, `SettingsConfigDict`); для персоны брать `model_config = ConfigDict(extra="forbid")`.

### `AC:src/composition.py` - фабрики с конфигом привязки (composition root)

**Аналог:** этот же файл (42 строки). Ленивые импорты внутри функции, обязательно сохранить (патчи тестов Фазы 2 ломаются иначе):
```python
def default_timesheet_service(db: Any) -> BaseTimesheetProvider:
    from src.connectors.aadhk.parser import AadhkIngestionService
    from src.connectors.aadhk.provider import AadhkTimesheetProvider
    return AadhkTimesheetProvider(AadhkIngestionService(db))

def default_lms_client() -> LmsClientLike:
    from src.connectors.guap_lms.client import GuapLmsClient
    return GuapLmsClient()
```
Копировать: сигнатуру `default_*` сохранить, значения (`base_url`, `default_project`, `daily_norm_hours`) брать из `current_persona()` вызовом внутри функции, не при импорте.

### `AC:src/brain/*.py` и `AC:src/main.py` - перенос промптов и параметров (service)

**Аналог:** `secretary_dialog.py:37` (`SECRETARY_SYSTEM_PROMPT = """Ты - ... доцента Попова Дмитрия Александровича.`) и место вызова `:698`:
```python
cfg_kwargs: dict[str, Any] = {
    "system_instruction": SECRETARY_SYSTEM_PROMPT,
    "temperature": 0.3,
}
```
Заменить на `render_prompt(current_persona(), "secretary")` в точке вызова (не модульная константа: Pitfall 8). То же для `intent_router.py:247`, `methodist.py:479,614`, `reply_generator.py:103,143`, `debrief_parser.py:118`, `summarizer.py:199,407`. Ловушка проекта: шаблон `debrief` без завершающего `\n`; `SCOPE_CHECK_PROMPT` в Jinja использует одинарные `{`/`}` и `{{ question }}`.

**Параметры проекта учёта** (`AC:src/main.py:296`):
```python
timesheet_pacing = await aadhk_svc.get_monthly_pacing(project_name="Тидекс")
```
Оставить аргумент `project_name=`, значение из персоны (характеризационные тесты Фазы 2 проверяют `{"project_name": "Тидекс"}`, `AC:tests/test_composition_di.py:247`).

**Слоты/предметы** (`AC:src/models/schedule.py:76-99`): словари `GUAP_BELL_SCHEDULE`, `SUBJECT_SHORT_NAMES`; дубль в `AC:src/calendar/client.py:13-18`, импорт в `live_ticker.py:30`. Сделать функции чтения из персоны, имена оставить только пока на них есть импорты.

### `AC:.importlinter` и `AC:tests/test_core_architecture.py` - регистрация `src.persona`

**Аналог:** `test_core_is_pure_forbids_every_other_src_module` (строки 50-62):
```python
forbidden = set(_lines(_contract("core-is-pure")["forbidden_modules"]))
missing = children - forbidden
assert not missing, f"core-is-pure не запрещает: {sorted(missing)}"
```
Любой новый верхний модуль `src/persona` обязан попасть в `forbidden_modules` контракта `core-is-pure` в `.importlinter`, иначе тест красный.

### `AC:src/persona/seed.py` и фикстура копии БД в `CA:backend/tests/conftest.py`

**Аналог:** `CA:scripts/gate.py:97-113` (`make_db_copy`) и `run_cmd` (строки 116-130).
```python
def make_db_copy(live_db: Path, tmp_dir: Path) -> Path:
    dst = tmp_dir / "assistant-copy.db"
    src = sqlite3.connect(live_db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        out = sqlite3.connect(dst)
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()
    return dst
```
Копировать в сессионную фикстуру chat-app: backup из `mode=ro`, затем `subprocess.run([CORE/.venv/bin/python, "-m", "src.persona.seed", "--db", copy], cwd=CORE)`, затем подмена `settings.SQLITE_DB_PATH`. Существующий `conftest.py` (фикстура `synthetic_persona` с `copy.deepcopy`) расширяется, а не заменяется. seed-CLI обязан отказывать на боевом пути (повтор защиты `gate.chat_pytest_env`) и не импортировать `src.config`.

### `CA:backend/app/api/v1/security.py` - Security Tile из таблиц (route)

**Аналог:** этот же файл. Что сохранить: ключи ответа и порядок записей (строки 131-165).
```python
for p in PROJECTS_REGISTRY:
    p_path = Path(p["path"])
    is_tydex = p["clearance"] == "restricted_nda"
    res = audit_path(p_path, is_tydex=is_tydex)
    ...
    overview.append({"id": p["id"], "name": p["name"], "account": p["account"],
        "clearance": p["clearance"], "clearance_label": p["clearance_label"], "color": p["color"],
        "path": p["path"], "exists": res["exists"], "audit_status": res["status"],
        "violations_count": ..., "origin_url": ..., "author_email": ...})
```
Заменить источник `PROJECTS_REGISTRY` (строки 31-68) на `await DatabaseService.list_workspaces(persona_id)` (ORDER BY `position`), при пустом результате - 503 (fail-closed, не «0 проектов, чисто»). `SECRET_PATTERNS`, `FORBIDDEN_FILES`, `audit_path`, `run_cmd` не трогать. Перед заменой: отдельный коммит характеризации (эталон из 4 записей и N01-N09).

### `CA:backend/app/api/v1/persona.py` + `router.py` (route, request-response)

**Аналог:** `security.py` (стиль маршрута) и `router.py`:
```python
router = APIRouter(prefix="/security", tags=["Security Shield"])
...
from app.api.v1.security import router as security_router
api_router.include_router(security_router)
```
Копировать: `router = APIRouter(prefix="/persona", tags=["Persona"])`, `@router.get("/current")`, регистрация одной строкой в `router.py`. Ответ только по белому списку полей (RESEARCH, раздел API), 503 если строки нет.

### `CA:backend/app/db.py` - `get_persona`/`list_workspaces` (service, CRUD)

**Аналог:** этот же файл, строки 10-16 и 140-155:
```python
@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
class DatabaseService:
    @staticmethod
    async def get_dashboard_summary() -> dict[str, Any]:
        async with get_db() as conn:
            cursor = await conn.execute("SELECT ... ;")
            rows = [dict(r) for r in await cursor.fetchall()]
```
Копировать как `@staticmethod async def` методы класса `DatabaseService`. Дефолт области: строки 149 и 244 `data.get("area", "ГУАП")` заменить на `data.get("area") or await resolve_default_area()`; то же в `dashboard_schemas.py:8,33` (`area: str | None = None`).

### `CA:backend/tests/test_persona_api.py` и др. (test, request-response)

**Аналог:** `CA:backend/tests/test_security_api.py` строки 1-14:
```python
@pytest.mark.anyio
async def test_security_overview():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/security/overview")
        assert resp.status_code == 200
```
Копировать как есть (`pytest.mark.anyio`, `ASGITransport`). Тесты не слабить: `len(projects) == 4`, `clearance == "restricted_nda"` остаются.

### Сканер хардкода и baseline (test, batch)

**Аналог:** `CA:scripts/gate.py:354-368`:
```python
def compare_shield_findings(found: collections.Counter, allowed: dict[tuple[str, str], int]):
    new = [... for (path, kind), count in sorted(found.items()) if count > allowed.get((path, kind), 0)]
    stale = [... for (path, kind), count in sorted(allowed.items()) if found.get((path, kind), 0) < count]
    return new, stale
```
Использовать ту же двойную проверку (превышение И устаревшая запись) для `tests/hardcode_baseline.py`; токены брать из персоны по умолчанию; замена константы `OWNER_TOKEN_DENYLIST` в `test_synthetic_persona.py:15-24`.

### Синтетическая персона (test fixture)

**Аналог:** `AC:tests/synthetic_persona.py` и `CA:backend/tests/synthetic_persona.py` (байт-в-байт, шаг гейта «дрейф SHA-256»). Изменение (функция `synthetic_to_config`) вносить в ОБЕ копии одним коммитом. chat-app пишет конфиг JSON-ом (читается `yaml.safe_load` в seed-CLI), PyYAML в chat-app не нужен.

## Общие паттерны

### Ленивые импорты и корень композиции
**Источник:** `AC:src/composition.py` (весь файл). **Применять:** все фабрики с параметрами привязок, `main.py`.

### Читать персону при вызове, не при импорте
**Источник:** Pitfall 8 RESEARCH (`SUBJECT_SHORT_NAMES`, `GUAP_BELL_SCHEDULE`). **Применять:** `brain/*`, `models/schedule.py`, `composition.py`. Иначе вторая персона в тесте не подхватится.

### Характеризация до рефакторинга
**Источник:** Фаза 2, `AC:tests/test_composition_di.py` (фейк-коннектор, `method_calls(calls)`). **Применять:** снимок промптов (первый план), эталон `/security/overview` и NDA-чек-лист (ДО замены `PROJECTS_REGISTRY`) отдельными коммитами.

### Защита боевой БД
**Источник:** `CA:scripts/gate.py:97-113`. **Применять:** фикстура копии БД, seed-CLI, любой шаг гейта: только `mode=ro` + backup; SHA-256 боевой БД не меняется.

### Fail-closed
**Источник:** `AC:src/notifier/bot_handler.py:100-103` (`_is_authorized` возвращает True при `None`: анти-пример, не менять в Фазе 3). **Применять:** `loader.py` не превращает незаданный `${TELEGRAM_USER_ID}` в `""`; Security Tile при пустой персоне отдаёт 503.

### Ограничения размещения файлов
- Эталоны промптов только в `tests/fixtures/prompts_snapshot/` (`.gitignore:20: data/` скрывает `tests/data/`); файлы бинарно, без лишнего `\n` у debrief.
- Новый `src/persona` внести в `core-is-pure`; новые отслеживаемые файлы не должны содержать строк, похожих на `SECRET_PATTERNS` (Web-аудит сканирует первые 100 файлов).
- NDA-слова в `config/persona.yaml`: единственное разрешённое исключение shield (решение OQ1, число находок 15 -> 18).

## Аналог не найден

| Файл | Роль | Поток | Причина |
|---|---|---|---|
| `AC:src/persona/loader.py` | utility | file-I/O | В коде нет загрузчика YAML и подстановки `${ENV}`; взять набросок `resolve_env` из RESEARCH |
| `AC:src/persona/current.py` | utility | request-response | Нет ContextVar-реестра; взять Pattern 3 из RESEARCH |
| `AC:src/persona/prompts.py` | utility | transform | Jinja2 не используется; взять `make_env` из RESEARCH (`SandboxedEnvironment`, `StrictUndefined`, `keep_trailing_newline=True`) |
| `AC:tests/fixtures/prompts_snapshot/*` | test data | file-I/O | Каталога фикстур в git нет (`git ls-files tests/fixtures` пусто) |
| `CA:backend/tests/test_nda_equivalence.py` | test | file-I/O | Тестов на временных git-репозиториях нет; использовать `make_repo` из RESEARCH |
| `CA:backend/tests/test_index_whitelabel.py` | test | static | Статических проверок `index.html` нет; читать файл и искать токены профиля из персоны |

## Метаданные

**Область поиска:** `AC:src/{core,storage,brain,models,notifier}`, `AC:src/composition.py`, `AC:tests`, `AC:.importlinter`, `CA:backend/app/{api/v1,core,db.py}`, `CA:backend/tests`, `CA:scripts/gate.py`.
**Просмотрено файлов:** около 20 (точечные фрагменты, большие файлы через grep + диапазоны).
**Дата извлечения:** 2026-10-02
