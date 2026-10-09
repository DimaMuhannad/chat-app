---
phase: 05-edinyy-hitl-primitiv
plan: 01
subsystem: hitl
tags: [hitl, confirmation-store, migrations, assistant-shared, HIT-01]

requires:
  - phase: 04-01
    provides: "assistant_shared пакет и базовая DDL-схема SQLite"
provides:
  - "Миграция 0002_pending_confirmations.sql и индексы"
  - "Модели данных ConfirmationStatus, ConfirmationChannel, PendingConfirmation"
  - "Асинхронное хранилище ConfirmationStore над SQLite (get_async_connection WAL)"
  - "Движок resume_action и хелперы confirm_pending_action, reject_pending_action"
  - "Набор тестов backend/tests/test_hitl_shared.py (5 тестов)"
affects: [phase-05-02, phase-05-03, phase-05-04]

actuals:
  tokens: 18000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Централизованный примитив Human-in-the-Loop в assistant_shared.hitl"
    - "Атомарный переход статусов pending -> confirmed/rejected с проверкой прав"
    - "Автоматическая пометка expired по истечении TTL"
    - "Идемпотентный resume_action с предотвращением повторного исполнения"

key-files:
  created:
    - /opt/assistant-shared/assistant_shared/db/migrations/0002_pending_confirmations.sql
    - /opt/assistant-shared/assistant_shared/hitl/__init__.py
    - /opt/assistant-shared/assistant_shared/hitl/models.py
    - /opt/assistant-shared/assistant_shared/hitl/store.py
    - /opt/assistant-shared/assistant_shared/hitl/decorators.py
    - /opt/assistant-shared/assistant_shared/hitl/engine.py
    - /opt/chat-app/backend/tests/test_hitl_shared.py
  modified: []

key-decisions:
  - "Миграция 0002 создаёт таблицу pending_confirmations с индексами по persona_id, status, expires_at"
  - "ConfirmationStore использует safe get_async_connection с PRAGMA WAL и timeout"
  - "resume_action выполняет зарегистрированное действие ровно один раз, блокируя race conditions"
  - "Предоставлены тестовые хелперы confirm_pending_action для безопасного двухшагового тестирования"

requirements-completed: [HIT-01]

coverage:
  - id: HIT-01-STORE
    description: "ConfirmationStore, модели и миграция 0002 в assistant_shared.hitl"
    requirement: "HIT-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_hitl_shared.py (5 passed)"
        status: pass
    human_judgment: false
---

# Plan 05-01: Summary

Общий примитив Human-in-the-Loop (HITL) успешно реализован в модуле `assistant_shared.hitl` и покрыт модульными тестами.

## What Was Done

1. **Миграция 0002:** Создан файл `/opt/assistant-shared/assistant_shared/db/migrations/0002_pending_confirmations.sql` с таблицей `pending_confirmations` и индексами.
2. **Модели:** Создан модуль `assistant_shared.hitl.models` со статусами `ConfirmationStatus` (`pending`, `confirmed`, `rejected`, `expired`), каналами `ConfirmationChannel` (`web`, `telegram`) и моделью `PendingConfirmation`.
3. **Хранилище:** Реализован класс `ConfirmationStore` в `assistant_shared.hitl.store` с атомарными методами создания, подтверждения, отклонения и проверки срока действия (TTL).
4. **Движок выполнения:** Реализован `assistant_shared.hitl.engine` с реестром обработчиков, функцией `resume_action` и программными тестовыми хелперами `confirm_pending_action`, `reject_pending_action`.
5. **Тестирование:** Создан `backend/tests/test_hitl_shared.py`, 5 из 5 тестов успешно пройдены (`@pytest.mark.anyio`).
