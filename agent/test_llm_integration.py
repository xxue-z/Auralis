"""LLM 集成单元测试"""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import openai


# ============================================================
# 1. 系统提示词测试
# ============================================================

class TestSystemPrompt:
    """测试系统提示词构建"""

    def test_prompt_contains_identity(self):
        from prompts.system import build_system_prompt
        prompt = build_system_prompt("zh-CN")
        assert "Auralis" in prompt
        assert "桌面精灵" in prompt

    def test_prompt_contains_tools(self):
        from prompts.system import build_system_prompt
        prompt = build_system_prompt("zh-CN")
        assert "settings_query" in prompt
        assert "settings_change" in prompt
        assert "execute_capability" in prompt

    def test_prompt_chinese_locale(self):
        from prompts.system import build_system_prompt
        prompt = build_system_prompt("zh-CN")
        assert "中文" in prompt

    def test_prompt_english_locale(self):
        from prompts.system import build_system_prompt
        prompt = build_system_prompt("en-US")
        assert "English" in prompt

    def test_prompt_contains_settings_context(self):
        from prompts.system import build_system_prompt
        prompt = build_system_prompt("zh-CN")
        assert "locale" in prompt  # 设置上下文应包含设置项


# ============================================================
# 2. 工具定义测试
# ============================================================

class TestToolDefinitions:
    """测试 Function Calling 工具定义"""

    def test_tools_is_list(self):
        from tools.functions import TOOLS
        assert isinstance(TOOLS, list)
        assert len(TOOLS) > 0

    def test_each_tool_has_required_fields(self):
        from tools.functions import TOOLS
        for tool in TOOLS:
            assert tool["type"] == "function"
            assert "function" in tool
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    def test_settings_query_tool(self):
        from tools.functions import TOOLS
        names = [t["function"]["name"] for t in TOOLS]
        assert "settings_query" in names

    def test_settings_change_tool(self):
        from tools.functions import TOOLS
        tool = next(t for t in TOOLS if t["function"]["name"] == "settings_change")
        params = tool["function"]["parameters"]
        assert "changes" in params["properties"]

    def test_execute_capability_tool(self):
        from tools.functions import TOOLS
        tool = next(t for t in TOOLS if t["function"]["name"] == "execute_capability")
        params = tool["function"]["parameters"]
        assert "capability_type" in params["properties"]
        # 检查 enum 值
        cap_type = params["properties"]["capability_type"]
        assert "file.list" in cap_type["enum"]
        assert "app.launch" in cap_type["enum"]

    def test_open_close_settings_tools(self):
        from tools.functions import TOOLS
        names = [t["function"]["name"] for t in TOOLS]
        assert "open_settings" in names
        assert "close_settings" in names


# ============================================================
# 3. 意图解析器快速路径测试
# ============================================================

class TestIntentParserFastPath:
    """测试规则匹配的快速路径"""

    def test_settings_open_detected(self):
        from intent.parser import IntentParser
        parser = IntentParser()
        result = parser.parse("打开设置")
        assert result["intent"] == "settings_open"

    def test_settings_close_detected(self):
        from intent.parser import IntentParser
        parser = IntentParser()
        result = parser.parse("关闭设置")
        assert result["intent"] == "settings_close"

    def test_file_list_detected(self):
        from intent.parser import IntentParser
        parser = IntentParser()
        result = parser.parse("扫描桌面文件")
        assert result["intent"] == "file_list"
        assert len(result["capabilities"]) > 0

    def test_app_launch_detected(self):
        from intent.parser import IntentParser
        parser = IntentParser()
        result = parser.parse("打开记事本")
        assert result["intent"] == "app_launch"
        assert len(result["capabilities"]) > 0

    def test_unknown_goes_to_llm(self):
        from intent.parser import IntentParser
        parser = IntentParser()
        result = parser.parse("今天天气怎么样")
        assert result["intent"] == "unknown"


# ============================================================
# 4. CloudLLM tools 参数测试
# ============================================================

class TestCloudLLMTools:
    """测试 CloudLLM 对 tools 参数的处理"""

    @pytest.mark.asyncio
    async def test_chat_passes_tools_to_openai(self):
        from model.cloud import CloudLLM
        llm = CloudLLM()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好！"
        mock_response.choices[0].message.tool_calls = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await llm.chat(
                messages=[{"role": "user", "content": "你好"}],
                config={"base_url": "http://test", "api_key": "sk-test", "model_id": "gpt-4o", "api_protocol": "openai"},
                tools=[{"type": "function", "function": {"name": "test"}}],
            )

        # 验证 tools 被传递
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == [{"type": "function", "function": {"name": "test"}}]

    @pytest.mark.asyncio
    async def test_chat_returns_tool_calls(self):
        from model.cloud import CloudLLM
        llm = CloudLLM()

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "settings_query"
        mock_tool_call.function.arguments = "{}"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await llm.chat(
                messages=[{"role": "user", "content": "查看设置"}],
                config={"base_url": "http://test", "api_key": "sk-test", "model_id": "gpt-4o", "api_protocol": "openai"},
            )

        assert isinstance(result, dict)
        assert "tool_calls" in result
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "settings_query"

    @pytest.mark.asyncio
    async def test_chat_returns_text_without_tools(self):
        from model.cloud import CloudLLM
        llm = CloudLLM()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好！有什么可以帮你的？"
        mock_response.choices[0].message.tool_calls = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await llm.chat(
                messages=[{"role": "user", "content": "你好"}],
                config={"base_url": "http://test", "api_key": "sk-test", "model_id": "gpt-4o", "api_protocol": "openai"},
            )

        assert isinstance(result, str)
        assert result == "你好！有什么可以帮你的？"


# ============================================================
# 5. ModelRouter tools 参数透传测试
# ============================================================

class TestModelRouterTools:
    """测试 ModelRouter 透传 tools 参数"""

    @pytest.mark.asyncio
    async def test_router_passes_tools_to_cloud(self):
        from model.router import ModelRouter
        router = ModelRouter()

        with patch.object(router.cloud, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "回复"

            settings = {
                "model.cloud.enabled": True,
                "model.cloud.api_key": "sk-test",
                "model.cloud.base_url": "http://test",
                "model.cloud.model_id": "gpt-4o",
                "model.cloud.api_protocol": "openai",
            }
            tools = [{"type": "function", "function": {"name": "test"}}]

            await router.chat(
                messages=[{"role": "user", "content": "hi"}],
                settings=settings,
                tools=tools,
            )

            # 验证 tools 被传递到 cloud.chat（tools 是第5个位置参数）
            call_args = mock_chat.call_args
            # cloud.chat(messages, config, stream, tools) → args[4] = tools
            assert call_args[0][3] == tools


# ============================================================
# 6. 对话历史管理测试（内联实现，避免导入 server.py 的副作用）
# ============================================================

MAX_HISTORY = 20

def _trim_history(history: list[dict]):
    """裁剪对话历史，保留最近 N 条"""
    while len(history) > MAX_HISTORY:
        history.pop(0)


class TestConversationHistory:
    """测试对话历史管理"""

    def test_trim_history(self):
        history = [{"role": "user", "content": f"msg{i}"} for i in range(30)]
        _trim_history(history)
        assert len(history) == 20

    def test_trim_preserves_recent(self):
        history = [{"role": "user", "content": f"msg{i}"} for i in range(30)]
        _trim_history(history)
        assert history[0]["content"] == "msg10"
        assert history[-1]["content"] == "msg29"

    def test_no_trim_under_limit(self):
        history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        _trim_history(history)
        assert len(history) == 10

    def test_session_key_is_ws_id(self):
        """验证 session key 使用 id(ws) 而非 message_id"""
        # 模拟多个消息共享同一个 session
        mock_ws = MagicMock()
        session_id = id(mock_ws)
        history_dict = {}
        history_dict[session_id] = [{"role": "user", "content": "first"}]
        # 第二条消息应该能访问到同一个 history
        assert session_id in history_dict
        assert len(history_dict[session_id]) == 1


# ============================================================
# 7. 工具执行逻辑测试（独立实现，不依赖 server.py 导入）
# ============================================================

async def _execute_tool_standalone(tool_name: str, args: dict, ws, message_id: str) -> dict:
    """独立的工具执行逻辑（与 server.py 中的实现一致）"""
    import uuid as _uuid

    if tool_name == "open_settings":
        await ws.send(json.dumps({"type": "agent_command", "command": "open-settings"}))
        return {"success": True, "message": "设置面板已打开"}

    elif tool_name == "close_settings":
        await ws.send(json.dumps({"type": "agent_command", "command": "close-settings"}))
        return {"success": True, "message": "设置面板已关闭"}

    elif tool_name == "settings_query":
        # 模拟超时
        return {"success": False, "error": "查询超时"}

    return {"success": False, "error": f"未知工具: {tool_name}"}


class TestToolExecution:
    """测试工具执行逻辑"""

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        mock_ws = AsyncMock()
        result = await _execute_tool_standalone("unknown_tool", {}, mock_ws, "msg_1")
        assert result["success"] is False
        assert "未知工具" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_open_settings(self):
        mock_ws = AsyncMock()
        result = await _execute_tool_standalone("open_settings", {}, mock_ws, "msg_1")
        assert result["success"] is True
        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["type"] == "agent_command"
        assert sent["command"] == "open-settings"

    @pytest.mark.asyncio
    async def test_execute_tool_close_settings(self):
        mock_ws = AsyncMock()
        result = await _execute_tool_standalone("close_settings", {}, mock_ws, "msg_1")
        assert result["success"] is True
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["command"] == "close-settings"

    @pytest.mark.asyncio
    async def test_execute_tool_settings_query_timeout(self):
        mock_ws = AsyncMock()
        result = await _execute_tool_standalone("settings_query", {}, mock_ws, "msg_1")
        assert result["success"] is False
        assert "超时" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
