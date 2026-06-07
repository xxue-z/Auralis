"""行为策略 — 性格参数影响 Agent 的实际行为决策"""

import logging
from typing import Any

logger = logging.getLogger("auralis.persona.behavior")


class PersonaBehavior:
    """人格行为策略：根据性格参数决定 Agent 行为"""

    def __init__(self, settings: dict):
        """
        Args:
            settings: 完整设置字典，包含 persona.* 设置
        """
        self.humor = settings.get("persona.humor", 0.5)
        self.verbosity = settings.get("persona.verbosity", 0.4)
        self.proactive = settings.get("persona.proactive", 0.3)
        self.precision = settings.get("persona.precision", 0.8)

    def should_proactive_suggest(self, context: dict) -> bool:
        """
        是否应该主动提供建议

        Args:
            context: 上下文信息
                - idle_time: 用户空闲时间（秒）
                - recent_actions: 最近的操作列表
                - current_task: 当前正在处理的任务

        Returns:
            是否应该主动建议
        """
        # 主动性越高，越容易主动发言
        idle_time = context.get("idle_time", 0)
        threshold = (1.0 - self.proactive) * 300  # 0.0→300s, 1.0→0s
        return idle_time > threshold

    def get_confirmation_style(self, risk_level: str) -> str:
        """
        根据性格决定确认方式

        Args:
            risk_level: 风险等级 ('low' | 'medium' | 'high')

        Returns:
            确认方式 ('skip' | 'simple' | 'standard' | 'detailed')
        """
        if risk_level == "low":
            # 低风险：根据精确度决定是否跳过确认
            if self.precision < 0.3:
                return "skip"  # 大胆执行，跳过确认
            return "simple"

        if risk_level == "high":
            # 高风险：总是需要确认
            if self.precision > 0.7:
                return "detailed"  # 详细确认
            return "standard"

        # 中风险：根据精确度决定
        if self.precision > 0.7:
            return "standard"
        elif self.precision < 0.3:
            return "simple"
        return "standard"

    def should_add_humor(self) -> bool:
        """是否应该添加幽默元素"""
        return self.humor > 0.6

    def get_response_length_hint(self) -> str:
        """
        获取回复长度提示

        Returns:
            'short' | 'medium' | 'long'
        """
        if self.verbosity < 0.3:
            return "short"
        elif self.verbosity > 0.7:
            return "long"
        return "medium"

    def should_suggest_follow_up(self) -> bool:
        """是否应该建议后续操作"""
        return self.proactive > 0.5

    def get_error_handling_style(self) -> str:
        """
        获取错误处理风格

        Returns:
            'terse' | 'standard' | 'detailed'
        """
        if self.verbosity < 0.3:
            return "terse"
        elif self.verbosity > 0.7:
            return "detailed"
        return "standard"

    def format_completion_message(self, task_name: str, success: bool) -> str:
        """
        根据性格格式化完成消息

        Args:
            task_name: 任务名称
            success: 是否成功

        Returns:
            格式化的完成消息
        """
        if success:
            if self.humor > 0.7:
                return f"✅ {task_name} 搞定啦！还有什么需要帮忙的吗？ 😊"
            elif self.humor > 0.4:
                return f"✅ {task_name} 已完成。"
            else:
                return f"{task_name} 执行完成。"
        else:
            if self.verbosity > 0.6:
                return f"❌ {task_name} 执行失败。请检查错误信息并重试。"
            else:
                return f"❌ {task_name} 失败。"

    def get_greeting(self, time_of_day: str = "default") -> str:
        """
        根据性格获取问候语

        Args:
            time_of_day: 'morning' | 'afternoon' | 'evening' | 'default'

        Returns:
            问候语
        """
        greetings = {
            "morning": {
                "formal": "早上好。",
                "friendly": "早上好！今天有什么可以帮你的吗？ ☀️",
                "playful": "早安呀！新的一天开始啦，准备好了吗？ 🌅",
            },
            "afternoon": {
                "formal": "下午好。",
                "friendly": "下午好！需要我帮忙处理什么吗？ 🌤️",
                "playful": "下午好～忙了一上午了吧？有什么需要帮忙的尽管说！ ☕",
            },
            "evening": {
                "formal": "晚上好。",
                "friendly": "晚上好！还在忙吗？有什么需要帮忙的尽管说～ 🌙",
                "playful": "晚上好呀！这么晚还在工作？注意休息哦～ 💫",
            },
            "default": {
                "formal": "你好。",
                "friendly": "你好！有什么可以帮你的吗？ ✨",
                "playful": "嗨！我在这里，随时准备帮忙！ 🎉",
            },
        }

        style = "formal"
        if self.humor > 0.6:
            style = "playful"
        elif self.humor > 0.3:
            style = "friendly"

        time_greetings = greetings.get(time_of_day, greetings["default"])
        return time_greetings.get(style, time_greetings["formal"])
