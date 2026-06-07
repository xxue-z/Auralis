"""DAG Planner 单元测试"""

import asyncio
import pytest
from planner.dag import (
    TaskNode, TaskGraph, TaskStatus,
    parse_planning_result, build_planning_prompt,
    _resolve_refs,
)
from planner.executor import TaskExecutor, summarize_results


# ============================================================
# TaskNode 测试
# ============================================================

class TestTaskNode:

    def test_create_node(self):
        """创建节点"""
        node = TaskNode(name="扫描桌面", tool_name="execute_capability")
        assert node.name == "扫描桌面"
        assert node.tool_name == "execute_capability"
        assert node.status == TaskStatus.PENDING
        assert node.result is None
        assert node.error is None
        assert node.dependencies == []
        assert node.provides == []
        assert node.consumes == []

    def test_create_node_with_id(self):
        """指定 ID 创建节点"""
        node = TaskNode(name="test", tool_name="tool", task_id="custom-id")
        assert node.id == "custom-id"

    def test_create_node_with_args(self):
        """带参数创建节点"""
        node = TaskNode(
            name="读文件",
            tool_name="execute_capability",
            args={"capability_type": "file.read", "payload": {"path": "/tmp/test"}},
            provides=["file_content"],
            consumes=["file_path"],
        )
        assert node.args["capability_type"] == "file.read"
        assert node.provides == ["file_content"]
        assert node.consumes == ["file_path"]

    def test_node_to_dict(self):
        """节点序列化"""
        node = TaskNode(name="test", tool_name="tool", task_id="abc")
        d = node.to_dict()
        assert d["id"] == "abc"
        assert d["name"] == "test"
        assert d["tool_name"] == "tool"
        assert d["status"] == "pending"


# ============================================================
# TaskGraph 测试
# ============================================================

class TestTaskGraph:

    def test_add_node(self):
        """添加节点"""
        graph = TaskGraph()
        node = TaskNode(name="A", tool_name="t1", task_id="a")
        graph.add_node(node)
        assert "a" in graph.nodes
        assert graph.nodes["a"].name == "A"

    def test_add_edge(self):
        """添加依赖边"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")
        assert ("a", "b") in graph.edges
        assert "a" in graph.nodes["b"].dependencies

    def test_get_ready_tasks_no_deps(self):
        """无依赖的任务返回 READY"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)

        ready = graph.get_ready_tasks()
        assert len(ready) == 2
        names = {n.name for n in ready}
        assert "A" in names
        assert "B" in names

    def test_get_ready_tasks_with_deps(self):
        """有依赖的任务在依赖未满足时不返回"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "A"

    def test_get_ready_tasks_after_completion(self):
        """依赖完成后下游变为可执行"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")

        # 完成 A
        graph.mark_completed("a", {"result": "ok"})

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "B"

    def test_mark_completed(self):
        """标记完成"""
        graph = TaskGraph()
        node = TaskNode(name="A", tool_name="t1", task_id="a")
        graph.add_node(node)

        graph.mark_completed("a", {"data": "test"})
        assert graph.nodes["a"].status == TaskStatus.COMPLETED
        assert graph.nodes["a"].result == {"data": "test"}

    def test_mark_failed_skips_downstream(self):
        """标记失败时下游被跳过"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        c = TaskNode(name="C", tool_name="t3", task_id="c")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(c)
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        graph.mark_failed("a", "出错了")
        assert graph.nodes["a"].status == TaskStatus.FAILED
        assert graph.nodes["b"].status == TaskStatus.SKIPPED
        assert graph.nodes["c"].status == TaskStatus.SKIPPED

    def test_is_complete(self):
        """所有节点完成/失败/跳过时返回 True"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)

        assert not graph.is_complete()

        graph.mark_completed("a")
        assert not graph.is_complete()

        graph.mark_failed("b")
        assert graph.is_complete()

    def test_topological_sort(self):
        """拓扑排序分层正确"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        c = TaskNode(name="C", tool_name="t3", task_id="c")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(c)
        # A → B → C（链式依赖）
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        layers = graph.topological_sort()
        assert len(layers) == 3
        assert layers[0] == ["a"]
        assert layers[1] == ["b"]
        assert layers[2] == ["c"]

    def test_topological_sort_parallel(self):
        """无依赖任务在同一层"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        c = TaskNode(name="C", tool_name="t3", task_id="c")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(c)
        # A 和 B 无依赖，C 依赖 A 和 B
        graph.add_edge("a", "c")
        graph.add_edge("b", "c")

        layers = graph.topological_sort()
        assert len(layers) == 2
        assert set(layers[0]) == {"a", "b"}
        assert layers[1] == ["c"]

    def test_cycle_detection(self):
        """检测循环依赖"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")
        graph.add_edge("b", "a")

        assert graph.detect_cycle()

    def test_no_cycle(self):
        """无循环依赖"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")

        assert not graph.detect_cycle()

    def test_to_dict(self):
        """序列化为字典"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        graph.add_node(a)

        d = graph.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert len(d["nodes"]) == 1
        assert d["nodes"][0]["name"] == "A"

    def test_from_dict_list(self):
        """从列表构建 TaskGraph"""
        data = [
            {"name": "扫描桌面", "tool": "execute_capability", "args": {}, "dependencies": []},
            {"name": "删除文件", "tool": "execute_capability", "args": {}, "dependencies": ["扫描桌面"]},
        ]
        graph = TaskGraph.from_dict(data)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

        # 找到删除文件节点
        delete_node = None
        for n in graph.nodes.values():
            if n.name == "删除文件":
                delete_node = n
        assert delete_node is not None
        assert len(delete_node.dependencies) == 1

    def test_from_dict_with_dependencies(self):
        """从字典构建，依赖按名称解析"""
        data = [
            {"name": "A", "tool": "t1", "dependencies": []},
            {"name": "B", "tool": "t2", "dependencies": ["A"]},
            {"name": "C", "tool": "t3", "dependencies": ["A", "B"]},
        ]
        graph = TaskGraph.from_dict(data)
        layers = graph.topological_sort()
        assert len(layers) == 3

    def test_upstream_results(self):
        """获取上游任务输出"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a", provides=["data"])
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")

        graph.mark_completed("a", {"value": 42})
        results = graph.get_upstream_results("b")
        assert "data" in results
        assert results["data"]["value"] == 42

    def test_resolve_args(self):
        """解析参数中的变量引用"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a", provides=["data"])
        b = TaskNode(name="B", tool_name="t2", task_id="b",
                      args={"path": "{{A}}"}, consumes=["data"])
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")

        graph.mark_completed("a", {"path": "/tmp/test.txt"})
        resolved = graph.resolve_args(b.args, "b")
        assert resolved["path"] == {"path": "/tmp/test.txt"}


# ============================================================
# 变量引用解析测试
# ============================================================

class TestResolveRefs:

    def test_simple_ref(self):
        """简单变量引用"""
        upstream = {"A": {"path": "/tmp"}}
        result = _resolve_refs("{{A}}", upstream)
        assert result == {"path": "/tmp"}

    def test_no_ref(self):
        """无引用的字符串保持不变"""
        upstream = {"A": {"path": "/tmp"}}
        result = _resolve_refs("plain text", upstream)
        assert result == "plain text"

    def test_nested_ref(self):
        """嵌套变量引用"""
        upstream = {"A": {"value": 42}}
        result = _resolve_refs({"key": "{{A}}", "other": "static"}, upstream)
        assert result["key"] == {"value": 42}
        assert result["other"] == "static"

    def test_list_ref(self):
        """列表中的变量引用"""
        upstream = {"A": [1, 2, 3]}
        result = _resolve_refs(["{{A}}", "static"], upstream)
        assert result[0] == [1, 2, 3]
        assert result[1] == "static"

    def test_missing_ref(self):
        """不存在的引用保持原样"""
        upstream = {}
        result = _resolve_refs("{{missing}}", upstream)
        assert result == "{{missing}}"


# ============================================================
# LLM 拆解结果解析测试
# ============================================================

class TestParsePlanningResult:

    def test_parse_json_array(self):
        """解析 JSON 数组"""
        output = '[{"name": "A", "tool": "t1", "dependencies": []}]'
        result = parse_planning_result(output)
        assert len(result) == 1
        assert result[0]["name"] == "A"

    def test_parse_json_array_with_markdown(self):
        """解析带 markdown 代码块的 JSON"""
        output = '```json\n[{"name": "A", "tool": "t1", "dependencies": []}]\n```'
        result = parse_planning_result(output)
        assert len(result) == 1

    def test_parse_dict_with_tasks(self):
        """解析带 tasks 字段的字典"""
        output = {"tasks": [{"name": "A", "tool": "t1", "dependencies": []}]}
        result = parse_planning_result(output)
        assert len(result) == 1

    def test_parse_dict_passthrough(self):
        """解析 dict 输入"""
        output = {"content": '[{"name": "A", "tool": "t1", "dependencies": []}]'}
        result = parse_planning_result(output)
        assert len(result) == 1

    def test_parse_invalid_json(self):
        """解析无效 JSON 返回空列表"""
        result = parse_planning_result("not valid json {{{")
        assert result == []

    def test_parse_empty(self):
        """解析空内容"""
        result = parse_planning_result("")
        assert result == []


# ============================================================
# build_planning_prompt 测试
# ============================================================

class TestBuildPlanningPrompt:

    def test_prompt_structure(self):
        """提示词结构正确"""
        messages = build_planning_prompt("帮我清理桌面")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "任务规划" in messages[0]["content"]
        assert "清理桌面" in messages[1]["content"]


# ============================================================
# TaskExecutor 测试
# ============================================================

class TestTaskExecutor:

    def _run(self, coro):
        """运行异步测试"""
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_execute_single_task(self):
        """单任务 DAG 正确执行"""
        results = []

        async def executor(tool_name, args):
            results.append((tool_name, args))
            return {"success": True, "output": "done"}

        graph = TaskGraph()
        node = TaskNode(name="A", tool_name="t1", args={"x": 1}, task_id="a")
        graph.add_node(node)

        executor_obj = TaskExecutor(tool_executor=executor)
        self._run(executor_obj.execute(graph))

        assert len(results) == 1
        assert results[0][0] == "t1"
        assert graph.nodes["a"].status == TaskStatus.COMPLETED
        assert graph.nodes["a"].result == {"success": True, "output": "done"}

    def test_execute_parallel_tasks(self):
        """无依赖任务并行执行"""
        execution_order = []

        async def executor(tool_name, args):
            execution_order.append(tool_name)
            await asyncio.sleep(0.01)
            return {"success": True}

        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        c = TaskNode(name="C", tool_name="t3", task_id="c")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(c)

        executor_obj = TaskExecutor(tool_executor=executor)
        self._run(executor_obj.execute(graph))

        # 三个任务都应该执行
        assert len(execution_order) == 3
        assert graph.is_complete()

    def test_execute_sequential_tasks(self):
        """有依赖任务按序执行"""
        execution_order = []

        async def executor(tool_name, args):
            execution_order.append(tool_name)
            return {"success": True}

        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        c = TaskNode(name="C", tool_name="t3", task_id="c")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(c)
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        executor_obj = TaskExecutor(tool_executor=executor)
        self._run(executor_obj.execute(graph))

        # A 必须在 B 之前，B 必须在 C 之前
        assert execution_order == ["t1", "t2", "t3"]

    def test_execute_with_variable_ref(self):
        """上游结果正确传递给下游"""
        async def executor(tool_name, args):
            if tool_name == "producer":
                return {"value": 42}
            elif tool_name == "consumer":
                return {"received": args.get("input")}
            return {"success": True}

        graph = TaskGraph()
        a = TaskNode(name="生产数据", tool_name="producer", task_id="a", provides=["data"])
        b = TaskNode(name="消费数据", tool_name="consumer", task_id="b",
                      args={"input": "{{生产数据}}"}, consumes=["data"])
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")

        executor_obj = TaskExecutor(tool_executor=executor)
        self._run(executor_obj.execute(graph))

        # 下游应该收到了上游的结果
        assert graph.nodes["b"].result["received"]["value"] == 42

    def test_execute_failure_skips_downstream(self):
        """任务失败时下游被跳过"""
        async def executor(tool_name, args):
            if tool_name == "fail":
                raise RuntimeError("执行失败")
            return {"success": True}

        graph = TaskGraph()
        a = TaskNode(name="失败任务", tool_name="fail", task_id="a")
        b = TaskNode(name="下游任务", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")

        executor_obj = TaskExecutor(tool_executor=executor)
        self._run(executor_obj.execute(graph))

        assert graph.nodes["a"].status == TaskStatus.FAILED
        assert graph.nodes["b"].status == TaskStatus.SKIPPED

    def test_execute_progress_callback(self):
        """进度回调正确触发"""
        progress_calls = []

        async def on_progress(progress):
            progress_calls.append(progress)

        async def executor(tool_name, args):
            return {"success": True}

        graph = TaskGraph()
        node = TaskNode(name="A", tool_name="t1", task_id="a")
        graph.add_node(node)

        executor_obj = TaskExecutor(tool_executor=executor, on_progress=on_progress)
        self._run(executor_obj.execute(graph))

        # 至少调用了 2 次（初始 + 完成）
        assert len(progress_calls) >= 2

    def test_execute_empty_graph(self):
        """空图直接返回"""
        async def executor(tool_name, args):
            return {"success": True}

        graph = TaskGraph()
        executor_obj = TaskExecutor(tool_executor=executor)
        result = self._run(executor_obj.execute(graph))
        assert len(result.nodes) == 0

    def test_cycle_fails_all_tasks(self):
        """循环依赖时所有任务失败"""
        async def executor(tool_name, args):
            return {"success": True}

        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")
        graph.add_edge("b", "a")

        executor_obj = TaskExecutor(tool_executor=executor)
        self._run(executor_obj.execute(graph))

        assert graph.nodes["a"].status == TaskStatus.FAILED
        assert graph.nodes["b"].status == TaskStatus.FAILED


# ============================================================
# summarize_results 测试
# ============================================================

class TestSummarizeResults:

    def test_summarize_all_success(self):
        """全部成功"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.mark_completed("a")
        graph.mark_completed("b")

        summary = summarize_results(graph)
        assert "✅" in summary
        assert "2" in summary

    def test_summarize_with_failures(self):
        """有失败"""
        graph = TaskGraph()
        a = TaskNode(name="A", tool_name="t1", task_id="a")
        b = TaskNode(name="B", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.mark_completed("a")
        graph.mark_failed("b", "超时")

        summary = summarize_results(graph)
        assert "✅" in summary
        assert "❌" in summary
        assert "超时" in summary

    def test_summarize_empty(self):
        """空图"""
        graph = TaskGraph()
        summary = summarize_results(graph)
        assert "完成" in summary
