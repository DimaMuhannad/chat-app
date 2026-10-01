---
last_mapped_commit: ee863eccdcc4889896a20f28c0c29a4e0ebe17b7
last_mapped_at: 2026-10-01
---
# Структура кодовой базы

**Analysis Date:** 2026-10-01

## Расположение директорий

```
/opt/chat-app/
├── backend/                        # FastAPI приложение
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app factory (create_app), global app instance
│   │   ├── db.py                   # DatabaseService с 40+ методами CRUD
│   │   ├── core/
│   │   │   └── config.py           # Settings singleton (BASE_URL, DB_PATH, CORS_ORIGINS)
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py       # API v1 router composition
│   │   │       ├── projects.py     # Projects endpoints (GET, POST, PUT, DELETE)
│   │   │       ├── tasks.py        # Tasks endpoints (GET, POST, PUT, PATCH, DELETE)
│   │   │       ├── reminders.py    # Reminders endpoints (GET, POST, PUT, PATCH, DELETE)
│   │   │       ├── documents.py    # Documents endpoints (GET, POST, PUT, DELETE)
│   │   │       ├── dashboard.py    # Dashboard summary aggregation
│   │   │       ├── security.py     # Security Shield, project audit, secret scanning
│   │   │       └── health.py       # Health check endpoint
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard_schemas.py # Pydantic schemas (ProjectCreate, TaskUpdate, etc.)
│   │   │   ├── agent.py            # Agent models (AgentConfig, AgentTask, Artifact)
│   │   │   └── chat.py             # Chat models (ChatMessage, ChatSession, streams)
│   │   ├── static/
│   │   │   └── index.html          # Single-page app (Tailwind + Lucide + Marked.js)
│   │   └── __pycache__/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_dashboard_api.py   # Tests for dashboard, projects, tasks, reminders, docs
│   │   ├── test_security_api.py    # Tests for security audit endpoints
│   │   ├── test_health.py          # Tests for health check
│   │   ├── test_models.py          # Tests for Pydantic model validation
│   │   └── __pycache__/
│   ├── requirements.txt            # Python dependencies (fastapi, uvicorn, pydantic, pytest, etc.)
│   └── .venv/                      # Python virtual environment (excluded from git)
├── docs/
│   ├── UNIVERSAL_ARCHITECTURE_BLUEPRINT.md  # Target architecture after 5 phases
│   └── [other documentation]
├── .planning/
│   └── codebase/
│       ├── ARCHITECTURE.md         # Current system architecture (you are here)
│       ├── STRUCTURE.md            # Directory layout and conventions (this file)
│       └── [future docs: CONVENTIONS.md, TESTING.md, STACK.md, etc.]
├── .claude/
│   ├── worktrees/
│   └── [CLI configuration]
├── .agents/
├── .git/
├── .pytest_cache/                  # (excluded from mapping)
├── logs/                           # (excluded from mapping)
├── uploads/                        # (excluded from mapping)
├── scratch/                        # (excluded from mapping)
├── scripts/
├── CLAUDE.md                       # Project guidelines (Python 3.12, FastAPI, SQLite, systemd)
├── README.md                       # Basic project description
└── [other root files]
```

## Назначение директорий

**`backend/app/`:**
- Purpose: Основное FastAPI приложение
- Contains: Конфигурация, API роутеры, data access layer, Pydantic модели, статический frontend
- Key files: main.py (entry), db.py (data), router.py (routes composition)

**`backend/app/api/v1/`:**
- Purpose: REST API v1 endpoints
- Contains: Функции-обработчики для Projects, Tasks, Reminders, Documents, Security, Dashboard, Health
- Naming: `{resource}.py` — один роутер на каждый основной entity
- Key files: router.py (главная композиция), projects.py, tasks.py, reminders.py, documents.py

**`backend/app/core/`:**
- Purpose: Приложение-wide конфигурация
- Contains: Settings singleton, constants, environment variables
- Key files: config.py (Settings class с DB_PATH, HOST, PORT, CORS_ORIGINS)

**`backend/app/models/`:**
- Purpose: Pydantic schemas и domain entities (в переходном состоянии)
- Contains: Input/output schemas (ProjectCreate, TaskUpdate), domain models (AgentConfig, ChatMessage)
- Key files: dashboard_schemas.py (основные CRUD schemas), agent.py (agent models), chat.py (chat/streaming models)

**`backend/app/static/`:**
- Purpose: Статический frontend (SPA)
- Contains: index.html с встроенными CSS (Tailwind CDN) и JavaScript
- Generated: Нет (рукописный HTML)
- Committed: Да

**`backend/tests/`:**
- Purpose: Unit и integration тесты
- Contains: pytest файлы с tests_ префиксом
- Key files: test_dashboard_api.py (основные CRUD тесты), test_security_api.py (security audit), test_health.py (health check)

**`.planning/codebase/`:**
- Purpose: Документация архитектуры и структуры для других Claude-команд
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md (future), TESTING.md (future)
- Generated: Нет (рукописная по /gsd-map-codebase)
- Committed: Да

**`docs/`:**
- Purpose: Планы и спецификации
- Contains: UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (целевое состояние)

## Расположение ключевых файлов

**Entry Points:**
- `backend/app/main.py:create_app()` — Фабрика FastAPI приложения (вызывается при импорте)
- `backend/app/main.py:app` — Глобальный инстанс приложения
- `backend/app/api/v1/router.py:api_router` — Главный маршрутизатор всех v1 endpoints

**Configuration:**
- `backend/app/core/config.py` — Settings (SQLITE_DB_PATH, WORKSPACE_ROOT, HOST, PORT, DEBUG, CORS_ORIGINS)
- `.env` файл (если есть) — переопределяет defaults в Settings

**Core Logic:**
- `backend/app/db.py` — DatabaseService с CRUD методами
- `backend/app/api/v1/security.py` — Security Shield, PROJECTS_REGISTRY, secret scanning patterns

**Testing:**
- `backend/tests/test_dashboard_api.py` — Основной набор CRUD тестов
- `backend/tests/test_security_api.py` — Tests для audit endpoints

## Соглашения по именованию

**Файлы:**
- Роутеры: `{resource}.py` (projects.py, tasks.py, reminders.py)
- Тесты: `test_{feature}.py` (test_dashboard_api.py, test_security_api.py)
- Схемы: `dashboard_schemas.py` (Pydantic models для CRUD)

**Функции:**
- Обработчики HTTP: `{verb}_{resource}` или просто глагол (list_projects, create_task, update_reminder)
- Database методы: `{verb}_{resource}` в DatabaseService (list_projects, get_task, create_reminder)
- Утилиты: `run_cmd()`, `audit_path()` в security.py

**Переменные:**
- camelCase для Pydantic полей (id, sessionId, createdAt в models)
- snake_case для Python переменных (project_id, created_at в db.py)
- UPPER_CASE для констант (PROJECTS_REGISTRY, SECRET_PATTERNS в security.py)

**Types:**
- Pydantic BaseModel для schemas (ProjectCreate, TaskUpdate, ReminderBase)
- dataclass или dict[str, Any] для внутренних entities (результаты SQL запросов)
- Optional[T] для nullable полей

## Где добавить новый код

**Новая фишка (endpoint):**
1. Добавить обработчик в `backend/app/api/v1/{resource}.py` (или создать новый файл)
2. Добавить метод в `backend/app/db.py:DatabaseService` для работы с данными
3. Добавить Pydantic schema в `backend/app/models/dashboard_schemas.py` для входящих данных
4. Добавить тест в `backend/tests/test_{resource}_api.py`
5. Зарегистрировать router в `backend/app/api/v1/router.py` через `api_router.include_router()`

**Новый API resource:**
- Файл: `backend/app/api/v1/{new_resource}.py`
- Структура:
  ```python
  from fastapi import APIRouter
  from app.db import DatabaseService
  from app.models.dashboard_schemas import {NewResourceCreate, NewResourceUpdate}
  
  router = APIRouter(prefix="/{new_resources}", tags=["{NewResource}"])
  
  @router.get("")
  async def list_new_resources(...): ...
  
  @router.post("", status_code=201)
  async def create_new_resource(data: NewResourceCreate): ...
  ```
- Затем включить в `backend/app/api/v1/router.py`

**Новые Pydantic schemas:**
- Location: `backend/app/models/dashboard_schemas.py`
- Pattern: Separate Base, Create, Update классы для каждого entity
  ```python
  class NewResourceBase(BaseModel):
      field1: str
      field2: Optional[str] = None
  
  class NewResourceCreate(NewResourceBase):
      pass
  
  class NewResourceUpdate(BaseModel):
      field1: Optional[str] = None
      field2: Optional[str] = None
  ```

**Новые domain entities:**
- Location: `backend/app/models/agent.py` или `backend/app/models/chat.py` (в зависимости от контекста)
- Pattern: Pydantic BaseModel с Field default factories

**Новые тесты:**
- Location: `backend/tests/test_{feature}.py`
- Pattern: @pytest.mark.anyio async functions, используются ASGITransport + AsyncClient
- Example из test_dashboard_api.py:
  ```python
  @pytest.mark.anyio
  async def test_projects_crud():
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          response = await client.get("/api/v1/projects")
          assert response.status_code == 200
  ```

## Специальные директории

**`.claude/worktrees/`:**
- Purpose: Изолированные git worktrees для параллельной работы нескольких Claude-сессий
- Generated: Да (создаются autogenerated при запуске в worktree-режиме)
- Committed: Нет (в .gitignore)

**`.pytest_cache/`, `logs/`, `uploads/`, `scratch/`:**
- Purpose: Runtime artifacts, логи, temp файлы
- Generated: Да
- Committed: Нет (в .gitignore)

**`.env`, `.env.local`, credentials.json:**
- Purpose: Секреты (API ключи, пароли, пути к БД)
- Note: НИКОГДА не читать и не коммитить — обрабатывать как forbidden
- Current: `.env` файл может существовать (не читаем)

## Ограничения и зависимости

**Backend Dependencies (requirements.txt):**
- fastapi>=0.115.0 — Web framework
- uvicorn[standard]>=0.30.0 — ASGI server
- pydantic>=2.9.0, pydantic-settings>=2.5.0 — Data validation
- websockets>=13.0 — WebSocket support (для будущих chat endpoints)
- httpx>=0.27.0 — HTTP client
- pytest>=8.3.0, pytest-asyncio>=0.24.0 — Testing

**Frontend Dependencies (CDN, не требуют установки):**
- Tailwind CSS (cdn.tailwindcss.com)
- Lucide Icons (unpkg.com/lucide@latest)
- Marked.js (cdn.jsdelivr.net/npm/marked)

**Database:**
- SQLite3 (встроен в Python)
- aiosqlite для async access
- Shared DB: `/opt/assistant-core/data/assistant.db`

**Deployment:**
- Python 3.12 (как указано в CLAUDE.md)
- systemd service (chat-app.service, если запущен как демон)
- NODE_OPTIONS="--max-old-space-size=1536" для VPS с 2GB RAM

---

*Structure analysis: 2026-10-01*
