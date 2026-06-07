"""MCP Router — 插件路由"""

import logging
from typing import Any, Callable, Awaitable

from mcp.schema import MCPRequest, MCPResponse, MCPCapability

logger = logging.getLogger("auralis.mcp.router")

# 插件执行器类型
PluginExecutor = Callable[[MCPRequest], Awaitable[MCPResponse]]


class PluginInfo:
    """插件信息"""

    def __init__(self, name: str, capabilities: list[str], executor: PluginExecutor):
        self.name = name
        self.capabilities = capabilities
        self.executor = executor

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "capabilities": self.capabilities,
        }


class MCPRouter:
    """MCP 插件路由器"""

    def __init__(self):
        self._plugins: dict[str, PluginInfo] = {}
        self._capability_map: dict[str, str] = {}  # capability -> plugin name

    def register_plugin(
        self,
        name: str,
        capabilities: list[str],
        executor: PluginExecutor,
    ) -> None:
        """
        注册插件

        Args:
            name: 插件名（如 'file.mcp'）
            capabilities: 支持的能力列表（如 ['file.read', 'file.delete']）
            executor: 执行器回调
        """
        if name in self._plugins:
            logger.warning(f"插件 '{name}' 已注册，将被覆盖")

        self._plugins[name] = PluginInfo(name, capabilities, executor)

        for cap in capabilities:
            if cap in self._capability_map:
                existing = self._capability_map[cap]
                logger.warning(f"能力 '{cap}' 已被插件 '{existing}' 注册，将被 '{name}' 覆盖")
            self._capability_map[cap] = name

        logger.info(f"注册插件: {name}，能力: {capabilities}")

    def unregister_plugin(self, name: str) -> bool:
        """
        注销插件

        Returns:
            是否成功注销
        """
        if name not in self._plugins:
            return False

        plugin = self._plugins[name]
        for cap in plugin.capabilities:
            if self._capability_map.get(cap) == name:
                self._capability_map.pop(cap, None)

        del self._plugins[name]
        logger.info(f"注销插件: {name}")
        return True

    def route(self, capability: MCPCapability) -> PluginInfo:
        """
        根据能力路由到对应插件

        Raises:
            KeyError: 未找到匹配的插件
        """
        cap_key = capability.full_name
        plugin_name = self._capability_map.get(cap_key)
        if not plugin_name:
            raise KeyError(f"未找到能力 '{cap_key}' 对应的插件")

        plugin = self._plugins.get(plugin_name)
        if not plugin:
            raise KeyError(f"插件 '{plugin_name}' 不存在")

        return plugin

    def has_capability(self, capability_name: str) -> bool:
        """检查能力是否已注册"""
        return capability_name in self._capability_map

    def list_plugins(self) -> list[dict]:
        """列出所有已注册插件"""
        return [p.to_dict() for p in self._plugins.values()]

    def list_capabilities(self) -> dict[str, str]:
        """列出所有已注册能力"""
        return dict(self._capability_map)

    def get_plugin(self, name: str) -> PluginInfo | None:
        """获取插件信息"""
        return self._plugins.get(name)
