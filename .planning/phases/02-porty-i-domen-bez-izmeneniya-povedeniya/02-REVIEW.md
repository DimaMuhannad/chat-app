---
phase: 02-porty-i-domen-bez-izmeneniya-povedeniya
reviewed: 2026-10-02T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - /opt/assistant-core/.importlinter
  - /opt/assistant-core/src/brain/secretary_dialog.py
  - /opt/assistant-core/src/calendar/provider.py
  - /opt/assistant-core/src/composition.py
  - /opt/assistant-core/src/connectors/aadhk/provider.py
  - /opt/assistant-core/src/connectors/guap_lms/provider.py
  - /opt/assistant-core/src/core/__init__.py
  - /opt/assistant-core/src/core/domain/__init__.py
  - /opt/assistant-core/src/core/domain/entities.py
  - /opt/assistant-core/src/core/domain/events.py
  - /opt/assistant-core/src/core/events/__init__.py
  - /opt/assistant-core/src/core/events/bus.py
  - /opt/assistant-core/src/core/ports/__init__.py
  - /opt/assistant-core/src/core/ports/clients.py
  - /opt/assistant-core/src/core/ports/connectors.py
  - /opt/assistant-core/src/notifier/bot_handler.py
  - /opt/assistant-core/src/notifier/live_ticker.py
  - /opt/assistant-core/src/parser/provider.py
  - /opt/assistant-core/tests/test_composition_di.py
  - /opt/assistant-core/tests/test_core_architecture.py
  - /opt/assistant-core/tests/test_core_domain.py
  - /opt/assistant-core/tests/test_core_events.py
  - /opt/assistant-core/tests/test_ports_conformance.py
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 02: Отчёт о код-ревью

**Reviewed:** 2026-10-02
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Проверен рефакторинг портов/адаптеров, DI через корень композиции и EventBus. Прогон подтвердил: 84 теста phase-02 проходят, `lint-imports` — 4 контракта KEPT, 0 broken. Поведенческая эквивалентность изменённых хунков `bot_handler.py`, `secretary_dialog.py`, `live_ticker.py` подтверждена: ленивые импорты в `composition.py` сохраняют работоспособность патчей модулей-источников, ветки try/except остались на тех же местах.

Критических (BLOCKER) дефектов не найдено. Основные замечания: DI для табеля неполный (путь Google Drive обходит внедрённый провайдер), адаптер ЛК публикует деструктивные операции без реального HITL-гейта (декларативная пометка), риск `"None"` в `submission_id`, смешение naive/aware datetime между сущностями и событиями.

Известный дефект `cur_m_name` (NameError в `/timesheet`, `bot_handler.py:1122`) заморожен характеризационным тестом намеренно и в новые находки не включён (см. IN-06).

## Warnings

### WR-01: `list_tasks` порождает `submission_id == "None"` для заданий без разобранного id

**File:** `/opt/assistant-core/src/connectors/guap_lms/provider.py:46`
**Issue:** `GuapLmsClient.list_tasks` кладёт `"id": task_id`, где `task_id = None`, если ссылка не совпала с regexp `/tasks/(\d+)/show` (client.py:~160-185). Адаптер делает `str(row["id"])` и получает строку `"None"`. Несколько таких заданий дадут одинаковые `submission_id`, а следующая фаза, привязав к этому id `delete_task`/`set_task_visibility`, обратится к несуществующему/неверному заданию. Тест `test_lms_list_tasks_maps_to_academic_submission` этот случай не покрывает.
**Fix:**
```python
return [
    AcademicSubmission(
        submission_id=str(row["id"]),
        ...
    )
    for row in rows
    if row.get("id") is not None  # строки без id не являются адресуемыми заданиями
]
```
и добавить тест со строкой `{"id": None, ...}`.

### WR-02: Деструктивные операции ЛК в адаптере выполняются без гейта; `REQUIRES_CONFIRMATION` только декларативна

**File:** `/opt/assistant-core/src/connectors/guap_lms/provider.py:68-72`, `/opt/assistant-core/src/core/ports/connectors.py:136-143`
**Issue:** CLAUDE.md требует HITL-гейт для любых деструктивных действий. `GuapLmsProvider.delete_task` напрямую вызывает `client.delete_task` (так же `set_task_visibility` публикует задание студентам). Пометка `REQUIRES_CONFIRMATION` ничем не проверяется, а единственная защита — тест `test_lms_provider_not_wired_into_production`, который ищет подстроку `"GuapLmsProvider"` в нескольких файлах. Любой код, получивший `BaseLMSProvider` через DI (в том числе под другим именем/через composition), удалит задание без подтверждения.
**Fix:** сделать гейт частью контракта адаптера уже сейчас, например:
```python
async def delete_task(self, task_id, semester_id=..., *, confirmed: bool = False) -> bool:
    if not confirmed:
        raise PermissionError("delete_task требует подтверждения человека (HITL)")
    return await asyncio.to_thread(self._client.delete_task, task_id, semester_id)
```
(в `semester_id` пробрасывать только переданное значение, чтобы не дублировать дефолт), либо вынести `REQUIRES_CONFIRMATION`-проверку в общий декоратор адаптера.

### WR-03: Внедрённый `timesheet_service` обходится на пути синхронизации Google Drive

**File:** `/opt/assistant-core/src/notifier/bot_handler.py:1158-1168`, `/opt/assistant-core/src/connectors/gdrive/client.py:244-255`
**Issue:** `cb_timesheet_sync` вызывает `client.sync_aadhk_from_drive(self.db)`, а тот внутри сам создаёт `AadhkIngestionService(db)` и сам делает ingest. После этого бот вызывает `reconcile_all_conflicts()` на `self._timesheet()` (внедрённом). Итог: при подмене провайдера (другой коннектор табеля) ингест идёт в Aadhk, а пересчёт конфликтов — в подменённом; DI формально есть, а на деле смешение двух реализаций. Тест `test_bot_uses_injected_timesheet_service` скрывает это, потому что фейковый Drive ничего не ингестит. Кроме того, адаптер gdrive напрямую зависит от адаптера aadhk (связность между коннекторами).
**Fix:** сменить контракт `DriveClientLike`: `download_latest_aadhk_backup() -> Path | None`, а ингест выполнять в боте через `self._timesheet().ingest_backup_file(path)`; либо передавать провайдера в `sync_aadhk_from_drive(db, timesheet=...)`. Как минимум — зафиксировать ограничение в docstring порта и в `clients.py`.

### WR-04: Смешение naive и aware datetime в доменной модели

**File:** `/opt/assistant-core/src/connectors/guap_lms/provider.py:22`, `/opt/assistant-core/src/core/domain/entities.py:35-36,55,75`, `/opt/assistant-core/src/core/domain/events.py:17`
**Issue:** `DomainEvent.occurred_at` — aware UTC, а `AcademicSubmission.deadline` (из `_parse_deadline` → `strptime`) — naive, `ScheduleEvent.starts_at/ends_at`, `EmailMessage.received_at` не оговаривают зону. Проект работает в `config.TZ` (Europe/Moscow). Сравнение naive с aware (`deadline < datetime.now(timezone.utc)`) даёт `TypeError`, а неявная интерпретация naive как UTC сдвинет срок на 3 часа. Контракт зоны нигде не зафиксирован и не проверяется.
**Fix:** в `_parse_deadline` возвращать `...replace(tzinfo=ZoneInfo(config.TZ))` (адаптеру разрешено знать `config`), а в сущностях документировать/валидировать «всегда aware» (`__post_init__` с проверкой `tzinfo is not None`) и добавить тест.

## Info

### IN-01: `health_check` у адаптеров практически тавтологичен

**File:** `/opt/assistant-core/src/connectors/aadhk/provider.py:25`, `/opt/assistant-core/src/parser/provider.py:26`, `/opt/assistant-core/src/calendar/provider.py:25`
**Issue:** `service.db is not None` (всегда истинно после конструктора), `bool(parser.base_url)` (у `ScheduleParser` дефолт непустой). Для календаря `dry_run=True` даёт `False` при полностью рабочем клиенте. Тест `test_health_check_is_offline` фиксирует `True` для schedule/timesheet, т.е. закрепляет бессмысленную проверку. Потребители будущего реестра коннекторов не отличат живой коннектор от мёртвого.
**Fix:** хотя бы проверять наличие доступных учётных данных/файла БД без сети, либо переименовать/задокументировать как «конфигурация присутствует».

### IN-02: EventBus — последовательный await без таймаута, нет отписки; docstring про «без содержимого» неточен

**File:** `/opt/assistant-core/src/core/events/bus.py:25-43`
**Issue:** (1) `publish` ждёт каждого подписчика по очереди: один зависший async-обработчик блокирует издателя и всех остальных, таймаута нет. (2) Нет `unsubscribe`, один и тот же обработчик можно подписать дважды (двойная доставка) — утечка подписчиков при динамической подписке. (3) `logger.exception` пишет traceback, а в тексте исключения обработчика может быть содержимое события; docstring утверждает, что содержимое не журналируется (тест проверяет только маркер в поле события, но не текст исключения).
**Fix:** добавить `unsubscribe`, дедупликацию (`if handler not in lst`), `asyncio.wait_for` с настраиваемым лимитом; в логе использовать `exc_info` без пользовательского текста или обновить docstring.

### IN-03: Тернарная логика «внедрённый или по умолчанию» продублирована трижды

**File:** `/opt/assistant-core/src/brain/secretary_dialog.py:143`, `/opt/assistant-core/src/notifier/live_ticker.py:118-122`, `/opt/assistant-core/src/notifier/bot_handler.py:94-98`
**Issue:** одна и та же конструкция `x if x is not None else default_timesheet_service(db)` в трёх местах; отличается только форма записи.
**Fix:** общий хелпер в `src/composition.py`, например `resolve_timesheet_service(injected, db)`, и вызывать его в трёх местах.

### IN-04: Хрупкие места в тестах

**File:** `/opt/assistant-core/tests/test_composition_di.py:155,426,451`, `/opt/assistant-core/tests/test_core_events.py:269-284`, `/opt/assistant-core/tests/test_ports_conformance.py:268-278`
**Issue:** (1) `UPLOAD_PATH` — боевой каталог `/opt/chat-app/uploads`, а `assert not Path(UPLOAD_PATH).exists()` упадёт, если файл с таким именем окажется там (каталог реально содержит пользовательские файлы). Предпочтительнее подменять директорию загрузок. (2) Тесты «не подключено» (`not_wired_into_production`) ищут подстроки в тексте исходников: ложно сработают на docstring/комментарий, и пропустят подключение через алиас. (3) `isinstance` для `runtime_checkable` Protocol проверяет только имена атрибутов — компенсировано `iscoroutinefunction`, но сигнатуры по-прежнему не проверяются (адаптеры принимают `*args, **kwargs`, расхождение с портом не будет поймано).
**Fix:** вынести путь загрузок в атрибут/конфиг и патчить его в тесте; для (3) добавить сверку `inspect.signature` или прогон mypy/pyright по протоколам.

### IN-05: Адаптер ЛК: `submit_grade` не поддерживается; общий `requests.Session` в нескольких потоках

**File:** `/opt/assistant-core/src/connectors/guap_lms/provider.py:77-81,43-75`
**Issue:** адаптер проходит `isinstance(..., BaseLMSProvider)`, но обязательный метод порта `submit_grade` всегда бросает `NotImplementedError` — контракт порта обещает больше, чем есть. Кроме того, каждый вызов уходит в `asyncio.to_thread` на одном `requests.Session`; одновременные `gather`-вызовы выполняют `ensure_authenticated`/login параллельно и не потокобезопасны.
**Fix:** вынести `submit_grade` из `BaseLMSProvider` в отдельный опциональный протокол; обернуть вызовы клиента в `asyncio.Lock`.

### IN-06: Заморожено/дорелизное, не относится к diff (справочно)

**File:** `/opt/assistant-core/src/notifier/bot_handler.py:1122`, `:1056-1057`
**Issue:** (1) Известный `NameError: cur_m_name` в `/timesheet` — намеренно не чинится, заморожен тестом `test_cmd_timesheet_characterization`. (2) Предсуществующее: `dest_path = f"/opt/chat-app/uploads/{doc.file_name}"` без санитизации имени (`../`) — доступно только авторизованному владельцу, но стоит `Path(name).name`.
**Fix:** (1) отдельная задача из backlog; (2) `dest_filename = Path(doc.file_name).name`.

---

_Reviewed: 2026-10-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
