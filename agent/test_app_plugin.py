"""app.mcp 插件单元测试"""

import pytest
from pathlib import Path
import json
import shutil

from mcp.schema import MCPRequest, MCPCapability
from mcp.plugin_loader import PluginLoader


class TestAppPlugin:

    @pytest.fixture
    def loader(self, tmp_path):
        """创建加载了 app.mcp 插件的 loader"""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "app.mcp"
        plugin_dir.mkdir(parents=True)

        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({
                "name": "app.mcp",
                "version": "1.0.0",
                "capabilities": ["app.launch", "app.close", "app.list"],
            }, f)

        src_plugin = Path(__file__).parent.parent / "plugins" / "app.mcp" / "plugin.py"
        shutil.copy2(str(src_plugin), str(plugin_dir / "plugin.py"))

        loader = PluginLoader(plugins_dir=plugins_dir)
        loader.load_all()
        return loader

    def _route_and_execute(self, loader, action, input_data):
        """路由并执行"""
        import asyncio
        plugin = loader.router.route(MCPCapability("app", action))
        req = MCPRequest.create("app", action, input_data)
        return asyncio.get_event_loop().run_until_complete(plugin.executor(req))

    def test_plugin_registered(self, loader):
        """插件已注册"""
        assert loader.router.has_capability("app.launch")
        assert loader.router.has_capability("app.close")
        assert loader.router.has_capability("app.list")

    def test_list_processes(self, loader):
        """列出进程"""
        resp = self._route_and_execute(loader, "list", {})
        assert resp.status == "success"
        # 进程列表可能为空（取决于环境），但不应报错
        assert "count" in resp.data

    def test_launch_app(self, loader):
        """启动应用（使用 notepad，Windows 自带）"""
        resp = self._route_and_execute(loader, "launch", {"app_id": "notepad"})
        assert resp.status == "success"
        assert resp.data["launched"] is True
        # 清理：关闭 notepad
        import subprocess
        subprocess.run(["taskkill", "/IM", "notepad.exe", "/F"], capture_output=True)

    def test_close_nonexistent_pid(self, loader):
        """关闭不存在的 PID"""
        resp = self._route_and_execute(loader, "close", {"pid": 99999999})
        assert resp.status == "success"
        assert resp.data["closed"] is False

    def test_launch_missing_app_id(self, loader):
        """缺少 app_id 参数"""
        resp = self._route_and_execute(loader, "launch", {})
        assert resp.status == "error"
        assert "app_id" in resp.error["message"]

    def test_close_missing_params(self, loader):
        """缺少关闭参数"""
        resp = self._route_and_execute(loader, "close", {})
        assert resp.status == "error"
