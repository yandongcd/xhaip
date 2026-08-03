"""Autonomous Clinical Decision Engine — 自主决策.

Rule-driven clinical decisions: load guidelines, evaluate patient data,
return structured decisions with confidence and evidence trails.

Usage:
    engine = DecisionEngine()
    result = engine.decide("orthopedic-surgery", patient_data)
    # -> {"decision": "THA手术", "confidence": 0.92, "rationale": [...], "evidence": [...]}
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Evaluates clinical rules against patient data, returning autonomous decisions."""

    def __init__(self, project_root: str = ""):
        if project_root:
            self.root = pathlib.Path(project_root)
        else:
            self.root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        self.rules_dir = self.root / "packages/haip-hospital/knowledge/rules"
        self.guidelines_dir = self.root / "packages/haip-hospital/knowledge/guidelines"
        self._rule_cache: dict[str, list[dict]] = {}

    def decide(self, agent_name: str, patient: dict[str, Any]) -> dict[str, Any]:
        """Autonomous decision for a patient by an agent."""
        rules = self._load_rules_for(agent_name)
        if not rules:
            return self._fallback_decision(agent_name, patient)

        matches = []
        for rule in rules:
            condition = rule.get("condition", {})
            if self._evaluate_condition(condition, patient):
                result = rule.get("result", {})
                matches.append({
                    "rule_id": rule.get("id", ""),
                    "description": rule.get("description", ""),
                    "diagnosis": result.get("diagnosis", ""),
                    "severity": result.get("severity", "正常"),
                    "recommendation": result.get("recommendation", ""),
                })

        if not matches:
            return self._fallback_decision(agent_name, patient)

        # Priority: most severe first
        severity_order = {"危重": 4, "高危": 3, "中危": 2, "低危": 1, "正常": 0}
        matches.sort(key=lambda m: severity_order.get(m["severity"], 0), reverse=True)

        primary = matches[0]
        return {
            "decision": primary["recommendation"],
            "diagnosis": primary["diagnosis"],
            "confidence": min(0.95, 0.6 + 0.1 * len(matches)),
            "severity": primary["severity"],
            "rationale": [m["description"] for m in matches],
            "alternatives": [m["recommendation"] for m in matches[1:4]],
            "matched_rules": len(matches),
            "autonomous": True,
        }

    def _load_rules_for(self, agent_name: str) -> list[dict]:
        if agent_name in self._rule_cache:
            return self._rule_cache[agent_name]

        rules = []
        agent_key = agent_name.replace("-", "_")

        for rd in sorted(self.rules_dir.iterdir()):
            if not rd.is_dir():
                continue
            if agent_key not in rd.name and agent_name.replace("-", "") not in rd.name.replace("_", ""):
                # Also check shared rules
                if rd.name not in ("shared", "ecg_patterns", "hip_fracture_timing", "hypertension", "rcri", "perioperative_mi"):
                    continue

            for rf in sorted(rd.glob("*.yaml")):
                try:
                    with open(rf, encoding="utf-8") as f:
                        for doc in yaml.safe_load_all(f):
                            if doc and "rules" in doc:
                                rules.extend(doc["rules"])
                except Exception:
                    logger.debug("Rule YAML load failed: %s", rf, exc_info=True)

        self._rule_cache[agent_name] = rules
        return rules

    def _evaluate_condition(self, condition: dict, patient: dict) -> bool:
        if not condition:
            return False

        field = condition.get("field", "")
        operator = condition.get("operator", "==")
        expected = condition.get("value")

        # Resolve nested fields (e.g., "ct.midline_shift")
        value = patient
        for part in field.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return False

        if value is None:
            return False

        # Type coercion
        if isinstance(expected, (int, float)) and isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                return False

        if operator == "==":
            return value == expected  # type: ignore[operator]
        if operator == "!=":
            return value != expected  # type: ignore[operator]
        if operator in (">", "gt"):
            return value > expected  # type: ignore[operator]
        if operator in ("<", "lt"):
            return value < expected  # type: ignore[operator]
        if operator in (">=", "gte"):
            return value >= expected  # type: ignore[operator]
        if operator in ("<=", "lte"):
            return value <= expected  # type: ignore[operator]
        return False

    def _fallback_decision(self, agent_name: str, patient: dict) -> dict[str, Any]:
        return {
            "decision": "按标准流程评估",
            "diagnosis": patient.get("diagnosis", "待评估"),
            "confidence": 0.5,
            "severity": "正常",
            "rationale": ["无匹配的临床规则，按标准流程处理"],
            "alternatives": [],
            "matched_rules": 0,
            "autonomous": False,
        }


# Singleton
_singleton_state: dict = {}


def get_decision_engine() -> DecisionEngine:
    from haip._singleton import locked_singleton
    return locked_singleton(DecisionEngine, _singleton_state, "engine")
