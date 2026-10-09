---
phase: 07-git-istochniki-i-dashbordy-notion
plan: 02
subsystem: security-airgap
tags: [security, airgap, git, nda, prompts, jinja2, GIT-03, GIT-04]

requires:
  - phase: 07-01
    provides: "Порт BaseGitSourceProvider, доменные сущности GitCommit и провайдер SshGitProvider"
provides:
  - "Функции is_nda_workspace, sanitize_git_commits_for_llm и sanitize_notion_payload_for_airgap в src/security/airgap.py"
  - "Jinja2-шаблон промпта секретаря git_progress.jinja2 для оценки хода разработки"
  - "Сквозной тест-ловушка tests/test_git_airgap_trap.py со SpyGenAIClient (6 тестов)"
affects: [07-03, 07-04]

actuals:
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Строгий корпоративный Air-Gap для репозиториев restricted_nda"
    - "Перехватчик SpyGenAIClient для гарантированного обнаружения утечек токенов"
    - "Двухуровневая санитизация: маскирование для LLM и агрегация для Notion"

key-files:
  created:
    - /opt/assistant-core/src/persona/prompts/git_progress.jinja2
    - /opt/assistant-core/config/prompts/git_progress_default.jinja2
    - /opt/assistant-core/tests/test_git_airgap_trap.py
  modified:
    - /opt/assistant-core/src/security/airgap.py

key-decisions:
  - "Для пространств restricted_nda сообщения коммитов, имена файлов и диффы никогда не передаются в LLM (GIT-04)"
  - "Для Notion полезная нагрузка NDA содержит только число коммитов и даты без детализации (D-05)"
  - "Публичные репозитории анализируются моделью для формирования семантических резюме на русском языке (D-04)"

requirements-completed: [GIT-03, GIT-04]

coverage:
  - id: GIT-03-SUMMARY
    description: "Формирование семантической выжимки хода работ по Git-коммитам"
    requirement: "GIT-03"
    verification:
      - kind: unit
        ref: "/opt/assistant-core/tests/test_git_airgap_trap.py (6 passed)"
        status: pass
    human_judgment: false
  - id: GIT-04-AIRGAP
    description: "Полная изоляция NDA-коммитов и отсутствие секретов в LLM/Notion"
    requirement: "GIT-04"
    verification:
      - kind: unit
        ref: "/opt/assistant-core/tests/test_git_airgap_trap.py (6 passed)"
        status: pass
    human_judgment: false
---

# Plan 07-02: Summary

Корпоративный NDA Air-Gap для Git-коммитов и шаблон оценки прогресса секретарем успешно реализованы и верифицированы тестом-ловушкой `SpyGenAIClient`.

## What Was Done

1. **Air-Gap и санитизация Git (`src/security/airgap.py`):**
   - Реализована функция `is_nda_workspace()`, определяющая принадлежность пространства к `restricted_nda` по объекту `Workspace`, уровню допуска или идентификатору пространства в персоне.
   - Реализована функция `sanitize_git_commits_for_llm()`: для NDA-репозиториев заменяет сообщения на маркер `[NDA: сообщение коммита скрыто Air-Gap]` и обнуляет счетчики изменений файлов и строк.
   - Реализована функция `sanitize_notion_payload_for_airgap()`: удаляет детальные списки коммитов, веток, файлов и подставляет безопасную сводку с числом коммитов.

2. **Шаблон промпта секретаря (`git_progress.jinja2`):**
   - Создан шаблон в `src/persona/prompts/git_progress.jinja2` (и копия в `config/prompts/git_progress_default.jinja2`).
   - Поддерживает русский язык, деловой стиль, фиксацию застоя (>7 дней без коммитов) и явное ветвление для режима NDA Air-Gap.

3. **Сквозной тест-ловушка (`tests/test_git_airgap_trap.py`):**
   - Создан тест с перехватчиком `SpyGenAIClient`, подтверждающий отсутствие утечек NDA-токенов в исходящие промпты LLM.
   - Проверено корректное поведение для открытых репозиториев (сообщения коммитов сохраняются для семантического анализа).
   - Все 6 тестов пройдены успешно.
