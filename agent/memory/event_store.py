"""事件记忆 — 记录用户操作和系统事件"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("auralis.memory.event")

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "conversations.db"


class EventStore:
    """事件存储（与 ConversationStore/AuditStore 共享 DB）"""

    def __init__(self, db_path: Path | str | None = None):
        self._db_path = str(db_path or DEFAULT_DB_PATH)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                result TEXT DEFAULT 'success',
                session_id TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_action
                ON events(action);
            CREATE INDEX IF NOT EXISTS idx_events_session
                ON events(session_id);
        """)
        conn.commit()

    def record(
        self,
        event_type: str,
        action: str,
        details: dict | None = None,
        result: str = "success",
        session_id: str = "",
    ):
        """记录一个事件"""
        conn = self._get_conn()
        details_json = json.dumps(details, ensure_ascii=False) if details else None
        conn.execute(
            "INSERT INTO events (event_type, action, details, result, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_type, action, details_json, result, session_id),
        )
        conn.commit()

    def query(
        self,
        event_type: str | None = None,
        action: str | None = None,
        session_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """查询事件"""
        conn = self._get_conn()
        conditions = []
        params: list[Any] = []

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])

        rows = conn.execute(
            f"SELECT * FROM events{where} "
            "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()

        results = []
        for row in rows:
            entry = dict(row)
            if entry.get("details"):
                try:
                    entry["details"] = json.loads(entry["details"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(entry)
        return results

    def cleanup_old(self, days: int = 90):
        """删除旧事件"""
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM events WHERE timestamp < datetime('now', ?)",
            (f"-{days} days",),
        )
        conn.commit()
