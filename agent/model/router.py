"""模型路由 — 云端/Ollama 自动切换"""

import logging
from typing import AsyncIterator
from model.cloud import CloudLLM

logger = logging.getLogger("auralis.model.router")


class ModelRouter:
    """模型路由：根据配置选择云端或本地模型，支持自动切换"""

    def __init__(self):
        self.cloud = CloudLLM()

    async def chat(
        self,
        messages: list[dict],
        settings: dict,
        stream: bool = False,
        tools: list[dict] | None = None,
    ) -> str | dict:
        """
        路由到合适的模型并调用

        Args:
            messages: 对话消息
            settings: 完整设置字典（从 settingsStore 读取）
            stream: 是否流式
            tools: Function Calling 工具定义

        Returns:
            str 或 {"content": str, "tool_calls": list}
        """
        cloud_enabled = settings.get("model.cloud.enabled", True)
        local_enabled = settings.get("model.local.enabled", False)
        auto_switch = settings.get("model.auto_switch", True)

        # 优先云端
        if cloud_enabled:
            try:
                return await self._call_cloud(messages, settings, stream, tools)
            except Exception as e:
                logger.warning(f"云端调用失败: {e}")
                if auto_switch and local_enabled:
                    logger.info("自动切换到本地模型")
                    return await self._call_local(messages, settings, stream, tools)
                raise

        # 仅本地
        if local_enabled:
            return await self._call_local(messages, settings, stream, tools)

        raise RuntimeError("没有可用的模型，请在设置中配置云端或本地模型")

    async def _call_cloud(
        self, messages: list[dict], settings: dict, stream: bool,
        tools: list[dict] | None = None,
    ) -> str | dict:
        """调用云端模型"""
        config = {
            "base_url": settings.get("model.cloud.base_url", "https://api.openai.com/v1"),
            "api_key": settings.get("model.cloud.api_key", ""),
            "model_id": settings.get("model.cloud.model_id", "gpt-4o"),
            "api_protocol": settings.get("model.cloud.api_protocol", "openai"),
        }

        if not config["api_key"]:
            raise RuntimeError("未配置 API Key，请在设置中填写")

        return await self.cloud.chat(messages, config, stream, tools)

    async def _call_local(
        self, messages: list[dict], settings: dict, stream: bool,
        tools: list[dict] | None = None,
    ) -> str | dict:
        """调用本地 Ollama 模型"""
        config = {
            "base_url": settings.get("model.local.base_url", "http://localhost:11434/v1"),
            "api_key": "ollama",  # Ollama 不需要真实 key
            "model_id": settings.get("model.local.model_id", "qwen2.5:1.5b"),
            "api_protocol": "openai",  # Ollama 兼容 OpenAI 协议
        }

        return await self.cloud.chat(messages, config, stream, tools)

    def get_config_for_settings(self, settings: dict) -> dict:
        """获取当前模型配置（供其他模块读取）"""
        if settings.get("model.cloud.enabled", True):
            return {
                "provider": "cloud",
                "base_url": settings.get("model.cloud.base_url"),
                "model_id": settings.get("model.cloud.model_id"),
                "api_protocol": settings.get("model.cloud.api_protocol"),
            }
        elif settings.get("model.local.enabled", False):
            return {
                "provider": "local",
                "base_url": settings.get("model.local.base_url"),
                "model_id": settings.get("model.local.model_id"),
                "api_protocol": "openai",
            }
        return {"provider": "none"}
