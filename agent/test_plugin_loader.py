"""MCP 插件加载器单元测试"""

import json
import pytest
from pathlib import Path

from mcp.plugin_loader import PluginLoader, PluginMeta
from mcp.router import MCPRouter
from mcp.schema import MCPRequest, MCPResponse


class TestPluginMeta:

    def test_from_json(self):
        """从 JSON 创建"""
        data = {
            "name": "test.mcp",
            "version": "1.0.0",
            "description": "测试插件",
            "capabilities": ["test.action"],
        }
        meta = PluginMeta.from_json(data)
        assert meta.name == "test.mcp"
        assert meta.version == "1.0.0"
        assert meta.capabilities == ["test.action"]

    def test_from_json_defaults(self):
        """默认值"""
        meta = PluginMeta.from_json({"name": "x"})
        assert meta.version == "0.0.1"
        assert meta.capabilities == []

    def test_to_dict(self):
        """序列化"""
        meta = PluginMeta.from_json({"name": "x", "version": "2.0", "description": "d", "capabilities": ["a.b"]})
        d = meta.to_dict()
        assert d["name"] == "x"
        assert d["version"] == "2.0"


class TestPluginLoader:

    @pytest.fixture
    def loader(self, tmp_path):
        """创建临时 PluginLoader"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        return PluginLoader(plugins_dir=plugins_dir, router=MCPRouter())

    def test_load_all_empty_dir(self, loader):
        """空目录无错误"""
        results = loader.load_all()
        assert results == []

    def test_load_plugin_from_dir(self, loader):
        """从目录加载插件"""
        plugin_dir = loader._plugins_dir / "test.mcp"
        plugin_dir.mkdir()

        # 写入 plugin.json
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({
                "name": "test.mcp",
                "version": "1.0.0",
                "description": "测试插件",
                "capabilities": ["test.action"],
            }, f)

        # 写入 plugin.py
        with open(plugin_dir / "plugin.py", "w") as f:
            f.write("""
from mcp.schema import MCPRequest, MCPResponse

async def execute(request: MCPRequest) -> MCPResponse:
    return MCPResponse.success(request.id, {"result": "ok"})
""")

        result = loader.load_plugin(plugin_dir)
        assert result["status"] == "ok"
        assert loader.router.has_capability("test.action")

    def test_load_invalid_plugin(self, loader):
        """无效插件跳过"""
        plugin_dir = loader._plugins_dir / "bad.mcp"
        plugin_dir.mkdir()
        # 没有 plugin.json

        result = loader.load_plugin(plugin_dir)
        assert result["status"] == "error"
        assert "plugin.json" in result["error"]

    def test_load_plugin_missing_entry(self, loader):
        """缺少入口文件"""
        plugin_dir = loader._plugins_dir / "noentry.mcp"
        plugin_dir.mkdir()
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({"name": "noentry.mcp", "capabilities": ["x.y"]}, f)

        result = loader.load_plugin(plugin_dir)
        assert result["status"] == "error"
        assert "入口文件" in result["error"]

    def test_load_plugin_invalid_json(self, loader):
        """plugin.json 格式错误"""
        plugin_dir = loader._plugins_dir / "badjson.mcp"
        plugin_dir.mkdir()
        with open(plugin_dir / "plugin.json", "w") as f:
            f.write("not json {{{")

        result = loader.load_plugin(plugin_dir)
        assert result["status"] == "error"
        assert "格式错误" in result["error"]

    def test_unload_plugin(self, loader):
        """卸载插件"""
        plugin_dir = loader._plugins_dir / "unload.mcp"
        plugin_dir.mkdir()
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({"name": "unload.mcp", "capabilities": ["u.x"]}, f)
        with open(plugin_dir / "plugin.py", "w") as f:
            f.write("async def execute(req): pass\n")

        loader.load_plugin(plugin_dir)
        assert loader.router.has_capability("u.x")

        assert loader.unload_plugin("unload.mcp")
        assert not loader.router.has_capability("u.x")

    def test_unload_nonexistent(self, loader):
        """卸载不存在的插件"""
        assert not loader.unload_plugin("nonexistent")

    def test_reload_plugin(self, loader):
        """重载插件"""
        plugin_dir = loader._plugins_dir / "reload.mcp"
        plugin_dir.mkdir()
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({"name": "reload.mcp", "capabilities": ["r.x"]}, f)
        with open(plugin_dir / "plugin.py", "w") as f:
            f.write("async def execute(req): pass\n")

        loader.load_plugin(plugin_dir)
        result = loader.reload_plugin("reload.mcp")
        assert result["status"] == "ok"

    def test_list_plugins(self, loader):
        """列出插件"""
        plugin_dir = loader._plugins_dir / "list.mcp"
        plugin_dir.mkdir()
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({"name": "list.mcp", "version": "1.0", "capabilities": ["l.x"]}, f)
        with open(plugin_dir / "plugin.py", "w") as f:
            f.write("async def execute(req): pass\n")

        loader.load_plugin(plugin_dir)
        plugins = loader.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "list.mcp"

    def test_plugin_executor_works(self, loader):
        """插件执行器可正常调用"""
        plugin_dir = loader._plugins_dir / "exec.mcp"
        plugin_dir.mkdir()
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({"name": "exec.mcp", "capabilities": ["e.x"]}, f)
        with open(plugin_dir / "plugin.py", "w") as f:
            f.write("""
from mcp.schema import MCPRequest, MCPResponse

async def execute(request: MCPRequest) -> MCPResponse:
    return MCPResponse.success(request.id, {"echo": request.input.get("msg", "")})
""")

        loader.load_plugin(plugin_dir)

        # 通过路由器调用
        import asyncio
        from mcp.schema import MCPCapability
        plugin = loader.router.route(MCPCapability("e", "x"))
        req = MCPRequest.create("e", "x", {"msg": "hello"})
        resp = asyncio.get_event_loop().run_until_complete(plugin.executor(req))
        assert resp.status == "success"
        assert resp.data["echo"] == "hello"

    def test_load_all_multiple(self, loader):
        """加载多个插件"""
        for name, caps in [("a.mcp", ["a.x"]), ("b.mcp", ["b.y"])]:
            d = loader._plugins_dir / name
            d.mkdir()
            with open(d / "plugin.json", "w") as f:
                json.dump({"name": name, "capabilities": caps}, f)
            with open(d / "plugin.py", "w") as f:
                f.write("async def execute(req): pass\n")

        results = loader.load_all()
        assert len(results) == 2
        assert all(r["status"] == "ok" for r in results)
