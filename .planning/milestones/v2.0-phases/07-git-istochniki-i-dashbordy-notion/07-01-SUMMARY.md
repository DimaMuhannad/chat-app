---
phase: 07-git-istochniki-i-dashbordy-notion
plan: 01
subsystem: git-connector
tags: [git, ssh, connectors, ports, domain, GIT-01, GIT-02]

requires:
  - phase: 02-01
    provides: "Базовые порты и доменная модель"
provides:
  - "Доменные сущности GitCommit и GitProgressReport (frozen slots dataclass)"
  - "Порт BaseGitSourceProvider с ролью GIT_SOURCE и областью видимости git.read"
  - "Расширение WorkspaceConfig полями ssh_alias, notion_project, git_host"
  - "Провайдер SshGitProvider с чтением истории git log и неблокирующим SSH fetch с таймаутом 30с"
  - "Набор модульных тестов tests/test_git_connector.py (13 тестов)"
affects: [07-02, 07-03, 07-04]

actuals:
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Строго read-only контракт для Git-источников (отсутствие методов push/commit)"
    - "Неблокирующий subprocess runner с защитой от зависания через asyncio.wait_for"
    - "Парсинг вывода git log через ASCII separator 0x1f и регулярные выражения shortstat"

key-files:
  created:
    - /opt/assistant-core/src/connectors/git/__init__.py
    - /opt/assistant-core/src/connectors/git/provider.py
    - /opt/assistant-core/tests/test_git_connector.py
  modified:
    - /opt/assistant-core/src/core/domain/entities.py
    - /opt/assistant-core/src/core/ports/connectors.py
    - /opt/assistant-core/src/persona/models.py

key-decisions:
  - "SshGitProvider реализует BaseGitSourceProvider и объявляет scope git.read (D-01)"
  - "Операции записи запрещены на уровне интерфейса и проверяются автотестами"
  - "Таймаут операций fetch составляет 30 секунд с безопасной обработкой сбоев сети (D-02)"
  - "SSH-ключи не сохраняются в коде/конфигурациях; провайдер полагается на системные алиасы ssh_alias"

requirements-completed: [GIT-01, GIT-02]

coverage:
  - id: GIT-01-PORT
    description: "Порт BaseGitSourceProvider и провайдер SshGitProvider без методов записи"
    requirement: "GIT-01"
    verification:
      - kind: unit
        ref: "/opt/assistant-core/tests/test_git_connector.py (13 passed)"
        status: pass
    human_judgment: false
  - id: GIT-02-SSH
    description: "Чтение репозиториев через ssh_alias и таймаут сетевых операций fetch"
    requirement: "GIT-02"
    verification:
      - kind: unit
        ref: "/opt/assistant-core/tests/test_git_connector.py (13 passed)"
        status: pass
    human_judgment: false
---

# Plan 07-01: Summary

Порт Git-источников `BaseGitSourceProvider`, доменные сущности `GitCommit`, `GitProgressReport` и асинхронный провайдер `SshGitProvider` успешно реализованы и протестированы.

## What Was Done

1. **Доменные сущности и порты:**
   - В `/opt/assistant-core/src/core/domain/entities.py` добавлены `GitCommit` и `GitProgressReport` (неизменяемые датаклассы со `slots=True`, `frozen=True`).
   - В `Workspace` добавлены атрибуты `ssh_alias` и `notion_project`.
   - В `/opt/assistant-core/src/core/ports/connectors.py` объявлен протокол `BaseGitSourceProvider` с ролью `ConnectorRole.GIT_SOURCE` и областью `required_scopes = ("git.read",)`.
   - В `/opt/assistant-core/src/persona/models.py` модель `WorkspaceConfig` дополнена полями `ssh_alias`, `notion_project`, `git_host`.

2. **Провайдер SshGitProvider:**
   - В `/opt/assistant-core/src/connectors/git/provider.py` реализован асинхронный адаптер:
     * `health_check()`: проверка наличия `git`.
     * `list_repositories()`: фильтрация рабочих пространств с репозиториями.
     * `fetch_remote()`: асинхронный запуск `git fetch --all --prune` с таймаутом `asyncio.wait_for` (30 с) и перехватом ошибок.
     * `get_commits_since()`: разбор `git log --format=... --shortstat` с парсингом хешей, дат, авторов и счетчиков изменений.

3. **Тестирование:**
   - Создан `tests/test_git_connector.py` с 13 модульными тестами, проверяющими соответствие протоколу, иммутабельность, отсутствие методов записи, парсинг логов, изоляцию сбоев сети и таймаутов.
   - Все 366 тестов `assistant-core` пройдены успешно (100% pass rate).
