"""MCP Schema 定义 — Request/Response 数据类"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPCapability:
    """能力引用"""
    namespace: str    # "file" | "app" | "system"
    action: str       # "read" | "delete" | "launch" | ...

    @property
    def full_name(self) -> str:
        """完整能力名（如 'file.delete'）"""
        return f"{self.namespace}.{self.action}"

    def to_dict(self) -> dict:
        return {"namespace": self.namespace, "action": self.action}

    @classmethod
    def from_dict(cls, data: dict) -> "MCPCapability":
        return cls(namespace=data["namespace"], action=data["action"])

    @classmethod
    def from_string(cls, full_name: str) -> "MCPCapability":
        """从 'file.delete' 格式解析"""
        parts = full_name.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"无效的能力名: {full_name}（应为 'namespace.action' 格式）")
        return cls(namespace=parts[0], action=parts[1])


@dataclass
class MCPRequest:
    """MCP 请求"""
    id: str
    capability: MCPCapability
    input: dict[str, Any]
    context: dict[str, Any]
    constraints: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    version: str = "1.0"

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "version": self.version,
            "capability": self.capability.to_dict(),
            "input": self.input,
            "context": self.context,
        }
        if self.constraints:
            result["constraints"] = self.constraints
        if self.policy:
            result["policy"] = self.policy
        if self.execution:
            result["execution"] = self.execution
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "MCPRequest":
        return cls(
            id=data["id"],
            capability=MCPCapability.from_dict(data["capability"]),
            input=data.get("input", {}),
            context=data.get("context", {}),
            constraints=data.get("constraints"),
            policy=data.get("policy"),
            execution=data.get("execution"),
            version=data.get("version", "1.0"),
        )

    @classmethod
    def create(
        cls,
        namespace: str,
        action: str,
        input_data: dict[str, Any],
        context: dict[str, Any] | None = None,
        **kwargs,
    ) -> "MCPRequest":
        """便捷创建方法"""
        return cls(
            id=f"mcp_{uuid.uuid4().hex[:12]}",
            capability=MCPCapability(namespace=namespace, action=action),
            input=input_data,
            context=context or {},
            **kwargs,
        )


@dataclass
class MCPResponse:
    """MCP 响应"""
    id: str
    status: str  # "success" | "error" | "blocked" | "pending_confirm"
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    confirm_required: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        result = {"id": self.id, "status": self.status}
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.confirm_required:
            result["confirmRequired"] = self.confirm_required
        if self.audit:
            result["audit"] = self.audit
        return result

    @classmethod
    def success(cls, request_id: str, data: dict[str, Any]) -> "MCPResponse":
        return cls(id=request_id, status="success", data=data)

    @classmethod
    def error(cls, request_id: str, code: str, message: str) -> "MCPResponse":
        return cls(id=request_id, status="error", error={"code": code, "message": message})

    @classmethod
    def blocked(cls, request_id: str, reason: str) -> "MCPResponse":
        return cls(id=request_id, status="blocked", error={"code": "blocked", "message": reason})

    @classmethod
    def pending_confirm(cls, request_id: str, message: str, risk_level: str) -> "MCPResponse":
        return cls(
            id=request_id,
            status="pending_confirm",
            confirm_required={"message": message, "riskLevel": risk_level},
        )
