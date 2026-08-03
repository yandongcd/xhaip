"""Tests for rules engine — evaluator, arbitration, impact, governance."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from haip.rules_engine.arbitration import evaluate_rules, register_source
from haip.rules_engine.evaluator import evaluate, register_callback
from haip.rules_engine.governance import (
    approve_change,
    create_change_request,
    get_pending_changes,
    reject_change,
)
from haip.rules_engine.impact import analyze_impact
from haip.rules_engine.models import (
    Certainty,
    ChangeType,
    EvaluationContext,
    EvidenceRef,
    GuidelineSource,
    ImpactReport,
    Rule,
    RuleDiff,
    RuleSet,
    RuleType,
    SourceTier,
)


class TestExpressionEvaluator:
    def setup_method(self):
        self.ctx = EvaluationContext({"age": 72, "gender": "M", "crp": 107.3, "hb": 109.5, "name": "test"})

    def test_empty_expression(self):
        assert evaluate("", self.ctx)

    def test_simple_comparison_eq(self):
        assert evaluate("gender == M", self.ctx)
        assert not evaluate("gender == F", self.ctx)

    def test_simple_comparison_gt(self):
        assert evaluate("age > 70", self.ctx)
        assert not evaluate("age > 80", self.ctx)

    def test_simple_comparison_gte(self):
        assert evaluate("age >= 72", self.ctx)

    def test_simple_comparison_lt(self):
        assert evaluate("hb < 120", self.ctx)

    def test_simple_comparison_ne(self):
        assert evaluate("gender != F", self.ctx)

    def test_in_expression(self):
        assert evaluate("gender IN [M, F]", self.ctx)
        assert not evaluate("gender IN [X, Z]", self.ctx)

    def test_range_expression(self):
        ctx = EvaluationContext({"crp": 107.3, "age": 72})
        assert evaluate("100 <= crp <= 200", ctx)
        assert not evaluate("200 <= crp <= 500", ctx)

    def test_range_expression_reverse(self):
        ctx = EvaluationContext({"age": 72})
        assert evaluate("100 >= age >= 50", ctx)

    def test_and_compound(self):
        assert evaluate("age >= 65 AND crp > 100", self.ctx)
        assert not evaluate("age >= 65 AND crp > 200", self.ctx)

    def test_or_compound(self):
        assert evaluate("crp > 200 OR hb < 110", self.ctx)
        assert not evaluate("crp > 200 OR hb > 200", self.ctx)

    def test_missing_field(self):
        assert not evaluate("missing_field == x", self.ctx)

    def test_string_comparison(self):
        assert evaluate("name == test", self.ctx)
        assert not evaluate("name == other", self.ctx)

    def test_callback(self):
        def is_senior(age_str):
            return int(age_str) >= 65

        register_callback("is_senior", is_senior)
        assert evaluate("$is_senior(age)", self.ctx)

    def test_nested_complex(self):
        ctx = EvaluationContext({"a": 10, "b": 20, "c": 30})
        assert evaluate("a < 20 AND b > 10 AND c >= 30", ctx)


class TestArbitration:
    def test_single_rule(self):
        rules = [Rule(id="r1", decision_point="test", conclusion="结论A", condition_expr="age > 60", certainty=Certainty.STRONG)]
        ctx = EvaluationContext({"age": 72})
        result = evaluate_rules(rules, ctx)
        assert result.winner_rule_id == "r1"
        assert result.conclusion == "结论A"
        assert result.strategy_used == "single_match"

    def test_no_match(self):
        rules = [Rule(id="r1", decision_point="test", conclusion="结论A", condition_expr="age > 100", certainty=Certainty.STRONG)]
        ctx = EvaluationContext({"age": 72})
        result = evaluate_rules(rules, ctx)
        assert result.winner_rule_id == ""
        assert "无匹配" in result.conclusion

    def test_consensus(self):
        rules = [
            Rule(id="r1", decision_point="test", conclusion="建议A", condition_expr="age > 60", certainty=Certainty.STRONG),
            Rule(id="r2", decision_point="test", conclusion="建议A", condition_expr="crp > 50", certainty=Certainty.MODERATE),
        ]
        ctx = EvaluationContext({"age": 72, "crp": 100})
        result = evaluate_rules(rules, ctx)
        assert result.conclusion == "建议A"
        assert result.strategy_used == "consensus"

    def test_conflict_arbitration(self):
        register_source(GuidelineSource(
            id="NICE-NG37", name="NICE NG37", tier=SourceTier.L2, version="2022",
            publish_date="2022-01-01", admin_priority=10,
        ))
        register_source(GuidelineSource(
            id="LOCAL-GUIDE", name="Local Guide", tier=SourceTier.L5, version="2024",
            publish_date="2024-01-01", admin_priority=100,
        ))

        rules = [
            Rule(id="r1", decision_point="surgery", conclusion="立即手术",
                 condition_expr="age > 60", certainty=Certainty.STRONG,
                 evidence=[EvidenceRef(source_id="NICE-NG37")], priority=0),
            Rule(id="r2", decision_point="surgery", conclusion="保守治疗",
                 condition_expr="age > 60", certainty=Certainty.MODERATE,
                 evidence=[EvidenceRef(source_id="LOCAL-GUIDE")], priority=0),
        ]
        ctx = EvaluationContext({"age": 72})
        result = evaluate_rules(rules, ctx)
        assert result.winner_rule_id != ""
        assert len(result.conflicts) > 0

    def test_conditionless_rule(self):
        rules = [Rule(id="r1", decision_point="test", conclusion="默认结论")]
        ctx = EvaluationContext({"age": 72})
        result = evaluate_rules(rules, ctx)
        assert result.conclusion == "默认结论"


class TestImpactAnalysis:
    def test_analyze_impact(self):
        changes = [
            {"type": "threshold_modified", "rule_id": "r1", "old_value": "age >= 70", "new_value": "age >= 65", "impact": "high"},
            {"type": "evidence_updated", "rule_id": "r2", "old_value": "", "new_value": "", "impact": "low"},
        ]
        report = analyze_impact("NICE-NG37", "2022.1", "2024.2", changes)
        assert report is not None
        assert report.source_id == "NICE-NG37"
        assert len(report.affected_rules) == 2
        assert report.summary["high"] == 1
        assert report.summary["low"] == 1

    def test_analyze_without_changes(self):
        report = analyze_impact("TEST-SRC", "1.0", "2.0", [])
        assert report is not None
        assert len(report.affected_rules) == 0
        assert report.summary["high"] == 0


class TestGovernance:
    def test_create_and_approve(self):
        impact = ImpactReport(source_id="S1", old_version="1.0", new_version="2.0",
                              affected_rules=[], summary={"high": 0, "medium": 0, "low": 0})
        cr = create_change_request(impact)
        assert cr.status.value == "pending"
        assert cr.id.startswith("cr-S1-")

    def test_get_pending(self):
        impact = ImpactReport(source_id="S2", old_version="1.0", new_version="2.0",
                              affected_rules=[], summary={"high": 0, "medium": 0, "low": 0})
        cr = create_change_request(impact)
        pending = get_pending_changes()
        assert len(pending) >= 1
        assert any(c.id == cr.id for c in pending)

    def test_approve(self):
        impact = ImpactReport(source_id="S3", old_version="1.0", new_version="2.0",
                              affected_rules=[], summary={})
        cr = create_change_request(impact)
        assert approve_change(cr.id, reviewed_by="admin")
        # Verify S3 is no longer pending
        assert cr.id not in [c.id for c in get_pending_changes()]

    def test_reject(self):
        impact = ImpactReport(source_id="S4", old_version="1.0", new_version="2.0",
                              affected_rules=[], summary={})
        cr = create_change_request(impact)
        assert reject_change(cr.id, reviewed_by="admin", reason="needs revision")
        assert cr.id not in [c.id for c in get_pending_changes()]

    def test_approve_already_processed(self):
        impact = ImpactReport(source_id="S5", old_version="1.0", new_version="2.0",
                              affected_rules=[], summary={})
        cr = create_change_request(impact)
        assert approve_change(cr.id)
        assert not approve_change(cr.id)  # Already approved, cannot re-approve
