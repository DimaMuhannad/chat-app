# Phase 05: Единый HITL-примитив - Research

**Date:** 2026-10-04  
**Status:** Completed  
**Domain:** Human-in-the-Loop (HITL), Telegram Bot confirmation flow, FastAPI 409 Conflict guardrails, SQLite versioned migration, safe action resumption, two-step CRUD testing.

---

<user_constraints>
## User Constraints & Implementation Decisions (from 05-CONTEXT.md)

Владелец проекта утвердил рекомендуемые параметры реализации (варианты 1А, 2А, 3А, 4А):

### 1. Формат и обработка карточки подтверждения в Telegram (D-01)
- Для Web-действий владельцу в Telegram отправляется лаконичная карточка с инлайн-кнопками:
  ```text
  ⚠️ Запрос на удаление из Web-интерфейса
  Сущность: [Задача / Проект / Документ / Напоминание]
  Название: «...»
  ID: #<id>
  [🗑 Да, удалить] [❌ Отклонить]
  ```
- Callback-данные используют префикс `hitl:confirm:<id>` и `hitl:reject:<id>`.
- Авторизованный канал подтверждения — строго Telegram владельца (проверка `allowed_user_id` персоны). Браузер подтверждать действие не может (защита от неавторизованного Web API).

### 2. Синхронизация и обратная связь в Web UI (D-02)
- Клиентский поллинг (KISS). При получении `409 Conflict` с `{confirmation_id, status: "pending"}` веб-интерфейс отображает уведомление/статус «Ожидает подтверждения в Telegram» и опрашивает `GET /api/v1/confirmations/{id}` каждые 2 секунды (таймаут 60 сек).
- При получении статуса `confirmed` элемент удаляется из DOM.

### 3. Политика времени жизни (TTL) и истечение запроса (D-03)
- Время жизни запроса на подтверждение `TTL = 10 минут`. По истечении времени статус автоматически считается `expired`.
- Нажатие устаревшей инлайн-кнопки в Telegram возвращает alert пользователю: *«Срок действия запроса истек»*, данные не удаляются.

### 4. Архитектура общего примитива в assistant_shared.hitl (D-04)
- Примитив размещается в пакете `assistant_shared.hitl`:
  • Модель `PendingConfirmation` (id, persona_id, action_type, target_id, payload, status, channel, created_at, expires_at, confirmed_by, confirmed_at);
  • Схема таблицы `pending_confirmations` добавляется миграцией DDL `0002_pending_confirmations.sql`;
  • Асинхронное хранилище `ConfirmationStore` (создание, получение, подтверждение, отклонение, очистка истекших);
  • Декоратор `@requires_confirmation` для FastAPI/хэндлеров и точка возобновления `resume_action` (гарантия idempotency: действие выполняется ровно один раз).

### 5. Двухшаговое тестирование для pytest (D-05)
- Библиотека `assistant_shared.hitl` предоставляет программный интерфейс `confirm_pending_action(confirmation_id, user_id)`, позволяющий тестам эмулировать подтверждение владельца без запуска polling-бота Telegram.
- Существующие CRUD-тесты `chat-app` переводятся на двухшаговый поток (DELETE -> 409 -> confirm -> 200/deleted) без ослабления проверок.

### 6. Сохранение Telegram UX 1:1 (D-06)
- Существующие сценарии в Telegram (`dlg:confirm_clear` и выставление оценок `submit_grade`) переводятся под управление `PendingConfirmation` без изменения текстов сообщений, кнопок и callback_data.
- Тесты `test_hitl_safety_guardrails.py` и `test_bot_group_isolation.py` должны проходить со 100% успехом без изменения ассертов.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

- **HIT-01** [chat-app + assistant-core]: Порт `ConfirmationStore`, `PendingConfirmation`, декоратор `@requires_confirmation` и единая точка `resume_action` в общей библиотеке; таблица `pending_confirmations` добавлена миграцией.
- **HIT-02** [assistant-core]: Telegram-flow (`clear_dialog`, выставление оценок `submit_grade`, прочие деструктивные действия) переведён на примитив без изменения UX; `test_hitl_safety_guardrails.py` и `test_bot_group_isolation.py` проходят без изменения ассертов.
- **HIT-03** [chat-app]: Все DELETE-эндпоинты chat-app (`projects`, `documents`, `tasks`, `reminders`) используют примитив: запрос без подтверждения возвращает 409 и создаёт запись в `pending_confirmations`, данные не удаляются; владельцу уходит карточка «Да / Отмена» в Telegram (проверка `allowed_user_id`), подтвердить или отклонить можно ТОЛЬКО оттуда (решение владельца 2026-10-01). Web API подтверждать не может; допустим лишь `GET /api/v1/confirmations/{id}` для показа статуса «ожидает подтверждения». Новый `test_web_hitl_guardrails.py`; существующие CRUD-тесты переведены на двухшаговый поток без ослабления силы проверки.
- **HIT-04** [chat-app + assistant-core]: Подтверждение приходит из авторизованного канала (Telegram владельца либо токен подтверждения, выданный интерфейсом; точный канал фиксируется в discuss-phase 5): анонимный HTTP-запрос не может подтвердить собственный DELETE. Веб-интерфейс показывает состояние «ожидает подтверждения» вместо ложного «удалено».
</phase_requirements>

---

## Technical Analysis & Existing Code Seams

### 1. Пакет assistant_shared и миграции SQLite
- В репозитории `/opt/assistant-shared` уже настроен модуль миграций `assistant_shared.db.migrator` и фабрика `connection.py` с поддержкой WAL и busy_timeout.
- Добавляется миграция `0002_pending_confirmations.sql`:
  ```sql
  CREATE TABLE IF NOT EXISTS pending_confirmations (
      id TEXT PRIMARY KEY,
      persona_id TEXT NOT NULL,
      action_type TEXT NOT NULL,
      target_id TEXT,
      payload TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      channel TEXT NOT NULL DEFAULT 'web',
      created_at TEXT NOT NULL,
      expires_at TEXT NOT NULL,
      confirmed_by TEXT,
      confirmed_at TEXT
  );
  CREATE INDEX IF NOT EXISTS idx_pending_confirmations_persona ON pending_confirmations(persona_id);
  CREATE INDEX IF NOT EXISTS idx_pending_confirmations_status ON pending_confirmations(status);
  CREATE INDEX IF NOT EXISTS idx_pending_confirmations_expires ON pending_confirmations(expires_at);
  ```

### 2. Пакет assistant_shared.hitl
- Модели данных:
  - `ConfirmationStatus`: enum (`pending`, `confirmed`, `rejected`, `expired`).
  - `PendingConfirmation`: Pydantic/dataclass с сериализацией payload в JSON.
- Хранилище `ConfirmationStore`:
  - `create_confirmation(persona_id, action_type, target_id, payload, channel, ttl_minutes=10)`
  - `get_confirmation(confirmation_id)`
  - `confirm_action(confirmation_id, user_id)`
  - `reject_action(confirmation_id, user_id)`
- Декоратор и реестр обработчиков:
  - `register_action_handler(action_type, handler)`
  - `@requires_confirmation(action_type)`
  - `resume_action(confirmation_id, user_id)`

### 3. Эндпоинты chat-app (HIT-03, HIT-04)
- Эндпоинты в `backend/app/api/v1/`:
  - `projects.py` (`DELETE /{project_id}`)
  - `documents.py` (`DELETE /{doc_id}`)
  - `tasks.py` (`DELETE /{task_id}`)
  - `reminders.py` (`DELETE /{reminder_id}`)
- Новый роутер: `backend/app/api/v1/confirmations.py`:
  - `GET /api/v1/confirmations/{confirmation_id}` -> `{id, status, action_type, target_id, expires_at}`

### 4. Интеграция с Telegram-ботом в assistant-core (HIT-02)
- В `src/notifier/bot_handler.py`:
  - Добавляются хэндлеры для `hitl:confirm:<id>` и `hitl:reject:<id>`.
  - Существующие вызовы `dlg:confirm_clear` используют `ConfirmationStore` для сохранения контекста подтверждения, при этом callback-данные и тексты в Telegram остаются абсолютно неизменными.
  - Тесты `test_hitl_safety_guardrails.py` и `test_bot_group_isolation.py` остаются зелеными без правки ассертов.

---

## Validation Architecture

### Verification Strategy & Test Suites

1. **Unit-тесты общего примитива (`test_hitl_shared.py`):**
   - Создание, получение, подтверждение и отмена запросов.
   - Проверка истечения срока действия (TTL) и блокировка подтверждения после `expired`.
   - Идемпотентность: повторный вызов `confirm_action` возвращает уже подтвержденный статус и не выполняет действие повторно.

2. **Интеграционные тесты Web Guardrails (`test_web_hitl_guardrails.py`):**
   - Вызов `DELETE /api/v1/projects/{id}`, `documents/{id}`, `tasks/{id}`, `reminders/{id}` возвращает HTTP 409 с `confirmation_id`.
   - Данные остаются в базе данных (проверка `SELECT`).
   - `GET /api/v1/confirmations/{id}` возвращает `status: "pending"`.
   - После вызова `confirm_pending_action(confirmation_id, owner_id)` статус меняется на `confirmed`, а данные удаляются.
   - Попытка подтверждения от чужого/анонимного пользователя отклоняется.

3. **Тесты обратной совместимости Telegram (`test_bot_hitl_parity.py`):**
   - Прогон `test_hitl_safety_guardrails.py` и `test_bot_group_isolation.py`.
   - Проверка карточки подтверждения для Web-действия в Telegram.

4. **Двухшаговые CRUD-тесты chat-app:**
   - Обновление существующих тестов удаления в `backend/tests/` для поддержки двухшагового протокола (DELETE -> 409 -> подтверждение).
   - Сквозной локальный гейт качества `scripts/gate.py` (ИТОГ: ЗЕЛЁНЫЙ).
