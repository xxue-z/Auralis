"""确认管理 — 决定是否需要用户确认，生成确认消息"""

import logging
from enum import Enum
from typing import Any

from policy.risk_engine import RiskLevel

logger = logging.getLogger("auralis.policy.confirmation")


class ConfirmationDecision(Enum):
    """确认决策"""
    AUTO_APPROVE = "auto_approve"       # 自动执行
    REQUIRE_CONFIRM = "require_confirm"  # 需要用户确认
    REJECT = "reject"                    # 拒绝执行


class ConfirmationInfo:
    """确认信息"""

    def __init__(
        self,
        decision: ConfirmationDecision,
        message: str = "",
        risk_level: str = "low",
    ):
        self.decision = decision
        self.message = message
        self.risk_level = risk_level

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "message": self.message,
            "risk_level": self.risk_level,
        }


# 操作中文名称映射
OPERATION_NAMES: dict[str, str] = {
    "file.read": "读取文件",
    "file.list": "列出文件",
    "file.write": "写入文件",
    "file.copy": "复制文件",
    "file.move": "移动文件",
    "file.delete": "删除文件",
    "app.launch": "启动应用",
    "app.close": "关闭应用",
    "app.list": "列出应用",
    "system.info": "查看系统信息",
    "system.lock": "锁定系统",
    "system.shutdown": "关闭系统",
    "system.clipboard.get": "读取剪贴板",
    "system.clipboard.set": "写入剪贴板",
}


class ConfirmationManager:
    """确认管理器"""

    def decide(
        self,
        capability_type: str,
        payload: dict[str, Any],
        risk_level: RiskLevel,
    ) -> ConfirmationInfo:
        """
        决定是否需要用户确认

        Args:
            capability_type: Capability 类型
            payload: 操作参数
            risk_level: 风险等级

        Returns:
            ConfirmationInfo
        """
        if risk_level == RiskLevel.LOW:
            return ConfirmationInfo(
                decision=ConfirmationDecision.AUTO_APPROVE,
                risk_level=risk_level.value,
            )

        # MEDIUM 和 HIGH 都需要确认
        message = self._format_confirm_message(capability_type, payload, risk_level)
        return ConfirmationInfo(
            decision=ConfirmationDecision.REQUIRE_CONFIRM,
            message=message,
            risk_level=risk_level.value,
        )

    def _format_confirm_message(
        self,
        capability_type: str,
        payload: dict[str, Any],
        risk_level: RiskLevel,
    ) -> str:
        """生成确认提示消息"""
        op_name = OPERATION_NAMES.get(capability_type, capability_type)
        risk_label = "⚠️ 中风险" if risk_level == RiskLevel.MEDIUM else "🔴 高风险"

        # 根据操作类型生成具体提示
        if capability_type.startswith("file."):
            path = payload.get("path", payload.get("from", ""))
            if capability_type == "file.delete":
                return f"{risk_label}：确定要删除文件吗？\n路径: {path}"
            elif capability_type == "file.write":
                return f"{risk_label}：确定要写入文件吗？\n路径: {path}"
            elif capability_type == "file.copy":
                return f"{risk_label}：确定要复制文件吗？\n从: {payload.get('from', '')}\n到: {payload.get('to', '')}"
            elif capability_type == "file.move":
                return f"{risk_label}：确定要移动文件吗？\n从: {payload.get('from', '')}\n到: {payload.get('to', '')}"
            elif capability_type == "file.search":
                return f"{risk_label}：确定要在以下目录搜索吗？\n范围: {payload.get('scope', '')}"
            else:
                return f"{risk_label}：即将执行 {op_name}\n路径: {path}"

        elif capability_type == "system.shutdown":
            delay = payload.get("delay", 0)
            if delay > 0:
                return f"{risk_label}：确定要关闭系统吗？\n将在 {delay} 秒后关机"
            else:
                return f"{risk_label}：确定要立即关闭系统吗？"

        elif capability_type == "app.close":
            app_id = payload.get("app_id", "未知应用")
            return f"{risk_label}：确定要关闭 {app_id} 吗？"

        else:
            return f"{risk_label}：即将执行 {op_name}"
