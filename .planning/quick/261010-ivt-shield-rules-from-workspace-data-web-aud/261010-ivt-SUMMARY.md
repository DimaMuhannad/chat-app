---
phase: quick-261010-ivt
plan: 01
status: complete
requirements: [SECF-01, SECF-02]
commit: 568ecf2
---

# Quick 261010-ivt Summary: shield rules from workspace data, web audit checks NDA keywords

Web-аудит (`/security/overview`, `/security/audit`) ищет слова NDA всех пространств в каталогах НЕ-NDA пространств;
`scripts/security_shield.py` стал fail-closed делегатором к обёртке assistant-core; тесты потребителя читают правила
и слова из данных пространств. Источник: бриф 02-CHATAPP-QUICK-BRIEF.md плана 02-07 assistant-core (D-12, D-18, D-21).

## Что сделано

- `backend/app/api/v1/security.py`: `collect_protected_keywords(workspaces)` один раз на запрос по ВСЕМ пространствам,
  `forbidden_keywords=` в оба вызова `audit_path` (через `asyncio.to_thread`); ключи ответа и тексты ошибок прежние.
- `scripts/security_shield.py`: запуск `<ASSISTANT_CORE_DIR|/opt/assistant-core>/.venv/bin/python` с обёрткой
  assistant-core, проброс аргументов и кода возврата; нет каталога, обёртки или интерпретатора - rc 1 и
  «SECURITY SHIELD ERROR». Импортов общей библиотеки и констант слов нет.
- Тесты: `nda_helpers.py` (общие хелперы), `test_web_nda_keywords.py` (3), `test_shield_delegator.py` (7, заменяет P03),
  перевод `test_nda_equivalence`, `test_security_shared`, `test_shield_regressions`, `test_shield_parity`,
  `test_persona_api`, `test_synthetic_persona` на данные пространств.
- Число тестов: 251 до, 261 после (+10).

## Отклонения

**1. [Решение владельца, вариант A] `test_security_audit_all`.** После правки web-аудит живого дерева находит слова NDA
в трёх отслеживаемых файлах публичных каталогов (`chat-app/.planning/milestones/v2.0-phases/04-.../04-REVIEW.md`,
`chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md`, `assistant-core/config/persona.yaml`); тест ждал `passed`.
Основной тест переведён на синтетические каталоги (4 пространства, `audited_count == 4`), живое дерево проверяет
`test_security_audit_all_live_tree_has_only_frozen_findings` с замороженным набором из этих трёх файлов: новая
находка краснит, допусков нет (D-21).

**2. Общий гейт chat-app красный не из-за этой правки.** Шаг `security_shield (--all)` сообщает «новая находка»
`04-REVIEW.md [nda-keyword] ×2`: файла нет в замороженном списке `scripts/gate.py` (там только blueprint ×3 и
`persona.yaml` ×3), а менять гейт нельзя (D-15). Прежняя обёртка chat-app байт-в-байт равна обёртке assistant-core
(sha256 совпадает), и она даёт ту же находку на HEAD до правки: красный был до задачи. Остальные строки гейта зелёные.
Решение (убрать слова из архивного отчёта либо дополнить замороженный список гейта) - за владельцем.

**3. Нестабильный `test_concurrent_write_two_processes`** один раз упал в прогоне гейта и три раза подряд проходил
отдельно; полные прогоны pytest зелёные (гонка двух процессов под нагрузкой, не связана с правкой).

## Проверка

- pytest против настоящей библиотеки: `261 passed`.
- pytest против копии итогового состояния библиотеки: `8 failed, 253 passed`; падают только тесты, запускающие обёртку
  assistant-core: 5 тестов `test_pre_commit_hook.py`, `test_cr02_flag_first_is_not_treated_as_path`,
  `test_delegator_end_to_end_blocks_secret_and_passes_clean`, `test_delegator_unknown_flag_exits_with_two`.
- `grep -c assistant_shared scripts/security_shield.py` = 0; `scripts/gate.py` не менялся.
- `chat-app.service` не перезапускался.
