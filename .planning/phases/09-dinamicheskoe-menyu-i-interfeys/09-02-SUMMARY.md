# Phase 9: Dynamic Menu & Interface - Plan 09-02 Summary (Wave 2)

**Дата:** 2026-10-07  
**Статус:** Выполнено успешно (100% GREEN)  
**Требования:** UXQ-02, D-02  
**Связанный план:** `09-02-PLAN.md`  

---

## 1. Выполненные задачи

### 09-02-01: Подключение CommandRegistry к FastIntentRouter для мгновенного fast-path сопоставления (< 10 мс)
- В файле `/opt/assistant-core/src/brain/intent_router.py`:
  * Расширен набор `VALID_ACTIONS` новыми действиями: `"today"`, `"help"`, `"undo_clear"`, `"menu"`, `"lms"`.
  * В конструктор `FastIntentRouter.__init__` добавлен параметр `command_registry: CommandRegistry | None = None`.
  * В метод `route` на шаге 0 (до сетевых вызовов LLM и тяжелых эвристик) добавлен опрос `self.command_registry.resolve_command_or_alias(cleaned)`. При обнаружении совпадения мгновенно формируется и возвращается `IntentResult` с `model="fast-rule"`, `confidence=1.0`, замеренной `latency_ms` (< 10 мс) и фиксацией в аудит-логе `_audit(user_id, cleaned, res)`.
  * Добавлены детерминированные шорткаты для действий `today`, `help`, `undo_clear`, `menu` в случае работы без реестра.
- В файле `/opt/assistant-core/src/notifier/commands.py`:
  * Удален конфликтный синоним `"меню"` из `help.default_aliases`, чтобы интент `/menu` не перехватывался справкой.
  * Улучшен алгоритм сопоставления в `resolve_command_or_alias`: поддержка точного сопоставления как первого токена (`word`), так и всей входящей строки (`cleaned`).

### 09-02-02: Диалоговое управление видимостью команд и персональными алиасами в bot_handler.py
- В файле `/opt/assistant-core/src/notifier/bot_handler.py`:
  * В `EmailBotHandler.__init__` инициализирован `self.command_registry` до роутера и передан в `FastIntentRouter(db=self.db, command_registry=self.command_registry)`.
  * В aiogram router зарегистрирована команда `Command("menu")` на метод `handle_cmd_menu`.
  * В `handle_user_text` перед классификацией интентов добавлены регулярные выражения для диалогового управления:
    1. **Скрытие команд/категорий:** `^скрой\s+(?:команды\s+)?(lms|лабы|табель|часы|почт[уа]|расписание|пары|методист[а]?)` -> сохранение `is_enabled=False` в SQLite, немедленная перерегистрация меню через `setup_bot_commands()`, ответ: `🙈 Команда **/{canonical}** скрыта из меню Telegram.`
    2. **Показ/восстановление команд:** `^(?:покажи|верни)\s+(?:команды\s+)?(lms|лабы|табель|часы|почт[уа]|расписание|пары|методист[а]?)` -> сохранение `is_enabled=True`, `setup_bot_commands()`, ответ: `👁️ Команда **/{canonical}** возвращена в меню Telegram.`
    3. **Создание персональных алиасов:** `^(?:называй|алиас|псевдоним)\s+/?([a-z0-9_а-яё]+)\s+(?:как|=)\s+/?([a-z0-9_а-яё]+)` -> нормализация, валидация через реестр команд, защита системных команд от перехвата (T-09-03: `cancel`, `clear`, `undo_clear`), сохранение в `bot_custom_aliases`, синхронизация меню, ответ: `🏷️ Псевдоним **/{alias}** привязан к команде **/{canonical}**.`
    4. **Удаление персональных алиасов:** `^удали\s+алиас\s+/?([a-z0-9_а-яё]+)` -> удаление из БД, синхронизация меню, ответ: `🗑️ Псевдоним **/{alias}** удален.`
  * В блоке диспетчеризации `handle_user_text` добавлены ветви:
    - `route_res.action in ("today", "schedule")` -> `self.handle_cmd_today(message)`
    - `route_res.action in ("lms", "lms_tasks")` -> `self.handle_cmd_lms_tasks(message)`
    - `route_res.action in ("undo_clear", "undo")` -> `self.handle_cmd_undo_clear(message)`
    - `route_res.action in ("help", "start")` -> `self.handle_cmd_help(message)`
    - `route_res.action == "menu"` -> `self.handle_cmd_menu(message)`
  * Реализован метод `handle_cmd_menu(self, message: Message)`: вывод статуса каталога (🟢 активна / ⚪ отключена), списка кастомных алиасов и подсказок по диалоговому управлению.

---

## 2. Результаты тестов и верификации

- **Модульные тесты реестра и меню:**
  `pytest tests/test_command_registry.py tests/test_bot_menu.py`:
  ```
  8 passed in 10.38s (100% PASS)
  ```
- **Модульные тесты FastIntentRouter:**
  `pytest tests/test_fast_intent_router.py`:
  ```
  13 passed in 4.79s (100% PASS)
  ```
- **Тесты снимков системных промптов:**
  `pytest tests/test_prompt_snapshot.py`:
  ```
  19 passed in 4.12s (100% PASS, байт-в-байт соответствие)
  ```
- **Сканер утечек токенов персоны:**
  `pytest tests/test_hardcode_scanner.py`:
  ```
  3 passed in 0.51s (100% PASS)
  ```
- **Архитектурный линтер (Dependency Inversion):**
  `lint-imports`:
  ```
  Contracts: 5 kept, 0 broken.
  use-cases (brain) не импортируют адаптеры KEPT
  ```
- **Quality Gate (`/opt/chat-app/scripts/gate.py`):**
  ```
  Гейт качества

  Репозиторий     Проверка                               Результат
  chat-app        pytest — тестов: 171                   ✓
  chat-app        import-linter                          ✓
  assistant-core  pytest — тестов: 409                   ✓
  assistant-core  import-linter                          ✓
  chat-app        security_shield (--all)                ✓
  assistant-core  security_shield (--all)                ✓
  оба             синтетическая персона (дрейф SHA-256)  ✓
  оба             токены персоны (дрейф SHA-256)         ✓
  оба             боевая assistant.db не изменена        ✓

  ИТОГ: ЗЕЛЁНЫЙ
  ```

---

## 3. Измененные файлы

```diff
M /opt/assistant-core/src/brain/intent_router.py (+70, -2)
M /opt/assistant-core/src/notifier/commands.py (+11, -8)
M /opt/assistant-core/src/notifier/bot_handler.py (+99, -7)
+ /opt/chat-app/.planning/phases/09-dinamicheskoe-menyu-i-interfeys/09-02-SUMMARY.md
```
