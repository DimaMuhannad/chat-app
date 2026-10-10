---
phase: quick-261010-ivt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/v1/security.py
  - scripts/security_shield.py
  - backend/tests/nda_helpers.py
  - backend/tests/test_web_nda_keywords.py
  - backend/tests/test_shield_delegator.py
  - backend/tests/test_nda_equivalence.py
  - backend/tests/test_security_shared.py
  - backend/tests/test_shield_regressions.py
  - backend/tests/test_shield_parity.py
  - backend/tests/test_persona_api.py
  - backend/tests/test_synthetic_persona.py
  - backend/tests/test_security_api.py
autonomous: true
requirements: [SECF-01, SECF-02]
---

# Quick 261010-ivt: shield rules from workspace data, web audit checks NDA keywords

Источник: `/opt/assistant-core/.planning/phases/02-bezopasnost-privatnost-i-nahodki-revyu/02-CHATAPP-QUICK-BRIEF.md`
(план 02-07 assistant-core, решения D-12, D-18, D-21). Правку chat-app допускает только эта малая задача.

## Задачи

1. `backend/app/api/v1/security.py`: один раз на запрос `collect_protected_keywords(workspaces)` по всем пространствам
   персоны, `forbidden_keywords=protected` в оба вызова `audit_path` (через `asyncio.to_thread`).
2. `scripts/security_shield.py`: тонкий делегатор к обёртке assistant-core (`ASSISTANT_CORE_DIR`, иначе
   `/opt/assistant-core`), аргументы и код возврата пробрасываются, fail-closed (rc 1, «SECURITY SHIELD ERROR»);
   без импорта общей библиотеки и без констант слов NDA.
3. Тесты потребителя: перевод на данные пространств (`workspaces=`, слова из `forbidden_keywords`), общий модуль
   `nda_helpers.py`, новые `test_web_nda_keywords.py` и `test_shield_delegator.py` (заменяет P03).
4. Решение владельца (вариант A): `test_security_audit_all` идёт по синтетическим каталогам; живое дерево проверяет
   отдельный тест с замороженным набором из трёх находок (новая находка краснит, допусков нет, D-21).

## Ограничения

`scripts/gate.py` не менять (D-15); без skip/xfail/deselected; число тестов не уменьшается; слова NDA и литералы
аккаунта в тексты не вставлять; `chat-app.service` не перезапускать; живую БД не открывать.

## Проверка

- полный `backend/tests` зелёный против настоящей библиотеки;
- против копии `shared-final` падают только тесты, запускающие обёртку assistant-core;
- `grep -c assistant_shared scripts/security_shield.py` равно 0; `git diff --stat` без `scripts/gate.py`.
