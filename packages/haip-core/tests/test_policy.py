"""Tests for policy engine (OPA-style)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from haip.policy import PolicyEngine, PolicyRule, get_policy_engine


class TestPolicyEngine:
    def test_default_deny(self):
        engine = PolicyEngine()
        assert not engine.allow({})

    def test_same_dept_access(self):
        engine = get_policy_engine()
        ctx = {"dept_scope": "self", "agent_department": "orthopedic_surgery", "patient_department": "orthopedic_surgery"}
        assert engine.allow(ctx)

    def test_cross_dept_denied(self):
        engine = get_policy_engine()
        ctx = {"dept_scope": "self", "agent_department": "cardiology", "patient_department": "orthopedic_surgery"}
        assert not engine.allow(ctx)

    def test_all_dept_access(self):
        engine = get_policy_engine()
        assert engine.allow({"dept_scope": "all"})

    def test_emergency_override(self):
        engine = get_policy_engine()
        assert engine.allow({"agent_id": "emergency"})

    def test_emergency_label(self):
        engine = get_policy_engine()
        assert engine.allow({"security_label": "EMERGENCY"})

    def test_consulted_access(self):
        engine = get_policy_engine()
        ctx = {"dept_scope": "consulted", "agent_department": "cardiology", "consulted_depts": ["cardiology", "orthopedic_surgery"]}
        assert engine.allow(ctx)

    def test_consulted_denied_not_in_list(self):
        engine = get_policy_engine()
        ctx = {"dept_scope": "consulted", "agent_department": "neurology", "consulted_depts": ["cardiology"]}
        assert not engine.allow(ctx)

    def test_deny_reason(self):
        engine = get_policy_engine()
        ctx = {"dept_scope": "self", "agent_department": "cardiology", "patient_department": "orthopedic_surgery"}
        reason = engine.deny_reason(ctx)
        assert "mismatch" in reason.lower() or "!=" in reason

    def test_custom_rule(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            name="test-special-access",
            description="Test rule",
            condition=lambda ctx: ctx.get("special_access") is True,
            priority=50,
        ))
        assert engine.allow({"special_access": True})
        assert not engine.allow({"special_access": False})

    def test_rule_priority(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(name="low-prio", condition=lambda _: False, priority=10))
        engine.add_rule(PolicyRule(name="high-prio", condition=lambda _: True, priority=100))
        assert engine.allow({})

    def test_list_rules(self):
        engine = get_policy_engine()
        rules = engine.list_rules()
        assert len(rules) >= 4

    def test_emergency_runtime(self):
        engine = PolicyEngine()
        engine.load_builtin_policies()
        assert not engine.is_emergency("test-agent")
        engine.enable_emergency("test-agent")
        assert engine.is_emergency("test-agent")
        engine.revoke_emergency("test-agent")
        assert not engine.is_emergency("test-agent")

    def test_remove_rule(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(name="temp", condition=lambda _: True, priority=10))
        assert engine.allow({})
        assert engine.remove_rule("temp")
        assert not engine.remove_rule("nonexistent")


class TestPolicyBuiltin:
    def test_all_four_builtins_exist(self):
        engine = get_policy_engine()
        names = {r["name"] for r in engine.list_rules()}
        assert "emergency-override" in names
        assert "all-dept-access" in names
        assert "consulted-dept-access" in names
        assert "same-dept-access" in names
