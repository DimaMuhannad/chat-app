---
last_mapped_commit: ee863eccdcc4889896a20f28c0c29a4e0ebe17b7
last_mapped_at: 2026-10-01
---
# Соглашения о кодировании

**Analysis Date:** 2026-10-01

## Соглашения об именовании

**Файлы:**
- Все модули и пакеты используют `snake_case`: `app/db.py`, `app/api/v1/projects.py`, `app/models/chat.py`
- Файлы с моделями: `models/chat.py`, `models/agent.py`, `models/dashboard_schemas.py`
- Файлы маршрутов API: `api/v1/{entity}.py` (projects.py, tasks.py, documents.py, reminders.py, health.py, security.py, dashboard.py)

**Функции и методы:**
- Используется `snake_case` для всех функций и методов: `get_utc_now()`, `create_project()`, `list_tasks()`, `audit_path()`, `get_dashboard_summary()`
- Асинхронные функции обозначаются с `async def`: `async def list_projects()`, `async def create_task()`
- Функции в ServiceClass используют `@staticmethod` для методов класса: `DatabaseService.list_projects()`, `DatabaseService.create_task()`
- Функции обработки маршрутов в API используют `async def` с префиксом операции: `async def get_health()`, `async def run_security_audit()`

**Переменные:**
- Используется `snake_case` для локальных переменных и параметров: `session_id`, `project_id`, `task_id`, `target_path`
- Приватные переменные (модуль-уровня): `START_TIME`, `PROJECTS_REGISTRY`, `SECRET_PATTERNS`, `FORBIDDEN_FILES`
- Переменные конфигурации (Settings): `UPPERCASE` - `PROJECT_NAME`, `SQLITE_DB_PATH`, `WORKSPACE_ROOT`, `API_V1_STR`, `CORS_ORIGINS`

**Типы и Enums:**
- Используется `PascalCase` для классов: `ChatMessage`, `ChatSession`, `AgentConfig`, `AgentTask`, `Artifact`
- Используется `PascalCase` для перечислений (Enum): `MessageRole`, `AgentStatus`, `AgentType`, `ChatResponseType`, `ArtifactType`
- Значения Enum используют `UPPERCASE`: `MessageRole.USER`, `AgentStatus.IDLE`, `AgentType.DEVELOPER`
- Базовые модели Pydantic используют `BaseModel`: `class ChatSession(BaseModel)`, `class ProjectCreate(BaseModel)`

## Стиль кода

**Форматирование:**
- Никакого явного инструмента форматирования не обнаружено (нет .prettierrc или pyproject.toml)
- Используется стандартный Python стиль с 4-пробельными отступами
- Максимальная длина строки не явно ограничена, но в коде присутствуют длинные строки

**Импорты:**
- Импорты организованы в три группы (PEP 8):
  1. Встроенные библиотеки: `from contextlib import asynccontextmanager`, `import logging`, `from datetime import datetime`, `import json`
  2. Внешние библиотеки: `from fastapi import APIRouter`, `from pydantic import BaseModel`, `import aiosqlite`
  3. Локальные импорты: `from app.db import DatabaseService`, `from app.core.config import settings`, `from app.models.chat import ChatMessage`
- Используются абсолютные импорты: `from app.db import ...`, не `from .db import ...`
- Импорты в одной строке для нескольких элементов из одного модуля: `from app.models import ChatMessage, ChatRequest, ChatSession`

**Aliases в импортах:**
- Используются `as` для переименования роутеров: `from app.api.v1.health import router as health_router`
- Используются для конфликтов имен и ясности: `from datetime import datetime, timezone`

## Организация кода

**Структура модулей:**
- Утилиты на уровне модуля находятся в начале файла: `def get_utc_now()`, `START_TIME = time.time()`
- Классы Enum определяются перед использованием: `class MessageRole(str, Enum):` перед `class ChatMessage(BaseModel):`
- Классы Pydantic группируются по функциональности: все Chat* модели в `models/chat.py`, все Agent* модели в `models/agent.py`
- DatabaseService использует методы с @staticmethod для каждой операции CRUD: `list_projects()`, `get_project()`, `create_project()`, `update_project()`, `delete_project()`

**Маршруты API:**
- Каждый маршрут - отдельный файл в `api/v1/`: `projects.py`, `tasks.py`, `documents.py`
- Роутер создается в начале: `router = APIRouter(prefix="/projects", tags=["Projects"])`
- Функции-обработчики определяются сразу после инициализации роутера
- Используется `exclude_unset=True` при обновлении моделей: `data.model_dump(exclude_unset=True)`

## Обработка ошибок

**Паттерн HTTPException:**

```python
from fastapi import HTTPException

@router.get("/{project_id}")
async def get_project(project_id: int):
    project = await DatabaseService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

- Используется `HTTPException` для всех ошибок API
- Проверяется существование ресурса перед возвратом
- Используются стандартные HTTP коды ошибок: 404 для не найденных ресурсов, 201 для успешного создания (`status_code=201`)
- Сообщения об ошибках на английском языке в API (`detail="Project not found"`)

**Обработка исключений в утилитах:**

```python
def run_cmd(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    try:
        res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return res.returncode, res.stdout.strip()
    except Exception as e:
        return 1, str(e)
```

- Используются try-except блоки для обработки исключений
- Возвращаются коды ошибок вместо выброса исключений в утилитах

**Обработка ошибок базы данных:**

```python
try:
    payload = json.loads(row["raw_payload"])
    # Process payload
except Exception:
    pass  # Graceful fallback
```

- Используется `pass` для graceful degradation при ошибках парсинга JSON

## Типизация

**Type hints используются везде:**

```python
async def list_projects(area: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    # ...
    return [dict(r) for r in await cursor.fetchall()]
```

- Используется `str | None` (PEP 604) вместо `Optional[str]`
- Используется `list[dict[str, Any]]` вместо `List[Dict[str, Any]]`
- Используется `dict[str, Any]` для словарей с неизвестными значениями

**Полные типы используются в DataService:**

```python
@staticmethod
async def create_task(data: dict[str, Any]) -> dict[str, Any]:
```

## Логирование

**Конфигурация логирования:**

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("chat-backend")
```

- Используется встроенный модуль `logging`
- Создается logger с именем приложения: `logging.getLogger("chat-backend")`
- Форматирование включает timestamp, имя логгера, уровень и сообщение

**Использование логирования:**

```python
logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
logger.info(f"Shutting down {settings.PROJECT_NAME}...")
```

- Используется `logger.info()` для информационных сообщений
- Используются f-strings для форматирования сообщений

## Комментарии

**Стиль комментариев:**
- Используются многострочные комментарии в коде: `# 1. Focus P1 tasks`, `# 2. Task counts by status`
- Используются для группировки логически связанных операций в методах
- Используются русские комментарии в кода для объяснения: `# Тест данных`, `# Проверка следующей даты`

**Docstrings:**

```python
async def run_security_audit(req: AuditRequest):
    """Executes on-demand live Security Shield audit for a project or all projects."""
```

- Используются docstrings для функций API
- Используются на английском языке для документирования API

## Паттерны проектирования

**Context managers для управления ресурсами:**

```python
@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
```

- Используется `@asynccontextmanager` для управления подключениями к БД
- Используется `async with` для гарантированного закрытия соединений
- Устанавливаются PRAGMA опции для БД в контексте

**Service Layer паттерн:**

```python
class DatabaseService:
    @staticmethod
    async def get_dashboard_summary() -> dict[str, Any]:
        async with get_db() as conn:
            # ...
```

- Используется класс DatabaseService со статическими методами для всех операций с БД
- Каждый метод открывает свое собственное соединение с БД
- Методы инкапсулируют SQL логику

**Асинхронность:**
- Все операции I/O используют `async/await`
- Все функции в API используют `async def`
- Все DatabaseService методы являются `async`
- Используется httpx для асинхронных HTTP запросов

**Pydantic модели с Field:**

```python
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: MessageRole
    content: str = ""
    created_at: datetime = Field(default_factory=get_utc_now)
```

- Используется `Field(default_factory=...)` для генерирования значений по умолчанию
- Используется `Field(default_factory=dict)` для пустых словарей и списков

## Безопасность

**Сканирование секретов:**
- Используются регулярные выражения для обнаружения утечек секретов: `SECRET_PATTERNS` список паттернов в `security.py`
- Сканируются запрещенные файлы: `.env*`, `*.key`, `*.pem` и т.д. через `FORBIDDEN_FILES`

**SQL параметризация:**

```python
cursor = await conn.execute(
    "SELECT * FROM projects WHERE id = ?;",
    (project_id,)
)
```

- Используются параметризованные запросы с `?` плейсхолдерами
- Параметры передаются в виде кортежа

---

*Convention analysis: 2026-10-01*
