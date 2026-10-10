---
phase: quick-261010-cgx
plan: 01
status: complete
requirements: []
commit: 27886b3
---

# Quick 261010-cgx Summary: cross-AI adapter protects gate environment, labels fallback gate, refuses symlinked gate path

Адаптер `scripts/agy_cross_ai.sh` защищает окружение гейта цели, честно называет вид выбранного гейта и отказывает
кодом 17 при символической ссылке на `scripts` или `scripts/gate.py`. Источник: бриф 02-CHATAPP-CROSSAI-QUICK-BRIEF.md
плана 02-09 assistant-core (D-17).

## Что сделано

- WR-05: в `PROTECTED` добавлены `tests/conftest.py`, `tests/live_db_guard.py`, `pytest.ini`, `pyproject.toml`,
  `scripts/deploy.py`, `src/config.py`, `requirements.txt`, `requirements-dev.txt` (11 записей стало 19, прежние сохранены).
  `is_protected` дополнительно защищает пути, равные каталогу-предку защищённого файла (`scripts`, `tests`, `src`).
- T-uo4-02: код 17, если `scripts` или `scripts/gate.py` цели - символическая ссылка и `AGY_GATE_CMD` не задан. Проверка
  до запуска агента и повторно перед гейтом (после применения патча; патч откатывается).
- WR-06: `GATE_KIND` (`test`, `target`, `adapter-fallback`); для `adapter-fallback` stderr и SUMMARY содержат
  «ВНИМАНИЕ: у целевого репозитория нет собственного гейта; выполнен гейт chat-app, цель им НЕ проверена».
- `SKILL.md`: защищённые пути, три вида гейта, строка 17 в таблице кодов.
- `test_security_shared.py::test_normalize_remote_formats`: личный аккаунт заменён на `ExampleOrg` и хост на `git.example.org`
  (5 вхождений, значения читались из данных персоны при правке; покрытие форматов https, ssh://, scp, http с хвостовым `/` прежнее).

## Тесты

- Тесты адаптера: 18 до, 34 после (+16: 8 путей окружения, ссылка `scripts` в патче, 17 до агента x2, 17 при заданном
  `AGY_GATE_CMD` не применяется, 17 с откатом перед гейтом, 3 теста вида гейта).
- Новые тесты на старом адаптере падают (15 из 16 новых; тест игнорирования ссылки при `AGY_GATE_CMD` проходит и там по
  определению). Без повторной проверки перед гейтом падает именно тест отката.
- Полный `backend/tests`: 277 passed. Общий гейт chat-app: «ИТОГ: ЗЕЛЁНЫЙ».
- `PROTECTED` нового состояния - надмножество прежнего (проверено разбором кортежа по `git show HEAD:`).

## Отклонения

Нет. `scripts/gate.py` не менялся, `chat-app.service` не перезапускался, агент не запускался.
