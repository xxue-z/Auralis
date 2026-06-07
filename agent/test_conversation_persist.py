"""对话历史持久化单元测试"""

import json
import pytest
import tempfile
from pathlib import Path
from memory.conversation_store import ConversationStore


@pytest.fixture
def store(tmp_path):
    """创建临时数据库的 ConversationStore"""
    db_path = tmp_path / "test_conversations.db"
    return ConversationStore(db_path=db_path)


# ============================================================
# 1. 基本保存和加载
# ============================================================

class TestSaveAndLoad:
    """测试消息保存和加载"""

    def test_save_and_load_single_message(self, store):
        store.save_message("s1", "user", "你好")
        history = store.get_history("s1")
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "你好"

    def test_save_multiple_messages(self, store):
        store.save_message("s1", "user", "你好")
        store.save_message("s1", "assistant", "你好！有什么可以帮你的？")
        store.save_message("s1", "user", "查看系统信息")

        history = store.get_history("s1")
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"

    def test_history_ordered_by_time(self, store):
        store.save_message("s1", "user", "第一条")
        store.save_message("s1", "user", "第二条")
        store.save_message("s1", "user", "第三条")

        history = store.get_history("s1")
        assert history[0]["content"] == "第一条"
        assert history[2]["content"] == "第三条"

    def test_tool_calls_saved(self, store):
        tool_calls = [{"id": "c1", "type": "function", "function": {"name": "test"}}]
        store.save_message("s1", "assistant", "", tool_calls=tool_calls)

        history = store.get_history("s1")
        assert len(history) == 1
        assert history[0]["tool_calls"] == tool_calls

    def test_tool_result_saved(self, store):
        store.save_message("s1", "tool", '{"success": true}', tool_call_id="c1")

        history = store.get_history("s1")
        assert len(history) == 1
        assert history[0]["role"] == "tool"
        assert history[0]["tool_call_id"] == "c1"


# ============================================================
# 2. 会话隔离
# ============================================================

class TestSessionIsolation:
    """测试不同会话的消息隔离"""

    def test_different_sessions_isolated(self, store):
        store.save_message("s1", "user", "会话1的消息")
        store.save_message("s2", "user", "会话2的消息")

        h1 = store.get_history("s1")
        h2 = store.get_history("s2")

        assert len(h1) == 1
        assert len(h2) == 1
        assert h1[0]["content"] == "会话1的消息"
        assert h2[0]["content"] == "会话2的消息"

    def test_empty_session_returns_empty(self, store):
        history = store.get_history("nonexistent")
        assert history == []


# ============================================================
# 3. 历史限制
# ============================================================

class TestHistoryLimit:
    """测试加载时的历史限制"""

    def test_limit_returns_recent(self, store):
        for i in range(30):
            store.save_message("s1", "user", f"msg{i}")

        history = store.get_history("s1", limit=10)
        assert len(history) == 10
        # 应返回最近 10 条
        assert history[0]["content"] == "msg20"
        assert history[9]["content"] == "msg29"

    def test_limit_larger_than_messages(self, store):
        store.save_message("s1", "user", "hello")
        history = store.get_history("s1", limit=50)
        assert len(history) == 1


# ============================================================
# 4. 会话管理
# ============================================================

class TestSessionManagement:
    """测试会话列表和删除"""

    def test_list_sessions(self, store):
        store.save_message("s1", "user", "第一条消息")
        store.save_message("s2", "user", "第二条消息")

        sessions = store.list_sessions()
        assert len(sessions) == 2
        session_ids = {s["session_id"] for s in sessions}
        assert "s1" in session_ids
        assert "s2" in session_ids

    def test_session_has_title(self, store):
        store.save_message("s1", "user", "这是一条很长的消息用来测试标题截断功能")
        sessions = store.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["title"] is not None
        assert len(sessions[0]["title"]) <= 53  # 50 chars + "..."

    def test_delete_session(self, store):
        store.save_message("s1", "user", "hello")
        store.save_message("s1", "assistant", "hi")
        store.delete_session("s1")

        history = store.get_history("s1")
        assert len(history) == 0

        sessions = store.list_sessions()
        assert all(s["session_id"] != "s1" for s in sessions)

    def test_message_count(self, store):
        store.save_message("s1", "user", "a")
        store.save_message("s1", "assistant", "b")
        store.save_message("s1", "user", "c")

        count = store.get_message_count("s1")
        assert count == 3


# ============================================================
# 5. 自动清理
# ============================================================

class TestAutoCleanup:
    """测试过期数据清理"""

    def test_cleanup_old_data(self, store):
        # 手动插入一条旧数据
        conn = store._get_conn()
        conn.execute(
            "INSERT INTO sessions (session_id, updated_at) VALUES (?, datetime('now', '-60 days'))",
            ("old_session",),
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, 'user', 'old message')",
            ("old_session",),
        )
        conn.commit()

        # 插入一条新数据
        store.save_message("new_session", "user", "new message")

        # 清理 30 天前的数据
        store.cleanup_old(days=30)

        # 旧数据应被删除
        old_history = store.get_history("old_session")
        assert len(old_history) == 0

        # 新数据应保留
        new_history = store.get_history("new_session")
        assert len(new_history) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
