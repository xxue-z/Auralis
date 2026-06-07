"""工具路由 — 桥接 LLM 工具调用与 MCP 插件系统"""

import logging
from typing import Any

from mcp.router import MCPRouter
from mcp.schema import MCPRequest, MCPResponse, MCPCapability

logger = logging.getLogger("auralis.router.tool")


class ToolRouter:
    """工具路由器：将 LLM 工具调用路由到 MCP 插件或前端"""

    def __init__(self, mcp_router: MCPRouter | None = None):
        self._mcp_router = mcp_router

    @property
    def mcp_router(self) -> MCPRouter | None:
        return self._mcp_router

    def set_mcp_router(self, router: MCPRouter) -> None:
        """设置 MCP 路由器"""
        self._mcp_router = router

    def can_handle_locally(self, capability_type: str) -> bool:
        """
        检查能力是否可以通过 MCP 插件本地处理

        Args:
            capability_type: 能力类型（如 'file.read', 'app.launch'）

        Returns:
            是否有本地插件可以处理
        """
        if not self._mcp_router:
            return False

        try:
            cap = MCPCapability.from_string(capability_type)
            self._mcp_router.route(cap)
            return True
        except KeyError:
            return False

    async def execute_locally(self, capability_type: str, payload: dict[str, Any]) -> dict:
        """
        通过 MCP 插件本地执行能力

        Args:
            capability_type: 能力类型（如 'file.read'）
            payload: 操作参数

        Returns:
            {"success": bool, "data": dict, "error": str|None}
        """
        if not self._mcp_router:
            return {"success": False, "data": None, "error": "MCP 路由器未初始化"}

        try:
            cap = MCPCapability.from_string(capability_type)
            plugin = self._mcp_router.route(cap)

            request = MCPRequest.create(
                namespace=cap.namespace,
                action=cap.action,
                input_data=payload,
            )

            response = await plugin.executor(request)

            return {
                "success": response.status == "success",
                "data": response.data,
                "error": response.error.get("message") if response.error else None,
            }

        except KeyError as e:
            return {"success": False, "data": None, "error": f"未找到插件: {e}"}
        except Exception as e:
            logger.error(f"本地执行失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def get_local_capabilities(self) -> list[str]:
        """获取所有可本地处理的能力"""
        if not self._mcp_router:
            return []
        return list(self._mcp_router.list_capabilities().keys())

    def get_stats(self) -> dict:
        """获取路由统计"""
        return {
            "mcp_router_available": self._mcp_router is not None,
            "local_capabilities": len(self.get_local_capabilities()),
        }
