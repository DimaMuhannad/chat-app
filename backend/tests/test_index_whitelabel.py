"""White-label страница (PER-05, BCK-01, D-12, D-16): в статике index.html нет профиля владельца.

Токены профиля берутся из данных персоны по умолчанию (owner_tokens из пары persona_tokens.py),
а не из списка в тесте. Эталон прежней статики - литералы ниже: для персоны по умолчанию
значения из /persona/current обязаны совпасть с ними дословно (видимое поведение не меняется).
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app

from .persona_tokens import owner_tokens, token_classes_in_line

INDEX_PATH = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"

FILL_TARGET_IDS = (
    "persona-header-subtitle",
    "persona-schedule-title",
    "area-filter-buttons",
    "modal-task-area",
    "modal-reminder-context",
    "sec-intro-text",
    "sec-clearance-caption",
    "sec-remote-caption",
    "sec-airgap-caption",
)

# Эталон прежней статики index.html (строки 70, 218, 442, 464, 492, 506, 659 до перевода на данные).
PREVIOUS_TEXTS = {
    "header_subtitle": "Попов Д.А. • ГУАП / Тидекс",
    "schedule_title": "Расписание ГУАП (Ближайшие пары)",
    "security_intro": "Оркестрация политик безопасности между публичными репозиториями ГУАП / AI Studio и закрытым NDA-контуром ООО «Тидекс».",
    "clearance_tile_caption": "ООО «Тидекс» (Строгая изоляция ноу-хау и ТГц фотоники)",
    "remote_tile_caption": "github-personal vs github-tydex (includeIf gitdir)",
    "airgap_tile_caption": "Запрет агентам читать артефакты Тидекс в открытых сессиях",
    "reminder_context_placeholder": "Например: ГУАП: Осенний семестр 2026 / Почта",
}
# Кнопки фильтра (строки 265-269): (значение, подпись); «Все сферы» - служебная кнопка, не данные.
PREVIOUS_FILTER_BUTTONS = [
    ("ГУАП", "🏛️ ГУАП"),
    ("Тидекс", "🔬 Тидекс"),
    ("AI & Dev Projects", "🤖 AI & Dev"),
    ("Наука и статьи", "📚 Наука"),
    ("Личное и семья", "🏠 Личное"),
]
# Опции формы (строки 582-587): (значение, подпись).
PREVIOUS_FORM_OPTIONS = [
    ("ГУАП", "🏛️ ГУАП"),
    ("Тидекс", "🔬 Тидекс"),
    ("AI & Dev Projects", "🤖 AI & Dev Projects"),
    ("Наука и статьи", "📚 Наука и статьи"),
    ("Личное и семья", "🏠 Личное и семья"),
    ("Финансы", "💰 Финансы"),
]


def _index_text() -> str:
    return INDEX_PATH.read_text(encoding="utf-8")


def _default_persona_config() -> dict:
    """config_json персоны по умолчанию из копии БД, на которую указывает settings (фикстура сессии)."""
    uri = Path(settings.SQLITE_DB_PATH).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        row = conn.execute(
            "SELECT config_json FROM personas WHERE id = ?;", (settings.PERSONA_ID,)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "персона по умолчанию не засеяна в копию БД"
    return json.loads(row[0])


def _inline_scripts(text: str) -> list[str]:
    pattern = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.S | re.I)
    return pattern.findall(text)


def _function_body(text: str, name: str) -> str:
    start = text.index(f"function {name}(")
    open_brace = text.index("{", text.index(")", start))
    depth = 0
    for pos in range(open_brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace : pos + 1]
    raise AssertionError(f"функция {name} не закрыта")


def test_static_index_has_no_owner_tokens():
    tokens = owner_tokens(_default_persona_config())
    assert any(tokens.values()), "токены профиля пусты: проверка ничего не проверяет"
    found: list[str] = []
    for number, line in enumerate(_index_text().splitlines(), start=1):
        for cls in sorted(token_classes_in_line(line, tokens)):
            found.append(f"строка {number}: класс {cls}")
    assert not found, "в index.html остались токены профиля владельца: " + "; ".join(found)


def test_index_loads_persona_before_render():
    text = _index_text()
    assert "persona/current" in text
    assert "function applyPersona" in text
    handler_start = text.index("addEventListener('DOMContentLoaded'")
    handler = text[handler_start : text.index("});", handler_start)]
    assert "loadPersona()" in handler and "refreshAll()" in handler
    assert handler.index("loadPersona()") < handler.index("refreshAll()")


def test_fill_targets_present_once():
    text = _index_text()
    for element_id in FILL_TARGET_IDS:
        assert len(re.findall(rf'\bid="{re.escape(element_id)}"', text)) == 1, element_id


@pytest.mark.anyio
async def test_persona_values_equal_previous_static_strings():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/persona/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ui"]["texts"] == PREVIOUS_TEXTS
    filters = [
        (a["value"], a["filter_label"]) for a in data["task_areas"] if a["show_in_filter"]
    ]
    assert filters == PREVIOUS_FILTER_BUTTONS
    options = [(a["value"], a["label"]) for a in data["task_areas"]]
    assert options == PREVIOUS_FORM_OPTIONS


def test_inline_script_passes_node_check(tmp_path):
    node = shutil.which("node")
    assert node is not None, "node не найден: проверка встроенного скрипта обязательна"
    scripts = _inline_scripts(_index_text())
    assert scripts, "во встроенных скриптах нет кода"
    target = tmp_path / "index-inline.js"
    target.write_text(scripts[-1], encoding="utf-8")
    env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=1536"}
    result = subprocess.run(
        [node, "--check", str(target)], capture_output=True, text=True, timeout=60, env=env
    )
    assert result.returncode == 0, result.stderr[-2000:]


def test_apply_persona_does_not_use_inner_html():
    body = _function_body(_index_text(), "applyPersona")
    assert "innerHTML" not in body
    assert "outerHTML" not in body
    assert "insertAdjacentHTML" not in body
