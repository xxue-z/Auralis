"""ToolRouter 单元测试"""

import pytest
import asyncio
from pathlib import Path
import json
import shutil

from router.tool_router import ToolRouter
from mcp.router import MCPRouter
from mcp.plugin_loader import PluginLoader
from mcp.schema import MCPRequest, MCPResponse


class TestToolRouter:

    @pytest.fixture
    def router_with_plugins(self, tmp_path):
        """创建带有 file.mcp 插件的 ToolRouter"""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "file.mcp"
        plugin_dir.mkdir(parents=True)

        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({
                "name": "file.mcp",
                "version": "1.0.0",
                "capabilities": ["file.read", "file.write", "file.delete", "file.list"],
            }, f)

        src_plugin = Path(__file__).parent.parent / "plugins" / "file.mcp" / "plugin.py"
        shutil.copy2(str(src_plugin), str(plugin_dir / "plugin.py"))

        loader = PluginLoader(plugins_dir=plugins_dir)
        loader.load_all()

        tool_router = ToolRouter(mcp_router=loader.router)
        return tool_router

    @pytest.fixture
    def router_without_plugins(self):
        """创建没有 MCP 路由器的 ToolRouter"""
        return ToolRouter()

    def test_can_handle_local(self, router_with_plugins):
        """可以本地处理的能力"""
        assert router_with_plugins.can_handle_locally("file.read")
        assert router_with_plugins.can_handle_locally("file.write")
        assert not router_with_plugins.can_handle_locally("unknown.capability")

    def test_can_handle_no_router(self, router_without_plugins):
        """没有 MCP 路由器时返回 False"""
        assert not router_without_plugins.can_handle_locally("file.read")

    def test_execute_locally_success(self, router_with_plugins, tmp_path):
        """本地执行成功"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        result = asyncio.get_event_loop().run_until_complete(
            router_with_plugins.execute_locally("file.read", {"path": str(test_file)})
        )
        assert result["success"] is True
        assert result["data"]["content"] == "hello"

    def test_execute_locally_not_found(self, router_with_plugins):
        """本地执行 - 文件不存在"""
        result = asyncio.get_event_loop().run_until_complete(
            router_with_plugins.execute_locally("file.read", {"path": "/nonexistent"})
        )
        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_execute_locally_unknown_capability(self, router_with_plugins):
        """本地执行 - 未知能力"""
        result = asyncio.get_event_loop().run_until_complete(
            router_with_plugins.execute_locally("unknown.action", {})
        )
        assert result["success"] is False

    def test_get_local_capabilities(self, router_with_plugins):
        """获取本地能力列表"""
        caps = router_with_plugins.get_local_capabilities()
        assert "file.read" in caps
        assert "file.write" in caps

    def test_get_stats(self, router_with_plugins):
        """获取统计信息"""
        stats = router_with_plugins.get_stats()
        assert stats["mcp_router_available"] is True
        assert stats["local_capabilities"] > 0

    def test_get_stats_no_router(self, router_without_plugins):
        """没有路由器时的统计"""
        stats = router_without_plugins.get_stats()
        assert stats["mcp_router_available"] is False
        assert stats["local_capabilities"] == 0
