# Phase 05: Единый HITL-примитив — Summary Plan 05-02

**Execution Date:** 2026-10-04  
**Plan:** 05-02 (Волна 2)  
**Title:** Защита DELETE-эндпоинтов chat-app и эндпоинт статуса подтверждений  
**Status:** Completed  

---

## 1. Objectives & Scope
Интегрировать примитив `assistant_shared.hitl` в API `chat-app`:
1. Перевести эндпоинты DELETE (`projects`, `documents`, `tasks`, `reminders`) на обязательный шлюз подтверждения с возвратом HTTP `409 Conflict`.
2. Добавить роутер `/api/v1/confirmations` с методом `GET /{confirmation_id}` для отслеживания статуса запроса веб-интерфейсом.
3. Реализовать модуль `backend/app/hitl_handlers.py` с регистрацией фактических исполнителей деструктивных действий через `resume_action`.
4. Подтвердить соответствие полным набором интеграционных тестов `backend/tests/test_web_hitl_guardrails.py`.

---

## 2. Implemented Changes

### A. Роутер статусов подтверждений (`backend/app/api/v1/confirmations.py`)
- Добавлен эндпоинт `GET /api/v1/confirmations/{confirmation_id}`.
- Реализована защита от раскрытия приватного payload (threat model T-05-04): наружу отдаются только безопасные метаданные (`id`, `persona_id`, `action_type`, `target_id`, `status`, `channel`, `created_at`, `expires_at`, `confirmed_by`, `confirmed_at`).
- Отсутствуют прямые методы подтверждения через Web API (HIT-03, HIT-04: Web API не может подтверждать действия).
- Роутер подключен в `backend/app/api/v1/router.py`.

### B. Защита DELETE-эндпоинтов
- В `backend/app/api/v1/projects.py`, `documents.py`, `tasks.py`, `reminders.py`:
  - Проверка наличия сущности: если не найдена — немедленный `404 Not Found`.
  - Если найдена — создание записи `PendingConfirmation` в `ConfirmationStore` со статусом `pending`, каналом `web` и TTL 10 минут.
  - Генерация стандартизированного исключения `HTTPException(409 Conflict)` с телом ошибки `confirmation_required`.
  - Данные в SQLite остаются нетронутыми при первичном вызове.

### C. Движок фактического исполнения (`backend/app/hitl_handlers.py`)
- Зарегистрированы асинхронные обработчики для всех 4 типов действий:
  - `delete_project` -> `DatabaseService.delete_project`
  - `delete_document` -> `DatabaseService.delete_document`
  - `delete_task` -> `DatabaseService.delete_task`
  - `delete_reminder` -> `DatabaseService.delete_reminder`
- Модуль импортирован в `backend/app/main.py` для автоматической регистрации при старте приложения.

### D. Тестовое покрытие (`backend/tests/test_web_hitl_guardrails.py`)
- 8/8 тестов успешно пройдены:
  1. `test_delete_returns_409_for_all_entities`: 409 Conflict на всех 4 ресурсах, валидация полей ответа, проверка неизменности записей в SQLite и создания записи в `pending_confirmations`.
  2. `test_delete_non_existent_returns_404`: 404 Not Found на несуществующие ID без создания подтверждений.
  3. `test_get_confirmation_status_and_metadata`: изоляция payload (T-05-04), чтение статуса и 404 на отсутствующий ID.
  4. `test_web_api_cannot_confirm_directly`: запрет POST/PUT подтверждения через Web API.
  5. `test_two_step_execution_flow`: двухшаговый сценарий (DELETE -> 409 -> подтверждение `confirm_pending_action` -> физическое удаление из БД).
  6. `test_resume_action_idempotency_and_atomic_lock`: защита от повторного выполнения действия (ValueError).
  7. `test_expired_confirmation_blocks_deletion`: автоматический переход в `expired` и блокировка выполнения по истечении TTL.
  8. `test_reject_action_blocks_deletion`: отклонение (`reject`) сохраняет данные в БД и блокирует возобновление.

### E. Адаптация тестов регрессии
- `backend/tests/test_dashboard_api.py`: шаг удаления проекта переведен на двухшаговый протокол HITL (D-05).
- `backend/tests/test_migrations.py`: обновлены ожидания последней версии схемы до `0002_pending_confirmations`.

---

## 3. Verification & Quality Gates Status

| Проверка | Команда | Результат |
|---|---|---|
| Трассирующий тест задачи 05-02-01 | `pytest backend/tests/test_web_hitl_guardrails.py -k test_delete_returns_409` | **PASSED** (1 passed) |
| Полный набор тестов HITL chat-app | `pytest backend/tests/test_web_hitl_guardrails.py` | **PASSED** (8 passed in 2.59s) |
| Полный тестовый набор chat-app | `pytest backend/tests/` | **PASSED** (167 passed in 19.66s) |
| Тесты безопасности assistant-core | `pytest tests/test_hitl_safety_guardrails.py` | **PASSED** (3 passed in 41.53s) |

---

## 4. Decisions Realized
- **D-01, D-02:** Эндпоинты DELETE возвращают 409, клиент опрашивает `GET /confirmations/{id}`, подтверждение возможно только через авторизованный вызов.
- **D-03:** TTL 10 минут, истекшие запросы переводятся в `expired` и блокируются.
- **D-04, D-05:** Использован общий примитив `assistant_shared.hitl`, для тестов применен хелпер `confirm_pending_action`.

---

## 5. Next Steps
- Переход к **Плану 05-03 (Волна 3)**: интеграция единого примитива в Telegram-flow `assistant-core` (`bot_handler.py`, обработчики `hitl:confirm:<id>` и `hitl:reject:<id>`, сохранение UX 1:1 для `clear_dialog` и `submit_grade`).
