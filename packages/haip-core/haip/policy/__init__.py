"""OPA-style Policy Engine — Python-native authorization policies.

Inspired by haip-0710's OPA Rego policies.
Provides declarative, hot-reloadable authorization rules.

Built-in policies:
    1. Same-department access (dept_scope = self)
    2. All-department access (dept_scope = all)
    3. Consultation cross-dept access (dept_scope = consulted)
    4. Emergency override (agent_id = emergency)

Usage:
    engine = PolicyEngine()
    engine.load_builtin_policies()
    allowed = engine.allow({
        "dept_scope": "self",
        "agent_department": "orthopedic_surgery",
        "patient_department": "orthopedic_surgery",
    })
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyRule:
    """A single authorization rule."""

    name: str
    description: str = ""
    condition: Callable[[dict[str, Any]], bool] = lambda _: False
    priority: int = 0  # Higher = evaluated first


class PolicyEngine:
    """Policy-based authorization engine."""

    def __init__(self):
        self._rules: list[PolicyRule] = []
        self._overrides: dict[str, Callable] = {}
        # Emergency/override flags
        self._emergency_access: dict[str, bool] = {}

    # ── Rule Management ──

    def add_rule(self, rule: PolicyRule):
        """Register a new policy rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: -r.priority)

    def remove_rule(self, name: str) -> bool:
        """Remove a policy rule by name."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        return len(self._rules) < before

    def load_builtin_policies(self):
        """Load the 4 built-in HAIP authorization policies."""
        # Clear existing
        self._rules.clear()

        # P1: Emergency override (highest priority)
        self.add_rule(PolicyRule(
            name="emergency-override",
            description="急诊 Agent 在所有场景下都允许读取",
            condition=lambda ctx: (
                ctx.get("agent_id") == "emergency"
                or ctx.get("security_label") == "EMERGENCY"
            ),
            priority=100,
        ))

        # P2: All-department access
        self.add_rule(PolicyRule(
            name="all-dept-access",
            description="全科室访问 — 专项/主数据 Agent 可读全院数据",
            condition=lambda ctx: ctx.get("dept_scope") == "all",
            priority=80,
        ))

        # P3: Consultation cross-dept access
        self.add_rule(PolicyRule(
            name="consulted-dept-access",
            description="会诊跨科室访问 — 仅允许被会诊科室读取该患者数据",
            condition=lambda ctx: (
                ctx.get("dept_scope") == "consulted"
                and ctx.get("agent_department") in ctx.get("consulted_depts", [])
            ),
            priority=60,
        ))

        # P4: Same-department access
        self.add_rule(PolicyRule(
            name="same-dept-access",
            description="同科室访问 — Agent 只能读自己科室的患者数据",
            condition=lambda ctx: (
                ctx.get("dept_scope") == "self"
                and ctx.get("agent_department") == ctx.get("patient_department")
            ),
            priority=40,
        ))

    # ── Authorization ──

    def allow(self, context: dict[str, Any]) -> bool:
        """Evaluate all policies against the context. Returns True if any rule allows.

        Follows the OPA pattern: default deny, explicit allow.
        """
        for rule in self._rules:
            try:
                if rule.condition(context):
                    return True
            except Exception:
                continue
        return False

    def deny_reason(self, context: dict[str, Any]) -> str:
        """Explain why access was denied (for audit)."""
        if self.allow(context):
            return "Access granted"

        reasons = []
        if "dept_scope" not in context:
            reasons.append("Missing dept_scope")
        elif context["dept_scope"] == "self":
            agent_dept = context.get("agent_department", "?")
            patient_dept = context.get("patient_department", "?")
            reasons.append(f"Department mismatch: {agent_dept} != {patient_dept}")
        elif context["dept_scope"] == "consulted":
            agent_dept = context.get("agent_department", "?")
            consulted = context.get("consulted_depts", [])
            reasons.append(f"Agent {agent_dept} not in consulted list: {consulted}")

        return " | ".join(reasons) if reasons else "No matching policy"

    # ── Emergency Access ──

    def enable_emergency(self, agent_id: str):
        """Grant emergency access to a specific agent."""
        self._emergency_access[agent_id] = True

    def is_emergency(self, agent_id: str) -> bool:
        """Check if an agent has emergency access."""
        return self._emergency_access.get(agent_id, False)

    def revoke_emergency(self, agent_id: str):
        """Revoke emergency access."""
        self._emergency_access.pop(agent_id, None)

    # ── Audit ──

    def list_rules(self) -> list[dict[str, Any]]:
        """List all registered policies."""
        return [
            {"name": r.name, "description": r.description, "priority": r.priority}
            for r in self._rules
        ]


# Global singleton
_policy_engine = PolicyEngine()
_policy_engine.load_builtin_policies()


def get_policy_engine() -> PolicyEngine:
    """Get the global policy engine singleton."""
    return _policy_engine
