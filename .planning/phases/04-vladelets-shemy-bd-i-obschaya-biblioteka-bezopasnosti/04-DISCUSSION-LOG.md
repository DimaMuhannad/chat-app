# Phase 04: Владелец схемы БД и общая библиотека безопасности - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-03
**Phase:** 04-vladelets-shemy-bd-i-obschaya-biblioteka-bezopasnosti
**Areas discussed:** Размещение общей библиотеки, Движок миграций схемы БД, Установка и дистрибуция pre-commit hook, Изоляция тестов chat-app

---

## 1. Размещение общей библиотеки

| Option | Description | Selected |
|--------|-------------|----------|
| Отдельный локальный пакет `/opt/assistant-shared` | Устанавливается через `pip install -e` в оба `.venv`; независимость репозиториев | ✓ (Claude's Discretion) |
| Пакет внутри `chat-app` (`packages/shared`) | Импортируется в `chat-app`, а `assistant-core` зависит от `chat-app` | |
| Зеркалирование кода библиотеки | Копии файлов в обоих репозиториях с проверкой SHA-256 в гейте | |

**User's choice:** Доверяю твоему варианту по всем вопросам (Claude's Discretion).
**Notes:** Выбран отдельный локальный пакет `/opt/assistant-shared` для соблюдения изоляции и выполнения DAT-04.

---

## 2. Движок миграций схемы БД

| Option | Description | Selected |
|--------|-------------|----------|
| Легковесный SQL-раннер версий (KISS) | Каталог `migrations/`, файлы `.sql`, таблица `schema_migrations`, без внешних зависимостей | ✓ (Claude's Discretion) |
| Alembic / SQLAlchemy | Стандартный инструмент миграций, требует внешних библиотек | |

**User's choice:** Решение принято по принципу KISS (Claude's Discretion).
**Notes:** Простой SQL-мигратор обеспечивает прозрачность, отсутствие лишних зависимостей и легкую проверку идемпотентности.

---

## 3. Установка и дистрибуция pre-commit hook

| Option | Description | Selected |
|--------|-------------|----------|
| Воспроизводимый скрипт установки `install_hooks.sh` | Скрипт в `scripts/` настраивает хук в `.git/hooks` или через `core.hooksPath` | ✓ (Claude's Discretion) |
| Ручная настройка окружения | Хуки настраиваются локально разработчиком | |

**User's choice:** Автоматический воспроизводимый скрипт установки (Claude's Discretion).
**Notes:** Обеспечивает соблюдение SEC-03 в обоих репозиториях.

---

## 4. Изоляция тестов chat-app

| Option | Description | Selected |
|--------|-------------|----------|
| Pytest-фикстура временной БД с накаткой схемы | Тесты создают временную SQLite БД через `/opt/assistant-shared`, изоляция от `/opt/assistant-core` | ✓ (Claude's Discretion) |
| Тестирование на копии боевой БД через gate.py | Текущий подход, сохраняющий привязку к исходному файлу | |

**User's choice:** Изоляция через фикстуру временной БД (Claude's Discretion).
**Notes:** Полностью удовлетворяет требованию DAT-04.

---

## Claude's Discretion

Все 4 направления реализации были делегированы владельцем проекта на усмотрение инженера-разработчика (Claude). Решения приняты в соответствии с принципами KISS, YAGNI и проектными требованиями DAT-01..DAT-04, SEC-01..SEC-03.

## Deferred Ideas

Отсутствуют — все затронутые вопросы находятся в границах Фазы 4.
