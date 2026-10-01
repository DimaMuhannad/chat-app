# Phase 1: Страховочная сеть и каркас - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-01
**Phase:** 1-Страховочная сеть и каркас
**Areas discussed:** Гейт и документ baseline; Установка import-linter; Вторая синтетическая персона; Красные тесты на старте (все — по усмотрению Claude)

---

## Выбор областей для обсуждения

| Option | Description | Selected |
|--------|-------------|----------|
| Гейт и документ baseline | Где живёт скрипт-гейт и документ baseline, формат итога, защита боевой assistant.db | |
| Установка import-linter | Куда добавить зависимость, где конфиг, как доказать падение на нарушении | |
| Вторая синтетическая персона | Форма заглушки, идентифицирующие поля, копии в двух репозиториях, что ждёт Фазы 3 | |
| Красные тесты на старте | Что считать «устранено без ослабления», когда выносить владельцу, изоляция assistant-core | |

**User's choice:** «Я не специалист продумай сам» — все четыре области делегированы Claude.
**Notes:** Владелец не выбирал варианты. Claude принял решения по KISS/YAGNI (D-01..D-19 в CONTEXT.md) с опорой на разведку: `import-linter` не установлен, но доступен на PyPI; в chat-app `.venv` нет PyYAML (поэтому заглушка персоны — Python-`dict`); `SQLITE_DB_PATH` и `DATABASE_URL` переопределяются окружением без правки кода; `bot_handler.py` лежит в `src/notifier/`, поэтому включён в источники контракта.

---

## Claude's Discretion

- Гейт и baseline: один stdlib-скрипт `scripts/gate.py`, `docs/BASELINE.md`, SHA-256 боевой БД до/после.
- import-linter: `requirements-dev.txt`, `.importlinter`, постоянный тест «падает на нарушении».
- Синтетическая персона: Python-`dict` + фикстура, без YAML и без предвосхищения схемы Фазы 3.
- Красные тесты: три корзины (окружение / устаревший тест / ошибка продакшен-кода); третья выносится владельцу.

## Deferred Ideas

- pre-commit hook (Фаза 4), временная БД из общей схемы (Фаза 4), общая библиотека вместо дублей (Фаза 4), тест-сканер хардкода (Фазы 3 и 6).
