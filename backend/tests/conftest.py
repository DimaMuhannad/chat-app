"""Общие фикстуры: вторая синтетическая персона (FND-03) и копия БД с засеянной персоной (D-04).

Сессионная autouse-фикстура persona_session_db делает копию БД из соединения mode=ro, засевает
её seed-CLI assistant-core (персона по умолчанию, затем вторая синтетическая персона из словаря
Фазы 1 через synthetic_to_config) и подменяет settings.SQLITE_DB_PATH: боевая БД не открывается
на запись ни под гейтом, ни при ручном запуске pytest.
"""

import copy
import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

from app.core.config import settings

from .synthetic_persona import SYNTHETIC_PERSONA, synthetic_to_config

SYNTHETIC_PERSONA_ID = SYNTHETIC_PERSONA["id"]


@pytest.fixture
def synthetic_persona() -> dict:
    """Независимая глубокая копия словаря синтетической персоны."""
    return copy.deepcopy(SYNTHETIC_PERSONA)


@pytest.fixture(scope="session", autouse=True)
def persona_session_db(tmp_path_factory):
    """Копия БД с таблицами персоны; settings.SQLITE_DB_PATH указывает на неё всю сессию."""
    core = Path(os.environ.get("ASSISTANT_CORE_DIR", "/opt/assistant-core"))
    src_db = Path(settings.SQLITE_DB_PATH).resolve()
    copy_path = tmp_path_factory.mktemp("persona-db") / "chat-tests.db"
    if copy_path.resolve() == src_db:
        pytest.fail("копия БД совпала с источником")

    source = sqlite3.connect(src_db.as_uri() + "?mode=ro", uri=True)
    try:
        target = sqlite3.connect(copy_path)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()

    env = {k: v for k, v in os.environ.items() if k != "PERSONA_CONFIG_PATH"}
    synthetic_file = copy_path.parent / "synthetic-persona.json"
    synthetic_file.write_text(
        json.dumps(synthetic_to_config(SYNTHETIC_PERSONA), ensure_ascii=False), encoding="utf-8"
    )
    seed_cmd = [str(core / ".venv" / "bin" / "python"), "-m", "src.persona.seed", "--db", str(copy_path)]
    # первый засев - персона по умолчанию, второй - синтетическая (JSON читает yaml.safe_load)
    for extra in ([], ["--persona-config", str(synthetic_file)]):
        result = subprocess.run(
            seed_cmd + extra,
            cwd=str(core),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            tail = "\n".join((result.stderr or result.stdout).splitlines()[-20:])
            pytest.fail(f"seed персоны в копию БД не удался (код {result.returncode}):\n{tail}")

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
        pytest.fail("персона по умолчанию не найдена в копии БД")
    return json.loads(row[0])
