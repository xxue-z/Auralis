"""本地模型单元测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from model.local import LocalLLM


class TestLocalLLM:

    @pytest.fixture
    def llm(self):
        return LocalLLM("http://localhost:11434")

    def test_api_url(self, llm):
        """API URL 正确"""
        assert llm.api_url == "http://localhost:11434"

    def test_openai_compatible_url(self, llm):
        """OpenAI 兼容 URL 正确"""
        assert llm.openai_compatible_url == "http://localhost:11434/v1"

    def test_trailing_slash_stripped(self):
        """尾部斜杠被去除"""
        llm = LocalLLM("http://localhost:11434/")
        assert llm.api_url == "http://localhost:11434"

    def test_get_openai_config(self, llm):
        """OpenAI 配置生成"""
        settings = {"model.local.base_url": "http://custom:8080/v1", "model.local.model_id": "llama3"}
        config = llm.get_openai_config(settings)
        assert config["base_url"] == "http://custom:8080/v1"
        assert config["model_id"] == "llama3"
        assert config["api_key"] == "ollama"
        assert config["api_protocol"] == "openai"

    def test_get_openai_config_defaults(self, llm):
        """默认配置"""
        config = llm.get_openai_config({})
        assert config["base_url"] == "http://localhost:11434/v1"
        assert config["model_id"] == "qwen2.5:1.5b"

    @pytest.mark.asyncio
    async def test_check_connection_success(self, llm):
        """连接成功"""
        mock_models = [{"name": "qwen2.5:1.5b", "size": 1000000}]
        with patch.object(llm, "list_models", new_callable=AsyncMock, return_value=mock_models):
            result = await llm.check_connection()
            assert result["connected"] is True
            assert "qwen2.5:1.5b" in result["models"]

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, llm):
        """连接失败"""
        import httpx
        with patch.object(llm, "list_models", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
            result = await llm.check_connection()
            assert result["connected"] is False
            assert "Ollama" in result["error"]

    @pytest.mark.asyncio
    async def test_list_models(self, llm):
        """获取模型列表"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"models": [{"name": "qwen2.5:1.5b"}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            models = await llm.list_models()
            assert len(models) == 1
            assert models[0]["name"] == "qwen2.5:1.5b"

    @pytest.mark.asyncio
    async def test_delete_model(self, llm):
        """删除模型"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.delete = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await llm.delete_model("test_model")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_model_failure(self, llm):
        """删除模型失败"""
        import httpx
        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.delete = AsyncMock(side_effect=httpx.ConnectError("refused"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await llm.delete_model("test_model")
            assert result["success"] is False
