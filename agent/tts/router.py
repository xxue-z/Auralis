"""TTS Router — 根据配置选择 TTS 引擎"""

import logging
from typing import Optional

logger = logging.getLogger("auralis.tts")

# 预设音线配置
VOICE_PRESETS = {
    "sweet_female": {
        "provider": "edge-tts",
        "voice_id": "zh-CN-XiaoyiNeural",
        "speed": 1.0,
        "pitch": 1.1,
    },
    "cute_female": {
        "provider": "edge-tts",
        "voice_id": "zh-CN-XiaohanNeural",
        "speed": 1.1,
        "pitch": 1.2,
    },
    "cool_female": {
        "provider": "edge-tts",
        "voice_id": "zh-CN-XiaomengNeural",
        "speed": 0.95,
        "pitch": 1.0,
    },
    "gentle_male": {
        "provider": "edge-tts",
        "voice_id": "zh-CN-YunxiNeural",
        "speed": 0.95,
        "pitch": 0.9,
    },
    "energetic_male": {
        "provider": "edge-tts",
        "voice_id": "zh-CN-YunjianNeural",
        "speed": 1.1,
        "pitch": 1.0,
    },
    "neutral": {
        "provider": "edge-tts",
        "voice_id": "zh-CN-XiaoxiaoNeural",
        "speed": 1.0,
        "pitch": 1.0,
    },
}


class TTSRouter:
    """TTS 路由：根据配置选择云端或本地 TTS"""

    def __init__(self):
        self._edge_tts = None
        self._openai_tts = None
        self._custom_voices: dict[str, dict] = {}  # 克隆/生成的自定义音色

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
        provider = settings.get("voice.provider", "edge-tts")
        speed = settings.get("voice.speed", 1.0)
        pitch = settings.get("voice.pitch", 1.0)

        # 获取音线配置（优先自定义音色）
        voice_config = self._custom_voices.get(voice_id)
        if not voice_config:
            voice_config = VOICE_PRESETS.get(voice_id, VOICE_PRESETS["neutral"])

        # 覆盖用户自定义的 speed/pitch
        voice_config = {**voice_config, "speed": speed, "pitch": pitch}

        try:
            if provider == "openai":
                return await self._openai_synthesize(text, voice_config)
            else:
                # 默认 edge-tts（免费，音质好）
                return await self._edge_synthesize(text, voice_config)
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            return None

    async def _edge_synthesize(self, text: str, config: dict) -> bytes:
        """Edge TTS 合成（微软免费 TTS）"""
        from edge_tts import Communicate

        voice_id = config["voice_id"]
        speed = config.get("speed", 1.0)
        pitch = config.get("pitch", 1.0)

        # 转换 speed/pitch 为 edge-tts 格式
        rate = f"+{int((speed - 1) * 100)}%" if speed >= 1 else f"{int((speed - 1) * 100)}%"
        pitch_str = f"+{int((pitch - 1) * 100)}%" if pitch >= 1 else f"{int((pitch - 1) * 100)}%"

        communicate = Communicate(text, voice_id, rate=rate, pitch=pitch_str)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        return audio_data

    async def _openai_synthesize(self, text: str, config: dict) -> bytes:
        """OpenAI TTS 合成"""
        from openai import AsyncOpenAI
        from config import config as app_config

        client = AsyncOpenAI(api_key=app_config.OPENAI_API_KEY)

        # OpenAI TTS voice 映射
        voice_map = {
            "sweet_female": "nova",
            "cute_female": "shimmer",
            "cool_female": "alloy",
            "gentle_male": "onyx",
            "energetic_male": "echo",
            "neutral": "fable",
        }

        voice = voice_map.get(config["voice_id"], "alloy")

        response = await client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
        )

        return await response.content
