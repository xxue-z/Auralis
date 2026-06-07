"""语义记忆 — 基于 SQLite 的文本存储和检索"""

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from memory.db import Database

logger = logging.getLogger("auralis.memory.semantic")

DEFAULT_SEMANTIC_DB = Path(__file__).parent.parent / "data" / "semantic.db"


def _escape_like(text: str) -> str:
    """转义 LIKE 查询中的通配符"""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SemanticStore:
    """语义记忆 — 存储用户偏好、知识、习惯，支持全文搜索"""

    def __init__(self, db_path: Path | str | None = None):
        self._db = Database(db_path or DEFAULT_SEMANTIC_DB)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return self._db.get_conn()

    def _init_db(self):
        """初始化数据库表"""
        self._db.init_tables("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                memory_type TEXT NOT NULL DEFAULT 'knowledge',
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'conversation',
                active INTEGER DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_memories_type
                ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_category
                ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_memories_active
                ON memories(active);
        """)

    def store(
        self,
        text: str,
        memory_type: str = "knowledge",
        category: str | None = None,
        source: str = "conversation",
    ) -> int:
        """
        存储一条语义记忆

        Args:
            text: 记忆文本内容
            memory_type: 类型 ('preference' | 'knowledge' | 'habit')
            category: 分类 ('desktop' | 'app' | 'file_system' | ...)
            source: 来源 ('conversation' | 'observation' | 'manual')

        Returns:
            新记忆的 ID
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO memories (text, memory_type, category, source) VALUES (?, ?, ?, ?)",
            (text, memory_type, category, source),
        )
        memory_id = cursor.lastrowid
        conn.commit()
        logger.info(f"存储语义记忆: id={memory_id}, type={memory_type}, category={category}")
        return memory_id

    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: str | None = None,
    ) -> list[dict]:
        """
        全文搜索语义记忆（LIKE 模式，兼容中文）

        Args:
            query: 搜索关键词
            top_k: 返回结果数量上限
            memory_type: 按类型过滤

        Returns:
            匹配的记忆列表
        """
        conn = self._get_conn()
        like_query = f"%{_escape_like(query)}%"

        if memory_type:
            rows = conn.execute(
                """SELECT id, text, memory_type, category, created_at, source
                   FROM memories
                   WHERE text LIKE ? ESCAPE '\\' AND memory_type = ? AND active = 1
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (like_query, memory_type, top_k),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, text, memory_type, category, created_at, source
                   FROM memories
                   WHERE text LIKE ? ESCAPE '\\' AND active = 1
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (like_query, top_k),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_by_type(self, memory_type: str, limit: int = 20) -> list[dict]:
        """按类型获取记忆"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, text, memory_type, category, created_at, source
               FROM memories
               WHERE memory_type = ? AND active = 1
               ORDER BY updated_at DESC
               LIMIT ?""",
            (memory_type, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_user_preferences(self) -> list[str]:
        """获取所有用户偏好"""
        prefs = self.get_by_type("preference", limit=50)
        return [p["text"] for p in prefs]

    def update(self, memory_id: int, text: str | None = None) -> bool:
        """更新记忆"""
        conn = self._get_conn()
        if text is not None:
            conn.execute(
                "UPDATE memories SET text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (text, memory_id),
            )
        conn.commit()
        return True

    def delete(self, memory_id: int) -> bool:
        """软删除记忆"""
        conn = self._get_conn()
        conn.execute(
            "UPDATE memories SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (memory_id,),
        )
        conn.commit()
        return True

    def count(self, memory_type: str | None = None) -> int:
        """统计记忆数量"""
        conn = self._get_conn()
        if memory_type:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM memories WHERE memory_type = ? AND active = 1",
                (memory_type,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM memories WHERE active = 1"
            ).fetchone()
        return row["cnt"] if row else 0

    def cleanup_old(self, days: int = 90) -> int:
        """清理过期记忆"""
        conn = self._get_conn()
        # 使用 JULIANDAY 比较日期
        cursor = conn.execute(
            "UPDATE memories SET active = 0 WHERE active = 1 AND created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        conn.commit()
        deleted = cursor.rowcount
        if deleted:
            logger.info(f"清理了 {deleted} 条过期语义记忆")
        return deleted
