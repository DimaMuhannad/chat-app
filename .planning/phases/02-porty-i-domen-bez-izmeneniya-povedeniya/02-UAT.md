---
status: testing
phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
source: [02-VERIFICATION.md]
started: 2026-10-02T10:30:00Z
updated: 2026-10-02T10:30:00Z
---

## Current Test

number: 1
name: SC4 — трактовка «use-cases зависят только от портов и домена» (D-04)
expected: |
  Владелец принимает, что use-cases (IntentRouter, Methodist, SecretaryDialog) могут зависеть от
  src.storage.db.Database, src.models.* и src.config наравне с src.core, а перевод на доменные
  сущности откладывается на Фазу 3+. Буквальная трактовка — это новый объём работ.
awaiting: user response

## Tests

### 1. SC4 — трактовка «use-cases зависят только от портов и домена» (D-04)
expected: Use-cases могут зависеть от src.storage.db.Database, src.models.* и src.config наравне с src.core; перевод на доменные сущности — Фаза 3+.
result: [pending]

### 2. PRT-02/PRT-03 — допущения edge-probe (async-порты, декларативная пометка подтверждения)
expected: Sync-разбор ScheduleParser обёрнут async-адаптером; REQUIRES_CONFIRMATION = {submit_grade, delete_task} — константа плюс тест, исполняемый гейт @requires_confirmation в Фазе 5 (риск WR-02 принят, адаптер ЛК не подключён к боевым потокам); GuapLmsClient соответствует порту через адаптер.
result: [pending]

### 3. PRT-04 — допущения edge-probe (DI через необязательные параметры, путь Google Drive)
expected: «Через конструктор» = параметры X | None = None с ленивым дефолтом из src.composition; непрямой импорт через src.composition разрешён; путь синхронизации Google Drive по-прежнему сам создаёт AadhkIngestionService (WR-03) — приемлемо до появления второго провайдера табеля.
result: [pending]

### 4. PRT-05 — допущения edge-probe (EventBus)
expected: «Без брокера» = только stdlib и src.core; «без межпроцессной передачи» = словарь подписчиков в объекте шины; «доставляет» = подписчик получает тот же объект события; ограничения (точный тип, нет unsubscribe, нет таймаута, IN-02) приняты осознанно.
result: [pending]

### 5. Живой запуск бота и демона после снятия остановки сервиса
expected: После ручного перезапуска assistant-worker (failed с 2026-10-01, до фазы) команды /today, живая сводка, секретарь с вопросом о табеле и синхронизация табеля с Google Drive отвечают как раньше (/timesheet падает с NameError, как и до фазы — известный дефект в backlog).
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
