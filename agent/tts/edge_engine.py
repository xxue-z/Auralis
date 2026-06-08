"""Edge TTS 引擎 — 微软免费云端 TTS"""

import logging
from typing import Optional

from .base import TTSEngine

logger = logging.getLogger("auralis.tts.edge")


class EdgeTTSEngine(TTSEngine):
    """基于 edge-tts 的云端合成（免费、音质好、需网络）"""

    # 内置音色映射
    VOICE_MAP = {
        "sweet_female": "zh-CN-XiaoyiNeural",
        "cute_female": "zh-CN-liaoning-XiaobeiNeural",
        "cool_female": "zh-CN-shaanxi-XiaoniNeural",
        "gentle_male": "zh-CN-YunxiNeural",
        "energetic_male": "zh-CN-YunjianNeural",
        "neutral": "zh-CN-XiaoxiaoNeural",
    }

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> Optional[bytes]:
        from edge_tts import Communicate

        # 解析 voice_id：支持 preset 名或直接 edge-tts voice ID
        edge_voice = self.VOICE_MAP.get(voice_id, voice_id)

        # 转换 speed/pitch 为 edge-tts 格式
        # rate: 百分比（+0% 不合法，跳过）
        # pitch: 赫兹（edge-tts 不接受百分比 pitch，用 Hz 偏移）
        kwargs = {}
        rate_pct = round((speed - 1) * 100)
        if rate_pct != 0:
            kwargs["rate"] = f"+{rate_pct}%" if rate_pct > 0 else f"{rate_pct}%"
        pitch_offset = round((pitch - 1.0) * 50)  # 1.1 → +5Hz, 0.9 → -5Hz
        if pitch_offset != 0:
            kwargs["pitch"] = f"+{pitch_offset}Hz" if pitch_offset > 0 else f"{pitch_offset}Hz"

        communicate = Communicate(text, edge_voice, **kwargs)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        return audio_data if audio_data else None

    def list_voices(self) -> list[dict]:
        return [
            {"id": k, "name": v, "engine": "edge-tts"}
            for k, v in self.VOICE_MAP.items()
        ]
