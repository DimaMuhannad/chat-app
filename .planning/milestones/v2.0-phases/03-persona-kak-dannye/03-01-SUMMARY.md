---
phase: 03-persona-kak-dannye
plan: 01
subsystem: testing
tags: [prompts, characterization, snapshot, pytest, gemini-fake, jinja2-prerequisite]

requires:
  - phase: 02-yadro-bez-profilya
    provides: гейт качества (234 теста assistant-core после Фазы 2), правило «характеризация до правки src»
provides:
  - побайтовые эталоны 8 системных промптов D-08 плюс полный текст вызова дебрифа в tests/fixtures/prompts_snapshot/
  - MANIFEST.json (символы, байты, SHA-256, источник, вид захвата, входные данные вызова)
  - tests/test_prompt_snapshot.py: 11 тестов, снимающих текст по месту вызова LLM через фейковый клиент
affects: [03-07, 03-08, 03-10]

actuals:
  tokens: 8497
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Характеризация по месту вызова: фейк Gemini запоминает system_instruction/contents, тест не импортирует константы промптов"
    - "Эталоны только в tests/fixtures/ (каталог data/ игнорируется git), отслеживание проверяет git ls-files --error-unmatch"
    - "Автоматический запрет реального genai.Client в тестах снимка (autouse-фикстура)"

key-files:
  created:
    - /opt/assistant-core/tests/test_prompt_snapshot.py
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/MANIFEST.json
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/secretary.txt
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/intent_router.txt
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/methodist.txt
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/methodist_scope_check.txt
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/reply_generator.txt
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/debrief.txt
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/debrief_call.txt
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/morning_brief.txt
    - /opt/assistant-core/tests/fixtures/prompts_snapshot/evening_digest.txt
  modified: []

key-decisions:
  - "Тест секретаря и методиста используют раздельные фейки: методист внутри answer_user_message тоже ходит в LLM, и без своего фейка уходил бы в сеть"
  - "Для дайджестов снимается именно system_instruction при фиксированных входах (дата 2026-09-30, завтра 2026-10-01); входы лежат в манифесте и читаются тестом"
  - "Эталон debrief.txt без завершающего перевода строки; полный текст вызова debrief_call.txt ловит лишний перевод строки в будущем шаблоне"

requirements-completed: [PER-07, BCK-01]

coverage:
  - id: D1
    description: "Побайтовые эталоны всех 8 системных промптов D-08 плюс debrief_call, отслеживаемые git, сняты с неизменённого src"
    requirement: "PER-07"
    verification:
      - kind: unit
        ref: "tests/test_prompt_snapshot.py#test_manifest_matches_files"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_snapshot.py#test_snapshot_files_tracked_by_git"
        status: pass
    human_judgment: false
  - id: D2
    description: "Текст по месту вызова LLM равен эталону побайтно для секретаря, маршрутизатора, методиста, проверки области, ответов на почту, дебрифа и обоих дайджестов"
    requirement: "BCK-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_snapshot.py (11 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "src/ assistant-core не изменён за план; гейт ЗЕЛЁНЫЙ, 234 теста assistant-core и 68 chat-app"
    requirement: "PER-07"
    verification:
      - kind: other
        ref: "git diff 150e9b3..HEAD -- src/ пусто; python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ"
        status: pass
    human_judgment: false

plan_head_before: 150e9b3b0698a1dc1c92599bcc61038ec10b3e6e
plan_head_after: caf4789d163810b9d52d39bb92b8af26b708003b
duration: 8min
completed: 2026-10-02
status: complete
---

# Phase 3 Plan 01: снимок системных промптов Summary

**Побайтовые эталоны восьми системных промптов (секретарь, маршрутизатор, методист, проверка области, ответы на почту, дебриф, утренний и вечерний дайджест) закреплены в git и 11 тестами по месту вызова LLM до любой правки src/brain; пререквизит W10 выполнен.**

## Performance

- **Duration:** 8 мин (15:19 - 15:27 UTC)
- **Tasks:** 2 из 2
- **Files:** 11 созданных, ни одного изменённого; src/ не тронут
- **Репозиторий:** только assistant-core (`main`, локальные коммиты, без push)

## Accomplishments

- Первый коммит фазы в assistant-core (4ea108b) содержит только tests/: тест-каркас, эталон секретаря и манифест (tracer: сквозной путь вызов LLM, захват, эталон в git, манифест, тест).
- Второй коммит (caf4789) добавляет остальные семь эталонов плюс `debrief_call.txt`; манифест содержит ровно 9 записей, в git отслеживаются 10 файлов снимка.
- Захват идёт по месту вызова: фейк `genai`-клиента запоминает `system_instruction` или `contents`, сравнение побайтно (`read_bytes()`, UTF-8, без нормализации). Тесты не импортируют `*_SYSTEM_PROMPT` и `SCOPE_CHECK_PROMPT`, поэтому переживут перенос в Jinja2 (03-07, 03-08) без правок.
- Длины: secretary 2718, intent_router 3269, methodist 4434, reply_generator 1346, debrief 1861 (без завершающего `\n`), debrief_call 1985, methodist_scope_check 680 (после `.format`), morning_brief 2039, evening_digest 908 символов.
- Опорное значение SHA-256 боевой БД `/opt/assistant-core/data/assistant.db` на старте плана и после него: `726c4e9970b2352b4dab97842e4ea89f24938b807a5ac6744018bee781cb7168` (не менялось; демон остановлен).

## Task Commits

1. **Задача 1 (tracer): снимок промпта секретаря** - `4ea108b` (test, assistant-core)
2. **Задача 2: снимок остальных семи промптов** - `caf4789` (test, assistant-core)

Метаданные плана (SUMMARY, STATE, ROADMAP) коммитятся в chat-app отдельно.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Первый прогон одноразового генератора ушёл в реальную сеть**
- **Found during:** Задача 1, снятие эталона секретаря
- **Issue:** `SecretaryDialogEngine.answer_user_message` внутри себя вызывает `MethodistService.check_scope`/`ask`; у методиста собственный клиент `genai.Client(api_key="x")`, и в первом прогоне генератора (scratchpad, не в репозитории) в `generativelanguage.googleapis.com` ушли 4 запроса (ответ 400 «API key not valid»). Содержимое запросов: один вопрос «Какие у меня задачи на сегодня?» и тексты запросов методиста без данных профиля и без реальных ключей (ключ `"x"`). Это противоречило митигации T-03-01 («без сети»).
- **Fix:** в генераторе и в тесте секретаря методисту подставлен отдельный фейк (`engine.methodist._client = FakeGeminiClient()`), плюс autouse-фикстура теста `forbid_real_gemini_client` подменяет `genai.Client` на функцию, бросающую `AssertionError`: любое будущее обращение к реальному клиенту в тестах снимка падает сразу. Эталон секретаря перегенерирован после исправления (результат тот же: 2718 символов, SHA-256 совпал).
- **Files modified:** tests/test_prompt_snapshot.py (до первого коммита)
- **Verification:** 11 passed; повторные прогоны без сетевых вызовов; гейт зелёный
- **Commit:** 4ea108b

### Уточнения без отклонения от смысла плана

- `captured_contents` возвращает текст `contents` и для строки, и для списка `types.Content` (нужно для дебрифа); тест секретаря из Задачи 1 не менялся.
- Для дайджестов входы (уроки, пункты, табель) записаны в манифест в JSON-виде и читаются тестом; `system_instruction` зависит только от дат, остальное сохранено для воспроизводимости.
- Вопрос для проверки области («Что приготовить на ужин из картофеля и грибов?») не содержит ни одного ключевого слова из обоих списков; тест дополнительно требует, чтобы вызов LLM действительно произошёл.

**Total deviations:** 1 auto-fixed (Rule 1 - сетевой вызов в одноразовом генераторе). **Impact:** на артефакты плана не влияет; в репозитории сетевых вызовов нет и быть не может.

## Authentication Gates

None.

## Verification Results

- `tests/test_prompt_snapshot.py`: 11 passed.
- `git diff --name-only 150e9b3b0698a1dc1c92599bcc61038ec10b3e6e..HEAD -- src/`: пусто. Оба коммита содержат только пути из tests/; удалений нет.
- Гейт `python3 /opt/chat-app/scripts/gate.py`: ИТОГ ЗЕЛЁНЫЙ; chat-app 68 тестов, assistant-core 234 теста (было 223, +11); import-linter, security_shield (--all), дрейф синтетической персоны, неизменность боевой БД: все зелёные.
- Гигиена секретов: `check_file_content` для теста, манифеста и девяти `.txt` печатает «нарушений: 0».
- Критерии приёмки Задач 1 и 2 (манифест из 9 записей, `debrief.txt` 1861 символ без `\n`, 0 упоминаний констант в тесте): выполнены.
- Сервисы не запускались и не перезапускались: assistant-worker `failed`, chat-app и dev-bridge `inactive`, как и до плана.

## Threat Model Status

- T-03-01 (реальный вызов LLM): митигирована; см. отклонение 1 про первый прогон генератора и закрывающую autouse-фикстуру.
- T-03-02 (эталон с уже изменённого кода): митигирована; src/ не менялся, первый коммит содержит только tests/.
- T-03-03 (адреса почты владельца в эталонах): принято по решению владельца OQ2; запись в BASELINE делает план 03-10.
- T-03-SC: установок пакетов не было.

## Known Stubs

None.

## Threat Flags

None.

## Next Phase Readiness

Эталоны и манифест готовы для 03-07/03-08 (перенос промптов в Jinja2): после переноса тесты `test_prompt_snapshot.py` должны остаться зелёными без правок; сравнение «шаблон = эталон» добавляется в тех планах. Блокеров нет.

## Self-Check: PASSED

- Файлы: 11 созданных файлов найдены на диске (`git ls-files` показывает 10 файлов снимка и тест).
- Коммиты 4ea108b и caf4789 найдены в `git log` assistant-core.
- Измеренное число коммитов плана: 2 (`git rev-list --count 150e9b3..HEAD`).
