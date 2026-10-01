---
last_mapped_commit: ee863eccdcc4889896a20f28c0c29a4e0ebe17b7
last_mapped_at: 2026-10-01
---
# Технологический стек

**Дата анализа:** 2026-10-01

## Языки

**Основной:**
- Python 3.12.3 - Бэкенд, обработка запросов, интеграция с внешними сервисами

**Вспомогательный:**
- HTML5 - Веб-интерфейс (статический SPA)
- CSS (Tailwind) - Стилизация
- JavaScript (Vanilla) - Интерактивность на клиенте

## Runtime

**Окружение:**
- Python 3.12 с использованием виртуального окружения (`.venv`)
- Запуск через `systemd` сервис `chat-app.service`

**Пакетный менеджер:**
- pip 26.2.1
- Lockfile: `requirements.txt` (находится в `backend/requirements.txt`)

## Фреймворки

**Core:**
- FastAPI 0.141.1 - REST API и WebSocket сервер, OpenAPI документация
- Uvicorn 0.54.0 (standard) - ASGI сервер для запуска FastAPI приложения
- Starlette 1.7.0 - Нижележащий слой HTTP обработки (зависимость FastAPI)

**Валидация данных:**
- Pydantic 2.13.5 - Валидация и сериализация данных
- Pydantic-settings 2.15.0 - Управление конфигурацией через переменные окружения

**Тестирование:**
- pytest 9.1.1 - Фреймворк для написания и запуска тестов
- pytest-asyncio 0.24.0 - Поддержка async тестов (работает с aiosqlite и httpx)

**Построение и разработка:**
- python-dotenv 1.2.3 - Загрузка переменных из `.env` файла

## Ключевые зависимости

**Критичные:**
- aiosqlite 0.22.1 - Асинхронный драйвер SQLite, используется для всех операций с БД
- websockets 13.0 - WebSocket протокол для двусторонней потоковой передачи (думающие процессы, ответы модели, результаты инструментов)
- httpx 0.28.1 - Асинхронный HTTP клиент для интеграции с внешними API (Google Gemini, Notion, GitHub)

**Инфраструктура:**
- anyio 4.15.1 - Асинхронная совместимость (используется для управления событиями)
- h11 0.16.0 - HTTP парсер (зависимость httpx)
- httpcore 1.0.9 - Низкоуровневый HTTP транспорт (зависимость httpx)

**Утилиты:**
- typing-extensions 4.16.0 - Расширенная типизация для Python 3.12
- certifi 2026.7.22 - Сертификаты SSL/TLS для HTTPS
- click 8.5.0 - CLI фреймворк (зависимость pytest)

## Конфигурация

**Окружение:**
- Загрузка из `.env` файла через `pydantic-settings`
- Параметры: `DEBUG`, `HOST`, `PORT`, `CORS_ORIGINS`, `SQLITE_DB_PATH`, `WORKSPACE_ROOT`
- Переменная окружения `CLAUDE_CODE_OAUTH_TOKEN` используется в скриптах для интеграции с Claude Code

**Сборка:**
- Запуск: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (в режиме разработки)
- Экспорт: `NODE_OPTIONS="--max-old-space-size=1536"` (оптимизация для VPS с 2GB RAM)

## Требования платформы

**Разработка:**
- Linux/Ubuntu 24.04 LTS (основной стек)
- Python 3.12+
- pip
- Доступ к файловой системе (`/opt/chat-app`, `/opt/assistant-core`)

**Production:**
- Linux VPS (текущее окружение: Амстердам, SpaceCore, 2 GB RAM, 4.5 GB Swap)
- SQLite БД должна быть доступна по пути `/opt/assistant-core/data/assistant.db`
- Запуск через systemd `chat-app.service`

---

*Анализ технологического стека: 2026-10-01*
