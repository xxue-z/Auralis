"""TTS 工厂 — 根据 provider 名称创建引擎实例"""

import logging
from typing import Optional

from .base import TTSEngine

logger = logging.getLogger("auralis.tts")

# 引擎注册表：provider 名 → 引擎类路径（懒导入，避免未安装的依赖报错）
_ENGINE_REGISTRY: dict[str, str] = {
    "edge":   ".edge_engine.EdgeTTSEngine",
    "openai": ".openai_engine.OpenAITTSEngine",
    "xiaomi": ".xiaomi_engine.XiaomiTTSEngine",
    "kokoro": ".kokoro_engine.KokoroEngine",       # 本地推理（测试版）
}

# 引擎实例缓存（单例）
_engine_cache: dict[str, TTSEngine] = {}


def _import_engine(import_path: str) -> type[TTSEngine]:
    """动态导入引擎类"""
    import importlib
    module_path, class_name = import_path.rsplit(".", 1)
    if module_path.startswith("."):
        import tts as tts_pkg
        module = importlib.import_module(module_path, tts_pkg.__package__)
    else:
        module = importlib.import_module(module_path)
    return getattr(module, class_name)


def create_engine(provider: str) -> Optional[TTSEngine]:
    """
    根据 provider 名称创建 TTS 引擎（单例）

    Args:
        provider: 引擎标识（edge / openai / xiaomi / kokoro）

    Returns:
        TTSEngine 实例，未知 provider 返回 None
    """
    if provider in _engine_cache:
        return _engine_cache[provider]

    import_path = _ENGINE_REGISTRY.get(provider)
    if not import_path:
        logger.error(f"未知 TTS 引擎: {provider}，可用: {list(_ENGINE_REGISTRY.keys())}")
        return None

    try:
        engine_cls = _import_engine(import_path)
        engine = engine_cls()
        _engine_cache[provider] = engine
        logger.info(f"TTS 引擎已创建: {provider} ({engine_cls.__name__})")
        return engine
    except ImportError as e:
        logger.error(f"TTS 引擎 {provider} 依赖缺失: {e}")
        return None
    except Exception as e:
        logger.error(f"TTS 引擎 {provider} 初始化失败: {e}")
        return None


def register_engine(provider: str, engine_class_path: str):
    """注册新的 TTS 引擎（插件化扩展）"""
    _ENGINE_REGISTRY[provider] = engine_class_path
    logger.info(f"TTS 引擎已注册: {provider}")


def list_engines() -> list[str]:
    """列出所有可用引擎"""
    return list(_ENGINE_REGISTRY.keys())
