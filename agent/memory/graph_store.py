"""图记忆 — 基于 JSON 的实体关系图谱"""

import json
import logging
import os
import tempfile
from collections import deque
from pathlib import Path
from typing import Any

logger = logging.getLogger("auralis.memory.graph")

DEFAULT_GRAPH_PATH = Path(__file__).parent.parent / "data" / "graph.json"


class GraphStore:
    """图记忆 — 存储实体间的关系（用户→应用、项目→文件等）"""

    def __init__(self, path: Path | str | None = None):
        self._path = Path(path or DEFAULT_GRAPH_PATH)
        self._data = self._load()

    def _load(self) -> dict:
        """加载图数据"""
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 确保结构完整
                    data.setdefault("nodes", [])
                    data.setdefault("edges", [])
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载图数据失败: {e}")
        return {"nodes": [], "edges": []}

    def _save(self):
        """保存图数据（原子写入：先写临时文件再替换）"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=self._path.parent, suffix=".tmp", prefix="graph_"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except Exception:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    # === 节点操作 ===

    def add_node(self, node_id: str, node_type: str, properties: dict | None = None) -> None:
        """
        添加节点

        Args:
            node_id: 节点唯一标识
            node_type: 节点类型 ('user' | 'project' | 'file' | 'app' | 'tool' | 'folder')
            properties: 节点属性
        """
        # 检查是否已存在
        existing = self.get_node(node_id)
        if existing:
            # 更新类型和属性
            existing["type"] = node_type
            if properties:
                existing["properties"].update(properties)
        else:
            self._data["nodes"].append({
                "id": node_id,
                "type": node_type,
                "properties": properties or {},
            })
        self._save()

    def get_node(self, node_id: str) -> dict | None:
        """获取节点"""
        for node in self._data["nodes"]:
            if node["id"] == node_id:
                return node
        return None

    def get_nodes_by_type(self, node_type: str) -> list[dict]:
        """按类型获取节点"""
        return [n for n in self._data["nodes"] if n["type"] == node_type]

    def get_all_node_ids(self) -> list[str]:
        """获取所有节点 ID"""
        return [n["id"] for n in self._data["nodes"]]

    def remove_node(self, node_id: str) -> bool:
        """删除节点及其所有边"""
        original_count = len(self._data["nodes"])
        self._data["nodes"] = [n for n in self._data["nodes"] if n["id"] != node_id]
        # 删除相关边
        self._data["edges"] = [
            e for e in self._data["edges"]
            if e["source"] != node_id and e["target"] != node_id
        ]
        if len(self._data["nodes"]) < original_count:
            self._save()
            return True
        return False

    # === 边操作 ===

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        properties: dict | None = None,
    ) -> None:
        """
        添加边

        Args:
            source: 源节点 ID
            target: 目标节点 ID
            relation: 关系类型 ('uses' | 'owns' | 'related_to' | 'prefers' | 'contains')
            properties: 边属性
        """
        # 检查是否已存在相同关系
        for edge in self._data["edges"]:
            if edge["source"] == source and edge["target"] == target and edge["relation"] == relation:
                # 合并属性
                if properties:
                    edge["properties"].update(properties)
                self._save()
                return

        self._data["edges"].append({
            "source": source,
            "target": target,
            "relation": relation,
            "properties": properties or {},
        })
        self._save()

    def get_edges(
        self,
        source: str | None = None,
        relation: str | None = None,
        target: str | None = None,
    ) -> list[dict]:
        """查询边"""
        results = []
        for edge in self._data["edges"]:
            if source and edge["source"] != source:
                continue
            if relation and edge["relation"] != relation:
                continue
            if target and edge["target"] != target:
                continue
            results.append(edge)
        return results

    def remove_edge(self, source: str, target: str, relation: str) -> bool:
        """删除指定边"""
        original_count = len(self._data["edges"])
        self._data["edges"] = [
            e for e in self._data["edges"]
            if not (e["source"] == source and e["target"] == target and e["relation"] == relation)
        ]
        if len(self._data["edges"]) < original_count:
            self._save()
            return True
        return False

    # === 查询 ===

    def get_related(self, node_id: str, depth: int = 1) -> dict:
        """
        BFS 获取关联节点

        Args:
            node_id: 起始节点 ID
            depth: 搜索深度

        Returns:
            {"nodes": [...], "edges": [...]}
        """
        visited = set()
        result_nodes = []
        result_edges = []

        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            current_id, current_depth = queue.popleft()
            if current_id in visited or current_depth > depth:
                continue
            visited.add(current_id)

            for edge in self._data["edges"]:
                neighbor_id = None
                if edge["source"] == current_id:
                    neighbor_id = edge["target"]
                elif edge["target"] == current_id:
                    neighbor_id = edge["source"]

                if neighbor_id and neighbor_id not in visited:
                    result_edges.append(edge)
                    neighbor_node = self.get_node(neighbor_id)
                    if neighbor_node:
                        result_nodes.append(neighbor_node)
                    if current_depth + 1 <= depth:
                        queue.append((neighbor_id, current_depth + 1))

        return {"nodes": result_nodes, "edges": result_edges}

    def to_context_string(self, node_id: str, depth: int = 2) -> str:
        """
        生成 LLM 可用的上下文字符串

        例如：
        "用户 --uses--> VS Code, VS Code --opens--> D:\\Project\\Auralis"
        """
        related = self.get_related(node_id, depth)
        if not related["edges"]:
            return ""

        lines = []
        for edge in related["edges"]:
            lines.append(f"{edge['source']} --{edge['relation']}--> {edge['target']}")
        return "\n".join(lines)

    # === 统计 ===

    def node_count(self) -> int:
        """节点数量"""
        return len(self._data["nodes"])

    def edge_count(self) -> int:
        """边数量"""
        return len(self._data["edges"])

    def stats(self) -> dict:
        """图统计信息"""
        node_types = {}
        for node in self._data["nodes"]:
            t = node["type"]
            node_types[t] = node_types.get(t, 0) + 1

        relation_types = {}
        for edge in self._data["edges"]:
            r = edge["relation"]
            relation_types[r] = relation_types.get(r, 0) + 1

        return {
            "total_nodes": len(self._data["nodes"]),
            "total_edges": len(self._data["edges"]),
            "node_types": node_types,
            "relation_types": relation_types,
        }
