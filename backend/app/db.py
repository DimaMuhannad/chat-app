import aiosqlite
import json
from datetime import datetime, timezone, date
from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager

from app.core.config import settings


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        yield conn


class PersonaNotLoadedError(RuntimeError):
    """Персона settings.PERSONA_ID не загружена в БД; HTTP-слой отвечает 503 (D-11, T-03-20)."""


class DatabaseService:
    @staticmethod
    async def resolve_default_area() -> str:
        """Область по умолчанию текущей персоны; без персоны - PersonaNotLoadedError (не строка владельца)."""
        row = await DatabaseService.get_persona(settings.PERSONA_ID)
        if row is None:
            raise PersonaNotLoadedError(settings.PERSONA_ID)
        return row["config"]["default_area"]

    @staticmethod
    async def get_persona(persona_id: str) -> dict[str, Any] | None:
        """Персона из таблицы personas; None, если строки или самой таблицы нет."""
        try:
            async with get_db() as conn:
                cursor = await conn.execute(
                    "SELECT id, display_name, config_json, updated_at FROM personas WHERE id = ?;",
                    (persona_id,),
                )
                row = await cursor.fetchone()
        except aiosqlite.OperationalError:
            return None
        if row is None:
            return None
        return {
            "id": row["id"],
            "display_name": row["display_name"],
            "config": json.loads(row["config_json"]),
            "updated_at": row["updated_at"],
        }

    @staticmethod
    async def list_workspaces(persona_id: str) -> list[dict[str, Any]]:
        """Рабочие пространства персоны в порядке position; пусто, если строк или таблицы нет."""
        try:
            async with get_db() as conn:
                cursor = await conn.execute(
                    "SELECT id, position, label, path, clearance, account, clearance_label, color, remote, "
                    "forbidden_remote_substrings, forbidden_keywords, remote_violation_message "
                    "FROM workspaces WHERE persona_id = ? ORDER BY position;",
                    (persona_id,),
                )
                rows = await cursor.fetchall()
        except aiosqlite.OperationalError:
            return []
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["forbidden_remote_substrings"] = json.loads(item["forbidden_remote_substrings"] or "[]")
            item["forbidden_keywords"] = json.loads(item["forbidden_keywords"] or "[]")
            result.append(item)
        return result

    @staticmethod
    async def get_dashboard_summary() -> dict[str, Any]:
        async with get_db() as conn:
            # 1. Focus P1 tasks
            cursor = await conn.execute(
                """
                SELECT t.*, p.name as project_name
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.status != 'done' AND t.priority = 'P1'
                ORDER BY t.due_date ASC LIMIT 5;
                """
            )
            focus_tasks = [dict(r) for r in await cursor.fetchall()]

            # 2. Task counts by status
            cursor = await conn.execute(
                "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status;"
            )
            task_status_counts = {row["status"]: row["cnt"] for row in await cursor.fetchall()}

            # 3. Task counts by area
            cursor = await conn.execute(
                "SELECT area, COUNT(*) as cnt FROM tasks WHERE status != 'done' GROUP BY area;"
            )
            task_area_counts = {row["area"]: row["cnt"] for row in await cursor.fetchall()}

            # 4. Active reminders
            cursor = await conn.execute(
                "SELECT * FROM reminders WHERE status = 'active' ORDER BY check_date ASC LIMIT 10;"
            )
            active_reminders = [dict(r) for r in await cursor.fetchall()]

            # 5. Counts
            cursor = await conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'active';")
            active_projects_count = (await cursor.fetchone())[0]

            cursor = await conn.execute("SELECT COUNT(*) FROM documents;")
            total_documents_count = (await cursor.fetchone())[0]

            # 6. Tomorrow's lessons (from schedule snapshot)
            tomorrow_lessons = []
            cursor = await conn.execute(
                "SELECT raw_payload FROM content_snapshots WHERE source_id LIKE 'rasp_guap_%' ORDER BY id DESC LIMIT 1;"
            )
            row = await cursor.fetchone()
            if row and row["raw_payload"]:
                try:
                    payload = json.loads(row["raw_payload"])
                    # Check next upcoming date
                    for day in payload.get("days", []):
                        if day.get("lessons"):
                            tomorrow_lessons = day.get("lessons")
                            break
                except Exception:
                    pass

            # 7. Today's email stats
            today_str = date.today().isoformat()
            cursor = await conn.execute(
                """
                SELECT id, subject, sender_name, sender_email, replied_at, category
                FROM email_messages
                WHERE is_answered = 1 AND substr(replied_at, 1, 10) = ?
                ORDER BY replied_at DESC;
                """,
                (today_str,),
            )
            answered_today = [dict(r) for r in await cursor.fetchall()]

            cursor = await conn.execute(
                """
                SELECT COUNT(*) FROM email_messages
                WHERE requires_action = 1 AND is_answered = 0 AND is_expired = 0 AND is_noise = 0;
                """
            )
            pending_emails_count = (await cursor.fetchone())[0]

            return {
                "focus_tasks": focus_tasks,
                "task_status_counts": task_status_counts,
                "task_area_counts": task_area_counts,
                "active_reminders": active_reminders,
                "active_projects_count": active_projects_count,
                "total_documents_count": total_documents_count,
                "schedule_lessons": tomorrow_lessons[:4],
                "answered_today": answered_today,
                "pending_emails_count": pending_emails_count,
            }

    # Projects
    @staticmethod
    async def list_projects(area: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        async with get_db() as conn:
            query = """
                SELECT p.*,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status != 'done') as open_tasks_count,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'done') as completed_tasks_count
                FROM projects p
                WHERE 1=1
            """
            params: list[Any] = []
            if area:
                query += " AND p.area = ?"
                params.append(area)
            if status:
                query += " AND p.status = ?"
                params.append(status)
            query += " ORDER BY p.id ASC;"
            cursor = await conn.execute(query, tuple(params))
            return [dict(r) for r in await cursor.fetchall()]

    @staticmethod
    async def get_project(project_id: int) -> dict[str, Any] | None:
        async with get_db() as conn:
            cursor = await conn.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def create_project(data: dict[str, Any]) -> dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        area = data.get("area") or await DatabaseService.resolve_default_area()
        async with get_db() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO projects (name, area, status, target_date, key_result, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data["name"],
                    area,
                    data.get("status", "active"),
                    data.get("target_date"),
                    data.get("key_result"),
                    data.get("description"),
                    now_iso,
                    now_iso,
                ),
            )
            await conn.commit()
            new_id = cursor.lastrowid
            return await DatabaseService.get_project(new_id)

    @staticmethod
    async def update_project(project_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clauses = [f"{k} = ?" for k in data.keys()]
        values = list(data.values()) + [project_id]
        async with get_db() as conn:
            cursor = await conn.execute(
                f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = ?;",
                tuple(values),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                return None
            return await DatabaseService.get_project(project_id)

    @staticmethod
    async def delete_project(project_id: int) -> bool:
        async with get_db() as conn:
            cursor = await conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
            await conn.commit()
            return cursor.rowcount > 0

    # Tasks
    @staticmethod
    async def list_tasks(
        status: str | None = None,
        area: str | None = None,
        priority: str | None = None,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]:
        async with get_db() as conn:
            query = """
                SELECT t.*, p.name as project_name
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE 1=1
            """
            params: list[Any] = []
            if status:
                query += " AND t.status = ?"
                params.append(status)
            if area:
                query += " AND t.area = ?"
                params.append(area)
            if priority:
                query += " AND t.priority = ?"
                params.append(priority)
            if project_id:
                query += " AND t.project_id = ?"
                params.append(project_id)
            query += " ORDER BY CASE t.priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 ELSE 4 END, t.due_date ASC, t.id DESC;"
            cursor = await conn.execute(query, tuple(params))
            return [dict(r) for r in await cursor.fetchall()]

    @staticmethod
    async def get_task(task_id: int) -> dict[str, Any] | None:
        async with get_db() as conn:
            cursor = await conn.execute(
                """
                SELECT t.*, p.name as project_name
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.id = ?;
                """,
                (task_id,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def create_task(data: dict[str, Any]) -> dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        area = data.get("area") or await DatabaseService.resolve_default_area()
        async with get_db() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO tasks (project_id, title, description, area, priority, status, due_date, estimated_minutes, context_tag, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.get("project_id"),
                    data["title"],
                    data.get("description"),
                    area,
                    data.get("priority", "P2"),
                    data.get("status", "todo"),
                    data.get("due_date"),
                    data.get("estimated_minutes"),
                    data.get("context_tag"),
                    now_iso,
                    now_iso,
                ),
            )
            await conn.commit()
            return await DatabaseService.get_task(cursor.lastrowid)

    @staticmethod
    async def update_task(task_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clauses = [f"{k} = ?" for k in data.keys()]
        values = list(data.values()) + [task_id]
        async with get_db() as conn:
            cursor = await conn.execute(
                f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?;",
                tuple(values),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                return None
            return await DatabaseService.get_task(task_id)

    @staticmethod
    async def delete_task(task_id: int) -> bool:
        async with get_db() as conn:
            cursor = await conn.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
            await conn.commit()
            return cursor.rowcount > 0

    # Reminders
    @staticmethod
    async def list_reminders(status: str | None = None) -> list[dict[str, Any]]:
        async with get_db() as conn:
            query = "SELECT * FROM reminders WHERE 1=1"
            params: list[Any] = []
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY status ASC, check_date ASC, id DESC;"
            cursor = await conn.execute(query, tuple(params))
            return [dict(r) for r in await cursor.fetchall()]

    @staticmethod
    async def get_reminder(reminder_id: int) -> dict[str, Any] | None:
        async with get_db() as conn:
            cursor = await conn.execute("SELECT * FROM reminders WHERE id = ?;", (reminder_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def create_reminder(data: dict[str, Any]) -> dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        async with get_db() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO reminders (task_id, what, person, check_date, context, source_type, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.get("task_id"),
                    data["what"],
                    data.get("person"),
                    data.get("check_date"),
                    data.get("context"),
                    data.get("source_type", "manual"),
                    data.get("status", "active"),
                    now_iso,
                    now_iso,
                ),
            )
            await conn.commit()
            return await DatabaseService.get_reminder(cursor.lastrowid)

    @staticmethod
    async def update_reminder(reminder_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clauses = [f"{k} = ?" for k in data.keys()]
        values = list(data.values()) + [reminder_id]
        async with get_db() as conn:
            cursor = await conn.execute(
                f"UPDATE reminders SET {', '.join(set_clauses)} WHERE id = ?;",
                tuple(values),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                return None
            return await DatabaseService.get_reminder(reminder_id)

    @staticmethod
    async def delete_reminder(reminder_id: int) -> bool:
        async with get_db() as conn:
            cursor = await conn.execute("DELETE FROM reminders WHERE id = ?;", (reminder_id,))
            await conn.commit()
            return cursor.rowcount > 0

    # Documents
    @staticmethod
    async def list_documents(project_id: int | None = None) -> list[dict[str, Any]]:
        async with get_db() as conn:
            query = """
                SELECT d.id, d.project_id, d.title, d.category, d.created_at, d.updated_at,
                       p.name as project_name, substr(d.content_markdown, 1, 200) as preview
                FROM documents d
                LEFT JOIN projects p ON d.project_id = p.id
                WHERE 1=1
            """
            params: list[Any] = []
            if project_id:
                query += " AND d.project_id = ?"
                params.append(project_id)
            query += " ORDER BY d.updated_at DESC, d.id DESC;"
            cursor = await conn.execute(query, tuple(params))
            return [dict(r) for r in await cursor.fetchall()]

    @staticmethod
    async def get_document(doc_id: int) -> dict[str, Any] | None:
        async with get_db() as conn:
            cursor = await conn.execute(
                """
                SELECT d.*, p.name as project_name
                FROM documents d
                LEFT JOIN projects p ON d.project_id = p.id
                WHERE d.id = ?;
                """,
                (doc_id,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def create_document(data: dict[str, Any]) -> dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        async with get_db() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO documents (project_id, title, category, content_markdown, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    data.get("project_id"),
                    data["title"],
                    data.get("category", "general"),
                    data.get("content_markdown", ""),
                    now_iso,
                    now_iso,
                ),
            )
            await conn.commit()
            return await DatabaseService.get_document(cursor.lastrowid)

    @staticmethod
    async def update_document(doc_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clauses = [f"{k} = ?" for k in data.keys()]
        values = list(data.values()) + [doc_id]
        async with get_db() as conn:
            cursor = await conn.execute(
                f"UPDATE documents SET {', '.join(set_clauses)} WHERE id = ?;",
                tuple(values),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                return None
            return await DatabaseService.get_document(doc_id)

    @staticmethod
    async def delete_document(doc_id: int) -> bool:
        async with get_db() as conn:
            cursor = await conn.execute("DELETE FROM documents WHERE id = ?;", (doc_id,))
            await conn.commit()
            return cursor.rowcount > 0
