"""TTS 引擎单元测试"""

import asyncio
import io
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================
# 工厂测试
# ============================================================

class TestTTSFactory:
    """测试 TTS 工厂"""

    def test_list_engines(self):
        from tts import list_engines
        engines = list_engines()
        assert "edge" in engines
        assert "openai" in engines
        assert "xiaomi" in engines
        assert "kokoro" in engines
        assert "supertonic" not in engines

    def test_create_edge_engine(self):
        from tts import create_engine
        engine = create_engine("edge")
        assert engine is not None
        assert hasattr(engine, "synthesize")
        assert hasattr(engine, "list_voices")

    def test_create_unknown_engine_returns_none(self):
        from tts import create_engine
        engine = create_engine("nonexistent_engine")
        assert engine is None

    def test_engine_singleton_cache(self):
        from tts import create_engine
        e1 = create_engine("edge")
        e2 = create_engine("edge")
        assert e1 is e2

    def test_register_custom_engine(self):
        from tts import register_engine, _ENGINE_REGISTRY
        register_engine("fake_test", "nonexistent.module.FakeEngine")
        assert "fake_test" in _ENGINE_REGISTRY
        del _ENGINE_REGISTRY["fake_test"]


# ============================================================
# Edge TTS 引擎测试
# ============================================================

class TestEdgeTTSEngine:
    """测试 Edge TTS 引擎"""

    def test_voice_map(self):
        from tts.edge_engine import EdgeTTSEngine
        engine = EdgeTTSEngine()
        voices = engine.list_voices()
        assert len(voices) == 6
        ids = [v["id"] for v in voices]
        assert "sweet_female" in ids

    def test_synthesize_returns_bytes(self):
        from tts.edge_engine import EdgeTTSEngine
        engine = EdgeTTSEngine()

        mock_chunk = {"type": "audio", "data": b"\xff\xfb\x90\x00" * 100}

        async def fake_stream():
            yield mock_chunk

        mock_communicate = MagicMock()
        mock_communicate.stream = fake_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            result = asyncio.get_event_loop().run_until_complete(
                engine.synthesize("test", "sweet_female", speed=1.0, pitch=1.0)
            )
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_synthesize_empty_returns_none(self):
        from tts.edge_engine import EdgeTTSEngine
        engine = EdgeTTSEngine()

        async def empty_stream():
            return
            yield

        mock_communicate = MagicMock()
        mock_communicate.stream = empty_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            result = asyncio.get_event_loop().run_until_complete(
                engine.synthesize("test", "sweet_female")
            )
            assert result is None

    def test_speed_pitch_conversion(self):
        from tts.edge_engine import EdgeTTSEngine
        engine = EdgeTTSEngine()

        async def empty_stream():
            return
            yield

        mock_communicate = MagicMock()
        mock_communicate.stream = empty_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate) as MockComm:
            asyncio.get_event_loop().run_until_complete(
                engine.synthesize("test", "sweet_female", speed=1.2, pitch=1.1)
            )
            call_kwargs = MockComm.call_args
            assert call_kwargs.kwargs.get("rate") == "+20%"
            assert "pitch" in call_kwargs.kwargs

    def test_default_speed_pitch_no_params(self):
        from tts.edge_engine import EdgeTTSEngine
        engine = EdgeTTSEngine()

        async def empty_stream():
            return
            yield

        mock_communicate = MagicMock()
        mock_communicate.stream = empty_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate) as MockComm:
            asyncio.get_event_loop().run_until_complete(
                engine.synthesize("test", "sweet_female", speed=1.0, pitch=1.0)
            )
            call_kwargs = MockComm.call_args
            assert "rate" not in call_kwargs.kwargs
            assert "pitch" not in call_kwargs.kwargs


# ============================================================
# OpenAI TTS 引擎测试
# ============================================================

class TestOpenAITTSEngine:
    """测试 OpenAI TTS 引擎"""

    def test_voice_map(self):
        from tts.openai_engine import OpenAITTSEngine
        engine = OpenAITTSEngine()
        voices = engine.list_voices()
        assert len(voices) == 6

    def test_synthesize(self):
        from tts.openai_engine import OpenAITTSEngine
        engine = OpenAITTSEngine()

        mock_response = MagicMock()
        mock_response.content = b"\xff\xfb\x90\x00" * 100
        mock_client = MagicMock()
        # OpenAI SDK 返回的是 async context manager，.content 是 bytes
        mock_speech = MagicMock()
        mock_speech.create = AsyncMock(return_value=mock_response)
        mock_client.audio.speech = mock_speech

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            with patch("config.config") as mock_cfg:
                mock_cfg.OPENAI_API_KEY = "test-key"
                result = asyncio.get_event_loop().run_until_complete(
                    engine.synthesize("test", "sweet_female", speed=1.0)
                )
                assert isinstance(result, bytes)
                assert len(result) > 0


# ============================================================
# Xiaomi TTS 引擎测试
# ============================================================

class TestXiaomiTTSEngine:
    """测试小米 MiMo TTS 引擎"""

    def test_voice_map(self):
        from tts.xiaomi_engine import XiaomiTTSEngine
        engine = XiaomiTTSEngine()
        voices = engine.list_voices()
        assert len(voices) == 6
        ids = {v["id"]: v["name"] for v in voices}
        assert ids["sweet_female"] == "冰糖"
        assert ids["neutral"] == "mimo_default"

    def test_synthesize_success(self):
        from tts.xiaomi_engine import XiaomiTTSEngine
        engine = XiaomiTTSEngine()

        fake_audio_b64 = "ZmFrZV9hdWRpb19kYXRh"  # base64("fake_audio_data")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "audio": {"data": fake_audio_b64}
                }
            }]
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("config.config") as mock_cfg:
                mock_cfg.MIMO_API_KEY = "test-key"
                result = asyncio.get_event_loop().run_until_complete(
                    engine.synthesize("你好", "sweet_female")
                )
                assert result == b"fake_audio_data"

    def test_synthesize_no_api_key(self):
        from tts.xiaomi_engine import XiaomiTTSEngine
        engine = XiaomiTTSEngine()

        with patch("config.config") as mock_cfg:
            mock_cfg.MIMO_API_KEY = ""
            result = asyncio.get_event_loop().run_until_complete(
                engine.synthesize("你好", "sweet_female")
            )
            assert result is None

    def test_synthesize_empty_audio_response(self):
        from tts.xiaomi_engine import XiaomiTTSEngine
        engine = XiaomiTTSEngine()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("config.config") as mock_cfg:
                mock_cfg.MIMO_API_KEY = "test-key"
                result = asyncio.get_event_loop().run_until_complete(
                    engine.synthesize("你好", "sweet_female")
                )
                assert result is None

    def test_synthesize_http_error(self):
        from tts.xiaomi_engine import XiaomiTTSEngine
        import httpx
        engine = XiaomiTTSEngine()

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="401", request=MagicMock(), response=mock_response
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("config.config") as mock_cfg:
                mock_cfg.MIMO_API_KEY = "bad-key"
                result = asyncio.get_event_loop().run_until_complete(
                    engine.synthesize("你好", "sweet_female")
                )
                assert result is None


# ============================================================
# Kokoro 引擎测试（测试版）
# ============================================================

class TestKokoroEngine:
    """测试 Kokoro 本地 TTS 引擎"""

    def test_voice_map(self):
        from tts.kokoro_engine import KokoroEngine
        engine = KokoroEngine()
        voices = engine.list_voices()
        assert len(voices) == 6

    def test_voice_has_test_label(self):
        """kokoro 音色应包含 [测试版] 标识"""
        from tts.kokoro_engine import KokoroEngine
        engine = KokoroEngine()
        voices = engine.list_voices()
        for v in voices:
            assert v.get("label") == "[测试版]"

    def test_synthesize_import_error(self):
        from tts.kokoro_engine import KokoroEngine
        engine = KokoroEngine()

        with patch.dict("sys.modules", {"kokoro": None}):
            with pytest.raises(ImportError, match="kokoro 未安装"):
                asyncio.get_event_loop().run_until_complete(
                    engine.synthesize("test", "sweet_female")
                )

    def test_synthesize_empty_audio(self):
        from tts.kokoro_engine import KokoroEngine
        engine = KokoroEngine()

        # 模拟 pipeline 返回空结果
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = []

        # 直接设置 _pipeline 跳过 _ensure_loaded
        engine._pipeline = mock_pipeline

        # mock soundfile 避免 numpy 加载问题
        mock_sf = MagicMock()
        with patch.dict("sys.modules", {"soundfile": mock_sf}):
            result = asyncio.get_event_loop().run_until_complete(
                engine.synthesize("test", "sweet_female")
            )
            assert result is None


# ============================================================
# TTSRouter 测试
# ============================================================

class TestTTSRouter:
    """测试 TTS 路由"""

    def test_router_synthesize_edge(self):
        from tts.router import TTSRouter
        router = TTSRouter()

        mock_engine = MagicMock()
        mock_engine.synthesize = AsyncMock(return_value=b"audio_data")

        with patch("tts.router.create_engine", return_value=mock_engine):
            result = asyncio.get_event_loop().run_until_complete(
                router.synthesize("hello", "sweet_female", {})
            )
            assert result == b"audio_data"
            mock_engine.synthesize.assert_called_once()

    def test_router_fallback_on_unknown_provider(self):
        from tts.router import TTSRouter
        router = TTSRouter()

        with patch("tts.router.create_engine", return_value=None):
            result = asyncio.get_event_loop().run_until_complete(
                router.synthesize("hello", "sweet_female", {})
            )
            assert result is None

    def test_router_custom_voice(self):
        from tts.router import TTSRouter
        router = TTSRouter()

        mock_engine = MagicMock()
        mock_engine.synthesize = AsyncMock(return_value=b"custom_audio")

        router.register_custom_voice("my_voice", {
            "provider": "edge",
            "voice_id": "custom_id",
            "speed": 1.2,
            "pitch": 1.0,
        })

        with patch("tts.router.create_engine", return_value=mock_engine):
            result = asyncio.get_event_loop().run_until_complete(
                router.synthesize("hello", "my_voice", {})
            )
            assert result == b"custom_audio"
            call_kwargs = mock_engine.synthesize.call_args
            assert call_kwargs.args[2] == 1.2

    def test_router_settings_override(self):
        from tts.router import TTSRouter
        router = TTSRouter()

        mock_engine = MagicMock()
        mock_engine.synthesize = AsyncMock(return_value=b"audio")

        with patch("tts.router.create_engine", return_value=mock_engine):
            asyncio.get_event_loop().run_until_complete(
                router.synthesize("hello", "sweet_female", {
                    "voice.speed": 2.0,
                    "voice.pitch": 0.5,
                })
            )
            call_args = mock_engine.synthesize.call_args
            assert call_args.args[2] == 2.0
            assert call_args.args[3] == 0.5

    def test_router_exception_returns_none(self):
        from tts.router import TTSRouter
        router = TTSRouter()

        mock_engine = MagicMock()
        mock_engine.synthesize = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("tts.router.create_engine", return_value=mock_engine):
            result = asyncio.get_event_loop().run_until_complete(
                router.synthesize("hello", "sweet_female", {})
            )
            assert result is None

    def test_get_available_engines(self):
        from tts.router import TTSRouter
        router = TTSRouter()
        engines = router.get_available_engines()
        assert "edge" in engines
        assert "xiaomi" in engines
        assert "kokoro" in engines
