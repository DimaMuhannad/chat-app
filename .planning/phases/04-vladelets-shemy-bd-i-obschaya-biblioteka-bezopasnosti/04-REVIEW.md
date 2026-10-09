---
phase: 04-vladelets-shemy-bd-i-obschaya-biblioteka-bezopasnosti
reviewed: 2026-10-09T00:00:00Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - /opt/assistant-core/scripts/install_hooks.sh
  - /opt/assistant-core/scripts/security_shield.py
  - /opt/assistant-core/src/storage/db.py
  - /opt/assistant-core/tests/hardcode_baseline.py
  - /opt/assistant-core/tests/test_nda_script_parity.py
  - /opt/assistant-shared/assistant_shared/__init__.py
  - /opt/assistant-shared/assistant_shared/db/__init__.py
  - /opt/assistant-shared/assistant_shared/db/connection.py
  - /opt/assistant-shared/assistant_shared/db/migrations/0001_initial_schema.sql
  - /opt/assistant-shared/assistant_shared/db/migrations/0002_pending_confirmations.sql
  - /opt/assistant-shared/assistant_shared/db/migrations/__init__.py
  - /opt/assistant-shared/assistant_shared/db/migrator.py
  - /opt/assistant-shared/assistant_shared/security/__init__.py
  - /opt/assistant-shared/assistant_shared/security/auditor.py
  - /opt/assistant-shared/assistant_shared/security/patterns.py
  - /opt/assistant-shared/assistant_shared/security/rules.py
  - /opt/assistant-shared/assistant_shared/security/runner.py
  - /opt/assistant-shared/pyproject.toml
  - /opt/assistant-shared/README.md
  - /opt/chat-app/backend/app/api/v1/security.py
  - /opt/chat-app/backend/app/core/config.py
  - /opt/chat-app/backend/app/db.py
  - /opt/chat-app/backend/tests/conftest.py
  - /opt/chat-app/backend/tests/hardcode_baseline.py
  - /opt/chat-app/backend/tests/test_concurrent_write.py
  - /opt/chat-app/backend/tests/test_database_isolated.py
  - /opt/chat-app/backend/tests/test_db_config.py
  - /opt/chat-app/backend/tests/test_gate.py
  - /opt/chat-app/backend/tests/test_migrations.py
  - /opt/chat-app/backend/tests/test_nda_equivalence.py
  - /opt/chat-app/backend/tests/test_pre_commit_hook.py
  - /opt/chat-app/backend/tests/test_security_shared.py
  - /opt/chat-app/backend/tests/test_shield_parity.py
  - /opt/chat-app/scripts/gate.py
  - /opt/chat-app/scripts/install_hooks.sh
  - /opt/chat-app/scripts/security_shield.py
findings:
  critical: 7
  warning: 14
  info: 4
  total: 25
status: issues_found
---

# Фаза 4: отчёт о код-ревью

**Проверено:** 2026-10-09
**Глубина:** standard
**Файлов:** 35
**Статус:** issues_found

## Сводка

Проверено текущее состояние пакета `assistant-shared` (мигратор, фабрика соединений, библиотека безопасности), тонкие обёртки `security_shield.py`, pre-commit hook, `install_hooks.sh`, гейт и тесты обоих репозиториев.

Общая оценка: структурно фаза выполнена (единый пакет, версионирование миграций, WAL, общий набор паттернов). Но сама защитная логика **fail-open** в нескольких местах. Я воспроизвёл эти сбои на временных git-репозиториях. Pre-commit hook и CLI shield пропускают переименованные файлы, файлы с не-ASCII именами, частично проиндексированные файлы и запуск с флагом `--all` первым аргументом. Web-аудит отвечает `passed`, когда просмотрел только первые 100 файлов. Проверка NDA-remote обходится портом или `ssh.github.com`. Мигратор падает при одновременном старте двух процессов: 27 из 30 прогонов с 4 процессами дали `IntegrityError`. Часть тестов (N05, N08) закрепляет fail-open поведение как «эталон».

Все воспроизведения выполнены вне репозитория (каталог scratchpad), исходники не менялись.

## Critical Issues

### CR-01: Pre-commit hook и CLI shield пропускают переименования, не-ASCII имена файлов и сбой git (fail-open)

**File:** `/opt/assistant-shared/assistant_shared/security/runner.py:25-38`, `/opt/assistant-shared/assistant_shared/security/auditor.py:154-161`
**Issue:** Три независимых способа получить пустой или неполный список файлов, после чего shield печатает «passed» и возвращает 0.
1. `git diff --cached --name-only --diff-filter=ACM` не включает статус `R`. Rename включён в git по умолчанию. `git mv cfg.txt credentials.json` даёт `R100`, shield пишет «No staged or modified files found to scan». Запрещённое имя файла и любые изменения при переименовании не проверяются. Воспроизведено.
2. Без `-z` git заключает не-ASCII пути в кавычки и экранирует их (`core.quotePath=true`), например `"\321\201\320\265..."`. Затем `repo_path / rel_path` указывает на несуществующий файл, и `check_file_content` молча возвращает `[]` (`is_file()` is False). Файл `секрет.py` с `api_key = '...'` прошёл проверку. Воспроизведено. Для русскоязычного владельца это нормальный сценарий.
3. `run_cmd` превращает любое исключение (таймаут, отсутствие git, `dubious ownership`) в `(1, str(e))`. Затем `get_staged_or_tracked_files` возвращает `[]`, и `audit_repository` возвращает 0. Это тот же fail-open.

**Fix:**
```python
# runner.py
def _git_z(repo_path, args):
    code, out = run_cmd(["git", "-c", "core.quotePath=false", *args, "-z"], cwd=str(repo_path))
    if code != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out}")
    return [p for p in out.split("\0") if p]

# --no-renames, чтобы переименования попадали как A; добавить T
files = _git_z(repo_path, ["diff", "--cached", "--name-only", "--no-renames", "--diff-filter=ACMRT"])
```
`run_cmd` с `text=True` и `.strip()` не годится для NUL-вывода. Нужен отдельный вызов с `stdout` в байтах. В `audit_repository` сбой git должен давать код возврата 1 (fail-closed), а не 0.

### CR-02: `security_shield.py --all` и несуществующий путь возвращают код 0

**File:** `/opt/chat-app/scripts/security_shield.py:18-20` (идентично в `/opt/assistant-core/scripts/security_shield.py`), `/opt/assistant-shared/assistant_shared/security/auditor.py:136-170`
**Issue:** `target = Path(sys.argv[1])` берёт первый аргумент как путь без разбора флагов. `python3 scripts/security_shield.py --all` превращает `--all` в каталог `cwd/--all`. Git-команды падают (см. CR-01), список файлов пуст, shield печатает «passed» и возвращает 0. То же для любого несуществующего каталога (`/nonexistent/zzz` даёт exit 0). Воспроизведено. Это отключает гейт, если его вызвать с флагом в другом порядке. `audit_repository` никогда не проверяет, что `repo_path` существует и является git-репозиторием.
**Fix:**
```python
import argparse
p = argparse.ArgumentParser()
p.add_argument("path", nargs="?", default=".")
p.add_argument("--all", action="store_true")
a = p.parse_args()
target = Path(a.path).resolve()
sys.exit(audit_repository(target, check_staged_only=not a.all))
```
А в `audit_repository` добавить в начало:
```python
if not repo_path.is_dir() or run_cmd(["git", "rev-parse", "--git-dir"], cwd=str(repo_path))[0] != 0:
    print("❌ не git-репозиторий"); return 1
```

### CR-03: Shield читает рабочее дерево, а не индекс (обход через частичное индексирование)

**File:** `/opt/assistant-shared/assistant_shared/security/auditor.py:159-161`
**Issue:** Для staged-режима список файлов берётся из индекса, но содержимое читается с диска (`full_path`). Если секрет проиндексирован, а затем удалён из рабочей копии, shield проходит, а коммит содержит секрет. Воспроизведено: `git add leak2.txt; echo clean > leak2.txt` даёт exit 0, в индексе секрет остаётся. Обычные `git add -p` и правка после `git add` приводят к тому же. И обратный случай: ложные срабатывания на не-проиндексированных правках.
**Fix:** в staged-режиме читать blob индекса: `git show :<path>` (`run_cmd(["git","show",f":{rel}"])`) или `git cat-file blob :path`. Прогонять `SECRET_PATTERNS` и ключевые слова по этому тексту.

### CR-04: Web-аудит `audit_path` возвращает `passed`, не просмотрев весь репозиторий

**File:** `/opt/assistant-shared/assistant_shared/security/auditor.py:99-124`
**Issue:**
- `[:max_files]` (100) молча обрезает список. Статус `passed` и `scanned_files=len(files_to_scan)` не сообщают об усечении. Репозиторий из 106 файлов с секретом в последнем файле дал `passed`, `scanned_files=100`. Воспроизведено. Тест `test_n08_web_scans_only_first_100_files` закрепляет это поведение как норму.
- Фолбэк для каталогов без git: `any(part.startswith(".") for part in p.parts)` проверяет **абсолютные** части пути. Если рабочее пространство лежит под скрытым каталогом (`~/.cache/...`, `/root/.claude/...`), пропускаются все файлы: `status=passed, scanned_files=0`. Воспроизведено. Даже в обычном каталоге скрытые файлы (`.env`) исключены, то есть `FORBIDDEN_FILES` для них не срабатывает (воспроизведено).
- `except Exception: pass` (стр. 123) глотает ошибки чтения: нечитаемый файл считается чистым. В CLI та же ситуация даёт нарушение «Read error», то есть поведение расходится.
- Ошибки git (`code_files != 0`) молча переключают на фолбэк.

**Fix:** убрать лимит (или возвращать `status="incomplete"` и нарушение при усечении), считать скрытые части по `p.relative_to(target_path).parts`, не пропускать `.env`, ошибки чтения превращать в нарушения:
```python
rel_parts = p.relative_to(target_path).parts
if p.is_file() and ".git" not in rel_parts: ...
...
except Exception as e:
    violations.append(f"{rel_path}: ошибка чтения ({e})")
if truncated: violations.append(f"CRITICAL: просканировано {max_files} из {total} файлов")
```

### CR-05: Проверка NDA-remote обходится (порт, `ssh.github.com`, pushurl, git-сбой)

**File:** `/opt/assistant-shared/assistant_shared/security/rules.py:28-43`, `/opt/assistant-shared/assistant_shared/security/auditor.py:82-96,141-152`
**Issue:** Правило NDA сопоставляет подстроку `host/owner` с нормализованным remote. Обходы, воспроизведённые через `normalize_remote`:
- `ssh://git@github.com:22/Owner/r.git` даёт `github.com:22/owner/r`, и подстрока `github.com/owner` не находится.
- `ssh://git@ssh.github.com:443/Owner/r.git` (штатный путь GitHub через порт 443) даёт `ssh.github.com:443/owner/r`, подстрока не находится.
- Проверяется только `git remote get-url origin` (fetch URL). `pushurl` и любые другие remote (`personal`) не проверяются. Именно push в личный аккаунт — угроза, от которой защищает правило.
- При `code != 0` (git недоступен, таймаут) проверка remote пропускается, а `status` остаётся `passed` (в тесте `n05` закреплено: NDA без origin даёт `clean`).

**Fix:** в `normalize_remote` отрезать порт и сопоставлять алиасы хостов (`ssh.github.com` как `github.com`); проверять все remote и push-URL (`git remote -v`, `git config --get-regexp 'remote\..*\.(push)?url'`); для NDA-пространства сбой git и отсутствие origin должны давать нарушение (fail-closed), а не `passed`.

### CR-06: Конкурентный `run_migrations` падает с `IntegrityError` (гонка при старте двух процессов)

**File:** `/opt/assistant-shared/assistant_shared/db/migrator.py:148-170`
**Issue:** Список `applied` читается до применения, `executescript` не берёт блокировку записи, а `INSERT INTO schema_migrations` не имеет `OR IGNORE`. Два процесса (worker, `persona/seed.py`, `email_collector.py:751` вызывают `init_db`, плюс chat-app) одновременно видят пустой `applied`, оба применяют 0001 (идемпотентно благодаря `IF NOT EXISTS`) и оба вставляют версию. Второй получает `sqlite3.IntegrityError: UNIQUE constraint failed: schema_migrations.version`. Воспроизведено: 27 из 30 прогонов с 4 параллельными процессами. Конкурентный тест `test_concurrent_write.py` вызывает `run_migrations` один раз до запуска воркеров и эту гонку не покрывает. Причём в сочетании с `Restart=always` сервис уходит в цикл рестартов.
**Fix:** сериализовать применение и повторно проверять внутри блокировки:
```python
conn.execute("BEGIN IMMEDIATE")
applied = set(list_applied_migrations(conn))
...
conn.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)", (version,))
conn.execute("COMMIT")
```
`executescript` делает неявный `COMMIT`, поэтому применять скрипт построчно через `conn.execute` внутри явной транзакции (SQLite поддерживает транзакционный DDL), либо использовать `fcntl.flock` на файле рядом с БД.

### CR-07: SECRET_PATTERNS не ловят реальные форматы ключей (в том числе Anthropic и PGP)

**File:** `/opt/assistant-shared/assistant_shared/security/patterns.py:7-13`
**Issue:** Проверка регулярных выражений на реальных форматах:
- Ключ Anthropic `sk-ant-api03-<...>` не ловится (в паттерне `sk-ant-[a-zA-Z0-9]{20,}` после `sk-ant-` стоит `api03-`, дефис ломает совпадение; первая ветка `sk-[a-zA-Z0-9]{20,}` тоже не совпадает из-за дефисов). Название паттерна «OpenAI/Anthropic API Key» создаёт ложное чувство защиты. `sk-proj-...` (OpenAI) тоже не ловится.
- `-----BEGIN PGP PRIVATE KEY BLOCK-----` не ловится (после `PRIVATE KEY` ожидается `-----`), `-----BEGIN ENCRYPTED PRIVATE KEY-----` тоже.
- `gho_`, `ghs_`, `ghu_` токены GitHub, AWS `AKIA...`, Slack `xoxb-` не покрыты.
- `Generic Bearer Secret` требует кавычку непосредственно после ключа и не ловит JSON `"api_key": "..."` и значения без кавычек (`API_KEY=abcdef...` в `.env`-подобных файлах).
- `FORBIDDEN_FILES` не включает `id_rsa`, `id_ed25519`, `.env.bak`, `.env.production.local`, `service-account*.json`, `.npmrc`.

В проекте используются Gemini/Anthropic/Telegram/Notion ключи, поэтому пропуск формата приводит к реальной утечке при коммите.
**Fix:**
```python
("Private Key", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----")),
("OpenAI/Anthropic API Key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}")),
("GitHub Token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b")),
("Generic Bearer Secret", re.compile(r"(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}")),
```
Добавить фикстуры для каждого реального формата в `test_security_shared.py` (сейчас тесты проверяют только синтетические строки, подогнанные под регулярные выражения).

## Warnings

### WR-01: Мигратор не атомарен; baseline-фолбэк режет SQL по `;` и тихо пропускает индексы

**File:** `/opt/assistant-shared/assistant_shared/db/migrator.py:105-128,154-170`
**Issue:**
- `executescript` выполняет неявный `COMMIT` и не транзакционен: сбой на середине оставляет частично применённую миграцию без записи в `schema_migrations`. Повтор безопасен лишь пока все операторы `IF NOT EXISTS` (будущий `ALTER TABLE ADD COLUMN` не идемпотентен).
- Фолбэк `sql_script.split(";")` ломает тела триггеров `... BEGIN ...; ...; END;` (в 0001 их шесть) и комментарии с `;`, поэтому для baseline-БД с отсутствующей колонкой падает с `incomplete input`, а не пропускает индекс.
- «Пропуск индекса» при `no such column` записывает миграцию как применённую. Схема baseline-БД навсегда расходится со свежей, и никто об этом не узнает (старые `ALTER TABLE ADD COLUMN` из `db.py` были удалены в коммите `51cf4d1`, а 0001 их не заменяет). `test_migrations_baseline_detection_existing_db` этот путь не проходит: все индексируемые колонки в тестовых таблицах есть.
- Пустой каталог миграций (`glob("*.sql") == []`) возвращает `[]` без ошибки.

**Fix:** выполнять миграцию в одной транзакции, при несоответствии колонок падать с понятной ошибкой либо добавлять миграцию-«выравнивание» с проверкой `PRAGMA table_info`; вместо `split(";")` использовать `sqlite3.complete_statement`. При пустом каталоге выбрасывать `FileNotFoundError`.

### WR-02: Пакет не включает `*.sql` в сборку (тихая no-op миграция при обычной установке)

**File:** `/opt/assistant-shared/pyproject.toml:16-18`
**Issue:** В `[tool.setuptools]` не указано `package-data`/`include-package-data` для `assistant_shared/db/migrations/*.sql`. Сейчас пакет стоит через editable `.pth`, поэтому всё работает. При обычном `pip install /opt/assistant-shared` (CI, Docker, другой хост) SQL-файлы не попадут в wheel, и `run_migrations` (см. WR-01) вернёт `[]` без ошибки: приложение стартует с пустой БД.
**Fix:**
```toml
[tool.setuptools.package-data]
"assistant_shared.db.migrations" = ["*.sql"]
```
и тест, что `MIGRATIONS_DIR.glob("*.sql")` непуст.

### WR-03: NDA-правила CLI захардкожены (путь содержит «tydex», литерал личного GitHub-аккаунта)

**File:** `/opt/assistant-shared/assistant_shared/security/auditor.py:144-152`, `/opt/assistant-core/tests/test_nda_script_parity.py:525-531`
**Issue:**
- NDA-режим определяется подстрокой `"tydex" in str(repo_path).lower()`, а не данными персоны (`workspaces.clearance`). Обратный сбой: публичный репозиторий в каталоге с «tydex» в пути (`/home/tydex/oss/x`) получает `is_public_repo=False`, и проверка NDA-слов отключается (fail-open). NDA-репозиторий вне такого пути проверяется как публичный: remote не проверяется вообще.
- Запрещённый remote `"github.com/dimamuhannad"` вшит в общую библиотеку, то есть личный идентификатор владельца в «универсальной» библиотеке, что противоречит цели универсализации и PER-08. Web-путь использует данные из БД (`nda_rule_for`), CLI — литерал: два источника истины.
- Тест паритета проверяет это регулярным выражением по исходнику (`"([^"]+)" in origin_norm`), читая файл по абсолютному пути `/opt/assistant-shared/...`. Любой рефакторинг ломает тест либо (при пустом `found`) создаёт ложное расхождение. `hardcode_baseline.py` пуст, потому что сканер не обходит `/opt/assistant-shared`, и вшитые литералы остаются невидимыми для гейта.

**Fix:** CLI должен получать правило по пути рабочей копии из таблицы `workspaces` (`nda_rule_for` по совпадению `path`) либо из файла конфигурации; литералы удалить. Тест паритета строить на поведении (подать remote, проверить результат), а не на разборе исходника.

### WR-04: Паритет Web и CLI не достигнут, хотя документирован как закрытый

**File:** `/opt/assistant-shared/assistant_shared/security/auditor.py:64-70,110-124`, `/opt/chat-app/backend/tests/test_nda_equivalence.py:15-16`, `/opt/chat-app/backend/tests/test_shield_parity.py:75-91`
**Issue:**
- Параметр `is_public_repo` в `audit_path` принимается, но не используется. Ключевые слова NDA Web-аудит не проверяет, хотя данные `workspaces.forbidden_keywords` хранятся в БД и в аудит не передаются. Докстринг тестов утверждает: «расхождение закрывает Фаза 4, SEC-01/02», но оно не закрыто.
- Web считает 1 нарушение на файл и паттерн (`pat.search(content)`), CLI — по одному на строку; Web продолжает сканировать содержимое запрещённых файлов, CLI останавливается (`return violations`). Тест `test_parity_between_web_audit_and_cli_shield` проходит только потому, что у фикстур по одной строке, и проверяет «100% паритет» лишь на этих данных.
- Сообщения на разных языках («Запрещенный файл…» и «Forbidden file…»), поэтому гейту и UI сложно сопоставлять находки.

**Fix:** вынести общую функцию сканирования одного файла (одна реализация для CLI и Web), передавать в неё `forbidden_keywords` из рабочего пространства, использовать её из обоих путей. Тест паритета строить на многострочных фикстурах.

### WR-05: Тестовые «швы» в боевом коде библиотеки и неиспользуемые импорты

**File:** `/opt/assistant-shared/assistant_shared/security/runner.py:10`, `/opt/assistant-shared/assistant_shared/security/auditor.py:41`, `/opt/chat-app/backend/app/api/v1/security.py:1-14`
**Issue:** `getattr(sys.modules.get("app.api.v1.security"), "subprocess", subprocess)` и `getattr(sys.modules.get("assistant_shared.security"), "open", open)` существуют только ради `monkeypatch` в тестах chat-app (`security.subprocess`, `shield.open`). Общая библиотека знает имя модуля одного из своих потребителей, а при его наличии в `sys.modules` подменяет `subprocess.run` и `open` патчем этого модуля. Модуль `security.py` в свою очередь импортирует `subprocess`, `FORBIDDEN_FILES`, `SECRET_PATTERNS`, `NdaRemoteRule`, `DEFAULT_REMOTE_VIOLATION`, `normalize_remote`, `run_cmd` исключительно для тестов (в самом файле не используются).
**Fix:** передавать зависимости явно (параметр `runner=subprocess.run`) или патчить `assistant_shared.security.runner.subprocess` в тестах; удалить неиспользуемые импорты.

### WR-06: `init_db` блокирует event loop и берёт приватный `_conn` aiosqlite

**File:** `/opt/assistant-core/src/storage/db.py:56-60,94`
**Issue:** `run_migrations` синхронный и выполняется внутри `async def` (CLAUDE.md требует async-first для I/O). С busy_timeout 30 с он может блокировать event loop демона. В ветке `:memory:` в мигратор передаётся приватный `conn._conn` — sqlite3-соединение, которым владеет рабочий поток aiosqlite. Это работает только потому, что соединение открыто с `check_same_thread=False` (в `test_migrations_aiosqlite_in_memory_connection` то же самое). Для соединения из `get_async_connection` (по умолчанию `check_same_thread=True`) такой вызов бросил бы `ProgrammingError`. Поддержка `_connection` в `_extract_sqlite_conn` — мёртвая ветка.
**Fix:** выполнять миграции через `await asyncio.to_thread(run_migrations, self.db_path)`; для `:memory:` использовать `conn.run`/`await conn.executescript` либо отдельный асинхронный API мигратора.

### WR-07: Таблицы вне владельца схемы и дублирование DDL

**File:** `/opt/assistant-core/src/storage/db.py:61-91,96-125`
**Issue:** `bot_command_settings`, `bot_custom_aliases`, `dialog_feedback_log` создаются прямо в `init_db`, а не миграцией, то есть «единый владелец схемы» (DAT-01) нарушен: версии `schema_migrations` их не знают, а chat-app получит схему без них. Один и тот же DDL скопирован в двух ветках (`:memory:` и файл). Для production-БД они уже существуют (подтверждено), но свежая БД получит их только при старте assistant-core. Chat-app сам миграции не применяет, поэтому на пустой БД, где первым стартовал chat-app, `get_persona` вернёт `None` и все эндпоинты безопасности ответят 503.
**Fix:** перенести три `CREATE TABLE` в `0003_*.sql`; в chat-app применять `run_migrations` на старте (lifespan) либо явно проверять `get_schema_version()` и отдавать понятную ошибку.

### WR-08: SQL-функция `lower` падает на не-строках и подменяет встроенную

**File:** `/opt/assistant-shared/assistant_shared/db/connection.py:36,54`, `/opt/assistant-core/src/storage/db.py:43`
**Issue:** Python-реализация `lambda s: s.lower() if s is not None else None` бросает `AttributeError` для INTEGER/BLOB. `SELECT lower(id) FROM projects` даёт `OperationalError: user-defined function raised exception` (воспроизведено), хотя встроенная `lower` вернула бы текст. Функция также не помечена `deterministic=True`, поэтому её нельзя использовать в индексах и генерируемых колонках. Реализация продублирована в трёх местах.
**Fix:**
```python
def _lower(v):
    return v.casefold() if isinstance(v, str) else v
conn.create_function("lower", 1, _lower, deterministic=True)
```
вынести в одну функцию в `connection.py`.

### WR-09: `install_hooks.sh` и pre-commit hook: хрупкая установка и неполная защита

**File:** `/opt/chat-app/scripts/install_hooks.sh:8-15` (идентично `/opt/assistant-core/scripts/install_hooks.sh`), `/opt/chat-app/.githooks/pre-commit:7-14`
**Issue:**
- `[ ! -d "${GIT_DIR}" ]` отвергает worktree и submodule (там `.git` — файл) с ошибкой «не является Git-репозиторием».
- `mkdir -p` затем `chmod +x pre-commit`: если файла нет, `set -e` обрывает установку криптичной ошибкой `chmod`.
- `git config core.hooksPath .githooks` молча перезаписывает ранее настроенный `hooksPath` (husky, чужие хуки) без предупреждения.
- Скрипт не проверяет, что Python-окружение умеет импортировать `assistant_shared`; hook в этом случае падает с кодом ≠ 0 уже при коммите.
- В hook при незаданном `VIRTUAL_ENV` первым кандидатом становится `/bin/python` (если он есть — системный Python без пакета).
- Сообщение shield говорит «Commit or push blocked», но pre-push hook не устанавливается, а `git commit --no-verify` обходит всё. Серверной проверки нет.
- Скрипты установки дублируются побайтово в двух репозиториях.

**Fix:** использовать `git -C "$REPO_DIR" rev-parse --git-dir`; проверять наличие hook-файла; предупреждать/запрашивать подтверждение при существующем `core.hooksPath`; после установки запускать smoke-проверку `python -c "import assistant_shared.security"`; пропускать пустые кандидаты (`[ -n "${VIRTUAL_ENV:-}" ]`).

### WR-10: Гейт — хеш боевой БД ненадёжен при WAL; боевая БД копируется впустую

**File:** `/opt/chat-app/scripts/gate.py:100-116,503-543`
**Issue:**
- Боевая БД в режиме WAL (`PRAGMA journal_mode` вернул `wal`; WAL включён фабрикой соединений Фазы 4). Записи попадают в `-wal`, а `db_unchanged_check` хеширует только основной файл. Запись тестов assistant-core в боевую БД (для них БД не переопределяется, защита — только хеш) может остаться незамеченной до checkpoint. И наоборот: работающий демон выполняет checkpoint, и хеш меняется без всякой вины тестов, давая нестабильный красный итог.
- chat-app-тесты после DAT-04 используют изолированную БД из `conftest.persona_session_db` (она перезаписывает `settings.SQLITE_DB_PATH`), так что копия боевой БД (`make_db_copy`) больше не используется chat-app-тестами, но гейт по-прежнему копирует боевую БД с почтой, памятью и т.п. во временный каталог и красит итог при её отсутствии. Комментарий «единственная точка замены в Фазе 4» не выполнен.

**Fix:** сравнивать результат `sqlite3 backup()`/`PRAGMA data_version`+содержимое таблиц (например хеш `iterdump()` через `mode=ro`) или хеш всех трёх файлов с принудительным `wal_checkpoint`; убрать копирование боевой БД и `chat_pytest_env` для chat-app либо использовать БД из мигратора.

### WR-11: Сама библиотека безопасности `assistant-shared` не защищена и не тестируется

**File:** `/opt/assistant-shared/` (репозиторий целиком), `/opt/chat-app/scripts/gate.py:501-543`
**Issue:** У репозитория `assistant-shared` нет собственных тестов, нет `.githooks`, он не входит в гейт (pytest, import-linter, shield запускаются только для двух репозиториев). Код с паттернами секретов и миграциями меняется без прогона какой-либо проверки, а тесты лежат в чужих репозиториях (`chat-app/backend/tests`) и зависят от наличия `/opt/assistant-shared` по абсолютному пути. Обёртки `security_shield.py` дополнительно добавляют `/opt/assistant-shared` в `sys.path` при `ImportError`, что маскирует сломанную установку.
**Fix:** перенести `test_security_shared.py`, `test_migrations.py`, `test_concurrent_write.py` в `assistant-shared/tests`, установить hook и добавить репозиторий в `gate.py`.

### WR-12: Небезопасные значения по умолчанию в `config.py` и скрытое создание пустой БД

**File:** `/opt/chat-app/backend/app/core/config.py:11-24`
**Issue:** `DEBUG=True`, `HOST="0.0.0.0"`, `CORS_ORIGINS=["*"]`, а `main.py` включает `allow_credentials=True` с `allow_methods/headers=["*"]`. Аутентификации на маршрутах нет (в `app` не найдено `Depends`/auth). Эндпоинты `/api/v1/security/overview` и `/audit` отдают любому клиенту сети пути, remote и e-mail автора рабочих пространств, включая NDA. Сервис уже запущен с `--host 0.0.0.0`. Дополнительно `SQLITE_DB_PATH="./data/assistant.db"` относителен к cwd (`WorkingDirectory=/opt/chat-app/backend`): при отсутствии переменной окружения `get_async_connection` молча создаёт пустую БД `/opt/chat-app/backend/data/assistant.db` (каталог `_ensure_parent_dir` создаёт сам), что даёт «раздвоение» БД между chat-app и assistant-core. Для общей БД путь должен быть обязательным.
**Fix:** `DEBUG=False`, `HOST="127.0.0.1"` по умолчанию, явный список `CORS_ORIGINS`, авторизация на `/security/*`; убрать значение по умолчанию у `SQLITE_DB_PATH` (или fail при отсутствии файла в production), не создавать БД в `get_async_connection` для читающих сервисов.

### WR-13: Блокирующие `subprocess` внутри `async` обработчиков безопасности

**File:** `/opt/chat-app/backend/app/api/v1/security.py:557,599` (вызовы `audit_path`), `/opt/assistant-shared/assistant_shared/security/runner.py:12-19`
**Issue:** `audit_path` синхронный: до трёх git-вызовов с таймаутом 15 с на пространство плюс чтение до 100 файлов. Он вызывается прямо в `async def`, поэтому один медленный репозиторий (NFS, большой индекс) блокирует event loop всего chat-app, включая WebSocket-стриминг и обращения к БД с WAL. Это ошибка корректности под нагрузкой, а не оптимизация.
**Fix:** `res = await asyncio.to_thread(audit_path, p_path, nda_rule=nda_rule_for(p))`.

### WR-14: Надёжность тестов: связь с боевым assistant-core, закрепление fail-open

**File:** `/opt/chat-app/backend/tests/conftest.py:44-58`, `/opt/chat-app/backend/tests/test_database_isolated.py:23,31`, `/opt/chat-app/backend/tests/test_nda_equivalence.py:179-191,150-155`, `/opt/chat-app/backend/tests/test_migrations.py:121-178`
**Issue:**
- `_get_default_persona` вставляет `/opt/assistant-core` в `sys.path` и импортирует боевой `src.persona.loader`, хотя докстринг модуля обещает, что «каталог assistant-core во время тестов недоступен и не используется» (DAT-04, D-10). `except Exception: pass` скрывает сбой загрузки и переключает на статическую фикстуру, поэтому набор тестов может зависеть от окружения. `test_database_isolated` жёстко ожидает `len(workspaces) == 4`, то есть привязан к текущему `persona.yaml`.
- `test_n08_*` и `test_n05_*` утверждают, что репозиторий с секретом после 100-го файла и NDA-репозиторий без origin — «чисто». Такие характеризационные тесты закрепляют дефекты CR-04/CR-05 как требуемое поведение и будут ломаться при исправлении.
- `test_pre_commit_hook.py` не содержит случаев rename, не-ASCII, частичного индексирования, вызова с `--all` (CR-01..CR-03). Конкурентный тест не проверяет конкурентные миграции (CR-06), baseline-тест не доходит до фолбэка (WR-01).
- `test_s06` проверяет `len(names) == 7` — хрупкая привязка к числу паттернов.

**Fix:** убрать импорт боевого loader из conftest (оставить статическую фикстуру); переписать N05/N08 как ожидание нарушения; добавить перечисленные регрессионные тесты.

## Info

### IN-01: `0002_pending_confirmations.sql` без ограничений целостности

**File:** `/opt/assistant-shared/assistant_shared/db/migrations/0002_pending_confirmations.sql:2-14`
**Issue:** Для HITL-таблицы нет `CHECK (status IN ('pending','confirmed','rejected','expired'))`, `CHECK (channel IN (...))`; `persona_id` без `REFERENCES personas(id)`; `created_at/expires_at` хранятся `TEXT` без согласованного формата (сравнение `expires_at < now` корректно только для единого ISO-формата с одной временной зоной). В `0001` те же ограничения для `workspaces.clearance` использованы, то есть подход непоследователен.
**Fix:** добавить `CHECK` и внешний ключ в следующей миграции (SQLite потребует пересоздание таблицы), документировать формат времени (UTC ISO-8601).

### IN-02: Имена столбцов в `UPDATE` собираются из ключей словаря

**File:** `/opt/chat-app/backend/app/db.py:218-221,314-317,380-383,457-460`
**Issue:** `f"{k} = ?" for k in data.keys()` подставляет ключи прямо в SQL. Сейчас безопасно только потому, что вызывающий код передаёт `model_dump(exclude_unset=True)` Pydantic-моделей; сам сервисный слой любую строку не отвергает (внутренний вызов с ключом из внешних данных даёт SQL-инъекцию). Функции ещё и мутируют переданный `data` (добавляют `updated_at`).
**Fix:** проверять ключи по белому списку столбцов таблицы и не мутировать вход (`data = {**data, "updated_at": ...}`).

### IN-03: `get_persona` / `list_workspaces` трактуют любой `OperationalError` как «персоны нет»

**File:** `/opt/chat-app/backend/app/db.py:40-41,63-64`
**Issue:** `database is locked` или повреждённый файл превращается в `None`/`[]`, затем в ответ 503 «рабочие пространства не загружены» или `PersonaNotLoadedError`. Для fail-closed безопасно, но маскирует настоящую причину при диагностике WAL-конфликтов.
**Fix:** перехватывать только сообщение `no such table`, остальные ошибки логировать и пробрасывать.

### IN-04: Ключевые слова NDA сравниваются с учётом регистра

**File:** `/opt/assistant-shared/assistant_shared/security/auditor.py:53-58`
**Issue:** `kw in line` не находит `TYDEX_INTERNAL_SECRET`, `Golay_Calibration_Key`. Остальные проверки (`normalize_remote`) используют `casefold`. Кроме того, чтение с `errors="ignore"` не распознаёт файлы в UTF-16.
**Fix:** сравнивать `kw.casefold() in line.casefold()`.

---

_Reviewed: 2026-10-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
