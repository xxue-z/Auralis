"""MCP 协议层单元测试"""

import pytest
from mcp.schema import MCPCapability, MCPRequest, MCPResponse
from mcp.router import MCPRouter
from mcp.validator import MCPValidator


# ============================================================
# MCPCapability 测试
# ============================================================

class TestMCPCapability:

    def test_creation(self):
        """创建能力"""
        cap = MCPCapability(namespace="file", action="delete")
        assert cap.namespace == "file"
        assert cap.action == "delete"
        assert cap.full_name == "file.delete"

    def test_from_dict(self):
        """从字典创建"""
        cap = MCPCapability.from_dict({"namespace": "app", "action": "launch"})
        assert cap.full_name == "app.launch"

    def test_from_string(self):
        """从字符串解析"""
        cap = MCPCapability.from_string("system.info")
        assert cap.namespace == "system"
        assert cap.action == "info"

    def test_from_string_invalid(self):
        """无效字符串报错"""
        with pytest.raises(ValueError):
            MCPCapability.from_string("invalid")

    def test_to_dict(self):
        """序列化"""
        cap = MCPCapability(namespace="file", action="read")
        d = cap.to_dict()
        assert d == {"namespace": "file", "action": "read"}


# ============================================================
# MCPRequest 测试
# ============================================================

class TestMCPRequest:

    def test_creation(self):
        """创建请求"""
        req = MCPRequest(
            id="test_001",
            capability=MCPCapability("file", "delete"),
            input={"path": "/tmp/test"},
            context={"os": "windows"},
        )
        assert req.id == "test_001"
        assert req.capability.full_name == "file.delete"
        assert req.version == "1.0"

    def test_create便捷方法(self):
        """便捷创建"""
        req = MCPRequest.create("app", "launch", {"app_id": "chrome"})
        assert req.id.startswith("mcp_")
        assert req.capability.full_name == "app.launch"

    def test_to_dict(self):
        """序列化"""
        req = MCPRequest.create("file", "list", {"path": "/tmp"})
        d = req.to_dict()
        assert d["id"] == req.id
        assert d["capability"]["namespace"] == "file"
        assert d["input"]["path"] == "/tmp"

    def test_from_dict(self):
        """从字典反序列化"""
        data = {
            "id": "test",
            "capability": {"namespace": "file", "action": "read"},
            "input": {"path": "/tmp"},
            "context": {},
        }
        req = MCPRequest.from_dict(data)
        assert req.id == "test"
        assert req.capability.full_name == "file.read"


# ============================================================
# MCPResponse 测试
# ============================================================

class TestMCPResponse:

    def test_success(self):
        """成功响应"""
        resp = MCPResponse.success("req_001", {"result": "ok"})
        assert resp.status == "success"
        assert resp.data["result"] == "ok"

    def test_error(self):
        """错误响应"""
        resp = MCPResponse.make_error("req_001", "NOT_FOUND", "文件不存在")
        assert resp.status == "error"
        assert resp.error["code"] == "NOT_FOUND"

    def test_blocked(self):
        """阻止响应"""
        resp = MCPResponse.blocked("req_001", "高风险操作")
        assert resp.status == "blocked"

    def test_pending_confirm(self):
        """待确认响应"""
        resp = MCPResponse.pending_confirm("req_001", "确定删除？", "high")
        assert resp.status == "pending_confirm"
        assert resp.confirm_required["riskLevel"] == "high"

    def test_to_dict(self):
        """序列化"""
        resp = MCPResponse.success("r1", {"data": 123})
        d = resp.to_dict()
        assert d["status"] == "success"
        assert d["data"]["data"] == 123


# ============================================================
# MCPRouter 测试
# ============================================================

class TestMCPRouter:

    @pytest.fixture
    def router(self):
        return MCPRouter()

    async def _mock_executor(self, request):
        return MCPResponse.success(request.id, {})

    def test_register_plugin(self, router):
        """注册插件"""
        router.register_plugin("file.mcp", ["file.read", "file.delete"], self._mock_executor)
        assert router.has_capability("file.read")
        assert router.has_capability("file.delete")

    def test_unregister_plugin(self, router):
        """注销插件"""
        router.register_plugin("file.mcp", ["file.read"], self._mock_executor)
        assert router.unregister_plugin("file.mcp")
        assert not router.has_capability("file.read")
        assert not router.unregister_plugin("nonexistent")

    def test_route(self, router):
        """路由到正确插件"""
        router.register_plugin("file.mcp", ["file.read", "file.delete"], self._mock_executor)
        router.register_plugin("app.mcp", ["app.launch"], self._mock_executor)

        plugin = router.route(MCPCapability("file", "delete"))
        assert plugin.name == "file.mcp"

        plugin = router.route(MCPCapability("app", "launch"))
        assert plugin.name == "app.mcp"

    def test_route_unknown(self, router):
        """未知能力报错"""
        with pytest.raises(KeyError):
            router.route(MCPCapability("unknown", "action"))

    def test_list_plugins(self, router):
        """列出插件"""
        router.register_plugin("file.mcp", ["file.read"], self._mock_executor)
        plugins = router.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "file.mcp"

    def test_list_capabilities(self, router):
        """列出能力"""
        router.register_plugin("file.mcp", ["file.read", "file.delete"], self._mock_executor)
        caps = router.list_capabilities()
        assert caps["file.read"] == "file.mcp"
        assert caps["file.delete"] == "file.mcp"

    def test_capability_override(self, router):
        """能力覆盖"""
        async def executor1(req):
            return MCPResponse.success(req.id, {"plugin": "old"})

        async def executor2(req):
            return MCPResponse.success(req.id, {"plugin": "new"})

        router.register_plugin("old.mcp", ["file.read"], executor1)
        router.register_plugin("new.mcp", ["file.read"], executor2)

        plugin = router.route(MCPCapability("file", "read"))
        assert plugin.name == "new.mcp"


# ============================================================
# MCPValidator 测试
# ============================================================

class TestMCPValidator:

    @pytest.fixture
    def validator(self):
        return MCPValidator()

    def test_valid_request(self, validator):
        """有效请求通过"""
        req = MCPRequest.create("file", "delete", {"path": "/tmp"})
        errors = validator.validate(req)
        assert errors == []

    def test_missing_id(self, validator):
        """缺失 ID"""
        req = MCPRequest(id="", capability=MCPCapability("file", "read"), input={}, context={})
        errors = validator.validate(req)
        assert any("ID" in e for e in errors)

    def test_invalid_version(self, validator):
        """无效版本"""
        req = MCPRequest(id="t", capability=MCPCapability("file", "read"), input={}, context={}, version="2.0")
        errors = validator.validate(req)
        assert any("版本" in e for e in errors)

    def test_invalid_namespace(self, validator):
        """无效命名空间"""
        req = MCPRequest.create("unknown", "action", {})
        errors = validator.validate(req)
        assert any("命名空间" in e for e in errors)

    def test_invalid_action(self, validator):
        """无效动作"""
        req = MCPRequest.create("file", "nonexistent", {})
        errors = validator.validate(req)
        assert any("动作" in e for e in errors)

    def test_all_namespaces_valid(self, validator):
        """所有命名空间有效"""
        test_actions = {
            "file": "read",
            "app": "launch",
            "system": "info",
            "ui": "click",
        }
        for ns, action in test_actions.items():
            req = MCPRequest.create(ns, action, {})
            errors = validator.validate(req)
            assert errors == [], f"命名空间 '{ns}' 应该有效"

    def test_validate_capability_string(self, validator):
        """校验能力字符串"""
        errors = validator.validate_capability_string("file.delete")
        assert errors == []

        errors = validator.validate_capability_string("invalid")
        assert len(errors) > 0

    def test_input_not_dict(self, validator):
        """输入不是字典"""
        req = MCPRequest(id="t", capability=MCPCapability("file", "read"), input="bad", context={})
        errors = validator.validate(req)
        assert any("输入" in e for e in errors)
