"""system.mcp 插件单元测试"""

import pytest
from pathlib import Path
import json
import shutil

from mcp.schema import MCPRequest, MCPCapability
from mcp.plugin_loader import PluginLoader


class TestSystemPlugin:

    @pytest.fixture
    def loader(self, tmp_path):
        """创建加载了 system.mcp 插件的 loader"""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "system.mcp"
        plugin_dir.mkdir(parents=True)

        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({
                "name": "system.mcp",
                "version": "1.0.0",
                "capabilities": ["system.info", "system.lock", "system.clipboard.get", "system.clipboard.set"],
            }, f)

        src_plugin = Path(__file__).parent.parent / "plugins" / "system.mcp" / "plugin.py"
        shutil.copy2(str(src_plugin), str(plugin_dir / "plugin.py"))

        loader = PluginLoader(plugins_dir=plugins_dir)
        loader.load_all()
        return loader

    def _route_and_execute(self, loader, action, input_data):
        """路由并执行"""
        import asyncio
        plugin = loader.router.route(MCPCapability("system", action))
        req = MCPRequest.create("system", action, input_data)
        return asyncio.get_event_loop().run_until_complete(plugin.executor(req))

    def test_plugin_registered(self, loader):
        """插件已注册"""
        assert loader.router.has_capability("system.info")
        assert loader.router.has_capability("system.lock")
        assert loader.router.has_capability("system.clipboard.get")
        assert loader.router.has_capability("system.clipboard.set")

    def test_system_info(self, loader):
        """获取系统信息"""
        resp = self._route_and_execute(loader, "info", {})
        assert resp.status == "success"
        assert resp.data["os"] in ("Windows", "Linux", "Darwin")
        assert "hostname" in resp.data
        assert "python_version" in resp.data

    def test_clipboard_set_and_get(self, loader):
        """剪贴板写入和读取"""
        # 写入
        resp = self._route_and_execute(loader, "clipboard.set", {"text": "test clipboard content"})
        assert resp.status == "success"
        assert resp.data["success"] is True

        # 读取（剪贴板可能被其他进程占用，所以只检查状态）
        resp = self._route_and_execute(loader, "clipboard.get", {})
        assert resp.status == "success"
        assert "text" in resp.data

    def test_clipboard_set_empty(self, loader):
        """剪贴板写入空内容"""
        resp = self._route_and_execute(loader, "clipboard.set", {"text": ""})
        assert resp.status == "success"
        assert resp.data["success"] is False
