# Universal Architecture Blueprint — Antigravity Studio & Assistant Core

**Статус:** проект архитектурного решения (Daedalus mandate, ЭТАП 4).
**Дата:** 2026-10-01.
**Область действия:** `/opt/chat-app` + `/opt/assistant-core`.

**Методологическая оговорка.** Разделы 1–2 опираются на построчный аудит кода (выполнен двумя подагентами, ключевые находки — `SQLITE_DB_PATH`, `PROJECTS_REGISTRY`, отсутствие auth на `DELETE`, HITL-паттерн в `bot_handler.py` — лично перепроверены чтением исходников). Раздел 7 (сопоставление с индустриальными паттернами) опирается на материалы, которые я лично проверил прямыми запросами (`WebFetch`) к первоисточникам 2026-10-01, **после того как** автоматический adversarial-verification конвейер упал из-за rate-limit провайдера, а затем инструмент `Workflow` был отключён для сессии целиком. Это не multi-vote verified отчёт — это точечная ручная проверка, но все источники — официальная документация или рецензируемые публикации (arXiv/ICLR), не блоги, кроме специально отмеченных.

---

## 1. Целевая архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STUDIO UI (chat-app)                        │
│  Manager View (обзор всех workspace/персон)  │  Editor View (1)     │
│  Security Tile · Task Dashboard · Git Registry · Artifacts Panel    │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ REST/WebSocket (аутентифицировано)
┌───────────────────────────────▼───────────────────────────────────┐
│                       CORE PLATFORM (домен)                        │
│  Entities: ScheduleEvent · WorkRecord · AcademicSubmission ·       │
│            Task · EmailMessage · Workspace · Persona               │
│  Ports:    BaseConnector · BaseScheduleProvider ·                  │
│            BaseTimesheetProvider · BaseLMSProvider ·               │
│            ConfirmationStore (HITL) · EventBus                     │
│  Use-cases (бывшие brain/*): IntentRouter · SecretaryDialog ·      │
│            Methodist — зависят ТОЛЬКО от портов выше               │
└───────┬───────────────────────────────────────────────┬───────────┘
        │ Domain Events (ScheduleChanged, TimesheetSynced,           │
        │ TaskCreated, SecurityViolationDetected,                    │
        │ DialogMemoryCleared, DelegatedToSpecialist)                │
┌───────▼─────────────┐   ┌──────────────────┐   ┌──────────────────▼──┐
│ PERSONA PLUGIN:      │   │ PERSONA PLUGIN:  │   │ PERSONA PLUGIN:      │
│ "popov-da-default"   │   │ (второй, любой)  │   │ security-governance  │
│ (Default Academic/   │   │ синтетическая    │   │ (Workspace registry, │
│  Industrial Plugin)  │   │ тест-персона     │   │  NDA air-gap)        │
│ guap_lms · aadhk ·   │   │ ...              │   │ chat-app Security    │
│ google_calendar ·    │   │                  │   │ Tile (сегодня —      │
│ notion · gdrive      │   │                  │   │  PROJECTS_REGISTRY)  │
└──────────────────────┘   └──────────────────┘   └──────────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────────────┐
│  STORAGE: persona-owned SQLite (chat.db, assistant.db) + checkpoint  │
│  store, keyed по persona_id/thread_id — никакой cross-repo absolute  │
│  path (см. Риск №1, Фаза 3)                                          │
└────────────────────────────────────────────────────────────────────┘
```

Три слоя разделены по правилу зависимостей Clean Architecture: Core Platform не импортирует ничего из Persona Plugins или Studio UI; Persona Plugins реализуют порты Core, но не знают друг о друге; Studio UI обращается к Core только через REST/WebSocket, никогда — к внутренним модулям assistant-core напрямую (сегодня нарушается через общий файл БД).

---

## 2. Спецификация портов (Ports)

### 2.1 Домен

```python
# core/domain/entities.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class WorkspaceClearance(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED_NDA = "restricted_nda"

@dataclass(frozen=True)
class ScheduleEvent:
    external_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    location: str | None = None

@dataclass(frozen=True)
class WorkRecord:
    shift_date: datetime
    hours: float
    project_tag: str          # было: хардкод "Тидекс"

@dataclass(frozen=True)
class AcademicSubmission:
    submission_id: str
    title: str
    deadline: datetime
    is_public: bool

@dataclass(frozen=True)
class Task:
    title: str
    area: str                 # свободная строка — уже так в БД сегодня, сохраняем
    status: str
```

### 2.2 Коннекторы (BaseConnector и наследники)

```python
# core/ports/connectors.py
from typing import Protocol, runtime_checkable
from datetime import datetime

@runtime_checkable
class BaseConnector(Protocol):
    connector_id: str
    required_scopes: tuple[str, ...]   # Zero-Trust: явно декларируемые привилегии

    async def health_check(self) -> bool: ...

class BaseScheduleProvider(BaseConnector, Protocol):
    async def fetch_events(self, since: datetime) -> list[ScheduleEvent]: ...
    async def diff_against(self, known: list[ScheduleEvent]) -> "ScheduleDiff": ...

class BaseTimesheetProvider(BaseConnector, Protocol):
    async def fetch_shifts(self, start: datetime, end: datetime) -> list[WorkRecord]: ...
    async def monthly_pacing(self, start: datetime, end: datetime,
                              norm_hours_per_day: float) -> "PacingReport": ...

class BaseLMSProvider(BaseConnector, Protocol):
    async def list_tasks(self) -> list[AcademicSubmission]: ...
    async def submit_grade(self, submission_id: str, grade: "Grade") -> None: ...
    # submit_grade и delete_task ОБЯЗАНЫ быть обёрнуты @requires_confirmation (см. 2.3)
```

**Как это ложится на существующий код** (из аудита): `src/calendar/client.py` ближе всего к `BaseScheduleProvider` уже сегодня — коэффициент переделки низкий, персона-специфика сосредоточена в двух маленьких таблицах форматирования (`SUBJECT_SHORT_NAMES`, `slot_map`), которые просто переезжают в `persona.yaml`. `src/connectors/aadhk/parser.py` → `BaseTimesheetProvider` требует умеренной переделки: сама логика парсинга уже схема-агностична (динамическая интроспекция таблиц), хардкод только в параметрах по умолчанию (`default_project="Тидекс"`, `daily_norm=8.5`). `src/connectors/guap_lms/client.py` → `BaseLMSProvider` требует самой глубокой переделки: это скрейпер одного конкретного сайта, а не клиент протокола — текущий класс становится первой конкретной реализацией интерфейса, а не самим интерфейсом.

### 2.3 HITL-примитив (вдохновлён LangGraph `interrupt()`/`Command(resume=...)`)

```python
# core/ports/hitl.py
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

@dataclass
class PendingConfirmation:
    action_id: str
    persona_id: str
    summary: str               # человекочитаемое описание — это уйдёт и в Telegram, и в Web UI
    payload: dict
    created_at: datetime

class ConfirmationStore(Protocol):
    async def create(self, action: PendingConfirmation) -> None: ...
    async def resolve(self, action_id: str, approved: bool) -> PendingConfirmation: ...

def requires_confirmation(summary_fn):
    """Декоратор для деструктивных методов портов (submit_grade, delete_task,
    clear_dialog_history, DELETE /projects/{id}, ...).

    Первый вызов: сохраняет PendingConfirmation через ConfirmationStore и поднимает
    ConfirmationRequired(action_id) вместо выполнения — ровно то же место остановки,
    что у LangGraph interrupt().

    resume_action(action_id, approved=True) — единая точка, вызываемая и из Telegram
    callback (`dlg:confirm_clear` и т.п.), и из `POST /api/v1/confirmations/{id}` —
    повторно вызывает исходный метод с сохранённым payload. Та же роль, что у
    Command(resume=...) в LangGraph, и то же свойство: thread_id у LangGraph —
    это action_id здесь."""
```

Это единственный механизм, закрывающий Риск №3 из аудита (HITL есть в Telegram, но отсутствует в Web Studio): сегодня `DELETE /api/v1/projects/{id}` не имеет вообще никакой серверной защиты (проверено лично чтением `projects.py:38-43`); после рефакторинга он оборачивается тем же декоратором, что `handle_cmd_clear_dialog` в `bot_handler.py` — один примитив, два интерфейса вызова.

### 2.4 Событийная шина

```python
# core/events/bus.py
from typing import Protocol, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass(frozen=True)
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class ScheduleChanged(DomainEvent): ...
@dataclass(frozen=True)
class TimesheetSynced(DomainEvent): ...
@dataclass(frozen=True)
class TaskCreated(DomainEvent): ...
@dataclass(frozen=True)
class SecurityViolationDetected(DomainEvent): ...
@dataclass(frozen=True)
class DialogMemoryCleared(DomainEvent): ...

@dataclass(frozen=True)
class DelegatedToSpecialist(DomainEvent):    # вдохновлено OpenHands AgentDelegateAction
    from_agent: str = ""
    to_agent: str = ""
    reason: str = ""

class EventBus(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None: ...
```

На старте — внутрипроцессная `asyncio`-реализация; задел на внешний брокер при реальном разделении chat-app/assistant-core на отдельные процессы (Фаза 3).

---

## 3. `persona.yaml` + схема SQLite

### 3.1 `config/persona.yaml` — дефолтный плагин (100% эквивалент сегодняшнего поведения)

```yaml
persona:
  id: "popov-da-default"
  display_name: "Дмитрий Александрович Попов"
  honorific: "доцент"
  timezone: "Europe/Moscow"

  telegram:
    authorized_user_ids: ["${TELEGRAM_USER_ID}"]

  # Пути — данные, обязательной раскладки каталогов нет (решение W6).
  # Все 4 записи = текущий PROJECTS_REGISTRY 1:1 (решение W2).
  # git: аккаунт/хост/SSH-профиль — необязательные данные (решение W1).
  workspaces:
    - id: "chat-app"
      label: "Antigravity Web Studio (chat-app)"
      clearance: public
      path: "/opt/chat-app"
      color: "blue"
      git: { host: "github.com", account: "DimaMuhannad", ssh_alias: null }
      notion_project: null
    - id: "assistant-core"
      label: "Assistant Core Daemon"
      clearance: public
      path: "/opt/assistant-core"
      color: "green"
      git: { host: "github.com", account: "DimaMuhannad", ssh_alias: null }
      notion_project: null
    - id: "guap-physics"
      label: "Кафедра физики ГУАП"
      clearance: internal
      path: "/opt/personal/guap-physics"
      color: "yellow"
      forbidden_remote_substrings: []
      forbidden_keywords: []
    - id: "tydex-optics"
      label: "ООО «Тидекс» — Оптические приборы"
      clearance: restricted_nda
      path: "/opt/work-tydex"
      color: "red"
      forbidden_remote_substrings: ["github.com/DimaMuhannad"]
      forbidden_keywords: ["tydex_internal_secret", "golay_calibration_key", "thz_proprietary_firmware"]

  # Роли разделены, на роль допускается несколько привязок (решение W8).
  connectors:
    schedule_source:
      - provider: "guap_rasp_parser"      # ScheduleParser, сайт расписания вуза
        scopes: ["schedule.read"]
        config: { base_url: "https://rasp.guap.ru/" }
    calendar_sync:
      - provider: "google_calendar"       # приёмник, не источник
        scopes: ["calendar.write"]
    timesheet:
      - provider: "aadhk"
        scopes: ["timesheet.read", "timesheet.write"]
        config: { daily_norm_hours: 8.5, default_project: "Тидекс" }
    lms:
      - provider: "guap_lms"              # GuapLmsClient, личный кабинет
        scopes: ["lms.read", "lms.grade"]
        config: { base_url: "https://pro.guap.ru" }
    git_source:                           # решение W1: прогресс проектов по коммитам, по SSH
      - provider: "ssh_git"
        scopes: ["git.read"]
    notion:                               # решение W7: дашборды проектов — функция платформы
      - provider: "notion"
        scopes: ["notion.read", "notion.write"]
        config: { projects: [] }          # список проектов задаётся в персоне

  prompts:
    secretary_system_prompt: "prompts/secretary_default.jinja2"
    intent_router_prompt: "prompts/intent_router_default.jinja2"
    methodist_prompt: "prompts/methodist_default.jinja2"
```

`scopes` в каждом блоке `connectors.*` — прямая реализация Zero-Trust least-privilege: ядро отказывается поднимать `GuapLmsClient` для процесса, которому персона не декларировала `lms.*`-scope (сегодня, например, chat-app процесс не имеет причин держать credentials GUAP LMS вообще — после рефакторинга это становится проверяемым фактом, а не просьбой "ну он же физически не импортирует это").

### 3.2 SQLite-схема (новые таблицы, дополняющие, не заменяющие существующие `projects`/`tasks`)

```sql
CREATE TABLE personas (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  config_json TEXT NOT NULL,     -- валидированный снапшот persona.yaml
  created_at TEXT NOT NULL
);

CREATE TABLE workspaces (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL REFERENCES personas(id),
  label TEXT NOT NULL,
  path TEXT NOT NULL,
  clearance TEXT NOT NULL CHECK (clearance IN ('public','internal','restricted_nda')),
  forbidden_remote_substrings TEXT,   -- JSON array
  forbidden_keywords TEXT,            -- JSON array
  color TEXT
);
-- заменяет PROJECTS_REGISTRY (security.py:31-68); Web UI таблица рендерится без изменений,
-- т.к. /security/overview уже отдаёт project-agnostic JSON (проверено).

CREATE TABLE connector_bindings (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL REFERENCES personas(id),
  role TEXT NOT NULL,             -- 'schedule_source' | 'calendar_sync' | 'timesheet' | 'lms' | 'git_source' | 'notion'
                                  -- несколько строк на одну роль допустимы (решение W8)
  provider TEXT NOT NULL,
  scopes TEXT NOT NULL,           -- JSON array
  config_json TEXT NOT NULL
);

CREATE TABLE pending_confirmations (   -- backing store для requires_confirmation (2.3)
  action_id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL REFERENCES personas(id),
  summary TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  approved INTEGER
);
```

---

## 4. Roadmap миграции

| Фаза | Содержание | Риск | Definition of Done |
|---|---|---|---|
| **0. Страховочная сеть** (1–2 нед.) | `import-linter`-контракт (domain не импортирует adapters); зафиксировать текущий pytest как baseline; каркас "второй синтетической персоны" (пока с заглушками) | Низкий | CI зелёный; baseline задокументирован |
| **1. Извлечение портов без изменения поведения** (2–3 нед.) | `core/ports/*`; существующие классы (`GuapLmsClient`, `AadhkIngestionService`, `GoogleCalendarClient`) делаются совместимыми с протоколами; inline-импорты в `secretary_dialog.py`/`bot_handler.py` → конструкторная инъекция (по образцу уже существующего `MethodistService`) | Средний — возможны несовместимые сигнатуры, нужны adapter-wrapper'ы | 100% текущих тестов проходят без изменения фикстур; `Protocol`-проверка подтверждает соответствие |
| **2. `persona.yaml` + SQLite-схема персон** (2 нед.) | Пререквизит: снимок текста всех системных промптов (решение W10). Таблицы из §3.2; `PROJECTS_REGISTRY` (все 4 записи) и хардкод-дефолты `'ГУАП'`/`'Тидекс'` → данные; NDA-правила → данные workspace (решение W3); промпты → Jinja2-шаблоны | Средний-высокий — промпты напрямую влияют на поведение LLM; закрывается снимком промптов | `PROJECTS_REGISTRY` удалён как код; снимок-тест: шаблон с персоной по умолчанию даёт промпт, идентичный сохранённому символ в символ; тест эквивалентности NDA-проверок; новый `test_persona_config.py` подтверждает, что вторая синтетическая персона даёт отличные от дефолтной промпты/scope-решения; 100% pytest |
| **3. Владелец схемы БД + общая security-библиотека** (2–3 нед.) | Решение W9: одна общая SQLite-база, но схема и миграции — в общей библиотеке; путь к базе — из настроек (убрать хардкод `SQLITE_DB_PATH`); режим WAL; межпроцессная шина не нужна. Решение W5: `SECRET_PATTERNS`/`FORBIDDEN_FILES`/`run_cmd()` + NDA-правила → одна библиотека, `security_shield.py` — тонкая обёртка; установка как pre-commit hook | Средний (был «самый высокий»: отказ от разделения БД и двойной записи снял основной риск) | `pytest backend/tests` проходит против свежей пустой временной БД без доступа к `/opt/assistant-core`; одна security-реализация, импортируемая из обоих мест |
| **4. Zero-Trust HITL унификация** (2 нед.) | `@requires_confirmation` + `pending_confirmations`; Telegram-flow переводится на примитив без изменения UX; тот же примитив добавляется на `DELETE /api/v1/projects/{id}`, `documents/{id}` в chat-app | Средний — важно сохранить Telegram UX 1:1 | `test_hitl_safety_guardrails.py`/`test_bot_group_isolation.py` без изменения ассертов; новый `test_web_hitl_guardrails.py`: прямой HTTP DELETE без токена → 409, не 200 |
| **5. Готовность к мультитенантности** (2–3 нед.) | Убрать мутацию глобального `config.GEMINI_API_KEY` в `key_rotator.py`; `WorkspaceScope`-enum для NDA air-gap внутри assistant-core (не только в chat-app, см. Риск №4 аудита) | Средний — тонкие concurrency-баги при удалении глобального стейта | Интеграционный тест инстанцирует 2 персоны одновременно, подтверждает отсутствие cross-talk; 100% прочих тестов |

**Сквозные требования по CLAUDE.md (не отдельная фаза, а гейт на каждой из них):** 100% pytest на каждом шаге, не только в конце; каждая фаза коммитится атомарно с возможностью revert; начиная с Фазы 2 — "вторая синтетическая персона" тест обязателен, это единственное доказательство, что универсализация реальна, а не только "тесты все еще зелёные" (Риск №7 исходного аудита).

---

## 5. Гарантии обратной совместимости

- Весь профиль Попова Д.А. (ГУАП + Тидекс, адреса, норма часов 8.5, каталог методических файлов, промпты) переносится **1:1** в `config/persona.yaml` как `popov-da-default` — Default Academic/Industrial Plugin. Ни один бит поведения не теряется: меняется только место хранения (код → данные).
- Это и есть персона, загружаемая по умолчанию при отсутствии `PERSONA_CONFIG_PATH` — поведение в проде не меняется ни на одном шаге плана до явного переключения на другую персону.
- Все существующие тестовые файлы (20 в assistant-core + 4 в chat-app с персона-зависимым контентом) должны проходить на каждом шаге. Там, где тест сегодня проверяет хардкод напрямую (например `test_search_local_files_catalog`, `test_fast_intent_router.py`), тест **переписывается** на проверку того же поведения через загруженную дефолтную персону — не удаляется и не ослабляется.
- Тесты, уже инвентаризированные аудитом как чистые safety/correctness-контракты (`test_hitl_safety_guardrails.py`, `test_bot_group_isolation.py`, `test_phase1.py`, `test_phase2_filter.py`, `test_key_rotator.py`, `test_voice.py`, parsing-тесты AADHk) — не трогаются вообще, кроме как фикстурами персоны.

---

## 6. Карта соответствия индустриальным паттернам

Проверено лично (`WebFetch`) 2026-10-01, после сбоя автоматической верификации.

| Наш компонент | Паттерн-источник | Источник (проверено лично) |
|---|---|---|
| `@requires_confirmation` + `pending_confirmations` | LangGraph `interrupt()` / `Command(resume=...)`, state, keyed по `thread_id` через `BaseCheckpointSaver`/`SqliteSaver` | docs.langchain.com/oss/python/langgraph/interrupts, .../checkpointers |
| `connector_bindings.scopes` (least privilege по персоне) | Semantic Kernel: функции/плагины регистрируются в собственном клонированном `Kernel` каждого агента, а не в глобальном реестре | learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-functions |
| «зарегистрировать, но не авто-вызывать» для опасных методов | SK `FunctionChoiceBehavior.Auto(auto_invoke=False)` | learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-functions |
| Событие `DelegatedToSpecialist` | OpenHands `AgentDelegateAction` — generalist-агент передаёт подзадачу специализированному | arXiv:2407.16741; ICLR 2025 proceedings |
| `BaseConnector.required_scopes` / декларативная активация | OpenHands SDK `SKILL.md` + `KeywordTrigger`/`PathTrigger` как модель декларативной, не глобальной регистрации | docs.openhands.dev/sdk/guides/skill |
| Manager View / Editor View в Studio UI | Google Antigravity: отдельные Editor View и Manager ("mission control") View + типизированные Artifacts (Task Lists, Implementation Plans, Walkthroughs) | обзоры запуска Google Antigravity (kdnuggets.com, blog.promptlayer.com) |
| Diff-viewer для изменений, предложенных агентом | Windsurf Cascade: accept/revert по отдельным файлам после выполнения | обзор архитектуры Windsurf Cascade (lowcode.agency) |
| Формализация фоновых sync-циклов (`run_sentinel_cycle` и т.п.) | Cursor subagents: явный `is_background` (returns immediately) vs foreground (blocks until done) | cursor.com/docs/subagents |
| **Не взято**: CrewAI callback-система как основа HITL | Документация CrewAI прямо подтверждает: `before/after_kickoff_callbacks`, `task_callback`, `step_callback` — это monitoring/logging-хуки, **не** approval-gate для деструктивных действий. Иерархическая делегация CrewAI (`manager_llm`) взята только как референс многоагентной модели, не для HITL | docs.crewai.com/en/concepts/crews, .../hierarchical-process |

---

## 7. Решения пользователя и оставшиеся вопросы

Решено 2026-10-01 (подробно: `.planning/intel/user-resolutions.md`):
1. **Фаза 3 (БД)** — одна общая база с явным владельцем схемы, миграциями, путём из настроек и WAL (не две БД и не read-only реплика).
2. **Фаза 2 (промпты)** — снимок промптов с побайтовым сравнением; golden-набор ответов LLM не нужен.
3. **Git-источники** — любое число репозиториев в разных git-сервисах, подключение по SSH; секретарь по коммитам оценивает прогресс проектов и обновляет дашборды Notion. Требует нового порта `git_source` и коннектора `notion`.
4. **Роли расписания** — `schedule_source` (парсер сайта вуза), `calendar_sync` (Google Calendar как приёмник), `lms` — раздельно, несколько привязок на роль.
5. **Workspace по умолчанию** — все 4 текущих проекта; пути — данные.

Остаётся открытым:
- Автоматическая адверсариальная верификация (`Workflow`) недоступна в этой сессии — раздел 6 выше прошёл только ручную точечную проверку. Если нужна полная multi-vote верификация перед тем, как эта карта соответствий станет основанием для технических решений, стоит перезапустить её в сессии, где `Workflow` снова доступен.
