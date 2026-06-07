"""云端 LLM 接口 — 支持 OpenAI 和 Anthropic 协议"""

import json
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
        tools: list[dict] | None = None,
    ) -> str | dict:
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
            tools: Function Calling 工具定义列表

        Returns:
            如果有 tool_calls，返回 {"content": str|None, "tool_calls": list}
            否则返回回复文本 str
        """
        protocol = config.get("api_protocol", "openai")

        if protocol == "anthropic":
            return await self._call_anthropic(messages, config, stream, tools)
        else:
            return await self._call_openai(messages, config, stream, tools)

    async def _call_openai(
        self, messages: list[dict], config: dict, stream: bool,
        tools: list[dict] | None = None,
    ) -> str | dict:
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

        kwargs = {
            "model": config["model_id"],
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.chat.completions.create(**kwargs)

        # 检查是否有 tool_calls
        choice = response.choices[0]
        if choice.message.tool_calls:
            return {
                "content": choice.message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in choice.message.tool_calls
                ],
            }

        return choice.message.content or ""

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
        self, messages: list[dict], config: dict, stream: bool,
        tools: list[dict] | None = None,
    ) -> str | dict:
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

        kwargs = {
            "model": config["model_id"],
            "system": system_msg,
            "messages": chat_messages,
            "max_tokens": 4096,
        }
        if tools:
            # Anthropic tools 格式转换
            anthropic_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    anthropic_tools.append({
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                        "input_schema": tool["function"]["parameters"],
                    })
            kwargs["tools"] = anthropic_tools

        response = await client.messages.create(**kwargs)

        # 检查是否有 tool_use
        tool_calls = []
        content_text = ""
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": json.dumps(block.input) if isinstance(block.input, dict) else block.input,
                })
            elif block.type == "text":
                content_text += block.text

        if tool_calls:
            return {"content": content_text or None, "tool_calls": tool_calls}

        return content_text

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
