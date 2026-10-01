---
last_mapped_commit: ee863eccdcc4889896a20f28c0c29a4e0ebe17b7
last_mapped_at: 2026-10-01
---
# Проблемы кодовой базы

**Дата анализа:** 2026-10-01

## Техдолг

### Сцепление с внешней БД `/opt/assistant-core`

**Проблема:** Конфигурация содержит абсолютный путь к БД другого репозитория
- **Файлы:** `backend/app/core/config.py:19`
- **Код:** `SQLITE_DB_PATH: str = "/opt/assistant-core/data/assistant.db"`
- **Влияние:** 
  - chat-app зависит от наличия и схемы `/opt/assistant-core`, нарушает разделение ответственности
  - Миграции и версионирование схемы БД живут в другом репозитории, но используются здесь
  - Невозможно развернуть chat-app отдельно от assistant-core без переконфигурации пути
  - При изменении схемы в assistant-core chat-app может сломаться без явного обновления
- **Подход к исправлению:**
  - Фаза 3 архитектурного плана: переехать на отдельную БД для chat-app (`data/chat.db`) с синхронизацией через EventBus
  - На переходный период: использовать read-only реплику или двойную запись
  - Описано подробно в `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` (Фаза 3)

### CORS открыт полностью

**Проблема:** Доступ разрешён с любых источников
- **Файлы:** `backend/app/core/config.py:16`, `backend/app/main.py:37-43`
- **Код:** `CORS_ORIGINS: List[str] = ["*"]`
- **Влияние:** 
  - Любой веб-сайт может делать запросы к API (CSRF-риск)
  - Особенно опасно для операций DELETE без защиты (см. раздел HITL ниже)
  - Credentials отправляются по кроссдоменным запросам (`allow_credentials=True`)
- **Подход к исправлению:**
  - Ограничить CORS_ORIGINS только до ожидаемых источников (localhost, домен студии)
  - Удалить `allow_credentials=True` если не требуется для cookie-auth
  - Для разработки: использовать переменную окружения CORS_ALLOWED_ORIGINS

### Реестр проектов захардкоден в коде

**Проблема:** Список рабочих проектов и их настройки живут в security.py как Python-константа
- **Файлы:** `backend/app/api/v1/security.py:31-68`
- **Структура:**
  ```python
  PROJECTS_REGISTRY = [
      {"id": "chat-app", "path": "/opt/chat-app", ...},
      {"id": "assistant-core", "path": "/opt/assistant-core", ...},
      {"id": "tydex-optics", "path": "/opt/work-tydex", ...},
      {"id": "guap-physics", "path": "/opt/personal/guap-physics", ...},
  ]
  ```
- **Влияние:**
  - Изменение рабочих пространств требует правки Python-кода и перезагрузки сервиса
  - При мультитенантности нужна БД, а не реестр в памяти
  - Hardcoded параметры `is_tydex` зависят от id проекта (строка 95: `if "github.com/DimaMuhannad" in origin_url`)
- **Подход к исправлению:**
  - Фаза 2 архплана: переехать PROJECTS_REGISTRY → `workspaces` таблица в SQLite
  - Добавить таблицу `personas` с управлением на уровне данных
  - REST API для добавления/удаления рабочих пространств
  - Описано в `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` раздел 3.2

### Дефолтные значения "ГУАП" жёстко вписаны

**Проблема:** Имя организации захардкодено в нескольких местах как дефолт для новых сущностей
- **Файлы:** 
  - `backend/app/db.py:149` — дефолт при создании проекта
  - `backend/app/db.py:244` — дефолт при создании задачи
  - `backend/app/models/dashboard_schemas.py:8` — дефолт в Pydantic-схеме
  - `backend/app/models/dashboard_schemas.py:33` — дефолт в схеме задачи
- **Влияние:**
  - Универсализация платформы невозможна: любой новый пользователь будет автоматически создавать задачи в "ГУАП"
  - При работе с несколькими персонами нужно переопределять area вручную
- **Подход к исправлению:**
  - Фаза 2: дефолты → `config/persona.yaml`
  - DatabaseService конструируется с текущей persona, которая предоставляет default_area
  - Тесты переписываются на проверку через загруженную персону
  - Описано в `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` раздел 5

### Hardcoded имена и титулы в интерфейсе

**Проблема:** Статический HTML содержит личные данные конкретного пользователя
- **Файлы:** `backend/app/static/index.html`
- **Примеры:**
  - `<p>Попов Д.А. • ГУАП / Тидекс</p>`
  - `filterTasks('ГУАП')` в JavaScript
  - Заглушка для напоминаний: `placeholder="Например: ГУАП: Осенний семестр 2026 / Почта"`
  - `document.getElementById('modal-task-area').value = 'ГУАП'`
- **Влияние:**
  - Интерфейс невозможно переиспользовать для других пользователей или организаций
  - Не соответствует цели "white-label Web UI"
  - При развёртывании на другом сервере требуется правка HTML
- **Подход к исправлению:**
  - Фаза 2: UI загружает persona-конфиг при инициализации через API `/api/v1/persona/current`
  - Все имена, области, titulары → в session state или Global React/Vue state
  - Шаблоны остаются в `index.html` только как fallback
  - Описано как часть Фазы 2 архплана

---

## Критические Уязвимости

### DELETE операции без server-side защиты

**Проблема:** Endpoints удаления не требуют подтверждения (HITL) и не проверяют токен на сервере
- **Файлы:** 
  - `backend/app/api/v1/projects.py:38-43` — `DELETE /api/v1/projects/{project_id}`
  - `backend/app/api/v1/documents.py:37-42` — `DELETE /api/v1/documents/{doc_id}`
  - `backend/app/api/v1/tasks.py` — DELETE для задач (если есть)
- **Код примера:**
  ```python
  @router.delete("/{project_id}")
  async def delete_project(project_id: int):
      deleted = await DatabaseService.delete_project(project_id)
      if not deleted:
          raise HTTPException(status_code=404, detail="Project not found")
      return {"ok": True}  # ← No auth, no HITL!
  ```
- **Влияние:**
  - Любой запрос (с CORS "*") может удалить проект/документ/задачу
  - Нет защиты от ошибочного/вредоносного удаления
  - В /opt/assistant-core есть HITL в `bot_handler.py`, но Web UI не имеет аналога
  - Не соответствует требованию архплана: "HITL для деструктивных операций"
- **Подход к исправлению:**
  - Немедленно: добавить server-side токен-проверку или IP-whitelist
  - Фаза 4: обернуть DELETE в `@requires_confirmation` декоратор
  - Создавать запись в `pending_confirmations`, возвращать 409 (Conflict) до одобрения
  - Одобрение может приходить из Telegram-бота или Web UI
  - Подробно описано в `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` раздел 2.3 и Фаза 4

### Отсутствие аутентификации слоя

**Проблема:** Никакого механизма проверки токена или идентичности запроса в API
- **Файлы:** `backend/app/main.py`, все файлы в `backend/app/api/v1/`
- **Влияние:**
  - Любой может вызвать любой endpoint (все GET/POST/PUT/DELETE доступны анонимно)
  - Нарушение контроля доступа: нет способа узнать "кто" сделал операцию
  - Логирование операций неполное (no user context)
  - При мультитенантности невозможна изоляция данных пользователей
- **Подход к исправлению:**
  - Добавить middleware для проверки Bearer-токена или Session-cookie
  - Использовать JWT или простую in-memory session-map для разработки
  - Извлекать persona_id из токена, передавать в DatabaseService
  - Все операции логировать с user_id

---

## Дублирование и Дрейф

### Две копии security-политики

**Проблема:** SECRET_PATTERNS и FORBIDDEN_FILES определены в двух местах с потенциалом дрейфа
- **Файлы:**
  - `backend/app/api/v1/security.py:13-29` — для Web API audit
  - `scripts/security_shield.py:18-35` — для pre-commit hook
- **Различия:**
  - `security.py` добавляет Generic Bearer Secret pattern на строке 25
  - `security_shield.py` не имеет этого pattern
  - При добавлении нового pattern в одном месте другое отстаёт
- **Влияние:**
  - Разные правила между Web audit и pre-commit hook
  - Secret может пройти pre-commit, но пойматься Web audit, или наоборот
  - Нарушает архпринцип DRY
- **Подход к исправлению:**
  - Фаза 3: создать общий пакет `core/security/patterns.py` (или похожее)
  - Оба модуля импортируют оттуда: `from core.security.patterns import SECRET_PATTERNS, FORBIDDEN_FILES`
  - Описано в архплане как часть "Развязка межрепозиторийной БД"
  - Текущий workaround: синхронизировать вручную на каждое изменение

### Hardcoded параметры персоны в разных слоях

**Проблема:** Параметры Попова ("Тидекс", "ГУАП", 8.5 часов/день, адреса каталогов) раскиданы по коду
- **Файлы:**
  - `backend/app/core/config.py:19` — путь БД assistant-core
  - `backend/app/api/v1/security.py:31-68` — PROJECTS_REGISTRY с путями
  - `backend/app/db.py:149, 244` — дефолт area "ГУАП"
  - `backend/app/models/dashboard_schemas.py:8, 33` — дефолты Pydantic
  - `backend/app/static/index.html` —硬编码 "Попов Д.А.", "ГУАП", "Тидекс"
  - `/opt/assistant-core/src/*` — путём интеграции в обоих репозиториях
- **Влияние:**
  - Для добавления второй персоны нужно менять код в 5+ местах
  - Нет единой точки конфигурации
  - Тесты зависят от hardcoded значений, что мешает параметризации
- **Подход к исправлению:**
  - Фаза 2: единая `config/persona.yaml` или БД
  - Все модули при загрузке читают активную персону: `current_persona = load_persona(persona_id)`
  - Defaults вычисляются из persona, а не захардкодены
  - Тесты запускаются с синтетической test-persona
  - Подробно в архплане, раздел 3

---

## Мёртвый и Потенциально Сломанный Код

### Невалидный импорт в scripts/notion_dev.py

**Проблема:** Импорт из несуществующего модуля
- **Файлы:** `scripts/notion_dev.py:14`
- **Код:** `from src import config`
- **Ошибка:** 
  - В репозитории нет папки `src/` на уровне, чтобы этот импорт работал
  - Правильный путь был бы `from backend.app.core import config` или локальный импорт
- **Влияние:**
  - Скрипт не может быть запущен: `ModuleNotFoundError: No module named 'src'`
  - Получение NOTION_API_KEY на строке 26 упадёт с AttributeError
- **Подход к исправлению:**
  - Перейти на относительный импорт или явный путь к backend
  - Или перенести конфиг в общую папку, доступную для scripts/
  - Добавить в CI проверку на import-ошибки для всех скриптов
  - На данный момент скрипт остаётся неработающим — переквалифицировать как archived или удалить

### Hardcoded NDA-правило для Тидекса

**Проблема:** Параметр `is_tydex` проверяется по hardcoded строке в git-remote
- **Файлы:** `backend/app/api/v1/security.py:95`
- **Код:** 
  ```python
  if is_tydex and code == 0 and "github.com/DimaMuhannad" in origin_url:
      violations.append("CRITICAL: Проект Тидекс скомпрометирован...")
  ```
- **Влияние:**
  - При переезде Тидекса на другой GitHub аккаунт или GitLab это правило перестанет работать
  - Hardcoded username (DimaMuhannad) не масштабируется
  - При создании второй персоны нужно добавить ещё одно такое правило
- **Подход к исправлению:**
  - Фаза 2: хранить `forbidden_remote_substrings` и `forbidden_keywords` в persona.yaml
  - Параметр `is_tydex` вычисляется из workspace.clearance == "restricted_nda"
  - Правило применяется из configuration, а не hardcoded
  - Описано в архплане, раздел 3.1

---

## Операционные Проблемы

### Wrapper systemctl скрывает ошибки stop/restart для dev-bridge

**Проблема:** `/usr/local/bin/systemctl` перехватывает команды остановки/перезагрузки и возвращает фальшивый успех
- **Файлы:** `/usr/local/bin/systemctl:3-8`
- **Код:**
  ```bash
  if [ -z "$FORCE_SYSTEMCTL_RESTART" ] && { 
      [[ "$*" =~ restart.*dev-bridge ]] || [[ "$*" =~ stop.*dev-bridge ]]; 
  }; then
      echo "● dev-bridge.service - Popov Dev Agent Telegram Bridge"
      echo "     Active: active (running)"
      echo "Notice: self-restart intercepted..."
      exit 0  # ← Успех, хотя сервис не был перезагружен!
  fi
  ```
- **Влияние:**
  - `systemctl stop chat-app` может одновременно остановить оба сервиса, но wrapper вернёт успех только для dev-bridge
  - Если попытаться остановить оба в одной команде (`systemctl stop chat-app dev-bridge`), вторая часть может быть проигнорирована
  - Мониторинг и автовосстановление не будут работать корректно
  - Скрывает реальные проблемы с сервисом
- **Подход к исправлению:**
  - Немедленно: использовать `FORCE_SYSTEMCTL_RESTART=1 systemctl stop dev-bridge` при реальной необходимости
  - Долгосрочно: убрать wrapper, использовать systemd `PartOf=` или явное управление в orchestration
  - Для разработки: использовать отдельный systemd user-service или supervisor
  - Задокументировать, что wrapper нужен, и когда переопределять

### Асинхронная остановка assistant-worker переходит в SIGKILL

**Проблема:** При остановке сервиса не успевает корректно завершить работу в течение таймаута SIGTERM
- **Влияние:**
  - Данные в памяти теряются без graceful shutdown
  - При частых перезагрузках может привести к corruption БД
  - Логи не записываются полностью
  - Долгоживущие операции (импорт, синхронизация) прерываются на полусредине
- **Подход к исправлению:**
  - Увеличить DefaultTimeoutStopSec в systemd unit (30 → 60 сек)
  - Добавить SIGTERM handler в главный цикл daemon, чтобы он завершал pending-операции
  - Использовать asyncio.CancelledError для graceful shutdown
  - Добавить метрику "shutdown_time" для мониторинга

### Plaintext API key в systemd unit-файле

**Проблема:** `/etc/systemd/system/dev-bridge.service` содержит конфиденциальный API key в открытом виде
- **Файлы:** `/etc/systemd/system/dev-bridge.service` (мировой доступ на чтение)
- **Влияние:**
  - Ключ доступен любому пользователю на сервере (`cat /etc/systemd/system/dev-bridge.service`)
  - При публикации конфигурации или снимках ВМ может утечь
  - Ротация ключа требует редактирования файла, перезагрузки systemd daemon
  - Нарушает Best Practice "Never commit secrets"
- **Риск:** Компрометация интеграции, несанкционированный доступ к внешнему сервису
- **Подход к исправлению:**
  - Немедленно: переместить ключ в `/opt/chat-app/.env` или `/etc/chat-app/secrets.conf`
  - Установить права доступа 600 (только root) на secret-файл
  - systemd unit читает переменные из EnvironmentFile=
  - Использовать systemd LoadCredential= для ещё большей безопасности (systemd 250+)
  - Ротация ключа делается через секуритизированный процесс, не через редактирование unit

---

## Пробелы в Тестировании

### Отсутствие тестов DELETE endpoint-ов с auth

**Проблема:** Тесты не проверяют, что DELETE требует аутентификации
- **Файлы:** `backend/tests/test_security_api.py` и `backend/tests/test_dashboard_api.py` — нет тестов DELETE
- **Риск:** Без явного теста изменение security-слоя может оставить DELETE открытым
- **Подход к исправлению:**
  - Фаза 0 (подстраховочная сеть): добавить тесты:
    ```python
    def test_delete_project_requires_auth():
        # DELETE без токена → 401 или 409
        response = client.delete("/api/v1/projects/1")
        assert response.status_code in [401, 409]
    
    def test_delete_project_requires_confirmation():
        # DELETE с токеном но без одобрения → 409 Conflict
        # Проверить, что в pending_confirmations появилась запись
    ```
  - Добавить в CI-gating

### Тесты персона-специфичны, не инвариантны

**Проблема:** Когда будет добавлена вторая синтетическая персона, тесты не будут переиспользоваться
- **Файлы:** Все тесты в `backend/tests/`
- **Пример:** Тест ожидает `area == "ГУАП"`, но при другой персоне это может быть другое значение
- **Влияние:** Это "единственное доказательство, что универсализация реальна" (архплан, сквозные требования)
- **Подход к исправлению:**
  - Фаза 2: тесты переписываются на проверку через `current_persona.default_area` вместо hardcoded "ГУАП"
  - Fixture-ы инициализируют персону из `config/persona.yaml`, а не ожидают её в памяти
  - Один набор тестов должен проходить для "popov-da-default" и для "test-synthetic-persona"

---

## Масштабируемость и Архитектура

### Global state и отсутствие persona-контекста

**Проблема:** Нет способа различить "в каком контексте работаем" — разделяемые ресурсы между персонами не изолированы
- **Влияние:**
  - При одновременной работе двух персон могут быть race conditions
  - Фиксации для одной персоны влияют на другую
  - Кэши могут вернуть данные от другой персоны
- **Подход к исправлению:**
  - Фаза 5: убрать мутирующие глобальные переменные (например, `config.GEMINI_API_KEY`)
  - Каждая persona хранит свои credentials в БД, зашифрованные
  - DatabaseService инициализируется с persona_id в конструкторе
  - Использовать contextvars для async-контекста persona

### Отсутствие миграций БД

**Проблема:** Schema в `/opt/assistant-core/data/`, но никакого инструмента для версионирования миграций
- **Влияние:**
  - Обновление schema требует ручного SQL или скрипта
  - При развёртывании нового кода со старой БД неясно, нужна ли миграция
  - Нет способа откатить изменения schema
- **Подход к исправлению:**
  - Использовать alembic или аналог для миграций Python
  - При инициализации приложения проверять версию schema, запускать pending-миграции
  - Все изменения schema коммитить в `backend/migrations/versions/*.py`

---

## Риски, Согласованные с Архитектурным Планом

Согласно `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md`:

| Риск | Локация | Фаза План | Статус |
|------|---------|-----------|--------|
| Риск №1: Абсолютный путь к БД (`/opt/assistant-core/data/assistant.db`) | `backend/app/core/config.py:19` | Фаза 3 | Открыт, критичен |
| Риск №2: Hardcoded PROJECTS_REGISTRY | `backend/app/api/v1/security.py:31-68` | Фаза 2 | Открыт, высокий |
| Риск №3: DELETE без HITL в Web UI | `backend/app/api/v1/projects.py:38-43`, `documents.py:37-42` | Фаза 4 | Открыт, критичен |
| Риск №4: Нет WorkspaceScope внутри assistant-core | `/opt/assistant-core` (не в этом repo) | Фаза 5 | Не проверено (в отдельном repo) |
| Риск №5: Мутирующий глобальный state (GEMINI_API_KEY rotation) | `/opt/assistant-core/src/key_rotator.py` | Фаза 5 | Не проверено (в отдельном repo) |
| Риск №7: Тесты все ещё зелёные, но универсализация не настоящая | Все тесты | Фаза 2 | Открыт, высокий |

Дополнительные находки в этом анализе (не упомянутые в архплане):
- Wrapper `/usr/local/bin/systemctl` скрывает stop-команды
- Plaintext ключ в dev-bridge.service
- Дублирование security-правил между security.py и security_shield.py
- Невалидный импорт в notion_dev.py
- Отсутствие тестов DELETE с auth
- No graceful shutdown в assistant-worker

---

*Анализ проблем: 2026-10-01*
