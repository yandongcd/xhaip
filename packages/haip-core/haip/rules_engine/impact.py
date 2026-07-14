"""Rule impact analyzer — assesses impact of guideline updates.

Ported from haip-0710's src/agents/rules/impact_analyzer.py.
"""

from __future__ import annotations

from typing import Any

from haip.rules_engine.models import ChangeType, ImpactReport, RuleDiff


def analyze_impact(
    source_id: str,
    old_version: str,
    new_version: str,
    changes: list[dict[str, Any]],
) -> ImpactReport | None:
    """Analyze the impact of a guideline version update.

    Args:
        source_id: Guideline source identifier.
        old_version: Previous guideline version.
        new_version: New guideline version.
        changes: List of change dicts with keys: type, rule_id, old_value, new_value, impact.

    Returns:
        ImpactReport summarizing affected rules.
    """
    rule_diffs = []

    for change in changes:
        change_type_str = change.get("type", "evidence_updated")
        rule_id = change.get("rule_id", "")
        old_val = change.get("old_value", "")
        new_val = change.get("new_value", "")
        impact = change.get("impact", "medium")

        try:
            ct = ChangeType(change_type_str)
        except ValueError:
            ct = ChangeType.EVIDENCE_UPDATED

        rd = RuleDiff(
            rule_id=rule_id,
            change_type=ct,
            old_value=old_val,
            new_value=new_val,
            impact_level=impact,
        )
        rule_diffs.append(rd)

    high = sum(1 for d in rule_diffs if d.impact_level == "high")
    medium = sum(1 for d in rule_diffs if d.impact_level == "medium")
    low = sum(1 for d in rule_diffs if d.impact_level == "low")

    return ImpactReport(
        source_id=source_id,
        old_version=old_version,
        new_version=new_version,
        affected_rules=rule_diffs,
        summary={"high": high, "medium": medium, "low": low},
    )
