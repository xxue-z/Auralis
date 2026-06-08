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
    ) -> Optional[bytes]:
        from openai import AsyncOpenAI
        from config import config as app_config

        client = AsyncOpenAI(api_key=app_config.OPENAI_API_KEY)
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
