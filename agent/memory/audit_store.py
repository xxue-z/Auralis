"""审计日志持久化 — SQLite 存储"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("auralis.memory.audit")

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "conversations.db"


class AuditStore:
    """审计日志存储（与 ConversationStore 共享 DB 文件）"""

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
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                capability_type TEXT NOT NULL,
                risk_level TEXT DEFAULT 'low',
                confirmed_by_user INTEGER DEFAULT 0,
                result TEXT DEFAULT 'pending',
                error_message TEXT,
                duration_ms INTEGER DEFAULT 0,
                details TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_session
                ON audit_log(session_id);
            CREATE INDEX IF NOT EXISTS idx_audit_capability
                ON audit_log(capability_type);
        """)
        conn.commit()

    def log(
        self,
        capability_type: str,
        session_id: str = "",
        risk_level: str = "low",
        confirmed_by_user: bool = False,
        result: str = "pending",
        error_message: str | None = None,
        duration_ms: int = 0,
        details: dict | None = None,
    ):
        """记录一条审计日志"""
        import json
        conn = self._get_conn()
        details_json = json.dumps(details, ensure_ascii=False) if details else None
        conn.execute(
            "INSERT INTO audit_log "
            "(session_id, capability_type, risk_level, confirmed_by_user, "
            "result, error_message, duration_ms, details) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id, capability_type, risk_level,
                1 if confirmed_by_user else 0,
                result, error_message, duration_ms, details_json,
            ),
        )
        conn.commit()

    def query(
        self,
        session_id: str | None = None,
        capability_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """查询审计日志"""
        conn = self._get_conn()
        conditions = []
        params: list[Any] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if capability_type:
            conditions.append("capability_type = ?")
            params.append(capability_type)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])

        rows = conn.execute(
            f"SELECT * FROM audit_log{where} "
            "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()

        return [dict(row) for row in rows]

    def count(self, session_id: str | None = None) -> int:
        """统计审计日志数量"""
        conn = self._get_conn()
        if session_id:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_log WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM audit_log").fetchone()
        return row["cnt"] if row else 0

    def cleanup_old(self, days: int = 90):
        """删除旧审计日志"""
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM audit_log WHERE timestamp < datetime('now', ?)",
            (f"-{days} days",),
        )
        conn.commit()
