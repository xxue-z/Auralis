"""AI 音线生成服务 — 根据文字描述生成音线"""

import logging

logger = logging.getLogger("auralis.tts.generator")


class VoiceGenerator:
    """根据文字描述生成音线配置"""

    # 声音特征关键词映射
    FEATURE_MAP = {
        # 音调
        "低沉": {"pitch": 0.7},
        "沙哑": {"pitch": 0.8, "timbre": "rough"},
        "尖细": {"pitch": 1.3},
        "高亢": {"pitch": 1.2},
        "温柔": {"pitch": 1.0, "speed": 0.95},
        # 语速
        "快速": {"speed": 1.2},
        "慢速": {"speed": 0.8},
        "急促": {"speed": 1.3},
        "缓慢": {"speed": 0.7},
        # 性别
        "男声": {"voice_id": "zh-CN-YunxiNeural"},
        "女声": {"voice_id": "zh-CN-XiaoyiNeural"},
        "少年": {"voice_id": "zh-CN-YunjianNeural"},
        "少女": {"voice_id": "zh-CN-XiaohanNeural"},
        # 情感
        "甜美": {"voice_id": "zh-CN-XiaoyiNeural", "pitch": 1.1},
        "活泼": {"voice_id": "zh-CN-YunjianNeural", "speed": 1.1},
        "沉稳": {"voice_id": "zh-CN-YunxiNeural", "speed": 0.95},
        "优雅": {"voice_id": "zh-CN-XiaomengNeural", "speed": 0.95},
        "可爱": {"voice_id": "zh-CN-XiaohanNeural", "pitch": 1.2},
        "冷酷": {"voice_id": "zh-CN-XiaomengNeural", "pitch": 0.95},
    }

    def generate(self, description: str) -> dict:
        """
        根据描述生成音线配置

        Args:
            description: 用户描述，如 "低沉沙哑的男声，像深夜电台主播"

        Returns:
            {
                "voice_id": str,
                "name": str,
                "description": str,
                "config": {"voice_id": str, "speed": float, "pitch": float}
            }
        """
        # 合并所有匹配的特征
        merged_config = {
            "voice_id": "zh-CN-XiaoxiaoNeural",  # 默认
            "speed": 1.0,
            "pitch": 1.0,
        }

        matched_features = []
        for keyword, config in self.FEATURE_MAP.items():
            if keyword in description:
                matched_features.append(keyword)
                for key, value in config.items():
                    if key == "voice_id":
                        merged_config["voice_id"] = value
                    else:
                        merged_config[key] = value

        # 生成名称
        name = description[:20] if len(description) > 20 else description
        if not matched_features:
            name = f"自定义_{name}"

        return {
            "voice_id": f"ai_{hash(description) % 10000}",
            "name": name,
            "description": description,
            "matched_features": matched_features,
            "config": merged_config,
        }
