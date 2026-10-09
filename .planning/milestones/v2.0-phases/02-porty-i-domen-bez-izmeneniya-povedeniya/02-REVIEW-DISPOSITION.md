---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "`list_tasks` порождает `submission_id == \"None\"` для заданий без разобранного id"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Деструктивные операции ЛК в адаптере выполняются без гейта; `REQUIRES_CONFIRMATION` только декларативна"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Внедрённый `timesheet_service` обходится на пути синхронизации Google Drive"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Смешение naive и aware datetime в доменной модели"
  - id: IN-01
    severity: info
    disposition: open
    title: "`health_check` у адаптеров практически тавтологичен"
  - id: IN-02
    severity: info
    disposition: open
    title: "EventBus — последовательный await без таймаута, нет отписки; docstring про «без содержимого» неточен"
  - id: IN-03
    severity: info
    disposition: open
    title: "Тернарная логика «внедрённый или по умолчанию» продублирована трижды"
  - id: IN-04
    severity: info
    disposition: open
    title: "Хрупкие места в тестах"
  - id: IN-05
    severity: info
    disposition: open
    title: "Адаптер ЛК: `submit_grade` не поддерживается; общий `requests.Session` в нескольких потоках"
  - id: IN-06
    severity: info
    disposition: open
    title: "Заморожено/дорелизное, не относится к diff (справочно)"
open: 10
total: 10
recorded: 2026-10-02T10:12:13.675Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
