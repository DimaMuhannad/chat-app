# Baseline Фазы 1: состояние тестов на старте

Документ фиксирует известное зелёное состояние обоих репозиториев до первого изменения поведения. Любой следующий шаг Фазы 1 и последующих фаз сравнивается с ним. Проверка выполняется одной командой `python3 scripts/gate.py` из `/opt/chat-app`.

Дата снятия: 2026-10-02.

## Окружение

| Компонент | chat-app (`backend/.venv`) | assistant-core (`.venv`) |
|-----------|----------------------------|--------------------------|
| Python | 3.12.3 | 3.12.3 |
| pytest | 9.1.1 | 9.1.1 |
| Плагин асинхронных тестов | anyio 4.15.1 | anyio 4.15.1, pytest-asyncio 1.4.0 (режим auto) |
| import-linter | 2.15 | 2.15 |
| grimp | 3.17 | 3.17 |

Версии получены через `importlib.metadata.version` в каждом `.venv`. import-linter и grimp установлены в этой фазе, после явного одобрения владельцем (проверка легитимности пакетов); вместе с ними добавлены только транзитивные rich 15.0.0, markdown-it-py 4.2.0, mdurl 0.1.2. Уже установленные пакеты не менялись.

## Репозитории на старте

| Репозиторий | Ветка | HEAD на момент снимка |
|-------------|-------|------------------------|
| chat-app (`/opt/chat-app`) | master | `11b0c5ebb9697f525fa37202a2871f1e4a7f6732` |
| assistant-core (`/opt/assistant-core`) | main | `6e0850bf58b3df9829a328e4da25f9fd84e86e74` |

SHA взяты из заголовков `docs/baseline/pytest-chat-app.txt` и `docs/baseline/pytest-assistant-core.txt`. Это фактические значения на момент снимка, а не из исследования: после исследования в chat-app появились коммиты каталога `.planning/`.

## Команды запуска

Документированные команды (CLAUDE.md):

- chat-app, из `/opt/chat-app`: `/opt/chat-app/backend/.venv/bin/pytest backend/tests`
- assistant-core: `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests` (запускать с рабочим каталогом `/opt/assistant-core`)

Команда гейта (из `/opt/chat-app`): `python3 scripts/gate.py`. Каталог assistant-core по умолчанию `/opt/assistant-core`, переопределяется переменной окружения `ASSISTANT_CORE_DIR`. Итог: таблица «репозиторий × проверка → ✓/✗» и последняя строка «ИТОГ: ЗЕЛЁНЫЙ» (код возврата 0) или «ИТОГ: КРАСНЫЙ» (код возврата 1).

Флаги, которые гейт добавляет к документированным командам: `-v`, `-p no:cacheprovider`, `--junitxml`, `--basetemp`. Они нужны только для отчётности и изоляции и не меняют набор тестов. Флагов `-k`, `-m`, `--deselect` гейт не использует.

Опция `--save-pytest-output КАТАЛОГ` записывает сырой вывод `pytest -v` каждого репозитория с заголовком (команда, коммит, дата). Снимок старта лежит в `docs/baseline/` и в Фазе 1 не перезаписывается.

## Результаты на старте

### chat-app: 14 тестов, 14 passed, 0 failed, 0 skipped, 2.80 с

| Файл | Тестов | Статус |
|------|--------|--------|
| backend/tests/test_dashboard_api.py | 5 | все passed |
| backend/tests/test_health.py | 4 | все passed |
| backend/tests/test_models.py | 2 | все passed |
| backend/tests/test_security_api.py | 3 | все passed |

Сырой вывод: `docs/baseline/pytest-chat-app.txt`. Запуск шёл на копии боевой базы (см. ниже). Файл `backend/tests/test_gate.py` создан после снимка и в него не входит.

### assistant-core: 127 тестов, 127 passed, 0 failed, 0 skipped, 31 предупреждение, 26.62 с

| Файл | Тестов | Статус |
|------|--------|--------|
| tests/test_aadhk_parser.py | 3 | все passed |
| tests/test_bot_group_isolation.py | 3 | все passed |
| tests/test_bot_menu.py | 3 | все passed |
| tests/test_brain.py | 6 | все passed |
| tests/test_debrief_parser.py | 2 | все passed |
| tests/test_email_collector.py | 7 | все passed |
| tests/test_email_reply_workflow.py | 8 | все passed |
| tests/test_fast_intent_router.py | 10 | все passed |
| tests/test_gdrive_client.py | 3 | все passed |
| tests/test_guap_lms.py | 8 | все passed |
| tests/test_hitl_safety_guardrails.py | 3 | все passed |
| tests/test_key_rotator.py | 6 | все passed |
| tests/test_live_ticker.py | 8 | все passed |
| tests/test_lms_bot_workflow.py | 10 | все passed |
| tests/test_memory_review.py | 5 | все passed |
| tests/test_methodist.py | 2 | все passed |
| tests/test_notion_client.py | 3 | все passed |
| tests/test_phase1.py | 15 | все passed |
| tests/test_phase2_filter.py | 8 | все passed |
| tests/test_secretary_dialog.py | 6 | все passed |
| tests/test_voice.py | 8 | все passed |

Сырой вывод: `docs/baseline/pytest-assistant-core.txt`.

## Защита боевой БД

- Гейт делает консистентную копию боевой `assistant.db` методом sqlite3 `backup()` из соединения в режиме `mode=ro` во временный каталог (права 0700) и удаляет каталог в блоке finally. Копия создаётся одной функцией `make_db_copy`: это единственная точка замены в Фазе 4 (DAT-04) на временную БД из общей схемы.
- chat-app: pytest получает переменную `SQLITE_DB_PATH` на копию. Без копии, а также при пути, равном боевой БД, pytest chat-app не запускается вовсе.
- assistant-core: переопределить БД окружением нельзя, потому что `src/config.py` вызывает `load_dotenv(..., override=True)` и значение из боевого `.env` перебивает окружение. Тесты assistant-core в боевую БД не пишут; защита для обоих репозиториев — контроль SHA-256 боевой БД до и после всех шагов гейта. Расхождение даёт красную строку «боевая assistant.db не изменена» и «ИТОГ: КРАСНЫЙ».
- SHA-256 боевой БД на старте: `baef14f707683c33fbb684765fb86408669075be14073ac70402585062cf9393`.
- Для Фазы 4: боевая БД остаётся единственным общим хранилищем двух репозиториев (DAT-02); подмена на временную БД из общей схемы закрывается пунктом DAT-04.

## Красные тесты на старте

Красных, пропущенных, xfail и deselected тестов на старте нет: 14 из 14 и 127 из 127 passed. Если красный тест появится, он классифицируется по трём корзинам:

1. Окружение или данные — чинится фикстурами или окружением, без правки ассертов.
2. Устаревший тест — отдельный атомарный коммит с сохранением смысла проверки и записью в этот документ.
3. Ошибка продакшен-кода — не чинится молча; решение выносится владельцу с вариантами.

## Внешний доступ тестов

Пять наборов могут выглядеть как обращения наружу: test_gdrive_client, test_notion_client, test_voice, test_guap_lms, test_lms_bot_workflow. По анализу они используют заглушки. Набор test_gdrive_client упаковывает копию файлов окружения и сессий во временный каталог pytest, поэтому гейт передаёт `--basetemp` внутрь своего временного каталога, который удаляется в блоке finally. Агенты эти файлы не читают.

## Наблюдения для следующих фаз

- Три набора тестов assistant-core создают в корне репозитория каталог с именем, начинающимся на `sqlite+aiosqlite:` (побочный эффект относительного пути БД). Фаза 1 его не меняет.
- `EmailCollector()` строит путь к боевой БД лениво, при первом обращении.
- Каталоги `src/connectors`, `src/sender` в assistant-core и `app/core` в chat-app являются namespace-каталогами без `__init__.py`. В Фазе 1 файлы `__init__.py` не добавляются (решение по рекомендации исследования).
- `test_security_audit_all` сканирует `git ls-files` обоих репозиториев (первые 100 файлов), поэтому новые файлы не должны содержать строк, похожих на секреты.
- Решение владельца: в Фазе 1 локальные коммиты в assistant-core делаются прямо в ветку main этого репозитория (push не выполняется).

## Архитектурный контракт и долг

Инструмент: import-linter 2.15 (grimp 3.17). Конфиги `.importlinter` (INI) лежат в корне каждого репозитория; `pyproject.toml` не создавался. Гейт печатает строку «import-linter» для каждого репозитория.

### assistant-core

Два контракта типа `forbidden`, команда `lint-imports --no-logo --no-cache` из `/opt/assistant-core` даёт «2 kept, 0 broken».

| Контракт | Источники | Запрещённые цели |
|----------|-----------|------------------|
| `brain-no-adapters` | `src.brain` | `src.connectors`, `src.calendar`, `src.parser`, `src.sender`, `src.collector`, `src.notifier` |
| `bot-handler-no-adapters` | `src.notifier.bot_handler` | `src.connectors`, `src.calendar`, `src.parser`, `src.sender`, `src.collector` |

Пять записей `ignore_imports` — известный долг, который только убывает (Фаза 2, PRT-04, опустошает список; запись удаляется в том же коммите, что и рефакторинг, иначе lint-imports сообщит об устаревшей записи). Тест `test_ignore_imports_debt_only_shrinks` не даёт числу записей превысить 5.

| # | Источник → цель | Строки | Вид |
|---|-----------------|--------|-----|
| 1 | `src.brain.secretary_dialog` → `src.connectors.aadhk.parser` | 139 | inline |
| 2 | `src.notifier.bot_handler` → `src.connectors.aadhk.parser` | 1052, 1095, 1144 | inline |
| 3 | `src.notifier.bot_handler` → `src.connectors.gdrive.client` | 1143 | inline |
| 4 | `src.notifier.bot_handler` → `src.connectors.guap_lms.client` | 23 | top-level |
| 5 | `src.notifier.bot_handler` → `src.sender.email_sender` | 22 | top-level |

Два из пяти нарушений — обычные импорты верхнего уровня, а не inline-импорты, как сказано в ROADMAP.

Известное нарушение вне контракта: `src.notifier.live_ticker -> src.connectors.aadhk.parser` (строка 115, inline). Это связь «адаптер → адаптер»; контракт её не охватывает и в `ignore_imports` её нет. Только фиксируется; решение (расширять ли контракт на `live_ticker`) принимается в Фазе 2.

Решения по настройке:

- `allow_indirect_imports = True`: считаются только прямые импорты. Иначе цепочка `bot_handler -> live_ticker -> connectors` потребовала бы в Фазе 2 рефакторинга `live_ticker`, которого нет в PRT-04.
- `root_packages = src, src.connectors, src.sender` (порции namespace-пакетов) вместо пустых `__init__.py`. Каталоги `src/connectors` и `src/sender` не содержат `__init__.py`, и без перечисления порций grimp их не видит: наивный контракт сообщает «KEPT» при реальных нарушениях. Продакшен-дерево в Фазе 1 не меняется (Open Question 2 решён по рекомендации исследования), а страж-тест `test_real_contract_modules_exist_in_graph` проверяет, что каждый модуль контракта есть в графе.
- Два контракта вместо одного: общий запрет `src.notifier` ложно срабатывал бы на соседние модули бот-обработчика.
- `src.main` — корень композиции, в контракт не входит.

Тесты контракта (`tests/test_architecture_contract.py`, 5 штук): падение на синтетическом нарушении, успех на чистом пакете, страж «модули контракта есть в графе», верхняя граница долга, падение реального контракта на копии пакета с внедрённым запрещённым импортом.

### chat-app

Один контракт `app-no-assistant-core` (type `forbidden`): пакет `app` не импортирует `src` (внутренние модули assistant-core, внешний запрещённый модуль через `include_external_packages = True`). `root_packages = app, app.core` — порция namespace-каталога `app/core`. Запуск: `PYTHONPATH=backend lint-imports --no-logo --no-cache` из `/opt/chat-app` (lint-imports добавляет в `sys.path` только текущий каталог, а пакет `app` лежит в `backend/`); результат «1 kept, 0 broken». Нарушений нет, `ignore_imports` пуст, верхняя граница долга в тесте равна 0. Контракт защищает от появления связи.

Тесты контракта: `backend/tests/test_architecture_contract.py`, те же пять имён, что в assistant-core.

## Ожидают Фазы 3

Вторая синтетическая персона (FND-03) лежит в `backend/tests/synthetic_persona.py` (chat-app) и в `tests/synthetic_persona.py` (assistant-core): две байт-в-байт одинаковые копии до общей библиотеки Фазы 4; расхождение краснит строку гейта «синтетическая персона (дрейф SHA-256)». Фикстура `synthetic_persona` возвращает независимую копию словаря.

Каркас сейчас проверяет только сами данные (D-14): наличие и непустоту идентифицирующих полей, отсутствие токенов владельца и реальных NDA-слов, ровно три уровня clearance, зарезервированные значения (домены `.example`, пути `/synthetic/`, диапазон идентификатора Telegram). Реальный Telegram ID владельца в тесты не копируется.

Проверки ниже перечислены только текстом, без маркеров пропуска и ожидаемого падения; они включаются в Фазе 3 (D-15). Тот же список стоит в докстринге `synthetic_persona.py`.

1. PER-01 — персона загружается из config/persona.yaml с Pydantic-валидацией; персона по умолчанию грузится без PERSONA_CONFIG_PATH;
2. PER-02 — персона записывается в таблицы personas, workspaces, connector_bindings; несколько привязок на одну роль;
3. PER-03/PER-04 — /api/v1/security/overview и аудит строятся из рабочих пространств персоны (три уровня clearance); NDA-проверки воспроизводятся из данных без ослабления;
4. PER-05 — дефолт области и white-label-поля веб-интерфейса приходят из /api/v1/persona/current;
5. PER-06 — параметры коннекторов (проект учёта, норма часов, адреса, предметы, слоты) читаются из персоны;
6. PER-07/BCK-02 — промпты секретаря, маршрутизатора и методиста рендерятся из шаблонов с этой персоной и отличаются от промптов персоны по умолчанию; тесты хардкода переписаны на загруженную персону;
7. PER-08 — сканер хардкода не находит токены владельца вне allowlist; denylist теста каркаса заменяется данными персоны по умолчанию;
8. PER-09 — test_persona_config.py: те же кодовые пути дают для синтетической персоны иные промпты, список рабочих пространств, дефолты и scope-решения.

## Политика security_shield

Решение владельца от 2026-10-02: вариант «Полный скан + список 15 (Рекомендуется)», внутренний идентификатор `b-all-frozen`.

Что это значит:

- Гейт запускает `scripts/security_shield.py` каждого репозитория с ключом `--all` (скан всех отслеживаемых файлов), а не только проиндексированных и изменённых. Режим по умолчанию на чистом дереве ничего не сканирует и был бы «зелёным по умолчанию»; поэтому он не используется. В `scripts/gate.py` это константа `SHIELD_MODE = "all"`.
- Строка shield красная, если: найдена новая находка сверх списка ниже; shield не запустился или упал (таймаут, неожиданный код возврата, код 1 без распознанных находок); запись списка устарела (находки по ней больше нет, а в списке она осталась).
- Список известных ложных срабатываний `KNOWN_SHIELD_FALSE_POSITIVES` только сокращается (правило 4 ниже). Автоматически он не пополняется, файлы Фазы 1 в него не вносятся.
- В консоль гейта и в этот документ попадают только путь, вид находки и число. Адреса remote, e-mail автора, текст NDA-слов и номера строк не печатаются и не сохраняются.
- Сам `scripts/security_shield.py` в Фазе 1 не менялся.

Реальных секретов среди находок нет: это определение списка слов в самом shield, пример конфигурации в документе архитектуры и учебные фиктивные ключи в тестах.

Известные находки `--all` на старте (всего 15):

| Репозиторий | Путь | Вид | Число |
|-------------|------|-----|-------|
| chat-app | docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md | nda-keyword | 3 |
| chat-app | scripts/security_shield.py | nda-keyword | 3 |
| assistant-core | scripts/security_shield.py | nda-keyword | 3 |
| assistant-core | tests/test_debrief_parser.py | secret: Generic Bearer Secret | 2 |
| assistant-core | tests/test_notion_client.py | secret: Generic Bearer Secret | 1 |
| assistant-core | tests/test_voice.py | secret: Generic Bearer Secret | 3 |

Итого: chat-app 6, assistant-core 9. Записи удаляются в том же коммите, что исправляет соответствующее место; если запись осталась после исправления места, гейт краснеет на устаревшей записи.

## Итог после Фазы 1

Финальный прогон `python3 scripts/gate.py` из `/opt/chat-app` (2026-10-02), код возврата 0:

| Репозиторий | Проверка | Результат |
|-------------|----------|-----------|
| chat-app | pytest — тестов: 68 | ✓ |
| chat-app | import-linter | ✓ |
| assistant-core | pytest — тестов: 139 | ✓ |
| assistant-core | import-linter | ✓ |
| chat-app | security_shield (--all) | ✓ |
| assistant-core | security_shield (--all) | ✓ |
| оба | синтетическая персона (дрейф SHA-256) | ✓ |
| оба | боевая assistant.db не изменена | ✓ |

ИТОГ: ЗЕЛЁНЫЙ.

Число тестов до и после фазы:

| Репозиторий | На старте («Результаты на старте») | После Фазы 1 | Добавлено |
|-------------|------------------------------------|--------------|-----------|
| chat-app | 14 | 68 | 54 |
| assistant-core | 127 | 139 | 12 |
| Всего | 141 | 207 | 66 |

Все 141 стартовых теста остались и проходят; ни один не удалён и не ослаблен, skip, xfail и deselect не вводились. Добавленные тесты относятся к гейту (`test_gate.py`), архитектурному контракту и каркасу синтетической персоны.

Инструменты: import-linter 2.15, grimp 3.17 (в обоих `.venv`).

Команда гейта: `python3 /opt/chat-app/scripts/gate.py`; строка с ней добавлена в `CLAUDE.md`, раздел Development Commands.

Подтверждения:

- Продакшен-код не изменён: за фазу нет коммитов и правок в `backend/app` (chat-app) и `src` (assistant-core).
- Сервисы chat-app и dev-bridge остановлены (`inactive`); assistant-worker не активен (`failed` с прошлого раза, до Фазы 1) и не запускался.
- SHA-256 боевой `assistant.db` равен стартовому (префикс `baef14f7`, полное значение в разделе «Защита боевой БД»).
- Локальные коммиты assistant-core лежат в ветке `main` по решению владельца; push не выполнялся.

### Сверка ignore_imports с `/opt/assistant-core/.importlinter`

Пять записей долга, дословно из файла конфигурации (удаляются Фазой 2, PRT-04):

```text
src.brain.secretary_dialog -> src.connectors.aadhk.parser
src.notifier.bot_handler -> src.connectors.aadhk.parser
src.notifier.bot_handler -> src.connectors.gdrive.client
src.notifier.bot_handler -> src.connectors.guap_lms.client
src.notifier.bot_handler -> src.sender.email_sender
```

Совпадение с таблицей раздела «Архитектурный контракт и долг»: 5 из 5.

## Правила

1. 100% pytest в обоих репозиториях на каждом шаге; проверяется гейтом.
2. Каждый шаг — атомарный коммит в своём репозитории; откат через `git revert` по SHA.
3. Существующие тесты не удаляются и не ослабляются: без skip, xfail, deselect и правки ассертов ради зелёного итога.
4. Списки долга (ignore_imports import-linter и известные ложные срабатывания shield) только сокращаются.
5. Сервисы chat-app, assistant-worker и dev-bridge остаются остановленными.
6. pytest chat-app запускается только через гейт или на копии БД.
