# Phase 05: Единый HITL-примитив — Summary Plan 05-03

**Execution Date:** 2026-10-04  
**Plan:** 05-03 (Волна 3)  
**Title:** Интеграция с Telegram Bot в assistant-core и паритет UX  
**Status:** Completed  
**Assistant-Core Commit:** `2ee891a`

---

## 1. Objectives & Scope
Интегрировать примитив `assistant_shared.hitl` в Telegram-бот `assistant-core`:
1. Реализовать отправку карточки подтверждения для Web-действий владельцу в Telegram (`send_web_hitl_card`).
2. Зарегистрировать callback-хэндлеры `hitl:confirm:<id>` и `hitl:reject:<id>` с обязательной проверкой `_is_authorized()`, вызовом `resume_action` и редактированием сообщений.
3. Перевести существующий флоу очистки диалога (`dlg:confirm_clear` / `dlg:cancel_clear`) под управление `ConfirmationStore` с сохранением 1:1 Telegram UX.
4. Обеспечить 100% прохождение существующих эталонных тестов безопасности бота без изменения ассертов.

---

## 2. Implemented Changes

### A. Telegram-карточка подтверждения Web-действий (`src/notifier/bot_handler.py`)
- Реализован метод `send_web_hitl_card(confirmation_id, chat_id)`:
  - Форматирует лаконичную карточку с эмодзи:
    ```text
    ⚠️ Запрос на удаление из Web-интерфейса

    Сущность: [Задача / Проект / Документ / Напоминание]
    Название: «...»
    ID: #...

    Подтверждаете удаление?
    ```
  - Прикрепляет инлайн-кнопки `[🗑 Да, удалить]` (`hitl:confirm:<id>`) и `[❌ Отклонить]` (`hitl:reject:<id>`).

### B. Обработчики callback-запросов (`cb_hitl_confirm`, `cb_hitl_reject`)
- Строгая проверка авторизации `_is_authorized(callback.from_user.id)` (threat model T-05-05: посторонние пользователи получают alert «⛔ Доступ запрещен», данные не удаляются).
- Проверка TTL: устаревшие запросы со статусом `expired` блокируются с алертом «Срок действия запроса истек».
- Исполнение через `resume_action(conf_id, store, confirmed_by=...)` с редактированием карточки на статус «🗑 Элемент успешно удален(а)».
- Отклонение через `store.reject_action(...)` с редактированием на «❌ Удаление отклонено. Элемент сохранен в базе данных».

### C. Паритет UX и фиксация в ConfirmationStore (D-06)
- В `cb_dlg_confirm_clear` и `cb_dlg_cancel_clear`:
  - Запрос фиксируется в `ConfirmationStore` (action_type: `clear_dialog`, channel: `telegram`).
  - Тексты сообщений, кнопки восстановления (`dlg:undo_clear`) и логика работы с историей диалога сохранены 1:1.

### D. Реестр обработчиков деструктивных действий
- Метод `_register_hitl_action_handlers()` регистрирует обработчики `delete_project`, `delete_document`, `delete_task`, `delete_reminder`, привязанные к экземпляру `Database`.

### E. Тестовое покрытие (`tests/test_bot_hitl_parity.py`)
- 6/6 тестов успешно пройдены:
  1. `test_send_web_hitl_card`: валидация текста карточки, кнопок и callback_data.
  2. `test_cb_hitl_confirm_authorized`: успешное подтверждение владельцем, удаление из SQLite, статус `confirmed`.
  3. `test_cb_hitl_confirm_unauthorized`: отказ постороннему пользователю, сохранение данных в SQLite, статус `pending`.
  4. `test_cb_hitl_reject`: отклонение, сохранение записи в SQLite, статус `rejected`.
  5. `test_cb_hitl_confirm_expired`: блокировка устаревшего запроса при истечении TTL.
  6. `test_dlg_clear_registers_in_confirmation_store`: запись `clear_dialog` в `ConfirmationStore` и сохранение UX 1:1.

---

## 3. Verification & Quality Gates Status

| Проверка | Команда | Результат |
|---|---|---|
| Новые тесты HITL Telegram бота | `pytest tests/test_bot_hitl_parity.py -v` | **PASSED** (6 passed in 15.66s) |
| Эталонные тесты безопасности HITL | `pytest tests/test_hitl_safety_guardrails.py -q` | **PASSED** (3 passed in 10.25s) |
| Тесты изоляции групп и каналов | `pytest tests/test_bot_group_isolation.py -q` | **PASSED** (3 passed in 9.42s) |
| Все эталонные тесты assistant-core | `pytest tests/test_hitl_safety_guardrails.py tests/test_bot_group_isolation.py -q` | **PASSED** (6 passed in 21.61s) |

---

## 4. Decisions Realized
- **D-01:** Инлайн-карточка Telegram с кнопками `hitl:confirm:<id>` и `hitl:reject:<id>`, проверка `allowed_user_id`.
- **D-03:** Блокировка истекших запросов по TTL.
- **D-04, D-06:** Сохранение 1:1 поведения `dlg:confirm_clear` с фиксацией в `ConfirmationStore`.

---

## 5. Next Steps
- Переход к **Плану 05-04 (Волна 4)**: обновление клиентского Web UI (`backend/app/static/index.html`) для поллинга статуса подтверждений, адаптация CRUD-тестов и запуск сквозного гейта качества `scripts/gate.py`.
