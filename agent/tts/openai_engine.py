"""OpenAI TTS 引擎 — 云端合成（付费、高质量）"""

import logging
from typing import Optional

from .base import TTSEngine

logger = logging.getLogger("auralis.tts.openai")


class OpenAITTSEngine(TTSEngine):
    """基于 OpenAI TTS API 的云端合成"""

    VOICE_MAP = {
        "sweet_female": "nova",
        "cute_female": "shimmer",
        "cool_female": "alloy",
        "gentle_male": "onyx",
        "energetic_male": "echo",
        "neutral": "fable",
    }

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 1.0,
        api_key: str = "",
    ) -> Optional[bytes]:
        from openai import AsyncOpenAI
        from config import config as app_config

        key = api_key or app_config.OPENAI_API_KEY
        if not key:
            logger.error("OpenAI TTS: API Key 未配置（env OPENAI_API_KEY 或 模型设置中的 API Key）")
            return None

        client = AsyncOpenAI(api_key=key)
        voice = self.VOICE_MAP.get(voice_id, "alloy")

        response = await client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            speed=speed,
        )

        return response.content

    def list_voices(self) -> list[dict]:
        return [
            {"id": k, "name": v, "engine": "openai"}
            for k, v in self.VOICE_MAP.items()
        ]
