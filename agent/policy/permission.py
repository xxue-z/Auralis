"""权限控制 — 检查操作是否被允许"""

import logging
from typing import Any

from policy.risk_engine import RiskLevel, _is_system_path

logger = logging.getLogger("auralis.policy.permission")


class PermissionResult:
    """权限检查结果"""

    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason

    def __bool__(self) -> bool:
        return self.allowed


class PermissionChecker:
    """权限控制器"""

    def check(
        self,
        capability_type: str,
        payload: dict[str, Any],
        risk_level: RiskLevel,
    ) -> PermissionResult:
        """
        检查操作是否被允许

        Args:
            capability_type: Capability 类型
            payload: 操作参数
            risk_level: 风险等级

        Returns:
            PermissionResult
        """
        # 高风险操作需要用户确认（不允许自动执行）
        if risk_level == RiskLevel.HIGH:
            return PermissionResult(
                False,
                f"高风险操作 '{capability_type}' 需要用户确认",
            )

        # 检查系统关键路径
        if self._has_system_path(payload):
            return PermissionResult(
                False,
                f"禁止操作系统关键路径",
            )

        logger.info(f"权限检查通过: {capability_type}")
        return PermissionResult(True)

    def _has_system_path(self, payload: dict[str, Any]) -> bool:
        """检查 payload 中是否包含系统关键路径"""
        # 检查常见路径字段
        for key in ("path", "from", "to"):
            path = payload.get(key, "")
            if path and _is_system_path(path):
                return True
        return False
