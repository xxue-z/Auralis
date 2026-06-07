"""风险评估引擎 — 评估 Capability 操作的风险等级"""

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("auralis.policy.risk")


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"         # 0.0 ~ 0.3 (不含) — 自动执行
    MEDIUM = "medium"   # 0.3 ~ 0.7 (不含) — 建议确认
    HIGH = "high"       # 0.7 ~ 1.0 — 需要确认


# 各 Capability 类型的基础风险评分 (0.0 ~ 1.0)
RISK_SCORES: dict[str, float] = {
    # 文件操作
    "file.read": 0.1,
    "file.list": 0.1,
    "file.write": 0.4,
    "file.copy": 0.3,
    "file.move": 0.4,
    "file.delete": 0.8,
    # 应用操作
    "app.launch": 0.2,
    "app.close": 0.3,
    "app.list": 0.0,
    # 系统操作
    "system.info": 0.0,
    "system.lock": 0.5,
    "system.shutdown": 0.9,
    "system.clipboard.get": 0.1,
    "system.clipboard.set": 0.2,
}

# 系统关键路径前缀（小写）
SYSTEM_PATH_PREFIXES = [
    "c:/windows",
    "c:/program files",
    "c:/program files (x86)",
    "c:/programdata",
    "/system",
    "/library",
    "/usr",
    "/bin",
    "/sbin",
    "/etc",
]


def _score_to_level(score: float) -> RiskLevel:
    """分数转风险等级"""
    if score < 0.3:
        return RiskLevel.LOW
    elif score < 0.7:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.HIGH


def _is_system_path(path: str) -> bool:
    """检查路径是否为系统关键路径"""
    path_lower = path.lower().replace("\\", "/")
    for prefix in SYSTEM_PATH_PREFIXES:
        if path_lower.startswith(prefix):
            return True
    return False


class RiskEngine:
    """风险评估引擎"""

    def evaluate(self, capability_type: str, payload: dict[str, Any]) -> tuple[RiskLevel, float]:
        """
        评估操作风险

        Args:
            capability_type: Capability 类型（如 'file.delete'）
            payload: 操作参数

        Returns:
            (风险等级, 风险分数)
        """
        # 获取基础分数
        base_score = RISK_SCORES.get(capability_type, 0.5)

        # 根据 payload 调整分数
        adjusted = self._adjust_for_payload(base_score, capability_type, payload)

        level = _score_to_level(adjusted)
        logger.info(f"风险评估: {capability_type} → {level.value} ({adjusted:.2f})")
        return level, adjusted

    def _adjust_for_payload(
        self, base_score: float, capability_type: str, payload: dict[str, Any]
    ) -> float:
        """根据 payload 内容调整风险分数"""
        score = base_score

        # 文件操作：系统路径 → 高风险
        if capability_type.startswith("file."):
            # 检查所有可能的路径字段
            for key in ("path", "from", "to", "scope"):
                path = payload.get(key, "")
                if path and _is_system_path(path):
                    score = max(score, 0.9)
                    break

            # 删除递归 → 更高风险
            if capability_type == "file.delete" and payload.get("recursive"):
                score = min(score + 0.1, 1.0)

        # 关机操作：短延迟 → 更高风险
        if capability_type == "system.shutdown":
            delay = payload.get("delay", 0)
            if delay == 0:
                score = min(score + 0.1, 1.0)

        return min(max(score, 0.0), 1.0)

    def get_risk_description(self, capability_type: str, score: float) -> str:
        """获取风险描述"""
        level = _score_to_level(score)
        descriptions = {
            RiskLevel.LOW: "低风险操作，将自动执行",
            RiskLevel.MEDIUM: "中风险操作，建议确认后执行",
            RiskLevel.HIGH: "高风险操作，需要用户确认",
        }
        return descriptions.get(level, "未知风险等级")
