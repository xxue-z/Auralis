"""端到端集成测试 — 验证整个系统协同工作"""

import pytest
import asyncio
from pathlib import Path
import json
import shutil
import tempfile

from mcp.schema import MCPRequest, MCPResponse, MCPCapability
from mcp.router import MCPRouter
from mcp.plugin_loader import PluginLoader
from mcp.validator import MCPValidator
from router.tool_router import ToolRouter
from policy.risk_engine import RiskEngine, RiskLevel
from policy.permission import PermissionChecker
from policy.confirmation import ConfirmationManager, ConfirmationDecision
from persona.behavior import PersonaBehavior
from memory.memory_layer import MemoryLayer
from planner.dag import TaskGraph, TaskNode
from planner.executor import TaskExecutor


class TestIntegrationEndToEnd:
    """端到端集成测试"""

    @pytest.fixture
    def full_system(self, tmp_path):
        """创建完整的测试系统"""
        plugins_dir = tmp_path / "plugins"
        for plugin_name, caps in [
            ("file.mcp", ["file.read", "file.write", "file.delete", "file.list"]),
        ]:
            plugin_dir = plugins_dir / plugin_name
            plugin_dir.mkdir(parents=True)
            with open(plugin_dir / "plugin.json", "w") as f:
                json.dump({"name": plugin_name, "version": "1.0.0", "capabilities": caps}, f)
            src = Path(__file__).parent.parent / "plugins" / plugin_name / "plugin.py"
            if src.exists():
                shutil.copy2(str(src), str(plugin_dir / "plugin.py"))

        loader = PluginLoader(plugins_dir=plugins_dir)
        results = loader.load_all()
        assert any(r["status"] == "ok" for r in results), f"插件加载失败: {results}"

        return {
            "loader": loader,
            "tool_router": ToolRouter(mcp_router=loader.router),
            "risk_engine": RiskEngine(),
            "permission_checker": PermissionChecker(),
            "confirm_manager": ConfirmationManager(),
            "memory_layer": MemoryLayer(tmp_path / "memory"),
            "behavior": PersonaBehavior({}),
            "validator": MCPValidator(),
        }

    def test_file_read_end_to_end(self, full_system):
        """端到端：文件读取"""
        test_file = Path(tempfile.mkdtemp()) / "test.txt"
        test_file.write_text("hello world")

        req = MCPRequest.create("file", "read", {"path": str(test_file)})
        errors = full_system["validator"].validate(req)
        assert errors == []

        risk_level, _ = full_system["risk_engine"].evaluate("file.read", {})
        assert risk_level == RiskLevel.LOW

        perm = full_system["permission_checker"].check("file.read", {}, risk_level)
        assert perm.allowed

        result = asyncio.get_event_loop().run_until_complete(
            full_system["tool_router"].execute_locally("file.read", {"path": str(test_file)})
        )
        assert result["success"]
        assert result["data"]["content"] == "hello world"

    def test_file_delete_high_risk(self, full_system):
        """端到端：文件删除（高风险）"""
        risk_level, _ = full_system["risk_engine"].evaluate("file.delete", {})
        assert risk_level == RiskLevel.HIGH

        perm = full_system["permission_checker"].check("file.delete", {}, risk_level)
        assert not perm.allowed

        confirm = full_system["confirm_manager"].decide("file.delete", {}, risk_level)
        assert confirm.decision == ConfirmationDecision.REQUIRE_CONFIRM

    def test_memory_integration(self, full_system):
        """端到端：记忆系统"""
        full_system["memory_layer"].store_preference("喜欢极简桌面", category="desktop")
        results = full_system["memory_layer"].semantic.search("桌面")
        assert len(results) >= 1

        ctx = full_system["memory_layer"].get_context_for_llm("帮我整理桌面")
        assert "极简桌面" in ctx or "桌面" in ctx

    def test_dag_execution(self):
        """端到端：DAG 执行"""
        async def mock_executor(tool_name, args):
            return {"success": True, "tool": tool_name}

        graph = TaskGraph()
        a = TaskNode(name="task_a", tool_name="t1", task_id="a")
        b = TaskNode(name="task_b", tool_name="t2", task_id="b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge("a", "b")

        executor = TaskExecutor(tool_executor=mock_executor)
        asyncio.get_event_loop().run_until_complete(executor.execute(graph))

        assert graph.nodes["a"].status.value == "completed"
        assert graph.nodes["b"].status.value == "completed"

    def test_mcp_protocol_flow(self, full_system):
        """端到端：MCP 协议流程"""
        req = MCPRequest.create("file", "list", {"path": "."})
        errors = full_system["validator"].validate(req)
        assert errors == []

        plugin = full_system["loader"].router.route(MCPCapability("file", "list"))
        assert plugin.name == "file.mcp"

        resp = asyncio.get_event_loop().run_until_complete(plugin.executor(req))
        assert resp.status == "success"


class TestUserPerspective:
    """用户视角测试"""

    def test_click_feedback(self):
        behavior = PersonaBehavior({"persona.humor": 0.5})
        msg = behavior.format_completion_message("点击操作", True)
        assert "完成" in msg or "搞定" in msg

    def test_file_operation_feedback(self):
        behavior = PersonaBehavior({"persona.humor": 0.5})
        msg = behavior.format_completion_message("文件清理", True)
        assert "清理" in msg

    def test_error_feedback(self):
        behavior = PersonaBehavior({"persona.humor": 0.5})
        msg = behavior.format_completion_message("文件删除", False)
        assert "失败" in msg

    def test_proactive_suggestion(self):
        behavior = PersonaBehavior({"persona.proactive": 0.5})
        assert behavior.should_proactive_suggest({"idle_time": 300})

    def test_confirmation_message(self):
        cm = ConfirmationManager()
        confirm = cm.decide("file.delete", {"path": "/tmp/test"}, RiskLevel.HIGH)
        assert "高风险" in confirm.message or "删除" in confirm.message
