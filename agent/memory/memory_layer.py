"""统一记忆接口 — 整合 Event/Semantic/Graph 三层记忆"""

import logging
from pathlib import Path
from typing import Any

from memory.event_store import EventStore
from memory.semantic_store import SemanticStore
from memory.graph_store import GraphStore

logger = logging.getLogger("auralis.memory")


class MemoryLayer:
    """统一记忆接口 — 为 LLM 提供上下文，管理三层记忆"""

    def __init__(self, data_dir: Path | str | None = None):
        """
        Args:
            data_dir: 数据目录（默认 agent/data/）
        """
        if data_dir:
            data_dir = Path(data_dir)
        else:
            data_dir = Path(__file__).parent.parent / "data"

        data_dir.mkdir(parents=True, exist_ok=True)

        self.event = EventStore(data_dir / "events.db")
        self.semantic = SemanticStore(data_dir / "semantic.db")
        self.graph = GraphStore(data_dir / "graph.json")

    def write(self, memory_type: str, data: dict) -> Any:
        """
        写入记忆

        Args:
            memory_type: 'event' | 'semantic' | 'graph'
            data: 记忆数据
        """
        if memory_type == "event":
            return self.event.record(
                event_type=data.get("event_type", "system_event"),
                action=data.get("action", ""),
                details=data.get("details"),
                result=data.get("result", "success"),
                session_id=data.get("session_id", ""),
            )
        elif memory_type == "semantic":
            return self.semantic.store(
                text=data["text"],
                memory_type=data.get("memory_type", "knowledge"),
                category=data.get("category"),
                source=data.get("source", "conversation"),
            )
        elif memory_type == "graph":
            if data.get("relation"):
                self.graph.add_edge(
                    source=data["source"],
                    target=data["target"],
                    relation=data["relation"],
                    properties=data.get("properties"),
                )
            else:
                self.graph.add_node(
                    node_id=data["id"],
                    node_type=data.get("type", "unknown"),
                    properties=data.get("properties"),
                )
        else:
            logger.warning(f"未知的记忆类型: {memory_type}")

    def search(self, query: str, types: list[str] | None = None) -> dict:
        """
        综合检索

        Args:
            query: 搜索关键词
            types: 检索类型列表（默认全部）

        Returns:
            {"events": [...], "semantic": [...], "graph": {...}}
        """
        types = types or ["event", "semantic", "graph"]
        results = {"events": [], "semantic": [], "graph": {}}

        if "event" in types:
            results["events"] = self.event.query(
                action=query, limit=10
            )

        if "semantic" in types:
            results["semantic"] = self.semantic.search(query, top_k=5)

        if "graph" in types:
            # 图检索使用节点 ID
            node = self.graph.get_node(query)
            if node:
                results["graph"] = self.graph.get_related(query, depth=2)

        return results

    def get_context_for_llm(self, user_input: str) -> str:
        """
        为 LLM 生成记忆上下文

        综合三层记忆，生成可注入 system prompt 的上下文文本
        """
        context_parts = []

        # 1. 用户偏好（语义记忆）
        preferences = self.semantic.get_user_preferences()
        if preferences:
            context_parts.append("用户偏好：" + "；".join(preferences[:5]))

        # 2. 相关语义记忆
        semantic_results = self.semantic.search(user_input, top_k=3)
        if semantic_results:
            texts = [r["text"] for r in semantic_results]
            context_parts.append("相关记忆：" + "；".join(texts))

        # 3. 实体关系（图记忆）
        # 尝试从用户输入中提取实体名
        for entity in self._extract_entities(user_input):
            related = self.graph.to_context_string(entity, depth=1)
            if related:
                context_parts.append(f"实体关系：\n{related}")

        return "\n".join(context_parts) if context_parts else ""

    def _extract_entities(self, text: str) -> list[str]:
        """从文本中提取可能的实体名（简单规则）"""
        entities = []
        # 检查图中已有的节点是否出现在文本中
        for node in self.graph._data["nodes"]:
            if node["id"] in text:
                entities.append(node["id"])
        return entities

    def record_user_action(
        self,
        action: str,
        details: dict | None = None,
        session_id: str = "",
    ) -> None:
        """便捷方法：记录用户操作事件"""
        self.write("event", {
            "event_type": "user_action",
            "action": action,
            "details": details,
            "result": "success",
            "session_id": session_id,
        })

    def store_preference(self, text: str, category: str | None = None) -> int:
        """便捷方法：存储用户偏好"""
        return self.write("semantic", {
            "text": text,
            "memory_type": "preference",
            "category": category,
        })

    def store_knowledge(self, text: str, category: str | None = None) -> int:
        """便捷方法：存储知识"""
        return self.write("semantic", {
            "text": text,
            "memory_type": "knowledge",
            "category": category,
        })

    def add_entity_relation(
        self,
        source: str,
        target: str,
        relation: str,
    ) -> None:
        """便捷方法：添加实体关系"""
        self.write("graph", {
            "source": source,
            "target": target,
            "relation": relation,
        })
