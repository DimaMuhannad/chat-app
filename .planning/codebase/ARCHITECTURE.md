---
last_mapped_commit: ee863eccdcc4889896a20f28c0c29a4e0ebe17b7
last_mapped_at: 2026-10-01
---
<!-- refreshed: 2026-10-01 -->

# Архитектура

**Analysis Date:** 2026-10-01

## Обзор системы

```
┌──────────────────────────────────────────────────────────────┐
│              STATIC HTML SPA (Frontend)                      │
│  /backend/app/static/index.html                             │
│  Tailwind CSS · Lucide Icons · Marked.js · JavaScript       │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP/REST (без аутентификации)
┌────────────────────────▼─────────────────────────────────────┐
│            FastAPI REST API Server                           │
│  /backend/app/main.py:app (FastAPI)                         │
│  Endpoints: /api/v1/{projects,tasks,reminders,documents,... │
└────────────────┬──────────────────────┬─────────────────────┘
                 │                      │
    ┌────────────▼──────┐    ┌──────────▼────────────┐
    │  API v1 Routers   │    │  Security Shield      │
    │  (router.py)      │    │  (security.py)        │
    │  ├─ projects      │    │  Hardcoded registry   │
    │  ├─ tasks         │    │  Secret scanning      │
    │  ├─ reminders     │    │  Projects audit       │
    │  ├─ documents     │    │  Air-gap enforcement  │
    │  ├─ dashboard     │    │                       │
    │  └─ health        │    └───────────────────────┘
    └────────────────┬──────────────────────┘
                     │
         ┌───────────▼───────────┐
         │  DatabaseService      │
         │  (static methods)     │
         │  ├─ CRUD ops for all  │
         │  ├─ aiosqlite conn    │
         │  └─ SQL query builder │
         └───────────────────────┘
                     │
         ┌───────────▼──────────────────┐
         │  SQLite Database             │
         │  Path: /opt/assistant-core/  │
         │        data/assistant.db     │
         │  Tables: projects, tasks,    │
         │          reminders, documents│
         │          content_snapshots   │
         │          email_messages, ... │
         └──────────────────────────────┘
```

## Ответственность компонентов

| Компонент | Ответственность | Файл |
|-----------|-----------------|------|
| FastAPI App | Инициализация приложения, CORS, middleware, маршруты | `backend/app/main.py` |
| API v1 Router | Композиция всех v1 маршрутов | `backend/app/api/v1/router.py` |
| Projects Router | GET/POST/PUT/DELETE проектов | `backend/app/api/v1/projects.py` |
| Tasks Router | GET/POST/PUT/PATCH/DELETE задач | `backend/app/api/v1/tasks.py` |
| Reminders Router | GET/POST/PUT/PATCH/DELETE напоминаний | `backend/app/api/v1/reminders.py` |
| Documents Router | GET/POST/PUT/DELETE документов | `backend/app/api/v1/documents.py` |
| Dashboard Router | Сводка метрик и KPI | `backend/app/api/v1/dashboard.py` |
| Security Router | Аудит проектов, сканирование секретов | `backend/app/api/v1/security.py` |
| DatabaseService | Все операции с БД (CRUD, агрегации) | `backend/app/db.py` |
| Settings | Конфигурация приложения | `backend/app/core/config.py` |

## Паттерн архитектуры

**Текущее состояние:** Монолитная архитектура с тремя слоями.

**Ключевые характеристики:**
- Один DatabaseService с 40+ статическими методами для всех CRUD операций
- Прямые SQL-запросы без ORM (используется только aiosqlite)
- Общая SQLite БД между chat-app и /opt/assistant-core (нарушение архитектурных границ)
- Жесткие дефолты (area="ГУАП", project_id уходит в NULL без указания)
- Отсутствие dependency injection — конструктивная инъекция только на уровне Settings
- Нет event bus, нет асинхронной публикации событий
- Hardcoded PROJECTS_REGISTRY в security.py — не извлечено в конфигурацию

## Слои

**REST API Layer:**
- Purpose: Обработка HTTP-запросов, валидация Pydantic-моделей, маршрутизация
- Location: `backend/app/api/v1/`
- Contains: Функции-обработчики, router-экземпляры
- Depends on: DatabaseService, models (Pydantic schemas)
- Used by: FastAPI app

**Data Access Layer (DatabaseService):**
- Purpose: Выполнение SQL-запросов, управление транзакциями
- Location: `backend/app/db.py`
- Contains: Статические методы для каждого основного entity (projects, tasks, reminders, documents)
- Depends on: aiosqlite, Settings (для пути БД)
- Used by: Все API роутеры

**Database:**
- Purpose: Хранилище данных
- Location: `/opt/assistant-core/data/assistant.db` (shared)
- Schema: ~12 таблиц (projects, tasks, reminders, documents, content_snapshots, email_messages, etc.)

## Поток данных

### Основной путь запроса

1. Браузер отправляет HTTP-запрос (GET /api/v1/projects) (`main.py:26-34`)
2. FastAPI маршрут перенаправляет в функцию-обработчик в projects.py (`projects.py:9-14`)
3. Обработчик вызывает DatabaseService.list_projects() (`db.py:111-129`)
4. DatabaseService выполняет SQL-запрос к SQLite через aiosqlite (`db.py:113-128`)
5. Результаты преобразуются в dict и возвращаются как JSON-ответ (`projects.py:14`)

### Dashboard Summary Flow

1. Запрос GET /api/v1/dashboard/summary (`dashboard.py:8`)
2. DatabaseService.get_dashboard_summary() выполняет 7 параллельных SQL-запросов (`db.py:20-107`)
3. Агрегирует результаты в единый dict с ключами: focus_tasks, task_counts, active_reminders, etc. (`db.py:97-107`)
4. Возвращает все данные одной посылкой

### Security Audit Flow

1. Запрос GET /api/v1/security/overview (`security.py:132-167`)
2. Для каждого проекта в PROJECTS_REGISTRY вызывается audit_path() (`security.py:79-125`)
3. audit_path() запускает git команды (git remote get-url, git config user.email, git ls-files)
4. Сканирует первые 100 файлов на SECRET_PATTERNS и FORBIDDEN_FILES (`security.py:13-29, 102-116`)
5. Возвращает агрегированный статус со списком violations

**Управление состоянием:**
- Состояние хранится в SQLite (никакого in-memory кэша, кроме START_TIME в health.py)
- Каждый запрос открывает новое соединение aiosqlite
- PRAGMA foreign_keys = ON гарантирует RI-проверки

## Ключевые абстракции

**DatabaseService:**
- Purpose: Унификация доступа к БД, повторное использование код для CRUD
- Examples: `DatabaseService.list_projects()`, `DatabaseService.create_task()`, `DatabaseService.get_dashboard_summary()`
- Pattern: Статические методы (Singleton через класс + статика), Context manager для соединений

**Pydantic Models (Schemas):**
- Purpose: Валидация входящих данных, сериализация при ответе
- Examples: `ProjectCreate`, `TaskUpdate`, `ReminderBase`
- Location: `backend/app/models/dashboard_schemas.py`

**Settings (Singleton):**
- Purpose: Централизованная конфигурация приложения
- Examples: `SQLITE_DB_PATH`, `WORKSPACE_ROOT`, `CORS_ORIGINS`
- Pattern: Singleton через pydantic_settings.BaseSettings

## Точки входа

**FastAPI App Factory:**
- Location: `backend/app/main.py:create_app()`
- Triggers: При импорте модуля (app = create_app() на строке 69)
- Responsibilities: Создание FastAPI инстанса, регистрация middleware, композиция роутеров

**API v1 Router:**
- Location: `backend/app/api/v1/router.py`
- Triggers: Включается в app через app.include_router(api_router, prefix="/api/v1") в main.py
- Responsibilities: Сборка всех поддоменов (projects, tasks, reminders, documents, security, dashboard, health)

**Static HTML SPA:**
- Location: `backend/app/static/index.html`
- Triggers: GET / маршрут в main.py:62-64 возвращает FileResponse(index.html)
- Responsibilities: Загружает весь frontend (HTML + Tailwind CDN + JavaScript логика встроена в HTML)

## Архитектурные ограничения

- **Threading:** Асинхронная архитектура (asyncio), но БД-запросы выполняются синхронно через aiosqlite на одном event loop (нет worker threads)
- **Глобальное состояние:** Settings инстанс (app.core.config), START_TIME в health.py, PROJECTS_REGISTRY и SECRET_PATTERNS в security.py (жесткие константы, не конфигурация)
- **Циклические импорты:** Нет известных циклических зависимостей
- **Общая БД:** Большой архитектурный риск — chat-app напрямую читает/пишет в /opt/assistant-core/data/assistant.db (Риск №1 из UNIVERSAL_ARCHITECTURE_BLUEPRINT.md)
- **Отсутствие HITL:** DELETE endpoints (delete_project, delete_task, delete_document) не имеют никакой защиты от случайных удалений (нарушение Риска №3 из blueprint)

## Антипаттерны

### Монолитная DatabaseService

**What happens:** Все CRUD операции собраны в один класс со 40+ статическими методами. Нет разделения ответственности по сущностям.

**Why it's wrong:** Трудно тестировать (нужно мокировать весь класс), трудно переиспользовать отдельные методы, нарушает Single Responsibility Principle.

**Do this instead:** Разделить на отдельные классы (ProjectRepository, TaskRepository, etc.) или использовать конструктивную инъекцию как в целевой архитектуре (см. UNIVERSAL_ARCHITECTURE_BLUEPRINT.md).

### Жесткие дефолты в коде

**What happens:** Значения вроде area="ГУАП" и project_tag="Тидекс" рассеяны по db.py (строки 149, 244).

**Why it's wrong:** При добавлении новой персоны (второй пользователь, вторая persona) нужно менять код, а не конфигурацию. Тесты с синтетической персоной не могут перекрыть текущие дефолты.

**Do this instead:** Все дефолты перенести в config/persona.yaml (как описано в blueprint), загружать при старте через Settings, инъектировать в DatabaseService.

### Общая БД между микросервисами

**What happens:** chat-app и /opt/assistant-core напрямую обращаются к одной SQLite БД (/opt/assistant-core/data/assistant.db).

**Why it's wrong:** Нарушает микросервисное разделение. Если assistant-core перезагружается, chat-app может получить inconsistent reads. Масштабирование на несколько инстансов невозможно.

**Do this instead:** Реализовать EventBus как в blueprint (Фаза 3). chat-app должна иметь собственную БД, обмениваться событиями через broker (Redis, AMQP).

## Обработка ошибок

**Strategy:** Простой — HTTPException для 404, no validation на level SQL.

**Patterns:**
- Если entity не найден: raise HTTPException(status_code=404, detail="X not found")
- SQL ошибки не перехватываются (пробивают 500)
- Pydantic ошибки (валидация входящих данных) возвращаются как 422 Unprocessable Entity

## Сквозные concern'ы

**Logging:** Базовый logging через Python logging (backend/app/main.py:12-16), логируется только INFO-уровень при старте/остановке сервера.

**Validation:** Pydantic при получении JSON-payload (ProjectCreate, TaskCreate, etc.), SQL-ошибки не перехватываются.

**Authentication:** Отсутствует — все endpoints доступны всем. CORS разрешены все origins ("*").

**Security Shield:** Хардкод PROJECTS_REGISTRY с path-проверками, git-командами для аудита, regex для сканирования SECRET_PATTERNS. Не масштабируется, не конфигурируется.

---

**Примечание о целевой архитектуре:** Файл `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` описывает целевое состояние после 5 фаз рефакторинга. Текущая документация (ARCHITECTURE.md и STRUCTURE.md) описывает только ACTUAL CURRENT STATE как он есть в коде сегодня, не целевую модель.

*Architecture analysis: 2026-10-01*
