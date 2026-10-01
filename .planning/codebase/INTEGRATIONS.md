---
last_mapped_commit: ee863eccdcc4889896a20f28c0c29a4e0ebe17b7
last_mapped_at: 2026-10-01
---
# Внешние интеграции

**Дата анализа:** 2026-10-01

## API и внешние сервисы

**LLM и AI моделирование:**
- Google Gemini - Основная модель для агента
  - SDK: google-genai (упомянута в GEMINI.md, но не в requirements.txt текущего пакета)
  - Модели: `gemini-2.5-pro` (по умолчанию в `backend/app/models/chat.py` и `agent.py`)
  - Использование: Потоковая генерация ответов через WebSocket

## Хранилище данных

**Базы данных:**
- SQLite
  - Расположение: `/opt/assistant-core/data/assistant.db` (задано в `backend/app/core/config.py` через `SQLITE_DB_PATH`)
  - Клиент: aiosqlite (асинхронный драйвер)
  - Используемые таблицы: `tasks`, `projects`, `reminders`, `documents`, `email_messages`, `content_snapshots`
  - Транзакции: Включены `PRAGMA foreign_keys = ON`

**Хранилище файлов:**
- Локальная файловая система только
  - Статические файлы: `backend/app/static/` (HTML/CSS/JS)
  - Загрузки: `uploads/` директория (в `.gitignore`)
  - Логи: `logs/` директория

**Кеширование:**
- Не используется (Redis/memcached отсутствуют)

## Аутентификация и идентификация

**Auth провайдер:**
- Не реализовано (открытый API)
- CORS включен для всех источников (`CORS_ORIGINS: ["*"]` в `config.py`)
- Безопасность: Полагается на контроль доступа на уровне инфраструктуры и HITL (Human-in-the-Loop) подтверждений для деструктивных операций

## Мониторинг и наблюдаемость

**Трассировка ошибок:**
- Не настроена внешняя интеграция

**Логирование:**
- Встроенное логирование Python через `logging` модуль
- Вывод: `stdout` (через systemd)
- Файл логов: `/opt/chat-app/logs/` (опционально)

## CI/CD и развертывание

**Хостинг:**
- Linux VPS (Амстердам, SpaceCore)
- systemd сервис: `chat-app.service`

**CI Pipeline:**
- Отсутствует (ручное тестирование через pytest)
- Тесты: `backend/tests/` запускаются через `pytest backend/tests`

## Конфигурация окружения

**Обязательные переменные окружения:**
- `DEBUG` - Режим разработки (по умолчанию: `True`)
- `HOST` - IP адрес прослушивания (по умолчанию: `0.0.0.0`)
- `PORT` - Порт (по умолчанию: `8000`)
- `SQLITE_DB_PATH` - Путь к БД (по умолчанию: `/opt/assistant-core/data/assistant.db`)
- `WORKSPACE_ROOT` - Корневая директория проекта (по умолчанию: `/opt/chat-app`)
- `CLAUDE_CODE_OAUTH_TOKEN` - Токен для Claude Code интеграции (загружается из `/opt/assistant-core/.env` в скриптах)

**Расположение секретов:**
- `.env` файл в корне проекта (исключен из git через `.gitignore`)
- Переменные окружения через systemd (в `/etc/systemd/system/chat-app.service`)

## Webhooks и обратные вызовы

**Входящие:**
- GET `/health` - Проверка состояния сервиса (возвращает `HealthResponse`)
- GET `/` - SPA dashboard (возвращает `index.html`)
- POST `/api/v1/projects` - Создание проекта
- POST `/api/v1/tasks` - Создание задачи
- POST `/api/v1/reminders` - Создание напоминания
- POST `/api/v1/documents` - Создание документа
- GET `/api/v1/security/overview` - Аудит безопасности и сканирование NDA air-gap

**Исходящие:**
- WebSocket потоковая передача к клиентам (теоретически поддерживается через FastAPI, но не активно используется в текущей версии)
- Вызовы к Google Gemini API (не показано в коде, но упомянуто в GEMINI.md как часть плана)

## Интеграция с соседним сервисом

**Assistant Core Daemon (`/opt/assistant-core`):**
- Адрес: `/opt/assistant-core/` (отдельный Python проект)
- Связь: Общая база данных SQLite (`/opt/assistant-core/data/assistant.db`)
- Функции: Мониторинг расписания GUAP, обработка Telegram сообщений, интеграция с Google Calendar
- Модели LLM: Gemini 3.5/3.6/3.8 Flash
- Не должен быть затронут разработкой chat-app

## GitHub интеграция

**Использование:**
- Аудит git remote URL для проектов (безопасность)
- Сканирование истории коммитов на утечки секретов
- Проверка конфигурации git (user.email)
- Поддержка NDA air-gap для приватных проектов (Tydex LLC)

**Механизм:**
- Команды: `git remote get-url origin`, `git ls-files`, `git config user.email`
- Исходящих вызовов API нет (только локальное сканирование через subprocess)

## Persona Plugins (планируется)

**Согласно UNIVERSAL_ARCHITECTURE_BLUEPRINT.md:**
- `popov-da-default` - Плагин по умолчанию (GUAP LMS + AADHk timesheet + Google Calendar + Notion + Google Drive)
- `security-governance` - Плагин безопасности (управление workspace и NDA air-gap)
- Планируется расширить на другие personas

---

*Аудит интеграций: 2026-10-01*
