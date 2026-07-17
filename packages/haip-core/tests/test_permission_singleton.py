"""D2 修复测试 — PermissionManager 单例 + 审计持久化 (源自商用评估 M1-1)."""

from __future__ import annotations

import os

import pytest


@pytest.fixture()
def perm_db(tmp_path, monkeypatch):
    db = tmp_path / "perm.db"
    monkeypatch.setenv("HAIP_PERMISSION_DB", str(db))
    from haip.permission import reset_permission_manager
    reset_permission_manager()
    yield db
    reset_permission_manager()
    monkeypatch.delenv("HAIP_PERMISSION_DB", raising=False)


class TestPermissionSingleton:
    def test_singleton_identity(self, perm_db):
        from haip.permission import get_permission_manager
        assert get_permission_manager() is get_permission_manager()

    def test_audit_persists_across_restart(self, perm_db):
        """审计必须落盘 — 重建单例 (模拟重启) 后记录仍在."""
        from haip.permission import (
            PermissionContext,
            get_permission_manager,
            reset_permission_manager,
        )
        pm = get_permission_manager()
        ctx = PermissionContext(user_id="dr_001", role="ROLE_PHYSICIAN", agent_id="orthopedic-surgery")
        pm.log_access(ctx, "A2A_call", "pharmacy.assess_nutrition", "allow")
        reset_permission_manager()  # 模拟进程重启
        pm2 = get_permission_manager()
        logs = pm2.get_audit_logs(limit=10)
        assert any(r["resource_id"] == "pharmacy.assess_nutrition" for r in logs), \
            "审计记录未持久化 — D2 未修复"

    def test_a2a_call_writes_audit(self, perm_db):
        """带 perm_ctx 的 a2a.call 必须在持久库留下审计记录."""
        from haip.a2a import call
        from haip.agent import DomainPlugin, ToolDef, register
        from haip.permission import get_permission_manager
        register(DomainPlugin(
            name="perm-audit-test", type="specialist",
            tools=[ToolDef(name="ping", description="", handler="json.dumps")]))
        call("perm-audit-test", "ping", {"obj": {}},
             perm_ctx={"user_id": "dr_001", "role": "ROLE_PHYSICIAN",
                       "agent_id": "perm-audit-test", "department": "", "is_emergency": False})
        logs = get_permission_manager().get_audit_logs(limit=20)
        assert any("perm-audit-test" in (r["resource_id"] or "") for r in logs), \
            "a2a 调用审计未写入持久库 (旧行为: 写入 :memory: 即弃)"

    def test_default_db_path_used_when_no_env(self, monkeypatch):
        """无 env 且非 test mode 时使用默认 data/permission.db 路径."""
        monkeypatch.delenv("HAIP_PERMISSION_DB", raising=False)
        monkeypatch.setenv("HAIP_TEST_MODE", "false")
        import haip.permission as perm_mod
        orig = perm_mod._default_db_path
        from pathlib import Path
        db = Path(__file__).parent / ".test_permission_tmp.db"
        monkeypatch.setattr(perm_mod, "_default_db_path", lambda: str(db))
        perm_mod.reset_permission_manager()
        try:
            perm_mod.get_permission_manager()
            assert db.exists()
        finally:
            perm_mod.reset_permission_manager()
            if db.exists():
                db.unlink()
            perm_mod._default_db_path = orig
            monkeypatch.delenv("HAIP_TEST_MODE", raising=False)
