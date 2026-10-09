# Phase 7: Git-источники и дашборды Notion - Context

**Gathered:** 2026-10-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Секретарь по коммитам из любого числа git-репозиториев (различные хосты, аккаунты, доступ по SSH) оценивает ход проектов и — после индивидуального подтверждения владельцем в Telegram через HITL-примитив — обновляет дашборды проектов в Notion.
Строгий NDA Air-Gap гарантирует, что данные репозиториев уровня `restricted_nda` (сообщения коммитов, диффы, файлы) не передаются в LLM, а в Notion уходят исключительно обезличенные агрегаты (число коммитов и даты).

В рамках фазы:
- Порт `BaseGitSourceProvider` (async, read-only) и реализация SSH Git коннектора (`git.read`).
- Подключение репозиториев через конфигурацию персоны (`git: host, account, ssh_alias, remote`).
- Анализ активности и прогресса секретарем (сводка, статистика, выявление застоя).
- Связка с проектами Notion через существующий `src/connectors/notion`.
- HITL-шлюз отправки отчетов в Notion с индивидуальными интерактивными карточками в Telegram.

Вне рамок фазы:
- Запись в git-репозитории (push, создание веток, коммиты).
- Изменение прав доступа или приватных ключей на сервере (ключи живут вне платформы).
- Автоматическая разморозка сервисов (решение владельца).
</domain>

<decisions>
## Implementation Decisions

### 1. Транспорт и синхронизация Git по SSH
- **D-01:** Чтение коммитов осуществляется из локальных каталогов рабочих пространств (`workspace.path`), а при наличии сконфигурированного SSH alias выполняется неблокирующий `git fetch` по SSH с таймаутом (20-30 с). Scope коннектора строго `git.read`, любые push/write-операции заблокированы на уровне контракта порта. — **Reversibility:** costly — интерфейс BaseGitSourceProvider используется секретарем и коннекторами.
- **D-02:** Обработка сбоев SSH-подключения или отсутствия директории репозитория: мягкий пропуск (graceful degrade) с фиксацией статуса ошибки (`offline` / `unreachable`) в объекте состояния. Демон и обработка остальных репозиториев не прерываются. — **Reversibility:** reversible.

### 2. Аналитика коммитов и оценка прогресса
- **D-03:** Временной диапазон выборки коммитов: анализ ведется с даты последней успешной синхронизации с Notion (с окном по умолчанию в 7 дней для первой синхронизации или при отсутствии сохраненной даты). — **Reversibility:** reversible.
- **D-04:** Формат резюме для `public` и `internal` репозиториев: семантическая сводка на русском языке с ключевыми изменениями, статистикой коммитов/активности и флагом предупреждения о застое (stagnation warning, если нет активности > 7 дней). — **Reversibility:** reversible.
- **D-05:** Строгий Air-Gap для `restricted_nda` (per W8, GIT-04, ISO-02): содержимое коммитов (сообщения, диффы, списки файлов) полностью исключено из передачи во внешнюю LLM через `WorkspaceScope`. В Notion для NDA-репозиториев передаются только обезличенные числовые агрегаты (число коммитов, дата последнего коммита, статус активности). — **Reversibility:** one-way — жесткое требование безопасности и корпоративного комплаенса.

### 3. Структура дашборда и сохранение в Notion
- **D-06:** Отчет о прогрессе проекта сохраняется в виде новой записи в связанной базе данных истории/логов активности проекта Notion (`project_activity_logs`) со ссылкой на проект, датой, числом коммитов, статусом и сгенерированным резюме. — **Reversibility:** costly — определяет структуру Notion-коннектора и формат DTO.

### 4. HITL-шлюз подтверждения в Telegram
- **D-07:** Подтверждение на отправку данных в Notion реализуется через отдельные интерактивные сообщения с кнопками «Подтвердить» / «Отклонить» для каждого проекта индивидуально (per решение владельца в discuss-phase), что обеспечивает гранулярный контроль над публикацией в Notion без единой пакетной свалки. — **Reversibility:** reversible.

### Claude's Discretion
- Конкретные имена полей в моделях данных `GitCommit` и `GitProgressReport`.
- Механизм тайм-аутов `asyncio.wait_for` при выполнении подпроцессов git.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Требования и архитектура проекта
- `.planning/REQUIREMENTS.md` §Фаза 7 (GIT-01..04, NTN-01..02)
- `.planning/ROADMAP.md` §Phase 7: Git-источники и дашборды Notion
- `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` §Раздел 4 (Секретарь и внешние источники)

### Существующие контракты и модули
- `/opt/assistant-core/src/core/ports/connectors.py` — базовые порты коннекторов
- `/opt/assistant-core/src/core/domain/entities.py` — доменные сущности и WorkspaceClearance
- `/opt/assistant-core/src/connectors/notion/client.py` — существующий клиент Notion API
- `/opt/assistant-core/src/security/workspace_scope.py` — изоляция NDA Air-Gap (ISO-02)
- `/opt/assistant-core/src/persona/models.py` — модели конфигурации персоны
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/connectors/notion`: готовый клиент работы с Notion API через `httpx`.
- `src/core/ports/confirmation.py` и `src/storage/hitl.py`: HITL-примитив подтверждения Фазы 5 (`@requires_confirmation`, `pending_confirmations`).
- `src/security/workspace_scope.py`: контекстный менеджер и декоратор проверки уровня допуска `WorkspaceClearance` (public / internal / restricted_nda).
- `src/persona/bindings.py`: привязки коннекторов к активной персоне.

### Established Patterns
- Async-first для всех портов коннекторов (`BaseConnector`, `BaseGitSourceProvider`).
- Конструкторная инъекция зависимостей в Use Cases (`SecretaryDialogEngine`).
- Fail-closed валидация Pydantic-моделей конфигурации персоны.
</code_context>

<specifics>
## Specific Ideas
- Индивидуальные интерактивные карточки подтверждения в Telegram для каждого проекта, дающие возможность выборочной публикации обновлений.
</specifics>

<deferred>
## Deferred Ideas
- **UI2-02**: Git Registry визуальный виджет в веб-интерфейсе Antigravity Studio (отложено в v2).
</deferred>

---

*Phase: 07-git-istochniki-i-dashbordy-notion*
*Context gathered: 2026-10-04*
