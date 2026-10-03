---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Правило NDA в веб-аудите отключается молча при пустых данных пространства (fail-open)"
  - id: CR-02
    severity: critical
    disposition: open
    title: "Форма задачи затирает область (area) пустой строкой, если значения нет в списке персоны или персона не загрузилась"
  - id: WR-01
    severity: warning
    disposition: open
    title: "Хранимый XSS через неэкранируемые поля задач и напоминаний (pre-existing, но фаза экранировала только area)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "PersonaConfigError проглатывается общими `except Exception` (ошибка конфигурации превращается в тихую деградацию)"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Ошибки рендера Jinja2 не приводятся к PersonaConfigError, полнота персоны не проверяется при загрузке"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Параметры привязок коннекторов не валидируются; тихие искажения и сырые исключения"
  - id: WR-05
    severity: warning
    disposition: open
    title: "В контекст каждого шаблона попадает вся персона, включая правила NDA"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Пути file_catalog, raw_dir, kb_dir не проверяются; ключевые слова не нормализуются"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Сопоставление remote в веб-аудите NDA слабое (регистр, scp-форма) и не fail-closed при отсутствии origin"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Косметические обращения к привязке schedule_source падают для персон без неё"
  - id: WR-09
    severity: warning
    disposition: open
    title: "Загрузчик не оборачивает UnicodeDecodeError"
  - id: IN-01
    severity: info
    disposition: open
    title: "Идентификаторы Telegram персоны нигде не используются"
  - id: IN-02
    severity: info
    disposition: open
    title: "Дрейф копий тестовых файлов отслеживается не для всех общих файлов"
  - id: IN-03
    severity: info
    disposition: open
    title: "Мелкие отличия поведения для персоны по умолчанию"
  - id: IN-04
    severity: info
    disposition: open
    title: "Слова и правила NDA лежат открытым текстом в отслеживаемом git-файле и в общей БД"
  - id: IN-05
    severity: info
    disposition: open
    title: "Частичная миграция даёт несогласованные тексты для второй персоны"
  - id: IN-06
    severity: info
    disposition: open
    title: "Мелкие несогласованности слоя БД chat-app"
  - id: IN-07
    severity: info
    disposition: open
    title: "MethodistService всегда читает настройки персоны, даже если каталоги переданы явно"
open: 18
total: 18
recorded: 2026-10-03T07:10:45.984Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| CR-02 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| WR-09 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
