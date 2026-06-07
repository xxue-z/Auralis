"""人格系统 — 根据设置参数调整 Agent 行为"""

# 人格参数到提示词指令的映射
HUMOR_LEVELS = {
    (0.0, 0.3): "保持专业严肃，不使用玩笑或表情符号。",
    (0.3, 0.6): "偶尔使用轻松的语气，可以适当使用表情符号。",
    (0.6, 0.8): "语气活泼友好，善用比喻和表情符号。",
    (0.8, 1.0): "非常幽默风趣，像朋友一样聊天，多用表情符号和俏皮话。",
}

VERBOSITY_LEVELS = {
    (0.0, 0.3): "回复极简，一两句话说清楚即可。",
    (0.3, 0.6): "回复适中，简洁但包含必要信息。",
    (0.6, 0.8): "回复较详细，提供背景信息和建议。",
    (0.8, 1.0): "回复非常详细，包含完整解释、步骤和注意事项。",
}

PROACTIVE_LEVELS = {
    (0.0, 0.3): "只在用户明确提问时回答，不主动提供建议。",
    (0.3, 0.6): "回答问题后可以简要提供建议。",
    (0.6, 0.8): "主动提供建议和相关操作提示。",
    (0.8, 1.0): "非常主动，经常提供建议、提醒和额外帮助。",
}

PRECISION_LEVELS = {
    (0.0, 0.3): "大胆执行操作，不需要过多确认。",
    (0.3, 0.6): "正常执行操作，高风险操作需要确认。",
    (0.6, 0.8): "谨慎执行操作，重要操作前确认。",
    (0.8, 1.0): "非常谨慎，每个操作都先确认，提供详细风险说明。",
}


def _get_level_instruction(value: float, level_map: dict) -> str:
    """根据数值获取对应的提示词指令"""
    for (low, high), instruction in level_map.items():
        if low <= value < high:
            return instruction
    # 超出范围时使用最高级别
    return list(level_map.values())[-1]


def build_persona_prompt(settings: dict) -> str:
    """根据人格设置生成提示词片段

    Args:
        settings: 完整设置字典，包含 persona.* 设置

    Returns:
        人格提示词片段
    """
    humor = settings.get("persona.humor", 0.5)
    verbosity = settings.get("persona.verbosity", 0.4)
    proactive = settings.get("persona.proactive", 0.3)
    precision = settings.get("persona.precision", 0.8)

    parts = []
    parts.append(f"幽默风格：{_get_level_instruction(humor, HUMOR_LEVELS)}")
    parts.append(f"回复详细度：{_get_level_instruction(verbosity, VERBOSITY_LEVELS)}")
    parts.append(f"主动性：{_get_level_instruction(proactive, PROACTIVE_LEVELS)}")
    parts.append(f"操作谨慎度：{_get_level_instruction(precision, PRECISION_LEVELS)}")

    return "\n".join(parts)
