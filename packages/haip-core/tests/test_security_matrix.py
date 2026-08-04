"""M1 安全基线 + 12 门户身份权限矩阵测试 (商用评估 M1-2/M1-3)."""

from __future__ import annotations

import pytest


class TestSecurityBaseline:
    def test_dev_mode_returns_violations_without_raising(self, monkeypatch):
        from haip.security_baseline import check_security_baseline
        for k in ("JWT_SECRET_KEY", "HAIP_ADMIN_PASSWORD", "HAIP_DOCTOR_PASSWORD"):
            monkeypatch.delenv(k, raising=False)
        violations = check_security_baseline(strict=False)
        assert any("JWT_SECRET_KEY" in v for v in violations)
        assert any("HAIP_ADMIN_PASSWORD" in v for v in violations)
        assert any("HAIP_DOCTOR_PASSWORD" in v for v in violations)

    def test_strict_mode_raises(self, monkeypatch):
        from haip.security_baseline import SecurityBaselineError, check_security_baseline
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(SecurityBaselineError):
            check_security_baseline(strict=True)

    def test_strict_mode_clean_env_passes(self, monkeypatch):
        from haip.security_baseline import check_security_baseline
        monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
        monkeypatch.setenv("HAIP_ADMIN_PASSWORD", "Str0ng!Passw0rd")
        monkeypatch.setenv("HAIP_DOCTOR_PASSWORD", "An0ther!Passw0rd")
        monkeypatch.setenv("ENCRYPTION_KEY", "y" * 32)
        assert check_security_baseline(strict=True) == []

    def test_strict_flag_from_env(self, monkeypatch):
        """HAIP_STRICT_SECURITY=true 时未显式传 strict 也应强制。"""
        from haip.security_baseline import SecurityBaselineError, check_security_baseline
        monkeypatch.setenv("HAIP_STRICT_SECURITY", "true")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(SecurityBaselineError):
            check_security_baseline()


class TestPortalIdentityMatrix:
    """12 门户身份必须全部映射到已定义 RBAC 角色, 且关键权限不变量成立."""

    def test_all_12_identities_mapped(self):
        from haip.auth.models import PORTAL_IDENTITY_ROLES, PREDEFINED_ROLES
        expected = {"director", "secretary", "vice-director", "dept-head", "attending",
                    "head-nurse", "pharmacist", "anesthesiologist", "med-tech",
                    "admin", "resident", "intern"}
        assert set(PORTAL_IDENTITY_ROLES) == expected
        for identity, role in PORTAL_IDENTITY_ROLES.items():
            assert role in PREDEFINED_ROLES, f"{identity} → {role} 未在 PREDEFINED_ROLES 定义"

    def test_intern_cannot_execute(self):
        """实习生不得独立执行 agent 工具 (越权治理)."""
        from haip.auth.models import PORTAL_IDENTITY_ROLES, Permission
        from haip.auth.rbac import has_permission
        role = PORTAL_IDENTITY_ROLES["intern"]
        assert not has_permission([role], Permission.AGENT_EXECUTE)
        assert has_permission([role], Permission.AGENT_READ)

    def test_leadership_audit_but_no_execute(self):
        """院领导: 可读审计与患者数据, 不执行工具。"""
        from haip.auth.models import PORTAL_IDENTITY_ROLES, Permission
        from haip.auth.rbac import has_permission
        for identity in ("director", "secretary", "vice-director"):
            role = PORTAL_IDENTITY_ROLES[identity]
            assert has_permission([role], Permission.AUDIT_READ), identity
            assert not has_permission([role], Permission.AGENT_EXECUTE), identity

    def test_clinical_roles_can_execute(self):
        from haip.auth.models import PORTAL_IDENTITY_ROLES, Permission
        from haip.auth.rbac import has_permission
        for identity in ("attending", "pharmacist", "anesthesiologist",
                         "med-tech", "resident", "dept-head"):
            assert has_permission([PORTAL_IDENTITY_ROLES[identity]], Permission.AGENT_EXECUTE), identity

    def test_head_nurse_fine_grained_not_blanket(self):
        """护士长: 无全域执行权, 走 permission 细粒度白名单 (最小权限)."""
        from haip.auth.models import PORTAL_IDENTITY_ROLES, Permission
        from haip.auth.rbac import has_permission
        from haip.permission import PermissionContext, PermissionManager
        role = PORTAL_IDENTITY_ROLES["head-nurse"]
        assert not has_permission([role], Permission.AGENT_EXECUTE)
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(role="ROLE_NURSE")
        assert pm.can_call_agent(ctx, "medical-record", "query_patient") is True
        assert pm.can_call_agent(ctx, "pharmacy", "calculate_tpn") is False
        pm.close()

    def test_nurse_role_bridged_to_permission_module(self):
        """ROLE_NURSE 码必须桥接到 rbac nurse 角色 (D2 词表断裂的补全)."""
        from haip.permission import _RBAC_ROLE_ALIASES
        assert _RBAC_ROLE_ALIASES.get("ROLE_NURSE") == "nurse"
