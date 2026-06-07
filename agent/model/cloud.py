"""云端 LLM 接口 — 支持 OpenAI 和 Anthropic 协议"""

import logging
from typing import AsyncIterator

logger = logging.getLogger("auralis.model.cloud")


class CloudLLM:
    """云端 LLM 调用封装"""

    async def chat(
        self,
        messages: list[dict],
        config: dict,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        调用云端 LLM

        Args:
            messages: [{"role": "user"/"assistant"/"system", "content": "..."}]
            config: {
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-...",
                "model_id": "gpt-4o",
                "api_protocol": "openai" / "anthropic",
            }
            stream: 是否流式返回

        Returns:
            完整回复文本，或流式返回的 AsyncIterator
        """
        protocol = config.get("api_protocol", "openai")

        if protocol == "anthropic":
            return await self._call_anthropic(messages, config, stream)
        else:
            return await self._call_openai(messages, config, stream)

    async def _call_openai(
        self, messages: list[dict], config: dict, stream: bool
    ) -> str | AsyncIterator[str]:
        """OpenAI 兼容协议调用（也适用于 Ollama、DeepSeek 等）"""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError("请安装 openai: pip install openai")

        client = AsyncOpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
        )

        if stream:
            return self._stream_openai(client, messages, config)

        response = await client.chat.completions.create(
            model=config["model_id"],
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def _stream_openai(
        self, client, messages: list[dict], config: dict
    ) -> AsyncIterator[str]:
        """OpenAI 流式返回"""
        response = await client.chat.completions.create(
            model=config["model_id"],
            messages=messages,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def _call_anthropic(
        self, messages: list[dict], config: dict, stream: bool
    ) -> str | AsyncIterator[str]:
        """Anthropic 协议调用"""
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise RuntimeError("请安装 anthropic: pip install anthropic")

        client = AsyncAnthropic(
            base_url=config["base_url"],
            api_key=config["api_key"],
        )

        # Anthropic 的 system 消息是单独参数
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        if stream:
            return self._stream_anthropic(client, system_msg, chat_messages, config)

        response = await client.messages.create(
            model=config["model_id"],
            system=system_msg,
            messages=chat_messages,
            max_tokens=4096,
        )
        return response.content[0].text

    async def _stream_anthropic(
        self, client, system: str, messages: list[dict], config: dict
    ) -> AsyncIterator[str]:
        """Anthropic 流式返回"""
        async with client.messages.stream(
            model=config["model_id"],
            system=system,
            messages=messages,
            max_tokens=4096,
        ) as stream:
            async for text in stream.text_stream:
                yield text
