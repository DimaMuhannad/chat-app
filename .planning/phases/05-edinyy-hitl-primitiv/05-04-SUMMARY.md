# Phase 05: Единый HITL-примитив — Summary Plan 05-04

**Execution Date:** 2026-10-04  
**Plan:** 05-04 (Волна 4)  
**Title:** Web UI поллинг статуса, обновление CRUD-тестов и сквозной гейт gate.py  
**Status:** Completed  

---

## 1. Objectives & Scope
Завершающая волна Фазы 05 («Единый HITL-примитив»):
1. Обновить клиентскую логику удаления в веб-интерфейсе `chat-app` (`backend/app/static/index.html`): перехват HTTP 409 Conflict, информационное всплывающее уведомление (toast) об ожидании подтверждения в Telegram, клиентский поллинг `GET /api/v1/confirmations/{id}` каждые 2 секунды (таймаут 60 сек), скрытие/удаление элемента из DOM строго после перехода статуса в `confirmed`.
2. Зафиксировать тест контракта клиентского поллинга `test_ui_polling_contract` в `backend/tests/test_web_hitl_guardrails.py`.
3. Запустить сквозной локальный гейт качества `python3 scripts/gate.py` и подтвердить 100% зелёный статус всех проверок обоих репозиториев (`chat-app` и `assistant-core`).

---

## 2. Implemented Changes

### A. Клиентский Web UI (`backend/app/static/index.html`)
- Реализован контейнер тостов `#toast-container` и функция `showToast(message, type, duration)` с поддержкой типов `'warning'` / `'hitl'`, `'success'`, `'error'`.
- Реализована функция `pollConfirmation(confirmationId, onSuccess, onError, maxDurationMs, intervalMs)`:
  - Опрашивает `GET /api/v1/confirmations/{confirmationId}` каждые 2 секунды.
  - При `status === 'confirmed'` вызывает `onSuccess` и удаляет элемент/обновляет интерфейс.
  - При `status === 'rejected'` или `'expired'` / `timeout` выводит предупреждение и сохраняет элемент в DOM.
- Обновлены обработчики удаления `deleteTask`, `deleteReminder`, `deleteProject`, `deleteDocument`:
  - При получении `409 Conflict` элемент не удаляется оптимистично (защита от ложного «удалено» per HIT-04, T-05-07).
  - Выводится toast: «⚠️ Запрос на удаление отправлен в Telegram. Ожидание подтверждения...».
  - Запускается фоновый поллинг статуса подтверждения.

### B. Контрактный тест клиентского поллинга (`backend/tests/test_web_hitl_guardrails.py`)
- Добавлен тест `test_ui_polling_contract`:
  - Проверяет двухшаговый цикл (DELETE -> 409 -> опрос в состоянии `pending` -> подтверждение владельцем -> опрос в состоянии `confirmed`).
  - Проверяет наличие в `index.html` функций `pollConfirmation`, `showToast`, перехвата статуса 409 и предупреждающего текста.

### C. Верификация сквозного гейта качества (`scripts/gate.py`)
- Запущен скрипт `python3 scripts/gate.py`:
  - `chat-app pytest`: 168 passed (✓)
  - `chat-app import-linter`: ✓
  - `assistant-core pytest`: 336 passed (✓)
  - `assistant-core import-linter`: ✓
  - `chat-app security_shield (--all)`: ✓
  - `assistant-core security_shield (--all)`: ✓
  - Синтетическая персона (дрейф SHA-256): ✓
  - Токены персоны (дрейф SHA-256): ✓
  - Боевая `assistant.db` не изменена: ✓
  - **ИТОГ: ЗЕЛЁНЫЙ**

---

## 3. Verification & Quality Gates Status

| Проверка | Команда | Результат |
|---|---|---|
| Трассирующий тест задачи 05-04-01 | `pytest backend/tests/test_web_hitl_guardrails.py -k test_ui_polling_contract -q` | **PASSED** (1 passed) |
| Все тесты HITL guardrails | `pytest backend/tests/test_web_hitl_guardrails.py -q` | **PASSED** (9 passed in 2.43s) |
| Все тесты бэкенда chat-app | `pytest backend/tests/ -q` | **PASSED** (168 passed in 38.49s) |
| Сквозной гейт качества платформы | `python3 scripts/gate.py` | **ИТОГ: ЗЕЛЁНЫЙ** (100%) |

---

## 4. Decisions Realized
- **D-02:** Клиентский поллинг каждые 2 сек с таймаутом 60 сек, отсутствие ложного "удалено".
- **D-05:** Двухшаговый протокол удаления во всех CRUD-тестах.

---

## 5. Phase 05 Completion
Все 4 плана Фазы 05 («Единый HITL-примитив») полностью выполнены:
- 05-01 (Волна 1): Общий примитив `assistant_shared.hitl`, модели, `ConfirmationStore`, миграция `0002`.
- 05-02 (Волна 2): Защита DELETE-эндпоинтов `chat-app` (409 Conflict), роутер `GET /confirmations/{id}`, движок `resume_action`.
- 05-03 (Волна 3): Telegram bot карточка подтверждения, callback-хэндлеры `hitl:confirm` / `hitl:reject`, паритет 1:1 `clear_dialog`.
- 05-04 (Волна 4): Клиентский поллинг в Web UI, тест контракта поллинга, 100% зелёный статус сквозного гейта `scripts/gate.py`.
