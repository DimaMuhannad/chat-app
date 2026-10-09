# Phase 05: Единый HITL-примитив - Context

**Gathered:** 2026-10-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Фаза 5 внедряет единый шлюз подтверждения Human-in-the-Loop (HITL) для любых деструктивных и критических действий платформы в Web и Telegram.
Прямой HTTP DELETE на ресурсы (`projects`, `documents`, `tasks`, `reminders`) больше не удаляет данные в обход шлюза — он возвращает статус `409 Conflict` и создает запрос в таблице `pending_confirmations`. Авторизованным каналом подтверждения деструктивных действий Web является Telegram владельца (проверка `allowed_user_id`). Telegram UX существующих подтверждений сохраняется 1:1.

</domain>

<decisions>
## Implementation Decisions

### 1. Формат и обработка карточки подтверждения в Telegram (Web -> Telegram)
- **D-01:** Для Web-действий владельцу в Telegram отправляется лаконичная карточка с инлайн-кнопками:
  ```text
  ⚠️ Запрос на удаление из Web-интерфейса
  Сущность: [Задача / Проект / Документ / Напоминание]
  Название: «...»
  ID: #<id>
  [🗑 Да, удалить] [❌ Отклонить]
  ```
  Callback-данные используют префикс `hitl:confirm:<id>` и `hitl:reject:<id>`. Проверка прав осуществляется строго по `allowed_user_id` персоны владельца. — **Reversibility:** costly — изменение формата callback затронет bot_handler и диспетчер.

### 2. Синхронизация и обратная связь в Web UI
- **D-02:** Клиентский поллинг (KISS). При получении `409 Conflict` с `{confirmation_id, status: "pending"}` веб-интерфейс отображает уведомление/статус «Ожидает подтверждения в Telegram» и опрашивает `GET /api/v1/confirmations/{id}` с интервалом 2 секунды (таймаут ожидания 60 секунд). При смене статуса на `confirmed` интерфейс удаляет элемент из DOM. Браузер подтверждать действие не может (защита от неавторизованного Web API). — **Reversibility:** reversible — локальная логика интерфейса.

### 3. Политика времени жизни (TTL) и истечение запроса
- **D-03:** Время жизни запроса на подтверждение `TTL = 10 минут`. По истечении времени статус автоматически считается `expired`. Нажатие устаревшей инлайн-кнопки в Telegram возвращает alert пользователю: *«Срок действия запроса истек»*, данные не удаляются. — **Reversibility:** reversible.

### 4. Архитектура общего примитива в assistant_shared.hitl
- **D-04:** Примитив размещается в пакете `assistant_shared.hitl` (установленном в обоих `.venv`):
  - Модель данных `PendingConfirmation` (id, persona_id, action_type, payload_json, status, created_at, expires_at, confirmed_by, confirmed_at).
  - Схема таблицы `pending_confirmations` добавляется миграцией DDL SQLite.
  - Асинхронное хранилище `ConfirmationStore` для создания, поиска, подтверждения и отмены запросов.
  - Декоратор `@requires_confirmation` для FastAPI/хэндлеров и точка возобновления `resume_action` (гарантия idempotency: действие выполняется строго один раз). — **Reversibility:** costly — общее ядро для обоих сервисов.

### 5. Механизм двухшагового тестирования для pytest
- **D-05:** Библиотека `assistant_shared.hitl` предоставляет программный интерфейс для подтверждения (`confirm_pending_action(confirmation_id, user_id)`), позволяющий тестовым фикстурам эмулировать успешное подтверждение владельца без поднятия polling-бота Telegram. Все существующие CRUD-тесты chat-app переводятся на двухшаговый поток (DELETE -> 409 -> подтверждение -> 200/удалено). — **Reversibility:** reversible.

### 6. Сохранение Telegram UX 1:1
- **D-06:** Существующие сценарии в Telegram (`dlg:confirm_clear` и выставление оценок `submit_grade`) переводятся под управление `PendingConfirmation` без изменения текстов сообщений, кнопок и callback_data. Тесты `test_hitl_safety_guardrails.py` и `test_bot_group_isolation.py` должны проходить со 100% успехом без правки ассертов. — **Reversibility:** costly — затрагивает стабильность Telegram-бота.

### Claude's Discretion
- Точный формат хранения полезной нагрузки (JSON payload) в `pending_confirmations`.
- Вспомогательные SQL-индексы таблицы `pending_confirmations` (`persona_id`, `status`, `expires_at`).
- Внутренняя реализация сопоставления типов сущностей для локализации текста на русском языке.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §HIT-01 — HIT-04 — формальные требования к единому HITL.
- `.planning/ROADMAP.md` §Phase 5 — цели, критерии успеха (DoD) и риски фазы.

### Code & Tests
- `/opt/assistant-core/src/notifier/bot_handler.py` — текущая логика подтверждения в Telegram (`confirm_clear`, `submit_grade`).
- `/opt/assistant-core/tests/test_hitl_safety_guardrails.py` — эталонные тесты безопасности HITL.
- `/opt/chat-app/backend/app/api/v1/{projects,documents,tasks,reminders}.py` — эндпоинты DELETE, подлежащие защите.
- `/opt/chat-app/backend/app/shared/` / `assistant_shared` — общая библиотека для размещения `assistant_shared.hitl`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `assistant_shared`: готовый общий пакет, уже подключенный в `.venv` обоих проектов.
- `aiosqlite` фабрика подключений с WAL (`assistant_shared.db` / `src/database/`): безопасный доступ к таблице подтверждений.
- `bot_handler.py`: готовые паттерны формирования `InlineKeyboardMarkup` с кнопками подтверждения.

### Established Patterns
- Декораторы маршрутизации FastAPI.
- Изолированные тестовые БД (`tmp_path`) при прогоне тестов для защиты боевой базы.

### Integration Points
- `chat-app/backend/app/api/v1/`: перехват DELETE и роутер `/api/v1/confirmations`.
- `chat-app/backend/app/static/`: UI обработка 409 Conflict и поллинг статуса.
- `assistant-core/src/notifier/bot_handler.py`: отправка карточек подтверждения Web-действий в Telegram и обработка кнопок.

</code_context>

<specifics>
## Specific Ideas
- Запрос подтверждения из Web должен однозначно идентифицировать сущность, чтобы владелец в Telegram понимал, что именно удаляется, не открывая веб-интерфейс.

</specifics>

<deferred>
## Deferred Ideas
- Мгновенное пуш-уведомление в Web через WebSocket при подтверждении в Telegram (отложено для снижения связности; поллинга каждые 2 сек достаточно).
- Пакетное подтверждение множественных действий (запланировано в Фазе 7 для обновлений Notion).

</deferred>

---

*Phase: 05-edinyy-hitl-primitiv*
*Context gathered: 2026-10-04*
