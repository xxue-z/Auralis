"""MCP 插件加载器 — 从 plugins/ 目录动态发现和加载插件"""

import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

from mcp.router import MCPRouter, PluginExecutor
from mcp.schema import MCPRequest, MCPResponse

logger = logging.getLogger("auralis.mcp.loader")

DEFAULT_PLUGINS_DIR = Path(__file__).parent.parent.parent / "plugins"


class PluginMeta:
    """插件元信息（从 plugin.json 读取）"""

    def __init__(self, name: str, version: str, description: str, capabilities: list[str], entry: str = "plugin"):
        self.name = name
        self.version = version
        self.description = description
        self.capabilities = capabilities
        self.entry = entry

    @classmethod
    def from_json(cls, data: dict) -> "PluginMeta":
        return cls(
            name=data["name"],
            version=data.get("version", "0.0.1"),
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            entry=data.get("entry", "plugin"),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": self.capabilities,
        }


class PluginLoader:
    """MCP 插件加载器"""

    def __init__(
        self,
        plugins_dir: Path | str | None = None,
        router: MCPRouter | None = None,
    ):
        self._plugins_dir = Path(plugins_dir or DEFAULT_PLUGINS_DIR)
        self._router = router or MCPRouter()
        self._loaded: dict[str, PluginMeta] = {}  # name → meta
        self._modules: dict[str, Any] = {}  # name → module

    @property
    def router(self) -> MCPRouter:
        """关联的路由器"""
        return self._router

    def load_all(self) -> list[dict]:
        """
        加载 plugins/ 目录下的所有插件

        Returns:
            加载结果列表 [{"name": str, "status": "ok"|"error", "error": str|None}]
        """
        results = []

        if not self._plugins_dir.exists():
            logger.info(f"插件目录不存在: {self._plugins_dir}")
            return results

        for plugin_dir in sorted(self._plugins_dir.iterdir()):
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("."):
                result = self.load_plugin(plugin_dir)
                results.append(result)

        logger.info(f"加载完成: {sum(1 for r in results if r['status'] == 'ok')} 个插件成功")
        return results

    def load_plugin(self, plugin_dir: Path) -> dict:
        """
        加载单个插件

        Args:
            plugin_dir: 插件目录路径

        Returns:
            {"name": str, "status": "ok"|"error", "error": str|None}
        """
        plugin_json = plugin_dir / "plugin.json"
        if not plugin_json.exists():
            return {"name": plugin_dir.name, "status": "error", "error": "缺少 plugin.json"}

        try:
            # 读取插件元信息
            with open(plugin_json, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
            meta = PluginMeta.from_json(meta_data)

            # 加载插件模块
            module_name = f"mcp_plugins.{meta.name.replace('.', '_')}"
            plugin_py = plugin_dir / f"{meta.entry}.py"
            if not plugin_py.exists():
                plugin_py = plugin_dir / "__init__.py"
            if not plugin_py.exists():
                return {"name": meta.name, "status": "error", "error": f"找不到入口文件: {meta.entry}.py"}

            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, plugin_py)
            if not spec or not spec.loader:
                return {"name": meta.name, "status": "error", "error": f"无法加载模块: {plugin_py}"}

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 获取插件执行器
            executor_func = getattr(module, "execute", None)
            if not executor_func:
                # 尝试获取 plugin 对象的 execute 方法
                plugin_obj = getattr(module, meta.entry, None) or getattr(module, "plugin", None)
                if plugin_obj and hasattr(plugin_obj, "execute"):
                    executor_func = plugin_obj.execute
                else:
                    return {"name": meta.name, "status": "error", "error": "找不到 execute 方法"}

            # 包装执行器（添加审计日志）
            async def wrapped_executor(request: MCPRequest, _exec=executor_func, _meta=meta) -> MCPResponse:
                try:
                    result = await _exec(request)
                    return result
                except Exception as e:
                    logger.error(f"插件 {_meta.name} 执行失败: {e}")
                    return MCPResponse.error(request.id, "PLUGIN_ERROR", str(e))

            # 注册到路由器
            self._router.register_plugin(meta.name, meta.capabilities, wrapped_executor)
            self._loaded[meta.name] = meta
            self._modules[meta.name] = module

            # 调用 onLoad 钩子
            on_load = getattr(module, "on_load", None) or getattr(module, "onLoad", None)
            if on_load:
                try:
                    if callable(on_load):
                        result = on_load()
                        if hasattr(result, "__await__"):
                            import asyncio
                            asyncio.get_event_loop().run_until_complete(result)
                except Exception as e:
                    logger.warning(f"插件 {meta.name} onLoad 钩子失败: {e}")

            logger.info(f"加载插件: {meta.name} v{meta.version} ({len(meta.capabilities)} 个能力)")
            return {"name": meta.name, "status": "ok", "error": None}

        except json.JSONDecodeError as e:
            return {"name": plugin_dir.name, "status": "error", "error": f"plugin.json 格式错误: {e}"}
        except Exception as e:
            return {"name": plugin_dir.name, "status": "error", "error": str(e)}

    def unload_plugin(self, name: str) -> bool:
        """
        卸载插件

        Returns:
            是否成功卸载
        """
        if name not in self._loaded:
            return False

        # 调用 onUnload 钩子
        module = self._modules.get(name)
        if module:
            on_unload = getattr(module, "on_unload", None) or getattr(module, "onUnload", None)
            if on_unload:
                try:
                    if callable(on_unload):
                        result = on_unload()
                        if hasattr(result, "__await__"):
                            import asyncio
                            asyncio.get_event_loop().run_until_complete(result)
                except Exception as e:
                    logger.warning(f"插件 {name} onUnload 钩子失败: {e}")

        # 从路由器注销
        self._router.unregister_plugin(name)

        # 清理
        module_name = f"mcp_plugins.{name.replace('.', '_')}"
        sys.modules.pop(module_name, None)
        self._loaded.pop(name, None)
        self._modules.pop(name, None)

        logger.info(f"卸载插件: {name}")
        return True

    def reload_plugin(self, name: str) -> dict:
        """
        重载插件

        Returns:
            加载结果
        """
        self.unload_plugin(name)

        plugin_dir = self._plugins_dir / name
        if not plugin_dir.exists():
            return {"name": name, "status": "error", "error": f"插件目录不存在: {plugin_dir}"}

        return self.load_plugin(plugin_dir)

    def list_plugins(self) -> list[dict]:
        """列出所有已加载的插件"""
        return [meta.to_dict() for meta in self._loaded.values()]
