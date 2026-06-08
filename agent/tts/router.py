"""TTS Router — 根据配置路由到对应引擎"""

import logging
from typing import Optional

from . import create_engine, list_engines
from .base import TTSEngine

logger = logging.getLogger("auralis.tts")

# 预设音线配置（provider + voice_id 映射）
VOICE_PRESETS = {
    "sweet_female": {
        "provider": "edge",
        "voice_id": "sweet_female",
        "speed": 1.0,
        "pitch": 1.1,
    },
    "cute_female": {
        "provider": "edge",
        "voice_id": "cute_female",
        "speed": 1.1,
        "pitch": 1.2,
    },
    "cool_female": {
        "provider": "edge",
        "voice_id": "cool_female",
        "speed": 0.95,
        "pitch": 1.0,
    },
    "gentle_male": {
        "provider": "edge",
        "voice_id": "gentle_male",
        "speed": 0.95,
        "pitch": 0.9,
    },
    "energetic_male": {
        "provider": "edge",
        "voice_id": "energetic_male",
        "speed": 1.1,
        "pitch": 1.0,
    },
    "neutral": {
        "provider": "edge",
        "voice_id": "neutral",
        "speed": 1.0,
        "pitch": 1.0,
    },
}


class TTSRouter:
    """TTS 路由：根据设置选择引擎，委托给工厂创建的引擎实例"""

    def __init__(self):
        self._custom_voices: dict[str, dict] = {}

    def register_custom_voice(self, voice_id: str, config: dict):
        """注册自定义音色（克隆或 AI 生成）"""
        self._custom_voices[voice_id] = config
        logger.info(f"注册自定义音色: {voice_id}")

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        settings: dict,
    ) -> Optional[bytes]:
        """
        合成语音

        Args:
            text: 要合成的文本
            voice_id: 音线 ID（preset_id 或 custom）
            settings: 完整设置字典

        Returns:
            音频数据（bytes），失败返回 None
        """
        # 获取音线配置（优先自定义音色）
        voice_config = self._custom_voices.get(voice_id)
        if not voice_config:
            voice_config = VOICE_PRESETS.get(voice_id, VOICE_PRESETS["neutral"])

        # 确定引擎（音线配置 > 全局设置）
        provider = voice_config.get("provider") or settings.get("voice.provider", "edge")
        speed = settings.get("voice.speed", voice_config.get("speed", 1.0))
        pitch = settings.get("voice.pitch", voice_config.get("pitch", 1.0))
        engine_voice_id = voice_config.get("voice_id", voice_id)

        # 通过工厂获取引擎
        engine = create_engine(provider)
        if not engine:
            logger.error(f"TTS 引擎不可用: {provider}，可用: {list_engines()}")
            return None

        try:
            return await engine.synthesize(text, engine_voice_id, speed, pitch)
        except Exception as e:
            logger.error(f"TTS 合成失败 [{provider}]: {e}")
            return None

    def get_available_engines(self) -> list[str]:
        """列出所有可用引擎"""
        return list_engines()
