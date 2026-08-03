"""Tests for Sprint 2-4: Permission System + Audit + A2A enforcement."""

import tempfile
from pathlib import Path

import pytest

from haip.permission import (
    PermissionContext,
    PermissionManager,
    get_permission,
)


class TestPermissionContext:
    def test_default(self):
        ctx = PermissionContext()
        assert ctx.user_id == ""
        assert ctx.role == ""
        assert ctx.agent_id == ""
        assert ctx.is_emergency is False

    def test_custom(self):
        ctx = PermissionContext(user_id="dr_001", role="ROLE_PHYSICIAN",
                                agent_id="orthopedic-surgery")
        assert ctx.user_id == "dr_001"
        assert ctx.role == "ROLE_PHYSICIAN"


class TestPermissionManagerSchema:
    def test_create_in_memory(self):
        pm = PermissionManager(":memory:")
        # Verify tables exist by querying
        tables = pm._db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "auth_user" in table_names
        assert "auth_role" in table_names
        assert "perm_agent_call_policy" in table_names
        assert "perm_data_policy" in table_names
        assert "audit_access_log" in table_names
        pm.close()

    def test_seed_defaults(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        # Check roles seeded
        roles = pm._db.execute("SELECT role_code FROM auth_role").fetchall()
        assert len(roles) >= 4  # at least 4 roles
        # Check users seeded
        users = pm._db.execute("SELECT user_id FROM auth_user").fetchall()
        assert len(users) >= 4
        pm.close()

    def test_seed_with_agents(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults(agent_ids=["orthopedic-surgery", "pharmacy", "cardiology"])
        agents = pm._db.execute("SELECT agent_id FROM auth_agent").fetchall()
        agent_ids = [a[0] for a in agents]
        assert "orthopedic-surgery" in agent_ids
        assert "pharmacy" in agent_ids
        pm.close()


class TestU2A:
    def test_get_user_roles(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        roles = pm.get_user_roles("dr_001")
        assert "ROLE_PHYSICIAN" in roles
        pm.close()

    def test_get_user_roles_unknown(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        roles = pm.get_user_roles("nonexistent")
        assert roles == []
        pm.close()

    def test_get_accessible_agents_empty(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        # No role-agent mappings seeded → empty list
        agents = pm.get_accessible_agents("dr_001")
        assert agents == []
        pm.close()


class TestA2A:
    def test_can_call_with_wildcard_policy(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(agent_id="orthopedic-surgery", role="ROLE_PHYSICIAN")
        # medical-record has wildcard policy for all callers
        result = pm.can_call_agent(ctx, "medical-record", "get_patient")
        assert result is True
        pm.close()

    def test_can_call_emergency(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(agent_id="emergency", is_emergency=True)
        result = pm.can_call_agent(ctx, "any-agent", "any-tool")
        assert result is True
        pm.close()

    def test_role_based_fallback(self):
        """Role-based check: pharmacist -> auth/rbac AGENT_EXECUTE enables all agents."""
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(role="pharmacist")
        # No explicit A2A policy for pharmacist→pharmacy exists,
        # but auth/rbac grants blanket AGENT_EXECUTE → allowed
        result = pm.can_call_agent(ctx, "pharmacy", "assess")
        assert result is True

    def test_role_based_denied(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(role="ROLE_NURSE")
        # nurse does not have pharmacy.*, only pharmacy-specific tools
        result = pm.can_call_agent(ctx, "pharmacy", "calculate_tpn")
        assert result is False
        pm.close()


class TestA2D:
    def test_can_access_self_department(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(agent_id="orthopedic-surgery", department="orthopedic")
        # No policy → default allow in dev mode
        allowed, _ = pm.can_access_data(ctx, "DP-HIS-PATIENT", patient_department="orthopedic")
        assert allowed is True
        pm.close()

    def test_emergency_all_access(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(is_emergency=True)
        allowed, _ = pm.can_access_data(ctx, "DP-EMR-NOTE")
        assert allowed is True
        pm.close()


class TestAudit:
    def test_log_access_writes_record(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(agent_id="orthopedic-surgery")
        pm.log_access(ctx, "A2A_call", "medical-record.get_patient", "allow")
        logs = pm._db.execute("SELECT COUNT(*) FROM audit_access_log").fetchone()
        assert logs[0] == 1
        pm.close()

    def test_log_denied(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        ctx = PermissionContext(agent_id="unauthorized")
        pm.log_access(ctx, "A2A_call", "restricted.tool", "deny", "Not in policy")
        row = pm._db.execute(
            "SELECT decision, reason FROM audit_access_log LIMIT 1"
        ).fetchone()
        assert row[0] == "deny"
        assert "Not in policy" in row[1]
        pm.close()


class TestRoleBasedCan:
    def test_admin_wildcard(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        assert pm.can("admin", "any_action") is True

    def test_pharmacist_has_agent_execute(self):
        """auth/rbac grants blanket AGENT_EXECUTE to pharmacist — any agent is accessible."""
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        result = pm.can("pharmacist", "pharmacy.assess")
        assert result is True  # blanket AGENT_EXECUTE → all agents

    def test_unknown_role(self):
        pm = PermissionManager(":memory:")
        pm.seed_defaults()
        assert pm.can("unknown_role", "pharmacy.assess") is False


class TestGlobalSingleton:
    def test_get_permission_returns_singleton(self):
        p1 = get_permission(":memory:")
        p2 = get_permission()
        assert p1 is p2
