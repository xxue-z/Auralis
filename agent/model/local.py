"""本地模型接口 — Ollama 连接管理、模型列表、健康检查"""

import json
import logging

import httpx

logger = logging.getLogger("auralis.model.local")

DEFAULT_OLLAMA_URL = "http://localhost:11434"


class LocalLLM:
    """Ollama 本地模型管理器"""

    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL, timeout: int = 120):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def api_url(self) -> str:
        """Ollama API 基础 URL"""
        return self._base_url

    @property
    def openai_compatible_url(self) -> str:
        """OpenAI 兼容端点 URL（供 router 使用）"""
        return f"{self._base_url}/v1"

    async def check_connection(self) -> dict:
        """
        检查 Ollama 连接状态

        Returns:
            {"connected": bool, "models": list, "error": str|None}
        """
        try:
            models = await self.list_models()
            return {
                "connected": True,
                "models": [m.get("name", "") for m in models],
                "error": None,
            }
        except httpx.ConnectError:
            return {
                "connected": False,
                "models": [],
                "error": "无法连接到 Ollama，请确认 Ollama 已启动",
            }
        except Exception as e:
            return {
                "connected": False,
                "models": [],
                "error": f"Ollama 连接异常: {type(e).__name__}: {e}",
            }

    async def list_models(self) -> list[dict]:
        """
        获取已安装的模型列表

        Returns:
            [{"name": str, "size": int, "modified": str, "digest": str}]
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return data.get("models", [])

    async def pull_model(self, model_name: str) -> dict:
        """
        拉取模型（流式返回进度）

        Args:
            model_name: 模型名称（如 'qwen2.5:1.5b'）

        Returns:
            {"success": bool, "status": str, "error": str|None}
        """
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/pull",
                    json={"name": model_name},
                ) as resp:
                    resp.raise_for_status()
                    last_status = ""
                    async for line in resp.aiter_lines():
                        if line:
                            try:
                                progress = json.loads(line)
                                last_status = progress.get("status", "")
                            except json.JSONDecodeError:
                                pass
                    return {"success": True, "status": last_status, "error": None}
        except httpx.ConnectError:
            return {"success": False, "status": "", "error": "无法连接到 Ollama"}
        except Exception as e:
            return {"success": False, "status": "", "error": str(e)}

    async def get_model_info(self, model_name: str) -> dict | None:
        """
        获取模型详情

        Args:
            model_name: 模型名称

        Returns:
            模型详情字典，或 None
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/show",
                    json={"name": model_name},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"获取模型信息失败: {e}")
            return None

    async def delete_model(self, model_name: str) -> dict:
        """
        删除模型

        Returns:
            {"success": bool, "error": str|None}
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.delete(
                    f"{self._base_url}/api/delete",
                    json={"name": model_name},
                )
                resp.raise_for_status()
                return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_openai_config(self, settings: dict) -> dict:
        """
        生成 OpenAI 兼容配置（供 router/cloud.py 使用）

        Args:
            settings: 应用设置字典

        Returns:
            OpenAI 兼容的 config 字典
        """
        return {
            "base_url": settings.get("model.local.base_url", self.openai_compatible_url),
            "api_key": "ollama",
            "model_id": settings.get("model.local.model_id", "qwen2.5:1.5b"),
            "api_protocol": "openai",
            "timeout": settings.get("model.timeout", 120),
        }
