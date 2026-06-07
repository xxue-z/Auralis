"""事件记忆单元测试"""

import pytest
from memory.event_store import EventStore


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_events.db"
    return EventStore(db_path=db_path)


class TestEventStore:
    """测试事件存储"""

    def test_record_and_query(self, store):
        store.record("user_action", "chat_input", {"content": "你好"})
        events = store.query()
        assert len(events) == 1
        assert events[0]["event_type"] == "user_action"
        assert events[0]["action"] == "chat_input"

    def test_record_with_details(self, store):
        store.record("system", "app_launch", {"app": "notepad"})
        events = store.query()
        assert events[0]["details"]["app"] == "notepad"

    def test_query_by_type(self, store):
        store.record("user_action", "chat")
        store.record("system", "app_launch")
        store.record("user_action", "settings_change")

        events = store.query(event_type="user_action")
        assert len(events) == 2

    def test_query_by_action(self, store):
        store.record("user_action", "chat")
        store.record("user_action", "settings_change")

        events = store.query(action="chat")
        assert len(events) == 1

    def test_query_by_session(self, store):
        store.record("user_action", "chat", session_id="s1")
        store.record("user_action", "chat", session_id="s2")

        events = store.query(session_id="s1")
        assert len(events) == 1

    def test_query_with_limit(self, store):
        for i in range(10):
            store.record("user_action", f"action_{i}")
        events = store.query(limit=3)
        assert len(events) == 3

    def test_cleanup_old(self, store):
        conn = store._get_conn()
        conn.execute(
            "INSERT INTO events (event_type, action, timestamp) VALUES (?, ?, datetime('now', '-100 days'))",
            ("old", "old_action"),
        )
        conn.commit()

        store.record("new", "new_action")
        store.cleanup_old(days=90)

        events = store.query()
        assert len(events) == 1
        assert events[0]["action"] == "new_action"
