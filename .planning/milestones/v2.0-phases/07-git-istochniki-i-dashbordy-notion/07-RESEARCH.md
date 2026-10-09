# Phase 07: Git-источники и дашборды Notion - Research

**Phase Target:** Секретарь по коммитам из любого числа git-репозиториев (различные хосты, аккаунты, доступ по SSH) оценивает ход проектов и — после индивидуального подтверждения владельцем в Telegram через HITL-примитив — обновляет дашборды проектов в Notion. Данные `restricted_nda` не передаются в LLM (в Notion уходят только обезличенные агрегаты).
**Requirements Covered:** `GIT-01`, `GIT-02`, `GIT-03`, `GIT-04`, `NTN-01`, `NTN-02`.
**Decisions Covered:** `D-01`, `D-02`, `D-03`, `D-04`, `D-05`, `D-06`, `D-07`.

---

## 1. Executive Summary & Architectural Overview

Phase 07 расширяет универсальную платформу ассистента возможностью непрерывного аудита хода разработки и проектной активности из внешних распределенных Git-репозиториев с автоматической синхронизацией в Notion Second Brain.

Ключевые архитектурные задачи фазы:
1. **Порт Git-источников и SSH-транспорт (GIT-01, GIT-02, D-01, D-02):**
   - Декларация структурного протокола `BaseGitSourceProvider(BaseConnector, Protocol)` с ролью `ConnectorRole.GIT_SOURCE` и разрешением `required_scopes = ("git.read",)`.
   - Запрет на любые операции записи (push, create branch, tag) на уровне контракта и реализации.
   - Реализация `SshGitProvider` на базе системного `git`: чтение коммитов из каталогов рабочих пространств (`workspace.path`), выполнение неблокирующего `git fetch` по SSH с таймаутом (20-30 с) при наличии `ssh_alias`.
   - Учет конфигурации рабочих пространств: любое число репозиториев на разных хостах (GitHub, GitLab, self-hosted) с разными SSH alias и аккаунтами без правки кода. Приватные ключи остаются на хосте в `~/.ssh/config`.
   - Graceful degradation: мягкий пропуск недоступных хостов или отсутствующих каталогов с фиксацией статуса ошибки, не прерывающий работу демона.

2. **Аналитика прогресса секретарем и NDA Air-Gap (GIT-03, GIT-04, D-03, D-04, D-05):**
   - Сбор коммитов с момента последней успешной синхронизации с Notion (с дефолтным окном 7 дней при первом запуске).
   - Для репозиториев уровней допуска `public` и `internal`: генерация семантической выжимки на русском языке (выполненные задачи, статистика коммитов, предупреждение о застое > 7 дней) через Jinja2-шаблон промпта секретаря.
   - Для репозиториев `restricted_nda`: строгий Air-Gap (через `src/security/airgap.py`). Сообщения коммитов, имена файлов, авторы и диффы полностью исключены из передачи во внешнюю LLM. В Notion передаются исключительно обезличенные числовые агрегаты (число коммитов и даты).

3. **Связка с Notion и сохранение логов активности (NTN-01, D-06):**
   - Расширение существующего клиента `NotionAsyncClient` методом создания записей в базе данных логов активности проектов (`project_activity_logs`).
   - Связывание рабочего пространства с проектом Notion через свойство `notion_project` в данных персоны (`WorkspaceConfig`).

4. **Индивидуальный HITL-шлюз в Telegram (NTN-02, D-07):**
   - Интеграция с единым HITL-примитивом платформы (`assistant_shared.hitl`).
   - Формирование отложенных подтверждений `PendingConfirmation` с типом действия `notion_project_sync`.
   - Отправка в Telegram владельца отдельных интерактивных карточек с inline-кнопками («Подтвердить» / «Отклонить») по каждому проекту индивидуально.
   - Идемпотентность: повторный запуск анализа не создает дублирующих записей; отклонение запроса не затрагивает Notion.

---

## 2. Architectural Responsibility Map

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  PHASE 07 ARCHITECTURE                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. DOMAIN & PORTS (assistant-core: src/core/)                                          │
│ - src/core/domain/entities.py                                                          │
│   • GitRepository(id, workspace_id, path, remote, ssh_alias, clearance, notion_project)   │
│   • GitCommit(hash, author, date, message, files_changed, insertions, deletions)          │
│   • GitProgressReport(repo_id, period_start, period_end, commit_count, summary, ...)       │
│ - src/core/ports/connectors.py                                                         │
│   • BaseGitSourceProvider(BaseConnector, Protocol) [git.read]                         │
│   • BaseNotionProvider(BaseConnector, Protocol) [notion.read, notion.write]            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. CONNECTORS & AIR-GAP (assistant-core: src/connectors/, src/security/)               │
│ - src/connectors/git/provider.py (SshGitProvider: git log / git fetch via asyncio)     │
│ - src/connectors/notion/client.py (append log_project_activity method)                 │
│ - src/security/airgap.py (filter_nda_git_activity: strip messages, files, diffs)     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. PERSONA & COMPOSITION (assistant-core: src/persona/, src/)                          │
│ - src/persona/models.py (WorkspaceConfig: ssh_alias, notion_project, git_host)         │
│ - src/persona/prompts/git_progress.jinja2 (prompt template for secretary evaluation)   │
│ - src/composition.py (bind BaseGitSourceProvider with required_scopes validation)      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. USE CASE & HITL ORCHESTRATION (assistant-core: src/brain/, assistant_shared.hitl)  │
│ - src/brain/git_evaluator.py (GitProgressEvaluator: collect, evaluate, airgap, report) │
│ - assistant_shared.hitl (register_action_handler for "notion_project_sync")            │
│ - src/notifier/telegram_notifier.py (send interactive project confirmation cards)      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. VERIFICATION & QUALITY GATES (assistant-core: tests/)                               │
│ - tests/test_git_connector.py (SSH / offline / timeout / read-only conformance)        │
│ - tests/test_git_airgap_trap.py (SpyGenAIClient trap: 0 NDA commit strings in LLM)     │
│ - tests/test_notion_git_hitl.py (HITL action lifecycle, idempotency, per-project cards) │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. User Constraints & Implementation Decisions (from CONTEXT.md)

| ID | Constraint | Description | Reversibility |
|---|---|---|---|
| **D-01** | Local repo reading + SSH fetch | Чтение коммитов из `workspace.path`, при наличии SSH alias — неблокирующий `git fetch` по SSH с таймаутом (20–30 с). Scope строго `git.read`. | costly |
| **D-02** | Graceful degradation | Недоступность SSH или отсутствие каталога не роняют демон, фиксируется статус ошибки (`offline`/`unreachable`). | reversible |
| **D-03** | Adaptive commit window | Сбор коммитов с момента последней успешной синхронизации (дефолт 7 дней при первом запуске). | reversible |
| **D-04** | Russian semantic summary | Для `public`/`internal` репозиториев — семантическая выжимка на русском, статистика и флаг застоя (> 7 дней). | reversible |
| **D-05** | Strict NDA Air-Gap | Для `restricted_nda` сообщения коммитов, имена файлов и диффы блокируются от передачи в LLM; в Notion передаются только число коммитов и даты. | one-way |
| **D-06** | Dedicated activity log DB | Сохранение отчета в Notion в виде новой записи в связанной базе данных логов активности проектов (`project_activity_logs`). | costly |
| **D-07** | Per-project Telegram cards | Индивидуальные интерактивные сообщения в Telegram с кнопками («Подтвердить» / «Отклонить») по каждому проекту отдельно. | reversible |

---

## 4. Technical Specifications & Interface Designs

### 4.1. Domain Entities (`src/core/domain/entities.py`)

```python
@dataclass(frozen=True, slots=True)
class GitCommit:
    """Неизменяемое представление коммита."""
    hash: str
    author: str
    date: datetime
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


@dataclass(frozen=True, slots=True)
class GitProgressReport:
    """Оценка хода работ по проекту."""
    workspace_id: str
    notion_project_id: str | None
    period_start: datetime
    period_end: datetime
    commit_count: int
    latest_commit_date: datetime | None
    summary_text: str
    is_stagnant: bool
    clearance: WorkspaceClearance
```

### 4.2. Port Definition (`src/core/ports/connectors.py`)

```python
@runtime_checkable
class BaseGitSourceProvider(BaseConnector, Protocol):
    """Порт источника данных Git (только чтение)."""

    role: ClassVar[ConnectorRole] = ConnectorRole.GIT_SOURCE
    required_scopes: ClassVar[tuple[str, ...]] = ("git.read",)

    async def list_repositories(self) -> list[Workspace]:
        """Возвращает список рабочих пространств с настроенным git."""
        ...

    async def fetch_remote(self, workspace: Workspace, timeout_sec: float = 30.0) -> bool:
        """Неблокирующий git fetch с таймаутом. Возвращает False при сбое связи."""
        ...

    async def get_commits_since(
        self,
        workspace: Workspace,
        since: datetime | None = None,
        max_commits: int = 100,
    ) -> list[GitCommit]:
        """Чтение коммитов из локального репозитория."""
        ...
```

### 4.3. Notion Activity Logger (`src/connectors/notion/client.py`)

Метод добавления записи активности:
```python
async def log_project_activity(
    self,
    database_id: str,
    project_page_id: str,
    date_iso: str,
    commit_count: int,
    status: str,
    summary: str,
) -> dict[str, Any]:
    """Создает запись в базе данных логов активности проектов Notion."""
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": f"Сводка {date_iso}"}}]},
            "Project": {"relation": [{"id": project_page_id}]},
            "Date": {"date": {"start": date_iso}},
            "Commits": {"number": commit_count},
            "Status": {"select": {"name": status}},
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary[:2000]}}]
                }
            }
        ]
    }
    async with self._client() as client:
        resp = await client.post("/pages", json=payload)
        resp.raise_for_status()
        return resp.json()
```

---

## 5. Security Threat Model & Failure Modes

| Threat ID | Threat Type | Component | Description | Mitigation Strategy |
|-----------|-------------|-----------|-------------|---------------------|
| **T-07-01** | Information Disclosure | GitEvaluator | Утечка сообщений коммитов или имен файлов закрытых NDA-репозиториев во внешнюю LLM | `filter_nda_git_activity` в `src/security/airgap.py` полностью отсекает `message` и имена файлов для `clearance == restricted_nda` перед вызовом LLM; тест `SpyGenAIClient` подтверждает 0 NDA-строк |
| **T-07-02** | Unauthorized Modification | SshGitProvider | Попытка изменения репозитория через push/commit | Порт не содержит методов записи; системные вызовы ограничены командами `git log` и `git fetch`; проверка прав `git.read` |
| **T-07-03** | Denial of Service | SshGitProvider | Зависание демона при недоступности SSH-хоста или медленном канале | Вызов `asyncio.wait_for(..., timeout=30.0)` на каждом SSH-вызове; мягкий перехват `TimeoutError` и `subprocess.SubprocessError` |
| **T-07-04** | State Corruption / Replay | HITL Action Handler | Повторная отправка отчета при повторном клике кнопки или перезапуске демона | Идемпотентность по ключу `confirmation_id`; статус `action_executed` в таблице `pending_confirmations`; дедупликация по дате в Notion |

---

## 6. Validation Architecture & Quality Gate Strategy

1. **Модульные тесты коннектора Git (`tests/test_git_connector.py`):**
   - Соответствие `SshGitProvider` протоколам `BaseConnector` и `BaseGitSourceProvider`.
   - Проверка парсинга `git log` (хэш, автор, дата, тело, статистика вставок/удалений).
   - Обработка таймаута SSH fetch (`asyncio.TimeoutError`) и отсутствующей директории репозитория (`D-02`).

2. **Тест NDA Air-Gap ловушки (`tests/test_git_airgap_trap.py`):**
   - Инстанцирование синтетической персоны с NDA-репозиторием.
   - Использование `SpyGenAIClient` для перехвата всех промптов.
   - Строгий assert отсутствия текста коммитов, имен файлов и веток репозитория `restricted_nda` в отправленных промптах (`GIT-04`).
   - Проверка полезной нагрузки, отправляемой в Notion: payload содержит только `commit_count` и `date`.

3. **Интеграционный тест HITL и Notion (`tests/test_notion_git_hitl.py`):**
   - Полный жизненный цикл: генерация отчета -> создание `PendingConfirmation` -> отправка индивидуальной карточки в Telegram -> подтверждение владельцем -> вызов `log_project_activity` в мок-клиенте Notion.
   - Проверка отклонения: при отклонении Notion не вызывается, статус переходит в `rejected`.

4. **Общий Quality Gate (`scripts/gate.py`):**
   - 100% прохождение pytest в обоих репозиториях.
   - `import-linter` (use-cases не импортируют конкретный `SshGitProvider`).
   - `security_shield (--all)` чист.
