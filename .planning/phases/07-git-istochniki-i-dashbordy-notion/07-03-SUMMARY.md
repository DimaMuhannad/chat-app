---
phase: 07-git-istochniki-i-dashbordy-notion
plan: 03
subsystem: notion-hitl
tags: [notion, hitl, git, confirmation-store, telegram, NTN-01, NTN-02]

requires:
  - phase: 07-02
    provides: "NDA Air-Gap для Git и санитизация полезной нагрузки"
provides:
  - "Метод log_project_activity в NotionAsyncClient для ведения логов активности"
  - "Сервисный класс GitProgressEvaluator в src/brain/git_evaluator.py"
  - "Регистрация обработчика действия notion_project_sync в assistant_shared.hitl"
  - "Генерация индивидуальных интерактивных карточек подтверждения в Telegram (D-07)"
  - "Набор интеграционных тестов tests/test_notion_git_hitl.py (5 тестов)"
affects: [07-04]

actuals:
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Строгий Human-in-the-Loop (HITL) шлюз перед любой записью в Notion"
    - "Гранулярное подтверждение: отдельная интерактивная карточка для каждого проекта"
    - "Идемпотентный resume_action с блокировкой повторного исполнения"

key-files:
  created:
    - /opt/assistant-core/src/brain/git_evaluator.py
    - /opt/assistant-core/tests/test_notion_git_hitl.py
  modified:
    - /opt/assistant-core/src/connectors/notion/client.py

key-decisions:
  - "Запись в Notion базы project_activity_logs выполняется исключительно после явного подтверждения владельца (NTN-02)"
  - "Для каждого проекта создается отдельный PendingConfirmation, давая владельцу гибкость выборочного аппрува (D-07)"
  - "Полезная нагрузка NDA-проектов проходит строгий фильтр sanitize_notion_payload_for_airgap перед созданием подтверждения"

requirements-completed: [NTN-01, NTN-02]

coverage:
  - id: NTN-01-LOGGER
    description: "Метод log_project_activity в NotionAsyncClient и структура свойств страницы Notion"
    requirement: "NTN-01"
    verification:
      - kind: integration
        ref: "/opt/assistant-core/tests/test_notion_git_hitl.py (5 passed)"
        status: pass
    human_judgment: false
  - id: NTN-02-HITL
    description: "HITL-подтверждение через Telegram и идемпотентное исполнение публикации"
    requirement: "NTN-02"
    verification:
      - kind: integration
        ref: "/opt/assistant-core/tests/test_notion_git_hitl.py (5 passed)"
        status: pass
    human_judgment: false
---

# Plan 07-03: Summary

Интеграция Notion Activity Logger и индивидуальный Telegram HITL-шлюз успешно реализованы и проверены сквозными интеграционными тестами.

## What Was Done

1. **NotionAsyncClient (`src/connectors/notion/client.py`):**
   - Реализован метод `log_project_activity(database_id, project_page_id, date_iso, commit_count, status, summary)`.
   - Запись создает страницу с реляцией к проекту Notion, датой, числовым счетчиком коммитов, селектом статуса и блоком текста с резюме.

2. **Оркестратор GitProgressEvaluator (`src/brain/git_evaluator.py`):**
   - `evaluate_workspaces()`: опрос репозиториев персоны, определение застоя (>7 дней), применение Air-Gap и расчет сводок.
   - `propose_notion_updates()`: создание индивидуальных объектов `PendingConfirmation` (action_type='notion_project_sync') со строгой фильтрацией NDA.
   - `format_telegram_card()`: формирование сообщений для Telegram в проектном стиле (эмодзи, без `#`) с кнопками `[✅ Опубликовать в Notion]` и `[❌ Отклонить]`.
   - Регистрация действия `notion_project_sync` в реестре `assistant_shared.hitl`.

3. **Интеграционное тестирование (`tests/test_notion_git_hitl.py`):**
   - Проверено создание отдельных карточек на каждый репозиторий (D-07).
   - Проверено исполнение `resume_action` при подтверждении (Notion вызывается ровно один раз).
   - Проверена идемпотентность (повторный клик отклоняется, повторные вызовы Notion заблокированы).
   - Проверено отклонение действия (Notion не вызывается).
   - Все 5 тестов пройдены успешно.
