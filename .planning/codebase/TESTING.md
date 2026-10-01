---
last_mapped_commit: ee863eccdcc4889896a20f28c0c29a4e0ebe17b7
last_mapped_at: 2026-10-01
---
# Паттерны тестирования

**Analysis Date:** 2026-10-01

## Фреймворк тестирования

**Запуск:**
- Framework: pytest 8.3.0+
- Плагин для асинхронности: pytest-asyncio 0.24.0+
- HTTP-тестирование: httpx 0.27.0+
- Команда для запуска: `/opt/chat-app/backend/.venv/bin/pytest backend/tests`

**Команды запуска:**

```bash
/opt/chat-app/backend/.venv/bin/pytest backend/tests                    # Run all tests
/opt/chat-app/backend/.venv/bin/pytest backend/tests -v               # Verbose mode
/opt/chat-app/backend/.venv/bin/pytest backend/tests -k test_health   # Run specific test
/opt/chat-app/backend/.venv/bin/pytest backend/tests -s               # Show prints
```

## Организация тестов

**Расположение:**
- Все тесты находятся в `backend/tests/` директории
- Один файл тестов на модуль: `test_health.py`, `test_models.py`, `test_dashboard_api.py`, `test_security_api.py`
- Конвенция именования: `test_*.py` для файлов, `test_*()` для функций

**Структура тестов:**

```
backend/
├── tests/
│   ├── __init__.py
│   ├── test_health.py           # Тесты health endpoint
│   ├── test_models.py           # Тесты Pydantic models (unit)
│   ├── test_dashboard_api.py    # Интеграционные тесты CRUD операций
│   └── test_security_api.py     # Тесты Security Shield API
└── app/
    ├── main.py
    ├── db.py
    └── ...
```

## Структура теста

**Асинхронное тестирование:**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.anyio
async def test_health_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
```

**Паттерн использования AsyncClient:**
1. Создание `ASGITransport` с приложением FastAPI
2. Использование `AsyncClient` с транспортом
3. Асинхронный вызов методов HTTP (get, post, put, delete, patch)
4. Проверка статус-кода ответа
5. Парсинг JSON ответа

**Unit тесты (без асинхронности):**

```python
def test_chat_models():
    session = ChatSession(title="Test Session", model="gemini-2.5-pro")
    assert session.id is not None
    assert session.title == "Test Session"
```

- Используется стандартный pytest без `@pytest.mark.anyio`
- Создаются объекты Pydantic моделей
- Проверяются значения полей

## Типы тестов

### Unit тесты: `test_models.py`

**Область:**
- Тестирование создания объектов Pydantic моделей
- Проверка значений полей по умолчанию
- Проверка сериализации моделей

**Без зависимостей от БД:**
- Тесты `test_chat_models()` и `test_agent_models()` создают модели в памяти
- Не обращаются к базе данных
- Работают на свежей чистой БД

**Пример:**

```python
def test_chat_models():
    session = ChatSession(title="Test Session", model="gemini-2.5-pro")
    assert session.id is not None
    assert session.title == "Test Session"
    
    msg = ChatMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content="Hello Agent!",
    )
    assert msg.role == MessageRole.USER
```

### Интеграционные тесты: `test_dashboard_api.py`

**Область:**
- Тестирование CRUD операций API
- Проверка взаимодействия с БД через API
- Проверка валидации данных

**Зависимость от БД:**
- Требует существующих записей в БД для чтения (reminders, documents, projects, tasks)
- `test_dashboard_summary()` - требует data в таблицах `content_snapshots`, `email_messages`, `reminders`
- `test_reminders_crud()` - требует минимум одного reminder в БД
- `test_documents_crud()` - требует минимум одного document в БД
- Все CRUD тесты создают новые записи и удаляют их (self-cleaning)

**Тест CRUD операций:**

```python
@pytest.mark.anyio
async def test_projects_crud():
    # 1. Чтение
    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) >= 1
    
    # 2. Создание
    create_res = await client.post("/api/v1/projects", json={
        "name": "Тестовый проект",
        "area": "AI & Dev Projects",
        "status": "active"
    })
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["name"] == "Тестовый проект"
    
    # 3. Удаление
    del_res = await client.delete(f"/api/v1/projects/{created['id']}")
    assert del_res.status_code == 200
```

**Проблема с чистой БД:**
- Тест `test_dashboard_summary()` может не пройти на чистой БД, если нет необходимых данных
- Тест `test_reminders_crud()` требует `reminders[0]["id"]` - нужен минимум один reminder
- Тест `test_documents_crud()` требует `docs[0]["id"]` - нужен минимум один document

### Интеграционные тесты: `test_security_api.py`

**Область:**
- Тестирование Security Shield API
- Проверка аудита проектов
- Проверка clearance levels

**Зависимость от persona-specific данных:**
- `test_security_overview()` - ожидает ровно 4 проекта:
  - `tydex-optics` с clearance `restricted_nda`
  - 3 других проекта
- Проверяется жестко: `assert len(data["projects"]) == 4`

**Проблема с универсализацией:**
- Тесты привязаны к persona-specific конфигурации:
  - Ожидается проект `tydex-optics` (Тидекс ООО, NDA)
  - Ожидаются остальные проекты (chat-app, assistant-core, guap-physics)
- На чистой БД эти тесты не будут работать без добавления в `PROJECTS_REGISTRY`
- Registry жестко закодирован в `app/api/v1/security.py` строках 31-68

### Smoke тесты: `test_health.py`

**Область:**
- Базовая проверка доступности endpoints
- Проверка структуры ответов
- Проверка наличия статических файлов

**Без зависимостей:**
- Все 4 теста работают на чистой БД
- Проверяют только наличие endpoint'ов и базовую структуру ответов
- `test_root()` проверяет наличие "Antigravity Studio" в index.html

**Примеры:**

```python
@pytest.mark.anyio
async def test_health_root():
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data

@pytest.mark.anyio
async def test_root():
    response = await client.get("/")
    assert response.status_code == 200
    assert "Antigravity Studio" in response.text
```

## Использование Mock'ов

**Текущий подход:**
- **NO мокирование используется** - тесты работают с реальной БД
- Все тесты используют реальное приложение FastAPI
- Тесты используют реальное SQLite соединение

**Что НЕ мокируется:**
- Приложение FastAPI
- Подключения к БД
- HTTP запросы (используется реальный ASGI transport)

**Возможные проблемы:**
- Тесты могут влиять друг на друга если не очищают данные
- Тесты медленнее из-за реальных операций с БД

## Фиксчи и фабрики

**Текущий подход:**
- **NO использования фиксчер PyTest** - данные создаются внутри тестов
- **NO использования фабрик** - данные создаются прямыми вызовами API

**Создание тестовых данных:**

```python

# Прямое использование API для создания данных

create_res = await client.post("/api/v1/projects", json={
    "name": "Тестовый проект",
    "area": "AI & Dev Projects",
    "status": "active"
})
```

**Очистка данных:**

```python

# Self-cleaning тесты - удаляют созданные данные в конце

del_res = await client.delete(f"/api/v1/projects/{created['id']}")
```

## Тестирование асинхронности

**Паттерн асинхронного тестирования:**

```python
@pytest.mark.anyio
async def test_async_operation():
    # Используется @pytest.mark.anyio для асинхронного теста
    # AsyncClient автоматически обрабатывает асинхронность
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        # Ожидание результата асинхронного вызова
```

## Тестирование ошибок

**Паттерн проверки ошибок:**

```python
@pytest.mark.anyio
async def test_get_project_not_found():
    # Предполагаемый паттерн (не найден в текущих тестах)
    response = await client.get("/api/v1/projects/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
```

**Текущие тесты:**
- Не проверяют ошибки 404 для не существующих ресурсов
- Не проверяют валидацию ошибок некорректных данных
- Фокусируются только на успешных сценариях

## Покрытие тестами

**Требуемое:**
- Никаких явных требований к покрытию в конфигурации
- CLAUDE.md требует 100% pass rate, но не требует X% покрытия кода

**Текущее состояние:**
- 13 тестов всего
- Unit тесты: 2 теста (test_models.py)
- Integration тесты: 4 теста (test_dashboard_api.py)
- API тесты: 3 теста (test_security_api.py)
- Smoke тесты: 4 теста (test_health.py)

**Пробелы в тестировании:**
- НЕТ тестов для:
  - Ошибки 404 (не найденные ресурсы)
  - Ошибки валидации (некорректные данные)
  - Обновление документов через PUT (тест есть, но валидация не проверяется)
  - Delete операции без проверки отсутствия после удаления
  - Фильтрация по параметрам (area, status, priority, project_id)

## Команды тестирования

**Запуск всех тестов:**

```bash
cd /opt/chat-app
/opt/chat-app/backend/.venv/bin/pytest backend/tests
```

**Запуск конкретного файла:**

```bash
/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_health.py
```

**Запуск конкретного теста:**

```bash
/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_health.py::test_health_root
```

**С выводом на экран:**

```bash
/opt/chat-app/backend/.venv/bin/pytest backend/tests -s
```

**Verbose mode:**

```bash
/opt/chat-app/backend/.venv/bin/pytest backend/tests -v
```

## Зависимость от внешних данных

### Тесты требующие `/opt/assistant-core/data/assistant.db`:

- **ВСЕ интеграционные тесты** - работают с реальной БД на пути `/opt/assistant-core/data/assistant.db` (из конфига `SQLITE_DB_PATH`)
- `test_dashboard_api.py` - все 4 теста
- `test_security_api.py` - все 3 теста

### Persona-specific зависимости:

- **`test_security_api.py`** - жестко ожидает 4 проекта:
  - chat-app
  - assistant-core
  - tydex-optics (Тидекс, NDA)
  - guap-physics (ГУАП, кафедра физики)
- Эти проекты определены в `PROJECTS_REGISTRY` в `app/api/v1/security.py`
- Тесты зависят от наличия этих конкретных проектов в файловой системе

### Зависимость от структуры БД:

- **`test_dashboard_summary()`** - требует таблиц:
  - `tasks` с P1 приоритетом
  - `projects` с active статусом
  - `reminders` с active статусом
  - `documents`
  - `content_snapshots` (для расписания)
  - `email_messages` (для email stats)
- Может не пройти на чистой БД если таблицы пусты

- **`test_reminders_crud()`** - требует минимум одного активного reminder в БД

- **`test_documents_crud()`** - требует минимум одного document в БД

### Тесты независимые от внешних данных:

- **`test_models.py`** - чистые unit тесты, работают везде
- **`test_health.py`** - не требуют данных в БД (кроме проверки наличия static/index.html)

## Проблема универсализации

**Текущее состояние:**
- Тесты привязаны к persona-specific конфигурации (ГУАП, Тидекс, Попов)
- Тесты не могут быть запущены на чистой БД без подготовки данных
- Ожидается конкретная структура проектов и данных

**Требуется для универсализации:**
- Переместить `PROJECTS_REGISTRY` в конфигурацию или БД
- Создать фиксчи или seed-данные для persona-specific тестов
- Разделить тесты на две категории:
  - Универсальные (работают везде)
  - Persona-specific (требуют конкретной конфигурации)

---

*Testing analysis: 2026-10-01*
