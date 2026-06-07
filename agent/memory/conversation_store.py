"""对话历史持久化 — SQLite 存储"""

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("auralis.memory.conversation")

# 数据库文件路径
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "conversations.db"


class ConversationStore:
    """对话历史持久化存储"""

    def __init__(self, db_path: Path | str | None = None):
        self._db_path = str(db_path or DEFAULT_DB_PATH)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT DEFAULT '',
                tool_calls TEXT,
                tool_call_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, created_at);
        """)
        conn.commit()

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str = "",
        tool_calls: list[dict] | None = None,
        tool_call_id: str | None = None,
    ):
        """保存一条消息"""
        conn = self._get_conn()

        # 确保 session 存在
        conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)",
            (session_id,),
        )

        # 插入消息
        tool_calls_json = json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None
        conn.execute(
            "INSERT INTO messages (session_id, role, content, tool_calls, tool_call_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, tool_calls_json, tool_call_id),
        )

        # 更新 session 的 updated_at 和 title
        conn.execute(
            "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP "
            "WHERE session_id = ?",
            (session_id,),
        )

        # 如果是第一条用户消息，用它做 session title
        if role == "user":
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages "
                "WHERE session_id = ? AND role = 'user'",
                (session_id,),
            ).fetchone()
            if row and row["cnt"] == 1:
                title = content[:50] + ("..." if len(content) > 50 else "")
                conn.execute(
                    "UPDATE sessions SET title = ? WHERE session_id = ?",
                    (title, session_id),
                )

        conn.commit()

    def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        """获取对话历史（按时间正序，最近 N 条）"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT role, content, tool_calls, tool_call_id "
            "FROM messages WHERE session_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()

        # 反转为正序（最旧在前）
        messages = []
        for row in reversed(rows):
            msg: dict[str, Any] = {"role": row["role"]}
            if row["content"]:
                msg["content"] = row["content"]
            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            messages.append(msg)

        return messages

    def list_sessions(self, limit: int = 50) -> list[dict]:
        """列出所有会话"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT session_id, title, created_at, updated_at "
            "FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_session(self, session_id: str):
        """删除会话及其所有消息"""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()

    def cleanup_old(self, days: int = 30):
        """删除超过指定天数的旧会话"""
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM messages WHERE session_id IN ("
            "  SELECT session_id FROM sessions "
            "  WHERE updated_at < datetime('now', ?)"
            ")",
            (f"-{days} days",),
        )
        conn.execute(
            "DELETE FROM sessions WHERE updated_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        conn.commit()

    def get_message_count(self, session_id: str) -> int:
        """获取会话的消息数量"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row["cnt"] if row else 0
