"""Общие хелперы тестов: данные NDA-пространства персоны из копии БД (SECF-01, SECF-02, D-12).

Правила NDA и слова читаются из таблицы workspaces копии БД; литералов слов и аккаунта в файле нет.
"""

import json
import sqlite3
from pathlib import Path

from app.core.config import settings

# Синтетическое значение поля remote: случайное совпадение по remote не меняет результат сопоставления
SYNTHETIC_WS_REMOTE = "https://git.example.org/ws/data.git"


def owner_nda_workspace() -> dict:
    """Строка restricted_nda персоны settings.PERSONA_ID из workspaces копии БД (списки декодированы)."""
    uri = Path(settings.SQLITE_DB_PATH).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, label, path, clearance, account, clearance_label, color, remote, "
            "forbidden_remote_substrings, forbidden_keywords, remote_violation_message "
            "FROM workspaces WHERE persona_id = ? AND clearance = 'restricted_nda' "
            "ORDER BY position LIMIT 1;",
            (settings.PERSONA_ID,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "у персоны нет NDA-пространства в копии БД"
    ws = dict(row)
    ws["forbidden_remote_substrings"] = json.loads(ws["forbidden_remote_substrings"] or "[]")
    ws["forbidden_keywords"] = json.loads(ws["forbidden_keywords"] or "[]")
    return ws


def owner_nda_keywords() -> list[str]:
    """Слова NDA пространства владельца из данных (непустой список)."""
    words = owner_nda_workspace()["forbidden_keywords"]
    assert words, "в данных NDA-пространства нет forbidden_keywords"
    return list(words)


def nda_workspace_at(path: Path) -> dict:
    """Копия NDA-пространства владельца с path во временном каталоге и синтетическим remote."""
    return {**owner_nda_workspace(), "path": str(path), "remote": SYNTHETIC_WS_REMOTE}
