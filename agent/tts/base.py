"""TTS 引擎抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional


class TTSEngine(ABC):
    """所有 TTS 引擎的统一接口"""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> Optional[bytes]:
        """
        合成语音

        Args:
            text: 要合成的文本
            voice_id: 音色标识（引擎内部映射）
            speed: 语速倍率（1.0 = 正常）
            pitch: 音调倍率（1.0 = 正常）

        Returns:
            音频数据（bytes），失败返回 None
        """
        ...

    @abstractmethod
    def list_voices(self) -> list[dict]:
        """列出该引擎可用的音色"""
        ...
