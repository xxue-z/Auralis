"""Kokoro 本地 TTS 引擎 — 轻量级本地推理（82M 参数）"""

import logging
from typing import Optional

from .base import TTSEngine

logger = logging.getLogger("auralis.tts.kokoro")


class KokoroEngine(TTSEngine):
    """
    Kokoro-82M 本地 TTS

    安装: pip install kokoro
    模型: hexgrad/Kokoro-82M（首次使用自动下载）
    特点: 82M 参数，推理快，支持中英文，离线可用
    """

    # 内置音色
    VOICE_MAP = {
        "sweet_female": "af_heart",
        "cute_female": "af_bella",
        "cool_female": "af_nicole",
        "gentle_male": "am_adam",
        "energetic_male": "am_michael",
        "neutral": "af_sarah",
    }

    def __init__(self):
        self._pipeline = None

    def _ensure_loaded(self):
        """懒加载模型（首次合成时初始化）"""
        if self._pipeline is not None:
            return

        try:
            from kokoro import KPipeline
            # lang_code: 'a' = American English, 'z' = 中文
            self._pipeline = KPipeline(lang_code="z")
            logger.info("Kokoro 模型加载完成")
        except ImportError:
            raise ImportError(
                "kokoro 未安装，请执行: pip install kokoro"
            )
        except Exception as e:
            raise RuntimeError(f"Kokoro 模型加载失败: {e}")

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> Optional[bytes]:
        import asyncio
        import io
        import soundfile as sf

        self._ensure_loaded()
        kokoro_voice = self.VOICE_MAP.get(voice_id, "af_sarah")

        # Kokoro 在线程池中运行（同步推理）
        def _run():
            audio_segments = []
            for _, _, audio in self._pipeline(text, voice=kokoro_voice, speed=speed):
                audio_segments.append(audio)
            if not audio_segments:
                return None
            import numpy as np
            combined = np.concatenate(audio_segments)
            buf = io.BytesIO()
            sf.write(buf, combined, 24000, format="WAV")
            return buf.getvalue()

        return await asyncio.to_thread(_run)

    def list_voices(self) -> list[dict]:
        return [
            {"id": k, "name": v, "engine": "kokoro", "label": "[测试版]"}
            for k, v in self.VOICE_MAP.items()
        ]
