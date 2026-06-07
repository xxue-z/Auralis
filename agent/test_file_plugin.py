"""file.mcp 插件单元测试"""

import pytest
from pathlib import Path

from mcp.schema import MCPRequest, MCPResponse, MCPCapability
from mcp.router import MCPRouter
from mcp.plugin_loader import PluginLoader


class TestFilePlugin:

    @pytest.fixture
    def loader(self, tmp_path):
        """创建加载了 file.mcp 插件的 loader"""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "file.mcp"
        plugin_dir.mkdir(parents=True)

        # 复制 plugin.json
        import json
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({
                "name": "file.mcp",
                "version": "1.0.0",
                "capabilities": ["file.read", "file.write", "file.delete", "file.list", "file.copy", "file.move", "file.info"],
            }, f)

        # 复制 plugin.py（从实际文件读取）
        import shutil
        src_plugin = Path(__file__).parent.parent / "plugins" / "file.mcp" / "plugin.py"
        shutil.copy2(str(src_plugin), str(plugin_dir / "plugin.py"))

        loader = PluginLoader(plugins_dir=plugins_dir)
        loader.load_all()
        return loader

    def _route_and_execute(self, loader, action, input_data):
        """路由并执行"""
        import asyncio
        plugin = loader.router.route(MCPCapability("file", action))
        req = MCPRequest.create("file", action, input_data)
        return asyncio.get_event_loop().run_until_complete(plugin.executor(req))

    def test_read_file(self, loader, tmp_path):
        """读取文件"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world", encoding="utf-8")

        resp = self._route_and_execute(loader, "read", {"path": str(test_file)})
        assert resp.status == "success"
        assert resp.data["content"] == "hello world"

    def test_write_file(self, loader, tmp_path):
        """写入文件"""
        test_file = tmp_path / "output.txt"
        resp = self._route_and_execute(loader, "write", {"path": str(test_file), "content": "test data"})
        assert resp.status == "success"
        assert test_file.read_text() == "test data"

    def test_list_directory(self, loader, tmp_path):
        """列出目录"""
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")

        resp = self._route_and_execute(loader, "list", {"path": str(tmp_path)})
        assert resp.status == "success"
        names = [e["name"] for e in resp.data["entries"]]
        assert "a.txt" in names
        assert "b.txt" in names

    def test_delete_file(self, loader, tmp_path):
        """删除文件"""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("delete me")

        resp = self._route_and_execute(loader, "delete", {"path": str(test_file)})
        assert resp.status == "success"
        assert not test_file.exists()

    def test_copy_file(self, loader, tmp_path):
        """复制文件"""
        src = tmp_path / "src.txt"
        src.write_text("copy me")
        dst = tmp_path / "dst.txt"

        resp = self._route_and_execute(loader, "copy", {"from": str(src), "to": str(dst)})
        assert resp.status == "success"
        assert dst.read_text() == "copy me"

    def test_move_file(self, loader, tmp_path):
        """移动文件"""
        src = tmp_path / "src.txt"
        src.write_text("move me")
        dst = tmp_path / "dst.txt"

        resp = self._route_and_execute(loader, "move", {"from": str(src), "to": str(dst)})
        assert resp.status == "success"
        assert not src.exists()
        assert dst.read_text() == "move me"

    def test_file_info(self, loader, tmp_path):
        """获取文件信息"""
        test_file = tmp_path / "info.txt"
        test_file.write_text("info content")

        resp = self._route_and_execute(loader, "info", {"path": str(test_file)})
        assert resp.status == "success"
        assert resp.data["is_file"] is True
        assert resp.data["extension"] == ".txt"

    def test_read_nonexistent(self, loader):
        """读取不存在的文件"""
        resp = self._route_and_execute(loader, "read", {"path": "/nonexistent/file.txt"})
        assert resp.status == "error"
        assert resp.error["code"] == "NOT_FOUND"

    def test_write_creates_dirs(self, loader, tmp_path):
        """写入文件自动创建目录"""
        test_file = tmp_path / "sub" / "dir" / "file.txt"
        resp = self._route_and_execute(loader, "write", {"path": str(test_file), "content": "nested"})
        assert resp.status == "success"
        assert test_file.read_text() == "nested"

    def test_plugin_registered(self, loader):
        """插件已注册到路由器"""
        assert loader.router.has_capability("file.read")
        assert loader.router.has_capability("file.write")
        assert loader.router.has_capability("file.delete")
