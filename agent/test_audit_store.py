"""审计日志持久化单元测试"""

import pytest
from memory.audit_store import AuditStore


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_audit.db"
    return AuditStore(db_path=db_path)


class TestAuditLog:
    """测试审计日志"""

    def test_log_and_query(self, store):
        store.log("file.list", session_id="s1", result="success", duration_ms=100)
        logs = store.query()
        assert len(logs) == 1
        assert logs[0]["capability_type"] == "file.list"
        assert logs[0]["result"] == "success"

    def test_log_with_error(self, store):
        store.log("app.launch", result="error", error_message="应用不存在")
        logs = store.query()
        assert logs[0]["error_message"] == "应用不存在"

    def test_query_by_session(self, store):
        store.log("file.list", session_id="s1")
        store.log("app.launch", session_id="s2")
        store.log("system.info", session_id="s1")

        logs = store.query(session_id="s1")
        assert len(logs) == 2

    def test_query_by_capability(self, store):
        store.log("file.list")
        store.log("app.launch")
        store.log("file.read")

        logs = store.query(capability_type="file.list")
        assert len(logs) == 1

    def test_count(self, store):
        store.log("file.list")
        store.log("app.launch")
        assert store.count() == 2

    def test_query_with_limit(self, store):
        for i in range(10):
            store.log(f"cap_{i}")
        logs = store.query(limit=3)
        assert len(logs) == 3

    def test_log_details(self, store):
        store.log("settings_change", details={"key": "locale", "value": "zh-CN"})
        logs = store.query()
        assert logs[0]["details"] is not None
        assert "locale" in logs[0]["details"]

    def test_cleanup_old(self, store):
        # 插入旧数据
        conn = store._get_conn()
        conn.execute(
            "INSERT INTO audit_log (capability_type, timestamp) VALUES (?, datetime('now', '-100 days'))",
            ("old_cap",),
        )
        conn.commit()

        store.log("new_cap")
        store.cleanup_old(days=90)

        logs = store.query()
        assert len(logs) == 1
        assert logs[0]["capability_type"] == "new_cap"
