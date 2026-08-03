"""测试 A2A Dispatcher."""

import builtins
import sys
from pathlib import Path

from haip.a2a import call, clear_history, get_history
from haip.agent import list_all
from haip.agent import register as reg_agent

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _setup_pharmacy_agent():
    from haip.agent import DomainPlugin, ToolDef
    list_all().clear()
    plugin = DomainPlugin(
        name="pharmacy", type="business", port=8770,
        tools=[ToolDef(
            name="calculate_tpn", description="TPN 配比计算",
            handler="pharmacy.handlers.calculate_tpn",
            input={"patient_id": "str", "energy_kcal": "float"},
        )],
    )
    reg_agent(plugin)


def _setup_perm_agent(name: str = "permtest"):
    from haip.agent import DomainPlugin, ToolDef
    reg_agent(DomainPlugin(
        name=name, type="specialist",
        tools=[ToolDef(name="now", description="时钟", handler="time.time",
                       input={})],
    ))


class TestA2ADispatcher:
    def setup_method(self):
        clear_history()
        list_all().clear()
        _setup_perm_agent()

    def test_call_unknown_agent(self):
        result = call("nonexistent", "test")
        assert result["status"] == "error"
        assert "Unknown agent" in result["error"]

    def test_call_unknown_tool(self):
        from haip.agent import DomainPlugin
        list_all().clear()
        reg_agent(DomainPlugin(name="test", type="specialist"))
        result = call("test", "nonexistent")
        assert result["status"] == "error"
        assert "error" in result
        assert any(kw in result.get("error", "").lower() for kw in ["not found", "unknown", "tool"])

    def test_call_history_recorded(self):
        from haip.agent import DomainPlugin, ToolDef
        list_all().clear()
        reg_agent(DomainPlugin(
            name="test", type="specialist",
            tools=[ToolDef(name="echo", description="", handler="pkg.mod.fn", input={})],
        ))
        _ = call("test", "echo", {"msg": "hi"})
        history = get_history()
        assert len(history) >= 1
        assert history[0]["agent"] == "test"


# ── C1: A2A 权限接线 (fail-closed) ──


class TestA2APermission:
    def setup_method(self):
        clear_history()
        list_all().clear()
        _setup_perm_agent("permtest")
        _setup_perm_agent("permtest_ok")
        from haip.permission import reset_permission_manager
        reset_permission_manager()

    def test_call_without_permission_denied(self):
        """(a) 无权限身份调用 → 标准错误结构 + PERMISSION_DENIED。"""
        from haip.permission import PermissionContext
        result = call("permtest", "now", {},
                      perm_ctx=PermissionContext(user_id="viewer1", role="viewer"))
        assert result["status"] == "error"
        assert result["code"] == "PERMISSION_DENIED"
        assert result["error"] == "Permission denied"
        assert result["detail"] == "Cannot call permtest.now"

    def test_call_with_permission_succeeds(self):
        """(b) 有权限身份 (admin) 调用 → 正常执行。"""
        from haip.permission import PermissionContext
        result = call("permtest_ok", "now", {},
                      perm_ctx=PermissionContext(user_id="admin1", role="admin"))
        assert result["status"] == "ok"
        assert result["agent"] == "permtest_ok"

    def test_call_no_context_non_test_mode_denied(self, monkeypatch):
        """非测试模式无身份上下文 → 拒绝 (PERMISSION_REQUIRED, 绝不静默放行)。"""
        monkeypatch.setenv("HAIP_TEST_MODE", "false")
        result = call("permtest_ok", "now", {})
        assert result["status"] == "error"
        assert result["code"] == "PERMISSION_REQUIRED"

    def test_call_permission_module_import_error_denied(self, monkeypatch):
        """(c) 权限模块不可导入 → fail-closed 拒绝 (不再 allow-all)。"""
        from haip.permission import PermissionContext
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "haip.permission":
                raise ImportError("simulated permission module outage")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        result = call("permtest_ok", "now", {},
                      perm_ctx=PermissionContext(user_id="admin1", role="admin"))
        assert result["status"] == "error"
        assert result["code"] == "PERMISSION_UNAVAILABLE"

    def test_permission_context_from_user_mapping(self):
        """HTTP current_user → PermissionContext 映射 (含角色提取)。"""
        from haip.a2a import permission_context_from_user
        pc = permission_context_from_user({
            "user_id": "u-42", "roles": ["doctor", "admin"], "tenant_id": None,
        })
        assert pc is not None
        assert pc.user_id == "u-42"
        assert pc.role == "doctor"
        assert pc.agent_id == "u-42"
        assert permission_context_from_user(None) is None
        assert permission_context_from_user({}) is None
