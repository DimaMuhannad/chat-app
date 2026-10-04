"""Изолированные тестовые фикстуры chat-app (DAT-04, D-09, D-10).

Тесты работают на чистой временной БД, создаваемой мигратором assistant_shared.db.migrator.
Каталог /opt/assistant-core во время тестов недоступен и не используется (нет subprocess к seed-CLI
и нет прямого копирования боевой базы assistant.db).
"""

import copy
import json
import os
from pathlib import Path
import sqlite3

import pytest

from app.core.config import settings
from assistant_shared.db.migrator import run_migrations

from .synthetic_persona import SYNTHETIC_PERSONA, synthetic_to_config

SYNTHETIC_PERSONA_ID = SYNTHETIC_PERSONA["id"]

DEFAULT_PERSONA_FIXTURE = json.loads('{"id": "popov-da-default", "display_name": "Попов Дмитрий Александрович", "short_name": "Попов Д.А.", "title": "доцент кафедры физики, к.ф.-м.н.", "organizations": {"university": {"name": "ГУАП", "aliases": ["GUAP"]}, "company": {"name": "Тидекс", "aliases": ["Tydex"]}}, "default_area": "ГУАП", "name_forms": {"nominative": "Попов Дмитрий Александрович", "genitive": "Попова Дмитрия Александровича", "dative_first_patronymic": "Дмитрию Александровичу", "genitive_first_patronymic": "Дмитрия Александровича", "instrumental_first_patronymic": "Дмитрием Александровичем", "short": "Попов Д.А.", "short_genitive": "Попова Д.А.", "initials_genitive": "Д.А. Попова", "signature": "Дмитрий Александрович Попов"}, "telegram": {"authorized_user_ids": ["${TELEGRAM_USER_ID}"], "bot_username": "opd_guap_popov_bot"}, "task_areas": [{"value": "ГУАП", "label": "🏛️ ГУАП", "filter_label": "🏛️ ГУАП", "show_in_filter": true}, {"value": "Тидекс", "label": "🔬 Тидекс", "filter_label": "🔬 Тидекс", "show_in_filter": true}, {"value": "AI & Dev Projects", "label": "🤖 AI & Dev Projects", "filter_label": "🤖 AI & Dev", "show_in_filter": true}, {"value": "Наука и статьи", "label": "📚 Наука и статьи", "filter_label": "📚 Наука", "show_in_filter": true}, {"value": "Личное и семья", "label": "🏠 Личное и семья", "filter_label": "🏠 Личное", "show_in_filter": true}, {"value": "Финансы", "label": "💰 Финансы", "filter_label": null, "show_in_filter": false}], "ui": {"texts": {"header_subtitle": "Попов Д.А. • ГУАП / Тидекс", "schedule_title": "Расписание ГУАП (Ближайшие пары)", "security_intro": "Оркестрация политик безопасности между публичными репозиториями ГУАП / AI Studio и закрытым NDA-контуром ООО «Тидекс».", "clearance_tile_caption": "ООО «Тидекс» (Строгая изоляция ноу-хау и ТГц фотоники)", "remote_tile_caption": "github-personal vs github-tydex (includeIf gitdir)", "airgap_tile_caption": "Запрет агентам читать артефакты Тидекс в открытых сессиях", "reminder_context_placeholder": "Например: ГУАП: Осенний семестр 2026 / Почта"}}, "workspaces": [{"id": "chat-app", "label": "🤖 Antigravity Web Studio (chat-app)", "path": "/opt/chat-app", "clearance": "public", "account": "DimaMuhannad (Personal / Academic)", "clearance_label": "🌐 Public / Open Source", "color": "blue", "remote": null, "forbidden_remote_substrings": [], "forbidden_keywords": [], "remote_violation_message": null}, {"id": "assistant-core", "label": "⚙️ Assistant Core Daemon", "path": "/opt/assistant-core", "clearance": "public", "account": "DimaMuhannad (Personal / Academic)", "clearance_label": "🌐 Public / Academic", "color": "green", "remote": null, "forbidden_remote_substrings": [], "forbidden_keywords": [], "remote_violation_message": null}, {"id": "tydex-optics", "label": "🔬 Оптические приборы и измерения (ООО «Тидекс»)", "path": "/opt/work-tydex", "clearance": "restricted_nda", "account": "ООО «Тидекс» (Corporate Organization)", "clearance_label": "🔴 Restricted NDA / Air-gap", "color": "red", "remote": null, "forbidden_remote_substrings": ["github.com/DimaMuhannad"], "forbidden_keywords": ["tydex_internal_secret", "golay_calibration_key", "thz_proprietary_firmware"], "remote_violation_message": "CRITICAL: Проект Тидекс скомпрометирован: remote указывает на личный публичный аккаунт!"}, {"id": "guap-physics", "label": "🏛️ Кафедра физики ГУАП (Лабораторные и LMS)", "path": "/opt/personal/guap-physics", "clearance": "internal", "account": "DimaMuhannad (ГУАП)", "clearance_label": "🟡 Internal Academic", "color": "yellow", "remote": null, "forbidden_remote_substrings": [], "forbidden_keywords": [], "remote_violation_message": null}], "connectors": {"schedule_source": [{"id": "main", "provider": "schedule_site", "scopes": ["schedule.read"], "config": {"base_url": "https://guap.ru/rasp", "lesson_slots": [{"number": 1, "start": "09:30"}, {"number": 2, "start": "11:10"}, {"number": 3, "start": "13:00"}, {"number": 4, "start": "15:10"}, {"number": 5, "start": "17:00"}, {"number": 6, "start": "18:40"}, {"number": 7, "start": "20:20"}], "subjects": {"физические основы нанотехнологий": "ФОНТ", "основы проектной деятельности в профессии": "ОПДвП", "основы проектной деятельности": "ОПД", "физика": "Физика"}}}], "calendar_sync": [{"id": "main", "provider": "google_calendar", "scopes": ["calendar.read", "calendar.write"], "config": {}}], "timesheet": [{"id": "main", "provider": "aadhk_timesheet", "scopes": ["timesheet.read", "timesheet.write"], "config": {"default_project": "Тидекс", "daily_norm_hours": 8.5}}], "lms": [{"id": "main", "provider": "lms_portal", "scopes": ["lms.read", "lms.write"], "config": {"base_url": "https://pro.guap.ru"}}], "git_source": [], "notion": []}, "methodist": {"raw_dir": "/opt/assistant-core/data/methodist/raw", "kb_dir": "/opt/assistant-core/data/methodist/knowledge_base", "file_catalog": [{"relpath": "templates/Форма_отчета_эффективный_контракт_ППС_2026.docx", "desc": "Официальный действующий бланк отчета кафедры физики от Новиковой Ю.А. (август 2026)", "keywords": ["контракт", "эффективн", "шаблон", "бланк", "форма", "ппс", "новиков"]}, {"relpath": "dept_physics/Попов_ДА_Образец_отчета_эффективный_контракт.docx", "desc": "Утвержденный заполненный образец отчета доцента Д.А. Попова (10.8 балла)", "keywords": ["контракт", "эффективн", "попов", "образец", "пример", "отчет"]}, {"relpath": "admin_lna/Приказ_ГУАП_05-259-26_Эффективный_контракт_2026.pdf", "desc": "Приказ ректора ГУАП № 05-259/26 от 17.04.2026 об утверждении изменений в критериях", "keywords": ["приказ", "контракт", "эффективн", "05-259", "регламент", "лна"]}, {"relpath": "admin_lna/Критерии_эффективного_контракта_ГУАП_2026.pdf", "desc": "Официальная шкала баллов и критериев стимулирующих выплат (Таблица 3 Положения)", "keywords": ["критери", "балл", "таблиц", "шкал", "контракт", "эффективн", "стимулир"]}, {"relpath": "admin_lna/polozhenie_ob_effektivnom_kontrakte_guap_2026.md", "desc": "Сводный аналитический регламент эффективного контракта кафедры физики ГУАП 2026", "keywords": ["положен", "регламент", "контракт", "эффективн"]}, {"relpath": "templates/Титульный_лист_и_протокол_ЛР2_Оптика.docx", "desc": "Официальный шаблон титульного листа и протокола измерений ЛР по оптике", "keywords": ["титульн", "оптик", "протокол", "лаб"]}, {"relpath": "templates/Титульный_лист_отчета_о_практической_работе_2025.docx", "desc": "Официальный шаблон титульного листа практической работы ГУАП", "keywords": ["титульн", "практик", "отчет"]}], "scope_rules": {"out_of_scope_keywords": ["тидекс", "табель", "смен", "часы работы", "выработка", "погод", "анекдот", "фильм", "игра", "криптовалют", "биткоин", "ресторан", "билет", "поезд", "рейс", "курс валют", "новости", "политик"], "academic_keywords": ["гост", "титульн", "отчет", "лабораторн", "физик", "фонт", "опд", "брс", "баллы", "погрешност", "протокол", "допуск", "защита", "практикум", "зачет", "экзамен", "кафедр", "попов", "гастелло", "формул", "график", "мнк", "шрифт", "поля", "студент", "семестр", "дедлайн", "пересдач", "рпд", "проектн", "лаба", "лабы", "методичк", "оформлен", "подпис", "правил", "коваленко", "задачник", "задач", "учебник", "комптон", "фотоэффект", "спектрометр", "ньютон", "интерференц", "дифракц", "маятник", "гистерезис", "холл", "эффективн", "контракт", "стимулирующ", "надбавк", "критери", "базов уровень", "повышенн уровень", "ппс", "новиков", "приказ 05-259", "печ.л", "п.л", "печатн лист", "соавтор", "варост"], "out_of_scope_reason": "Вопрос относится к сторонней теме вне методической работы кафедры физики ГУАП"}}, "prompts": {"secretary": "prompts/secretary_default.jinja2", "intent_router": "prompts/intent_router_default.jinja2", "methodist": "prompts/methodist_default.jinja2", "methodist_scope_check": "prompts/methodist_scope_check_default.jinja2", "reply_generator": "prompts/reply_generator_default.jinja2", "debrief": "prompts/debrief_default.jinja2", "morning_brief": "prompts/morning_brief_default.jinja2", "evening_digest": "prompts/evening_digest_default.jinja2"}}')


def _get_default_persona() -> dict:
    """Возвращает актуальный словарь персоны по умолчанию.

    Если каталог assistant-core доступен, считывает через штатный loader,
    иначе использует статическую каноническую фикстуру DEFAULT_PERSONA_FIXTURE.
    """
    core_dir = Path(os.environ.get("ASSISTANT_CORE_DIR", "/opt/assistant-core"))
    loader_path = core_dir / "src" / "persona" / "loader.py"
    if loader_path.is_file():
        try:
            import sys
            if str(core_dir) not in sys.path:
                sys.path.insert(0, str(core_dir))
            from src.persona.loader import load_persona
            return load_persona().model_dump(mode="json")
        except Exception:
            pass
    return copy.deepcopy(DEFAULT_PERSONA_FIXTURE)


def _seed_persona_into_db(conn: sqlite3.Connection, persona_dict: dict) -> None:
    p_id = persona_dict["id"]
    display_name = persona_dict.get("display_name", p_id)
    config_json = json.dumps(persona_dict, ensure_ascii=False)
    conn.execute(
        """
        INSERT INTO personas (id, display_name, config_json, created_at, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            display_name = excluded.display_name,
            config_json = excluded.config_json,
            updated_at = excluded.updated_at;
        """,
        (p_id, display_name, config_json),
    )
    conn.execute("DELETE FROM workspaces WHERE persona_id = ?;", (p_id,))
    for pos, ws in enumerate(persona_dict.get("workspaces", [])):
        conn.execute(
            """
            INSERT INTO workspaces (
                persona_id, id, position, label, path, clearance, account,
                clearance_label, color, remote, forbidden_remote_substrings,
                forbidden_keywords, remote_violation_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                p_id,
                ws["id"],
                ws.get("position", pos),
                ws["label"],
                ws["path"],
                ws["clearance"],
                ws.get("account", ""),
                ws.get("clearance_label", ""),
                ws.get("color"),
                ws.get("remote"),
                json.dumps(ws.get("forbidden_remote_substrings", []), ensure_ascii=False),
                json.dumps(ws.get("forbidden_keywords", []), ensure_ascii=False),
                ws.get("remote_violation_message"),
            ),
        )
    conn.execute("DELETE FROM connector_bindings WHERE persona_id = ?;", (p_id,))
    for role, bindings in (persona_dict.get("connectors") or {}).items():
        for pos, binding in enumerate(bindings or []):
            b_id = binding.get("id", str(pos))
            conn.execute(
                """
                INSERT INTO connector_bindings (
                    id, persona_id, role, provider, scopes, config_json, position
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    f"{p_id}/{role}/{b_id}",
                    p_id,
                    role,
                    binding.get("provider", ""),
                    json.dumps(binding.get("scopes", []), ensure_ascii=False),
                    json.dumps(binding.get("config", {}), ensure_ascii=False),
                    pos,
                ),
            )


def _seed_all_test_data(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        # 1. Персона по умолчанию
        default_persona = _get_default_persona()
        _seed_persona_into_db(conn, default_persona)

        # 2. Синтетическая персона
        synth_config = synthetic_to_config(SYNTHETIC_PERSONA)["persona"]
        _seed_persona_into_db(conn, synth_config)

        # 3. Базовые сущности для CRUD-тестов
        conn.execute(
            "INSERT INTO projects (id, name, area, status, description) VALUES (1, 'Тестовый семестр', 'ГУАП', 'active', 'Описание');"
        )
        conn.execute(
            "INSERT INTO tasks (id, project_id, title, area, priority, status) VALUES (1, 1, 'Фокус задача', 'ГУАП', 'P1', 'todo');"
        )
        conn.execute(
            "INSERT INTO reminders (id, task_id, what, person, check_date, status) VALUES (1, 1, 'Проверить отчет', 'Староста', '2026-10-05', 'active');"
        )
        conn.execute(
            "INSERT INTO documents (id, project_id, title, category, content_markdown) VALUES (1, 1, 'План работ', 'general', '# План');"
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def synthetic_persona() -> dict:
    """Независимая глубокая копия словаря синтетической персоны."""
    return copy.deepcopy(SYNTHETIC_PERSONA)


@pytest.fixture(scope="session", autouse=True)
def persona_session_db(tmp_path_factory):
    """Изолированная временная БД с таблицами платформы и данными персоны (DAT-04)."""
    copy_path = tmp_path_factory.mktemp("isolated-db") / "chat-tests.db"
    run_migrations(copy_path)
    _seed_all_test_data(copy_path)

    previous = settings.SQLITE_DB_PATH
    settings.SQLITE_DB_PATH = str(copy_path)
    try:
        yield copy_path
    finally:
        settings.SQLITE_DB_PATH = previous


@pytest.fixture(scope="session")
def default_persona_config(persona_session_db) -> dict:
    """Поля персоны по умолчанию (config_json строки personas с id settings.PERSONA_ID).

    Форма та же, что у PersonaConfig.model_dump(mode="json") в assistant-core: данные профиля
    владельца берутся отсюда, а не копируются в тесты (PER-08, D-16).
    """
    connection = sqlite3.connect(persona_session_db)
    try:
        row = connection.execute(
            "SELECT config_json FROM personas WHERE id = ?;", (settings.PERSONA_ID,)
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        pytest.fail("персона по умолчанию не найдена в изолированной БД")
    return json.loads(row[0])
