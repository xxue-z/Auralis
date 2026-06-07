"""记忆系统单元测试 — SemanticStore + GraphStore + MemoryLayer"""

import json
import tempfile
import pytest
from pathlib import Path

from memory.semantic_store import SemanticStore
from memory.graph_store import GraphStore
from memory.memory_layer import MemoryLayer


# ============================================================
# SemanticStore 测试
# ============================================================

class TestSemanticStore:

    @pytest.fixture
    def store(self, tmp_path):
        """创建临时 SemanticStore"""
        return SemanticStore(tmp_path / "test_semantic.db")

    def test_store_and_search(self, store):
        """存储后可搜索到"""
        store.store("用户喜欢极简桌面", memory_type="preference", category="desktop")
        results = store.search("极简桌面")
        assert len(results) >= 1
        assert "极简桌面" in results[0]["text"]

    def test_search_by_type(self, store):
        """按类型过滤搜索"""
        store.store("用户喜欢极简桌面", memory_type="preference")
        store.store("VS Code 是代码编辑器", memory_type="knowledge")
        results = store.search("桌面", memory_type="preference")
        assert all(r["memory_type"] == "preference" for r in results)

    def test_get_user_preferences(self, store):
        """获取所有用户偏好"""
        store.store("喜欢极简", memory_type="preference")
        store.store("使用深色主题", memory_type="preference")
        store.store("VS Code 是编辑器", memory_type="knowledge")
        prefs = store.get_user_preferences()
        assert len(prefs) == 2
        assert "喜欢极简" in prefs

    def test_update_memory(self, store):
        """更新记忆内容"""
        mid = store.store("原始内容", memory_type="knowledge")
        store.update(mid, text="更新后的内容")
        results = store.search("更新后")
        assert len(results) >= 1

    def test_delete_memory(self, store):
        """软删除记忆"""
        mid = store.store("要删除的内容", memory_type="knowledge")
        store.delete(mid)
        results = store.search("要删除")
        assert len(results) == 0

    def test_cleanup_old(self, store):
        """清理过期记忆"""
        store.store("新记忆", memory_type="knowledge")
        # 手动插入一条旧记录
        conn = store._get_conn()
        conn.execute(
            "INSERT INTO memories (text, memory_type, created_at) VALUES (?, ?, datetime('now', '-100 days'))",
            ("旧记忆", "knowledge"),
        )
        conn.commit()
        # 清理 90 天前的
        deleted = store.cleanup_old(days=90)
        assert deleted >= 1
        # 新记忆应该还在
        assert store.count() >= 1

    def test_search_no_results(self, store):
        """搜索无结果返回空列表"""
        store.store("相关内容", memory_type="knowledge")
        results = store.search("完全不相关的内容xyz")
        assert results == []

    def test_store_with_metadata(self, store):
        """带元数据存储"""
        mid = store.store(
            "用户偏好深色主题",
            memory_type="preference",
            category="appearance",
            source="observation",
        )
        assert mid > 0
        assert store.count() == 1

    def test_count(self, store):
        """统计记忆数量"""
        store.store("条目1", memory_type="preference")
        store.store("条目2", memory_type="preference")
        store.store("条目3", memory_type="knowledge")
        assert store.count() == 3
        assert store.count(memory_type="preference") == 2

    def test_get_by_type(self, store):
        """按类型获取"""
        store.store("偏好1", memory_type="preference")
        store.store("偏好2", memory_type="preference")
        store.store("知识1", memory_type="knowledge")
        prefs = store.get_by_type("preference")
        assert len(prefs) == 2


# ============================================================
# GraphStore 测试
# ============================================================

class TestGraphStore:

    @pytest.fixture
    def graph(self, tmp_path):
        """创建临时 GraphStore"""
        return GraphStore(tmp_path / "test_graph.json")

    def test_add_and_get_node(self, graph):
        """添加和获取节点"""
        graph.add_node("vscode", "app", {"name": "VS Code"})
        node = graph.get_node("vscode")
        assert node is not None
        assert node["type"] == "app"
        assert node["properties"]["name"] == "VS Code"

    def test_add_edge(self, graph):
        """添加边"""
        graph.add_node("user", "user")
        graph.add_node("vscode", "app")
        graph.add_edge("user", "vscode", "uses")
        edges = graph.get_edges(source="user")
        assert len(edges) == 1
        assert edges[0]["relation"] == "uses"

    def test_get_edges_filter(self, graph):
        """按条件过滤边"""
        graph.add_node("user", "user")
        graph.add_node("vscode", "app")
        graph.add_node("project", "project")
        graph.add_edge("user", "vscode", "uses")
        graph.add_edge("user", "project", "owns")
        graph.add_edge("vscode", "project", "opens")

        # 按 source 过滤
        edges = graph.get_edges(source="user")
        assert len(edges) == 2

        # 按 relation 过滤
        edges = graph.get_edges(relation="uses")
        assert len(edges) == 1

        # 按 target 过滤
        edges = graph.get_edges(target="project")
        assert len(edges) == 2

    def test_get_related_bfs(self, graph):
        """BFS 获取关联节点"""
        graph.add_node("user", "user")
        graph.add_node("vscode", "app")
        graph.add_node("project", "project")
        graph.add_edge("user", "vscode", "uses")
        graph.add_edge("vscode", "project", "opens")

        related = graph.get_related("user", depth=2)
        node_ids = {n["id"] for n in related["nodes"]}
        assert "vscode" in node_ids
        assert "project" in node_ids
        assert len(related["edges"]) == 2

    def test_remove_node(self, graph):
        """删除节点及边"""
        graph.add_node("user", "user")
        graph.add_node("vscode", "app")
        graph.add_edge("user", "vscode", "uses")

        graph.remove_node("user")
        assert graph.get_node("user") is None
        assert graph.get_edges(source="user") == []

    def test_persistence(self, tmp_path):
        """保存后重新加载"""
        path = tmp_path / "persist.json"
        g1 = GraphStore(path)
        g1.add_node("test", "app")
        g1.add_edge("a", "b", "uses")

        g2 = GraphStore(path)
        assert g2.get_node("test") is not None
        assert len(g2.get_edges()) == 1

    def test_to_context_string(self, graph):
        """生成上下文字符串"""
        graph.add_node("user", "user")
        graph.add_node("vscode", "app")
        graph.add_edge("user", "vscode", "uses")

        ctx = graph.to_context_string("user")
        assert "user" in ctx
        assert "vscode" in ctx
        assert "uses" in ctx

    def test_circular_references(self, graph):
        """循环引用不无限递归"""
        graph.add_node("a", "app")
        graph.add_node("b", "app")
        graph.add_edge("a", "b", "related_to")
        graph.add_edge("b", "a", "related_to")

        related = graph.get_related("a", depth=10)
        # 不应无限递归
        assert len(related["nodes"]) <= 2

    def test_stats(self, graph):
        """图统计信息"""
        graph.add_node("a", "app")
        graph.add_node("b", "user")
        graph.add_edge("a", "b", "uses")
        stats = graph.stats()
        assert stats["total_nodes"] == 2
        assert stats["total_edges"] == 1
        assert stats["node_types"]["app"] == 1

    def test_remove_edge(self, graph):
        """删除边"""
        graph.add_node("a", "app")
        graph.add_node("b", "app")
        graph.add_edge("a", "b", "uses")
        assert graph.remove_edge("a", "b", "uses")
        assert len(graph.get_edges()) == 0

    def test_add_edge_update_existing(self, graph):
        """重复添加相同边会更新"""
        graph.add_node("a", "app")
        graph.add_node("b", "app")
        graph.add_edge("a", "b", "uses", {"count": 1})
        graph.add_edge("a", "b", "uses", {"count": 2})
        edges = graph.get_edges(source="a")
        assert len(edges) == 1
        assert edges[0]["properties"]["count"] == 2


# ============================================================
# MemoryLayer 测试
# ============================================================

class TestMemoryLayer:

    @pytest.fixture
    def layer(self, tmp_path):
        """创建临时 MemoryLayer"""
        return MemoryLayer(tmp_path / "test_memory")

    def test_write_and_search_semantic(self, layer):
        """统一写入和检索语义记忆"""
        layer.write("semantic", {"text": "用户喜欢深色主题", "memory_type": "preference"})
        results = layer.search("深色主题", types=["semantic"])
        assert len(results["semantic"]) >= 1

    def test_write_and_search_event(self, layer):
        """统一写入和检索事件记忆"""
        layer.write("event", {
            "event_type": "user_action",
            "action": "chat",
            "details": {"content": "hello"},
        })
        results = layer.search("chat", types=["event"])
        assert len(results["events"]) >= 1

    def test_write_graph(self, layer):
        """写入图记忆"""
        layer.write("graph", {"id": "vscode", "type": "app"})
        layer.write("graph", {"source": "user", "target": "vscode", "relation": "uses"})
        assert layer.graph.node_count() >= 1
        assert layer.graph.edge_count() >= 1

    def test_get_context_for_llm(self, layer):
        """生成 LLM 上下文"""
        layer.store_preference("喜欢极简桌面", category="desktop")
        layer.store_knowledge("VS Code 是代码编辑器", category="app")
        ctx = layer.get_context_for_llm("帮我整理桌面")
        # 应该包含偏好信息
        assert "极简桌面" in ctx or "偏好" in ctx

    def test_convenience_methods(self, layer):
        """便捷方法"""
        mid = layer.store_preference("测试偏好")
        assert mid > 0

        mid = layer.store_knowledge("测试知识")
        assert mid > 0

        layer.add_entity_relation("user", "vscode", "uses")
        assert layer.graph.edge_count() >= 1

    def test_record_user_action(self, layer):
        """记录用户操作"""
        layer.record_user_action("chat", {"content": "hello"}, session_id="s1")
        results = layer.event.query(action="chat")
        assert len(results) >= 1
