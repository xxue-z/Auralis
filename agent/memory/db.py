"""统一数据库管理 — 三个 Store 共享的 SQLite 基础设施"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("auralis.memory.db")

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "conversations.db"


class Database:
    """SQLite 数据库连接管理（asyncio 单线程安全）"""

    def __init__(self, db_path: Path | str | None = None):
        self._db_path = str(db_path or DEFAULT_DB_PATH)
        self._conn: sqlite3.Connection | None = None

    def get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（懒初始化）"""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def init_tables(self, schema: str):
        """初始化数据库表"""
        conn = self.get_conn()
        conn.executescript(schema)
        conn.commit()
