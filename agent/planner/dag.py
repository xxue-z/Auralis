"""DAG 任务图 — 数据结构 + LLM 任务拆解"""

import json
import logging
import uuid
from enum import Enum
from typing import Any

logger = logging.getLogger("auralis.planner")


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"       # 等待执行
    READY = "ready"           # 依赖已满足，可执行
    RUNNING = "running"       # 正在执行
    COMPLETED = "completed"   # 执行成功
    FAILED = "failed"         # 执行失败
    SKIPPED = "skipped"       # 被跳过（上游失败）


class TaskNode:
    """任务节点"""

    def __init__(
        self,
        name: str,
        tool_name: str,
        args: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
        provides: list[str] | None = None,
        consumes: list[str] | None = None,
        task_id: str | None = None,
    ):
        self.id = task_id or str(uuid.uuid4())[:8]
        self.name = name
        self.tool_name = tool_name
        self.args = args or {}
        self.status = TaskStatus.PENDING
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.dependencies = dependencies or []
        self.provides = provides or []
        self.consumes = consumes or []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tool_name": self.tool_name,
            "args": self.args,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "dependencies": self.dependencies,
            "provides": self.provides,
            "consumes": self.consumes,
        }


class TaskGraph:
    """DAG 任务图"""

    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}
        self.edges: list[tuple[str, str]] = []  # (from_id, to_id)
        self._name_to_id: dict[str, str] = {}   # name → id 映射

    def add_node(self, node: TaskNode) -> None:
        """添加任务节点"""
        self.nodes[node.id] = node
        self._name_to_id[node.name] = node.id

    def add_edge(self, from_id: str, to_id: str) -> None:
        """添加依赖边（from_id 必须先于 to_id）"""
        self.edges.append((from_id, to_id))
        # 将依赖 id 添加到目标节点
        if to_id in self.nodes:
            self.nodes[to_id].dependencies.append(from_id)

    def get_ready_tasks(self) -> list[TaskNode]:
        """获取所有依赖已满足、可执行的任务（状态为 PENDING 或 READY）"""
        ready = []
        for node in self.nodes.values():
            if node.status not in (TaskStatus.PENDING, TaskStatus.READY):
                continue
            # 检查所有依赖是否已完成
            deps_met = all(
                self.nodes[dep_id].status == TaskStatus.COMPLETED
                for dep_id in node.dependencies
                if dep_id in self.nodes
            )
            if deps_met:
                ready.append(node)
        return ready

    def mark_completed(self, task_id: str, result: dict[str, Any] | None = None) -> None:
        """标记任务完成"""
        if task_id in self.nodes:
            self.nodes[task_id].status = TaskStatus.COMPLETED
            self.nodes[task_id].result = result

    def mark_failed(self, task_id: str, error: str = "") -> None:
        """标记任务失败"""
        if task_id in self.nodes:
            self.nodes[task_id].status = TaskStatus.FAILED
            self.nodes[task_id].error = error
            # 标记所有下游为 SKIPPED
            self._skip_downstream(task_id)

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        """更新任务状态"""
        if task_id in self.nodes:
            self.nodes[task_id].status = status

    def is_complete(self) -> bool:
        """所有任务是否都已完成（完成/失败/跳过）"""
        return all(
            n.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED)
            for n in self.nodes.values()
        )

    def topological_sort(self) -> list[list[str]]:
        """拓扑排序，返回分层结果（同层任务可并行）"""
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        for _, to_id in self.edges:
            if to_id in in_degree:
                in_degree[to_id] += 1

        layers: list[list[str]] = []
        remaining = set(self.nodes.keys())

        while remaining:
            # 找出入度为 0 的节点
            layer = [nid for nid in remaining if in_degree.get(nid, 0) == 0]
            if not layer:
                break  # 有环
            layers.append(layer)
            for nid in layer:
                remaining.remove(nid)
                # 只减去从当前节点出发的边
                for from_id, to_id in self.edges:
                    if from_id == nid and to_id in in_degree:
                        in_degree[to_id] -= 1

        return layers

    def detect_cycle(self) -> bool:
        """检测是否存在循环依赖"""
        layers = self.topological_sort()
        return len(layers) == 0 and len(self.nodes) > 0

    def get_upstream_results(self, task_id: str) -> dict[str, Any]:
        """获取上游任务的输出结果（用于变量引用解析）"""
        results = {}
        visited = set()

        def _collect(tid: str):
            if tid in visited or tid not in self.nodes:
                return
            visited.add(tid)
            node = self.nodes[tid]
            if node.status == TaskStatus.COMPLETED and node.result:
                for var_name in node.provides:
                    results[var_name] = node.result
                results[tid] = node.result       # 用任务 ID 作为引用
                results[node.name] = node.result  # 也用任务名作为引用
            for dep_id in node.dependencies:
                _collect(dep_id)

        _collect(task_id)
        return results

    def resolve_args(self, args: dict[str, Any], task_id: str) -> dict[str, Any]:
        """解析参数中的变量引用（{{task_name.result.field}}）"""
        upstream = self.get_upstream_results(task_id)
        return _resolve_refs(args, upstream)

    def to_dict(self) -> dict:
        """序列化为字典（用于前端进度展示）"""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [{"from": f, "to": t} for f, t in self.edges],
        }

    def _skip_downstream(self, failed_id: str) -> None:
        """标记失败节点的所有下游为 SKIPPED"""
        for _, to_id in self.edges:
            if to_id == failed_id:
                continue
            if to_id in self.nodes and self.nodes[to_id].status == TaskStatus.PENDING:
                # 检查是否依赖了失败的节点
                if failed_id in self.nodes[to_id].dependencies:
                    self.nodes[to_id].status = TaskStatus.SKIPPED
                    self._skip_downstream(to_id)

    @classmethod
    def from_dict(cls, data: dict | list) -> "TaskGraph":
        """从字典/列表构建 TaskGraph（解析 LLM 输出）"""
        graph = cls()

        if isinstance(data, dict):
            tasks = data.get("tasks", data.get("nodes", []))
        elif isinstance(data, list):
            tasks = data
        else:
            raise ValueError(f"无法解析任务数据: {type(data)}")

        # 第一遍：创建所有节点，记录 name → id 映射
        name_id_map: dict[str, str] = {}
        for task in tasks:
            node = TaskNode(
                name=task.get("name", "未命名任务"),
                tool_name=task.get("tool", task.get("tool_name", "")),
                args=task.get("args", {}),
                provides=task.get("provides", []),
                consumes=task.get("consumes", []),
            )
            graph.add_node(node)
            name_id_map[node.name] = node.id

        # 第二遍：解析依赖关系（支持按名称引用）
        for task in tasks:
            node_name = task.get("name", "")
            node_id = name_id_map.get(node_name)
            if not node_id:
                continue

            for dep_name in task.get("dependencies", []):
                dep_id = name_id_map.get(dep_name)
                if dep_id:
                    graph.add_edge(dep_id, node_id)
                else:
                    logger.warning(f"依赖任务不存在: {dep_name}")

        return graph


def _resolve_refs(obj: Any, upstream: dict[str, Any]) -> Any:
    """递归解析 {{ref}} 变量引用"""
    if isinstance(obj, str):
        # 简单变量引用：{{task_name}}
        if obj.startswith("{{") and obj.endswith("}}"):
            ref = obj[2:-2].strip()
            if ref in upstream:
                return upstream[ref]
        return obj
    elif isinstance(obj, dict):
        return {k: _resolve_refs(v, upstream) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_refs(item, upstream) for item in obj]
    return obj


# === LLM 任务拆解 ===

PLANNING_SYSTEM_PROMPT = """你是一个任务规划助手。将用户指令拆解为可执行的任务 DAG。

## 可用工具

1. **execute_capability** — 执行系统操作
   - capability_type: file.list | file.read | file.write | file.delete | file.move | file.copy | app.launch | app.close | app.list | system.info | system.lock | system.shutdown | system.clipboard
   - payload: 取决于 capability_type

2. **settings_query** — 查询应用设置（无参数）

3. **settings_change** — 修改应用设置
   - changes: [{"key": "设置项路径", "value": 新值}]

4. **open_settings** — 打开设置面板（无参数）

5. **close_settings** — 关闭设置面板（无参数）

## 输出格式

返回一个 JSON 数组，每个元素代表一个任务：

```json
[
  {
    "name": "任务名称（简短描述）",
    "tool": "工具名",
    "args": { ... },
    "dependencies": ["前置任务名称"],
    "provides": ["输出变量名"],
    "consumes": ["输入变量名"]
  }
]
```

## 规则

1. 如果任务之间有先后顺序或数据依赖，用 dependencies 表示
2. 如果没有依赖关系，dependencies 留空数组
3. args 中可以用 `{{任务名称}}` 引用上游任务的完整输出结果
4. 只返回 JSON 数组，不要包含其他文本或 markdown 代码块标记

## 示例

用户："扫描桌面文件，删除大于100MB的，然后打开 Chrome"
```json
[
  {
    "name": "扫描桌面",
    "tool": "execute_capability",
    "args": {"capability_type": "file.list", "payload": {"path": "~\\\\Desktop"}},
    "dependencies": [],
    "provides": ["桌面文件列表"],
    "consumes": []
  },
  {
    "name": "删除大文件",
    "tool": "execute_capability",
    "args": {"capability_type": "file.delete", "payload": {"path": "{{扫描桌面}}"}},
    "dependencies": ["扫描桌面"],
    "provides": [],
    "consumes": ["桌面文件列表"]
  },
  {
    "name": "打开 Chrome",
    "tool": "execute_capability",
    "args": {"capability_type": "app.launch", "payload": {"app_id": "chrome"}},
    "dependencies": [],
    "provides": [],
    "consumes": []
  }
]
```
"""


def build_planning_prompt(user_input: str) -> list[dict]:
    """构建任务拆解的 LLM 消息"""
    return [
        {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]


def parse_planning_result(llm_output: str | dict) -> list[dict]:
    """解析 LLM 返回的任务拆解结果"""
    if isinstance(llm_output, dict):
        # 如果 dict 已经包含 tasks/nodes 字段，直接返回
        if "tasks" in llm_output:
            return llm_output["tasks"] if isinstance(llm_output["tasks"], list) else []
        if "nodes" in llm_output:
            return llm_output["nodes"] if isinstance(llm_output["nodes"], list) else []
        content = llm_output.get("content", "")
    else:
        content = str(llm_output)

    # 尝试提取 JSON
    content = content.strip()

    # 去掉可能的 markdown 代码块标记
    if content.startswith("```"):
        lines = content.split("\n")
        # 去掉首尾的 ``` 行
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```") and not in_block:
                in_block = True
                continue
            elif line.strip() == "```" and in_block:
                break
            elif in_block:
                json_lines.append(line)
        content = "\n".join(json_lines)

    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "tasks" in result:
            return result["tasks"]
        else:
            logger.warning(f"LLM 返回格式不符合预期: {type(result)}")
            return []
    except json.JSONDecodeError as e:
        logger.warning(f"解析 LLM 任务拆解结果失败: {e}")
        return []
