# Phase 9: Dynamic Menu & Interface - Plan 09-01 Summary (Wave 1)

**Дата:** 2026-10-07
**Статус:** Выполнено успешно (100% GREEN)
**Требования:** UXQ-01, D-01
**Связанный план:** `09-01-PLAN.md`

---

## 1. Выполненные задачи

### 09-01-01: Создание таблиц настроек команд в SQLite и модуля commands.py
- В файле `src/storage/db.py`:
  * В метод `Database.init_db()` добавлены DDL-скрипты создания таблиц:
    ```sql
    CREATE TABLE IF NOT EXISTS bot_command_settings (
        command_name TEXT PRIMARY KEY,
        is_enabled INTEGER NOT NULL DEFAULT 1,
        custom_description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS bot_custom_aliases (
        alias TEXT PRIMARY KEY,
        canonical_command TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ```
  * Реализованы асинхронные методы:
    - `get_command_settings() -> dict[str, dict[str, Any]]`
    - `set_command_setting(command_name: str, is_enabled: bool, custom_description: str | None = None)`
    - `get_custom_aliases() -> dict[str, str]`
    - `set_custom_alias(alias: str, canonical_command: str)`
    - `remove_custom_alias(alias: str) -> bool`
- Создан модуль `src/notifier/commands.py`:
  * Датакласс `CommandSpec` с валидацией имени по стандарту Telegram Bot API (`^[a-z0-9_]{1,32}$`).
  * Класс `CommandRegistry` с динамической фильтрацией по активным коннекторам персоны (`schedule_source`, `timesheet`, `lms`, `mail`, `academic`).
  * Методы `get_active_commands()`, `get_telegram_commands()`, `resolve_command_or_alias()`.

### 09-01-02: Интеграция CommandRegistry в bot_handler.py и модульные тесты
- В файле `src/notifier/bot_handler.py`:
  * В `EmailBotHandler.__init__` инициализирован `self.command_registry = CommandRegistry(db=self.db, persona_getter=current_persona)`.
  * Переписан метод `setup_bot_commands()`: отказ от жестко зашитого списка команд в пользу `await self.command_registry.get_telegram_commands()`.
  * Добавлено логирование категорий зарегистрированных команд.
- Создан файл модульных тестов `tests/test_command_registry.py`:
  * `test_command_registry_default_catalog`: проверка базового набора из 9 команд и валидации латиницы.
  * `test_command_registry_disable_connector`: проверка исчезновения команд при отключении коннектора.
  * `test_command_registry_db_settings_override`: проверка применения переопределений из SQLite.
  * `test_command_registry_resolve_aliases`: проверка дефолтных и кастомных алиасов.
  * `test_command_spec_name_validation`: проверка запрета недопустимых символов и кириллицы в слагах.

---

## 2. Результаты тестов

- `pytest tests/test_command_registry.py tests/test_bot_menu.py`:
  ```
  8 passed in 10.40s
  ```
- Quality Gate: проверяется через `scripts/gate.py`.

---

## 3. Измененные и созданные файлы

```diff
+ /opt/assistant-core/src/notifier/commands.py (+313)
+ /opt/assistant-core/tests/test_command_registry.py (+87)
M /opt/assistant-core/src/storage/db.py (+92)
M /opt/assistant-core/src/notifier/bot_handler.py (+15, -18)
```
