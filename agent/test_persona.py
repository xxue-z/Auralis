"""人格系统单元测试"""

from persona.persona import build_persona_prompt, _get_level_instruction


class TestPersonaPrompt:
    """测试人格提示词生成"""

    def test_default_persona(self):
        settings = {}
        prompt = build_persona_prompt(settings)
        assert "幽默" in prompt
        assert "详细度" in prompt
        assert "主动性" in prompt
        assert "谨慎" in prompt

    def test_humor_levels(self):
        # 低幽默度
        prompt = build_persona_prompt({"persona.humor": 0.1})
        assert "专业严肃" in prompt

        # 高幽默度
        prompt = build_persona_prompt({"persona.humor": 0.9})
        assert "幽默风趣" in prompt

    def test_verbosity_levels(self):
        prompt = build_persona_prompt({"persona.verbosity": 0.1})
        assert "极简" in prompt

        prompt = build_persona_prompt({"persona.verbosity": 0.9})
        assert "非常详细" in prompt

    def test_proactive_levels(self):
        prompt = build_persona_prompt({"persona.proactive": 0.1})
        assert "不主动" in prompt

        prompt = build_persona_prompt({"persona.proactive": 0.9})
        assert "非常主动" in prompt

    def test_precision_levels(self):
        prompt = build_persona_prompt({"persona.precision": 0.1})
        assert "大胆" in prompt

        prompt = build_persona_prompt({"persona.precision": 0.9})
        assert "非常谨慎" in prompt

    def test_custom_full_settings(self):
        settings = {
            "persona.humor": 0.7,
            "persona.verbosity": 0.5,
            "persona.proactive": 0.4,
            "persona.precision": 0.6,
        }
        prompt = build_persona_prompt(settings)
        # 应包含所有四个维度
        assert "幽默" in prompt
        assert "详细度" in prompt
        assert "主动性" in prompt
        assert "谨慎" in prompt


class TestGetLevelInstruction:
    """测试级别映射"""

    def test_boundary_values(self):
        level_map = {
            (0.0, 0.5): "低",
            (0.5, 1.0): "高",
        }
        assert _get_level_instruction(0.0, level_map) == "低"
        assert _get_level_instruction(0.49, level_map) == "低"
        assert _get_level_instruction(0.5, level_map) == "高"
        assert _get_level_instruction(1.0, level_map) == "高"  # 超出范围用最高

    def test_out_of_range_uses_highest(self):
        level_map = {
            (0.0, 0.3): "低",
            (0.3, 0.7): "中",
            (0.7, 1.0): "高",
        }
        assert _get_level_instruction(1.5, level_map) == "高"
