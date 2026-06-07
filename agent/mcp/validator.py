"""MCP Schema 校验器"""

import logging
from mcp.schema import MCPRequest, MCPCapability

logger = logging.getLogger("auralis.mcp.validator")

# 支持的命名空间
VALID_NAMESPACES = {"file", "app", "system", "ui"}

# 支持的动作（按命名空间）
VALID_ACTIONS = {
    "file": {"read", "write", "delete", "list", "search", "move", "copy", "info"},
    "app": {"launch", "close", "list", "focus"},
    "system": {"info", "lock", "shutdown", "clipboard.get", "clipboard.set"},
    "ui": {"click", "type", "screenshot", "find"},
}


class MCPValidator:
    """MCP 请求校验器"""

    def validate(self, request: MCPRequest) -> list[str]:
        """
        校验 MCP 请求

        Returns:
            错误消息列表（空列表表示校验通过）
        """
        errors = []

        # 校验 ID
        if not request.id:
            errors.append("请求 ID 不能为空")

        # 校验版本
        if request.version != "1.0":
            errors.append(f"不支持的版本: {request.version}（仅支持 1.0）")

        # 校验能力
        cap_errors = self._validate_capability(request.capability)
        errors.extend(cap_errors)

        # 校验输入
        if not isinstance(request.input, dict):
            errors.append("输入参数必须是字典类型")

        # 校验上下文
        if not isinstance(request.context, dict):
            errors.append("上下文必须是字典类型")

        return errors

    def _validate_capability(self, capability: MCPCapability) -> list[str]:
        """校验能力引用"""
        errors = []

        if not capability.namespace:
            errors.append("能力命名空间不能为空")
        elif capability.namespace not in VALID_NAMESPACES:
            errors.append(
                f"无效的命名空间: '{capability.namespace}'"
                f"（有效值: {', '.join(sorted(VALID_NAMESPACES))}）"
            )

        if not capability.action:
            errors.append("能力动作不能为空")
        elif capability.namespace in VALID_ACTIONS:
            valid = VALID_ACTIONS[capability.namespace]
            if capability.action not in valid:
                errors.append(
                    f"命名空间 '{capability.namespace}' 中无效的动作: '{capability.action}'"
                    f"（有效值: {', '.join(sorted(valid))}）"
                )

        return errors

    def validate_capability_string(self, cap_string: str) -> list[str]:
        """校验能力字符串格式（如 'file.delete'）"""
        try:
            cap = MCPCapability.from_string(cap_string)
            return self._validate_capability(cap)
        except ValueError as e:
            return [str(e)]
