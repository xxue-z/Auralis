"""Policy & Safety 单元测试"""

import pytest
from policy.risk_engine import RiskEngine, RiskLevel, _is_system_path
from policy.permission import PermissionChecker, PermissionResult
from policy.confirmation import ConfirmationManager, ConfirmationDecision


# ============================================================
# RiskEngine 测试
# ============================================================

class TestRiskEngine:

    @pytest.fixture
    def engine(self):
        return RiskEngine()

    def test_low_risk_operations(self, engine):
        """低风险操作"""
        for op in ["file.read", "file.list", "app.list", "system.info"]:
            level, score = engine.evaluate(op, {})
            assert level == RiskLevel.LOW
            assert score < 0.3

    def test_medium_risk_operations(self, engine):
        """中风险操作"""
        for op in ["file.write", "file.copy", "file.move", "app.close", "system.lock"]:
            level, score = engine.evaluate(op, {})
            assert level == RiskLevel.MEDIUM
            assert 0.3 <= score < 0.7

    def test_high_risk_operations(self, engine):
        """高风险操作"""
        for op in ["file.delete", "system.shutdown"]:
            level, score = engine.evaluate(op, {})
            assert level == RiskLevel.HIGH
            assert score >= 0.7

    def test_system_path_increases_risk(self, engine):
        """系统路径提高风险"""
        level_normal, score_normal = engine.evaluate("file.delete", {"path": "C:/Users/test/tmp.txt"})
        level_system, score_system = engine.evaluate("file.delete", {"path": "C:/Windows/System32/test.txt"})
        assert score_system > score_normal

    def test_recursive_delete_higher_risk(self, engine):
        """递归删除提高风险"""
        _, score_normal = engine.evaluate("file.delete", {"path": "/tmp/test"})
        _, score_recursive = engine.evaluate("file.delete", {"path": "/tmp/test", "recursive": True})
        assert score_recursive > score_normal

    def test_immediate_shutdown_higher_risk(self, engine):
        """立即关机提高风险"""
        _, score_delayed = engine.evaluate("system.shutdown", {"delay": 30})
        _, score_immediate = engine.evaluate("system.shutdown", {"delay": 0})
        assert score_immediate > score_delayed

    def test_unknown_capability_medium(self, engine):
        """未知操作默认中风险"""
        level, score = engine.evaluate("unknown.operation", {})
        assert level == RiskLevel.MEDIUM
        assert score == 0.5

    def test_risk_description(self, engine):
        """风险描述"""
        desc_low = engine.get_risk_description("file.read", 0.1)
        desc_high = engine.get_risk_description("file.delete", 0.8)
        assert "自动执行" in desc_low
        assert "确认" in desc_high


# ============================================================
# _is_system_path 测试
# ============================================================

class TestIsSystemPath:

    def test_windows_system_paths(self):
        """Windows 系统路径"""
        assert _is_system_path("C:/Windows/System32")
        assert _is_system_path("C:\\Windows\\System32")
        assert _is_system_path("C:/Program Files/Google")
        assert _is_system_path("C:/ProgramData/Microsoft")

    def test_unix_system_paths(self):
        """Unix 系统路径"""
        assert _is_system_path("/usr/bin/python")
        assert _is_system_path("/etc/passwd")
        assert _is_system_path("/system/framework")

    def test_user_paths(self):
        """用户路径不被拦截"""
        assert not _is_system_path("C:/Users/test/Desktop")
        assert not _is_system_path("D:/Project/Auralis")
        assert not _is_system_path("~/Documents")


# ============================================================
# PermissionChecker 测试
# ============================================================

class TestPermissionChecker:

    @pytest.fixture
    def checker(self):
        return PermissionChecker()

    def test_low_risk_allowed(self, checker):
        """低风险操作通过"""
        result = checker.check("file.read", {}, RiskLevel.LOW)
        assert result.allowed

    def test_medium_risk_allowed(self, checker):
        """中风险操作通过"""
        result = checker.check("file.write", {"path": "/tmp/test.txt"}, RiskLevel.MEDIUM)
        assert result.allowed

    def test_high_risk_rejected(self, checker):
        """高风险操作拒绝"""
        result = checker.check("file.delete", {}, RiskLevel.HIGH)
        assert not result.allowed
        assert "确认" in result.reason

    def test_system_path_rejected(self, checker):
        """系统路径拒绝"""
        result = checker.check("file.write", {"path": "C:/Windows/test.txt"}, RiskLevel.MEDIUM)
        assert not result.allowed
        assert "系统" in result.reason

    def test_system_path_in_from_field(self, checker):
        """from 字段系统路径拒绝"""
        result = checker.check("file.move", {"from": "C:/Windows/System32/test.txt", "to": "/tmp/"}, RiskLevel.MEDIUM)
        assert not result.allowed

    def test_permission_result_bool(self, checker):
        """PermissionResult 布尔值"""
        allowed = checker.check("file.read", {}, RiskLevel.LOW)
        denied = checker.check("file.delete", {}, RiskLevel.HIGH)
        assert bool(allowed)
        assert not bool(denied)


# ============================================================
# ConfirmationManager 测试
# ============================================================

class TestConfirmationManager:

    @pytest.fixture
    def manager(self):
        return ConfirmationManager()

    def test_low_risk_auto_approve(self, manager):
        """低风险自动通过"""
        info = manager.decide("file.read", {}, RiskLevel.LOW)
        assert info.decision == ConfirmationDecision.AUTO_APPROVE

    def test_medium_risk_require_confirm(self, manager):
        """中风险需要确认"""
        info = manager.decide("file.write", {"path": "/tmp/test.txt"}, RiskLevel.MEDIUM)
        assert info.decision == ConfirmationDecision.REQUIRE_CONFIRM
        assert "写入" in info.message
        assert info.risk_level == "medium"

    def test_high_risk_require_confirm(self, manager):
        """高风险需要确认"""
        info = manager.decide("file.delete", {"path": "/tmp/test.txt"}, RiskLevel.HIGH)
        assert info.decision == ConfirmationDecision.REQUIRE_CONFIRM
        assert "删除" in info.message
        assert info.risk_level == "high"

    def test_shutdown_confirm_message(self, manager):
        """关机确认消息"""
        info = manager.decide("system.shutdown", {"delay": 0}, RiskLevel.HIGH)
        assert "立即" in info.message
        assert "关闭系统" in info.message

    def test_shutdown_delayed_message(self, manager):
        """延迟关机消息"""
        info = manager.decide("system.shutdown", {"delay": 30}, RiskLevel.HIGH)
        assert "30" in info.message

    def test_app_close_message(self, manager):
        """关闭应用消息"""
        info = manager.decide("app.close", {"app_id": "chrome"}, RiskLevel.MEDIUM)
        assert "chrome" in info.message

    def test_to_dict(self, manager):
        """序列化"""
        info = manager.decide("file.read", {}, RiskLevel.LOW)
        d = info.to_dict()
        assert d["decision"] == "auto_approve"
        assert d["risk_level"] == "low"
