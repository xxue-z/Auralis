"""小米 MiMo TTS 引擎 — 云端合成（OpenAI 兼容接口）"""

import base64
import logging
from typing import Optional

from .base import TTSEngine

logger = logging.getLogger("auralis.tts.xiaomi")


class XiaomiTTSEngine(TTSEngine):
    """
    小米 MiMo TTS 引擎

    API: https://api.xiaomimimo.com/v1/chat/completions
    认证: api-key 或 Authorization: Bearer
    模型: mimo-v2.5-tts
    文档: https://platform.xiaomimimo.com/docs/zh-CN/api/chat/openai-api
    """

    API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
    MODEL = "mimo-v2.5-tts"

    # 预设音色 → 小米音色 ID
    VOICE_MAP = {
        "sweet_female": "冰糖",
        "cute_female": "茉莉",
        "cool_female": "苏打",
        "gentle_male": "白桦",
        "energetic_male": "Milo",
        "neutral": "mimo_default",
    }

    # 音色风格描述（user message）
    VOICE_STYLE = {
        "sweet_female": "温柔甜美的女声，语调柔和",
        "cute_female": "可爱软萌的女声，语调活泼",
        "cool_female": "冷静优雅的女声，语调平稳",
        "gentle_male": "温和稳重的男声，语速适中",
        "energetic_male": "充满活力的男声，语速稍快",
        "neutral": "平和中性的声音，标准播报",
    }

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> Optional[bytes]:
        import httpx
        from config import config as app_config

        api_key = getattr(app_config, "MIMO_API_KEY", "")
        if not api_key:
            logger.error("MIMO_API_KEY 未配置")
            return None

        voice = self.VOICE_MAP.get(voice_id, "mimo_default")
        style = self.VOICE_STYLE.get(voice_id, "平和中性的声音")

        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "user", "content": style},
                {"role": "assistant", "content": text},
            ],
            "audio": {
                "format": "mp3",
                "voice": voice,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.API_URL, json=payload, headers=headers)
                resp.raise_for_status()

                data = resp.json()
                audio_b64 = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("audio", {})
                    .get("data")
                )

                if not audio_b64:
                    logger.warning("小米 TTS 响应中无音频数据")
                    return None

                return base64.b64decode(audio_b64)

        except httpx.HTTPStatusError as e:
            logger.error(f"小米 TTS HTTP 错误: {e.response.status_code} {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"小米 TTS 请求失败: {e}")
            return None

    def list_voices(self) -> list[dict]:
        return [
            {"id": k, "name": v, "engine": "xiaomi"}
            for k, v in self.VOICE_MAP.items()
        ]
