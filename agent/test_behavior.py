"""行为策略单元测试"""

import pytest
from persona.behavior import PersonaBehavior


class TestPersonaBehavior:

    @pytest.fixture
    def formal_behavior(self):
        """正式风格（低幽默、低主动性、高精确度）"""
        return PersonaBehavior({
            "persona.humor": 0.1,
            "persona.verbosity": 0.2,
            "persona.proactive": 0.1,
            "persona.precision": 0.9,
        })

    @pytest.fixture
    def friendly_behavior(self):
        """友好风格（中等幽默、中等主动性）"""
        return PersonaBehavior({
            "persona.humor": 0.5,
            "persona.verbosity": 0.5,
            "persona.proactive": 0.5,
            "persona.precision": 0.5,
        })

    @pytest.fixture
    def playful_behavior(self):
        """活泼风格（高幽默、高主动性、低精确度）"""
        return PersonaBehavior({
            "persona.humor": 0.9,
            "persona.verbosity": 0.8,
            "persona.proactive": 0.8,
            "persona.precision": 0.2,
        })

    def test_proactive_suggest_short_idle(self, formal_behavior):
        """短空闲时间不主动建议"""
        assert not formal_behavior.should_proactive_suggest({"idle_time": 10})

    def test_proactive_suggest_long_idle(self, playful_behavior):
        """长空闲时间主动建议"""
        assert playful_behavior.should_proactive_suggest({"idle_time": 300})

    def test_confirmation_style_low_risk(self, formal_behavior):
        """低风险确认方式"""
        style = formal_behavior.get_confirmation_style("low")
        assert style in ("skip", "simple", "standard")

    def test_confirmation_style_high_risk(self, formal_behavior):
        """高风险总是需要确认"""
        style = formal_behavior.get_confirmation_style("high")
        assert style in ("standard", "detailed")

    def test_humor_threshold(self, friendly_behavior):
        """幽默阈值"""
        assert not friendly_behavior.should_add_humor()  # 0.5 < 0.6

    def test_humor_high(self, playful_behavior):
        """高幽默"""
        assert playful_behavior.should_add_humor()  # 0.9 > 0.6

    def test_response_length_short(self, formal_behavior):
        """短回复"""
        assert formal_behavior.get_response_length_hint() == "short"

    def test_response_length_long(self, playful_behavior):
        """长回复"""
        assert playful_behavior.get_response_length_hint() == "long"

    def test_suggest_follow_up(self, playful_behavior):
        """建议后续操作"""
        assert playful_behavior.should_suggest_follow_up()

    def test_completion_message_success(self, playful_behavior):
        """成功完成消息"""
        msg = playful_behavior.format_completion_message("文件清理", True)
        assert "完成" in msg or "搞定" in msg

    def test_completion_message_failure(self, formal_behavior):
        """失败消息"""
        msg = formal_behavior.format_completion_message("文件清理", False)
        assert "失败" in msg

    def test_greeting_formal(self, formal_behavior):
        """正式问候"""
        greeting = formal_behavior.get_greeting("morning")
        assert "早上好" in greeting
        assert "☀️" not in greeting  # 正式风格不带表情

    def test_greeting_playful(self, playful_behavior):
        """活泼问候"""
        greeting = playful_behavior.get_greeting("morning")
        assert "早" in greeting
        assert "🌅" in greeting  # 活泼风格带表情

    def test_default_settings(self):
        """默认设置"""
        behavior = PersonaBehavior({})
        assert behavior.humor == 0.5
        assert behavior.verbosity == 0.4
        assert behavior.proactive == 0.3
        assert behavior.precision == 0.8
