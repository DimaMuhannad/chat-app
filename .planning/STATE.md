---
gsd_state_version: '1.0'
status: planning
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-01)

**Core value:** Профиль владельца целиком живёт в данных, а платформа работает для любой персоны — без регрессии поведения и без ослабления HITL и air-gap NDA.
**Current focus:** Phase 0 — Страховочная сеть и каркас

## Current Position

Phase: 0 of 6 (всего 7 фаз: 0–6) — Страховочная сеть и каркас
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-10-01 — Создан roadmap: 7 фаз, 42 требования v1, покрытие 42/42

Progress: [░░░░░░░░░░] 0%

## Состояние окружения: ЗАМОРОЖЕН (с 2026-10-01)

Проект заморожен намеренно. Проверено 2026-10-01 командами только для чтения:

| Сервис | Состояние | Автозапуск |
|--------|-----------|------------|
| assistant-worker | failed (вероятно, SIGKILL при остановке; не проверялось) | disabled |
| chat-app | inactive | disabled |
| dev-bridge | inactive | disabled |

- Процессов uvicorn и демона нет. Фаза 0 стартует из этого состояния.
- Разморозка — явное решение владельца; ни одна фаза не включает сервисы автоматически.
- `/usr/local/bin/systemctl` подделывает успех `stop`/`restart` для dev-bridge (OPS-01): состояние проверять через `systemctl is-active`.
- Baseline тестов НЕ снят: прогон chat-app пишет в боевую `assistant.db`; снимается в Фазе 0 на копии БД.
- Репозитории: `/opt/chat-app` (ветка master, здесь `.planning/`), `/opt/assistant-core` (ветка main).

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Полный журнал — в PROJECT.md (`<decisions>` и Key Decisions). Кратко:

- [Владелец W2/W6]: 4 рабочих пространства по умолчанию; пути — данные, репозитории не переносятся.
- [Владелец W5/W9]: одна общая БД с владельцем схемы, WAL, без шины и двойной записи; одна security-библиотека + pre-commit hook.
- [Владелец W1/W7/W8]: Фаза 6 — git по SSH и Notion через HITL; роли расписания разделены.
- [Владелец W10]: снимок промптов — пререквизит Фазы 2.
- [Roadmapper, ждёт подтверждения]: Phase 6 после Phase 5; «CI» = локальный гейт; HITL на все DELETE chat-app.

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 0] Состояние тестов на старте неизвестно; возможны красные тесты, которые нужно устранить без ослабления ассертов.
- [Phase 2] Открыт вопрос: где живёт загрузчик персоны до появления общей библиотеки (Фаза 3).
- [Phase 3] Открыт вопрос: физическое расположение общей библиотеки; артефакты в корне assistant-core (пустой `assistant.db`, каталог `sqlite+aiosqlite:`).
- [Phase 4] Канал подтверждения Web-действий при API без аутентификации (OPS-05) — решить в discuss-phase 4.
- [Phase 6] Можно ли писать в Notion агрегаты по NDA-репозиториям (по умолчанию нет).
- [Перед разморозкой chat-app] API без аутентификации и CORS `*` (v2: AUTH2-01/02) — решение владельца.
- [Операционное] Ключ в юните dev-bridge (OPS-02) — владелец не ротирует; assistant-worker уходит в SIGKILL (OPS-03); `notion_dev.py` в chat-app с битым импортом (OPS-04, вне миграции).

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| v2 | AUTH2-01/02 аутентификация и CORS; UI2-01/02; NTN2-01; PLT2-01 | Deferred | 2026-10-01 | v1 |

## Session Continuity

Last session: 2026-10-01
Stopped at: Roadmap и STATE созданы; следующий шаг — `/gsd-plan-phase 0`
Resume file: None
