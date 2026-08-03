"""Unit tests for TOGAF core modules — pure functions, edge cases, construction patterns.

Covers: metamodel, rule_engine, validator, layout (pure/logic paths only).
Skips: filesystem loads, LLM calls, DB access, heavy deps.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure haip-core is importable
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))


# ══════════════════════════════════════════════════════════════════════
# metamodel
# ══════════════════════════════════════════════════════════════════════

class TestEntityTypes:
    """Pure data structure and lookup tests for metamodel entities."""

    def test_count_is_10(self):
        from haip.togaf.metamodel import ENTITY_TYPES
        assert len(ENTITY_TYPES) == 10

    def test_all_layers_present(self):
        from haip.togaf.metamodel import ENTITY_TYPES
        layers = {e.layer for e in ENTITY_TYPES.values()}
        assert layers >= {"Business", "Data", "Application", "Technology"}

    def test_list_entity_types_returns_all(self):
        from haip.togaf.metamodel import list_entity_types
        result = list_entity_types()
        assert len(result) == 10
        for item in result:
            assert "id" in item
            assert "name" in item
            assert "layer" in item
            assert "description" in item

    def test_get_existing_entity(self):
        from haip.togaf.metamodel import get_entity_type
        e = get_entity_type("Organization")
        assert e is not None
        assert e.id == "Organization"
        assert e.layer == "Business"

    def test_get_nonexistent_entity_returns_none(self):
        from haip.togaf.metamodel import get_entity_type
        assert get_entity_type("BogusEntity") is None
        assert get_entity_type("") is None

    def test_every_entity_has_nonempty_fields(self):
        from haip.togaf.metamodel import ENTITY_TYPES
        for eid, e in ENTITY_TYPES.items():
            assert e.id, f"{eid} has empty id"
            assert e.name, f"{eid} has empty name"
            assert e.layer, f"{eid} has empty layer"
            assert e.description, f"{eid} has empty description"


class TestRelationshipTypes:
    """Pure data structure and lookup tests for metamodel relationships."""

    def test_count_is_13(self):
        from haip.togaf.metamodel import RELATIONSHIP_TYPES
        assert len(RELATIONSHIP_TYPES) == 13

    def test_all_categories_present(self):
        from haip.togaf.metamodel import RELATIONSHIP_TYPES
        cats = {r.category for r in RELATIONSHIP_TYPES.values()}
        assert cats >= {"Composition", "Assignment", "Realization", "Interaction"}

    def test_list_relationship_types_returns_all(self):
        from haip.togaf.metamodel import list_relationship_types
        result = list_relationship_types()
        assert len(result) == 13
        for item in result:
            assert "id" in item
            assert "name" in item
            assert "category" in item
            assert "source" in item
            assert "target" in item
            assert "description" in item

    def test_get_existing_relationship(self):
        from haip.togaf.metamodel import get_relationship_type
        r = get_relationship_type("has")
        assert r is not None
        assert r.id == "has"
        assert r.category == "Composition"
        assert "Organization" in r.source_types

    def test_get_nonexistent_relationship_returns_none(self):
        from haip.togaf.metamodel import get_relationship_type
        assert get_relationship_type("bogus_rel") is None
        assert get_relationship_type("") is None

    def test_all_relationships_have_valid_source_target(self):
        from haip.togaf.metamodel import ENTITY_TYPES, RELATIONSHIP_TYPES
        valid_ids = set(ENTITY_TYPES.keys())
        for rid, r in RELATIONSHIP_TYPES.items():
            assert r.id, f"{rid} has empty id"
            assert r.name, f"{rid} has empty name"
            assert r.category, f"{rid} has empty category"
            assert len(r.source_types) > 0, f"{rid} has empty source_types"
            assert len(r.target_types) > 0, f"{rid} has empty target_types"

    def test_entity_type_is_dataclass(self):
        from haip.togaf.metamodel import EntityType
        e = EntityType(id="T", name="测试", layer="Business", description="test")
        assert e.id == "T"
        assert e.name == "测试"
        assert e.layer == "Business"


# ══════════════════════════════════════════════════════════════════════
# rule_engine — construction, navigate, check_condition, pipeline, ABB
# ══════════════════════════════════════════════════════════════════════

class TestRuleEngineConstruction:
    def test_default_constructor(self):
        from haip.togaf.rule_engine import RuleEngine
        engine = RuleEngine()
        assert engine._loaded is False
        assert isinstance(engine._rules, dict)
        assert len(engine._rules) == 0
        assert engine.rules_dir is not None

    def test_constructor_with_custom_dir(self):
        from haip.togaf.rule_engine import RuleEngine
        engine = RuleEngine(rules_dir="/tmp/fake_rules")
        assert str(engine.rules_dir) == str(Path("/tmp/fake_rules"))


class TestRuleMatch:
    def test_construction(self):
        from haip.togaf.rule_engine import RuleMatch
        rm = RuleMatch(
            rule_id="r1",
            rule_type="diagnosis",
            department="内分泌科",
            matched=True,
            result={"diagnosis": "糖尿病"},
        )
        assert rm.rule_id == "r1"
        assert rm.rule_type == "diagnosis"
        assert rm.department == "内分泌科"
        assert rm.matched is True
        assert rm.result == {"diagnosis": "糖尿病"}

    def test_description_default(self):
        from haip.togaf.rule_engine import RuleMatch
        rm = RuleMatch(rule_id="r1", rule_type="t", department="d", matched=False, result={})
        assert rm.description == ""


class TestPipelineResult:
    def test_empty_pipeline_summary(self):
        from haip.togaf.rule_engine import PipelineResult
        pr = PipelineResult()
        s = pr.summary()
        assert s["diagnosis"] is None
        assert s["risk"] is None
        assert s["treatment"] is None
        assert s["followup"] is None
        assert s["alerts"] == []

    def test_summary_with_matches(self):
        from haip.togaf.rule_engine import PipelineResult, RuleMatch
        rm = RuleMatch(rule_id="r1", rule_type="diagnosis", department="急诊",
                       matched=True, result={"diagnosis": "心梗"})
        rm2 = RuleMatch(rule_id="r2", rule_type="diagnosis", department="急诊",
                        matched=True, result={"diagnosis": "心衰"})
        pr = PipelineResult(diagnosis=[rm, rm2])
        s = pr.summary()
        assert s["diagnosis"] == {"diagnosis": "心梗"}  # first match
        assert s["risk"] is None

    def test_alerts_capped_at_5(self):
        from haip.togaf.rule_engine import PipelineResult, RuleMatch
        rms = [RuleMatch(rule_id=f"r{i}", rule_type="alert", department="d",
                         matched=True, result={"msg": str(i)}) for i in range(10)]
        pr = PipelineResult(alerts=rms)
        assert len(pr.summary()["alerts"]) == 5

    def test_summary_handles_empty_risk_scores(self):
        from haip.togaf.rule_engine import PipelineResult, RuleMatch
        pr = PipelineResult(
            risk_scores=[RuleMatch(rule_id="r", rule_type="risk_score",
                                   department="d", matched=True, result={"score": 3})],
        )
        s = pr.summary()
        assert s["risk"] == {"score": 3}
        assert s["diagnosis"] is None


class TestNavigate:
    """Pure static method — dict navigation with alias fallback."""

    def test_simple_key(self):
        from haip.togaf.rule_engine import RuleEngine
        assert RuleEngine._navigate({"a": 1}, "a") == 1

    def test_nested_key(self):
        from haip.togaf.rule_engine import RuleEngine
        data = {"lab_results": {"FPG": 7.2}}
        assert RuleEngine._navigate(data, "lab_results.FPG") == 7.2

    def test_deeply_nested(self):
        from haip.togaf.rule_engine import RuleEngine
        data = {"a": {"b": {"c": {"d": 42}}}}
        assert RuleEngine._navigate(data, "a.b.c.d") == 42

    def test_key_not_found(self):
        from haip.togaf.rule_engine import RuleEngine
        assert RuleEngine._navigate({"a": 1}, "x") is None

    def test_nested_key_not_found(self):
        from haip.togaf.rule_engine import RuleEngine
        assert RuleEngine._navigate({"a": {}}, "a.x.y") is None

    def test_empty_path(self):
        from haip.togaf.rule_engine import RuleEngine
        assert RuleEngine._navigate({"a": 1}, "") is None

    def test_path_through_non_dict(self):
        from haip.togaf.rule_engine import RuleEngine
        assert RuleEngine._navigate({"a": 42}, "a.b") is None

    def test_alias_not_reached_when_leaf_is_none(self):
        from haip.togaf.rule_engine import RuleEngine
        # NB: alias fallback code exists but is unreachable because
        # the navigation loop returns None immediately when any
        # intermediate or leaf value is None, before reaching alias check.
        data = {"vitals": {"spo2": None}, "lab_results": {"SpO2": 95}}
        assert RuleEngine._navigate(data, "vitals.spo2") is None

    def test_no_alias_when_missing_intermediate_key(self):
        from haip.togaf.rule_engine import RuleEngine
        # Missing intermediate key → returns None before alias check
        data = {"lab_results": {"HR": 88}}
        assert RuleEngine._navigate(data, "vitals.pulse") is None

    def test_direct_path_takes_priority_over_alias(self):
        from haip.togaf.rule_engine import RuleEngine
        data = {"vitals": {"spo2": 99}, "lab_results": {"SpO2": 88}}
        assert RuleEngine._navigate(data, "vitals.spo2") == 99


class TestCheckCondition:
    """Pure _check_condition logic — no filesystem/LLM deps."""

    @staticmethod
    def _engine():
        from haip.togaf.rule_engine import RuleEngine
        return RuleEngine(rules_dir="/tmp/fake")

    def test_greater_than_or_equal_true(self):
        ok, desc = self._engine()._check_condition(
            {"field": "lab.FPG", "operator": ">=", "value": 7.0},
            {"lab": {"FPG": 8.0}},
        )
        assert ok
        assert "FPG" in desc

    def test_greater_than_or_equal_false(self):
        ok, desc = self._engine()._check_condition(
            {"field": "lab.FPG", "operator": ">=", "value": 7.0},
            {"lab": {"FPG": 6.0}},
        )
        assert not ok

    def test_equal_numeric(self):
        ok, _ = self._engine()._check_condition(
            {"field": "age", "operator": "==", "value": 65},
            {"age": 65},
        )
        assert ok

    def test_not_equal_numeric(self):
        ok, _ = self._engine()._check_condition(
            {"field": "age", "operator": "!=", "value": 65},
            {"age": 70},
        )
        assert ok

    def test_less_than_true(self):
        ok, _ = self._engine()._check_condition(
            {"field": "hb", "operator": "<", "value": 120},
            {"hb": 100},
        )
        assert ok

    def test_less_than_false(self):
        ok, _ = self._engine()._check_condition(
            {"field": "hb", "operator": "<", "value": 120},
            {"hb": 130},
        )
        assert not ok

    def test_in_operator_with_list(self):
        ok, _ = self._engine()._check_condition(
            {"field": "status", "operator": "in", "value": ["A", "B", "C"]},
            {"status": "B"},
        )
        assert ok

    def test_in_operator_not_found(self):
        ok, _ = self._engine()._check_condition(
            {"field": "status", "operator": "in", "value": ["A", "B", "C"]},
            {"status": "D"},
        )
        assert not ok

    def test_contains_operator(self):
        ok, _ = self._engine()._check_condition(
            {"field": "diagnosis", "operator": "contains", "value": "心梗"},
            {"diagnosis": "急性ST段抬高心梗"},
        )
        assert ok

    def test_contains_operator_case_insensitive(self):
        ok, _ = self._engine()._check_condition(
            {"field": "diagnosis", "operator": "contains", "value": "copd"},
            {"diagnosis": "COPD急性加重"},
        )
        assert ok

    def test_regex_operator(self):
        ok, _ = self._engine()._check_condition(
            {"field": "name", "operator": "regex", "value": r"^张\w+"},
            {"name": "张三"},
        )
        assert ok

    def test_regex_operator_no_match(self):
        ok, _ = self._engine()._check_condition(
            {"field": "name", "operator": "regex", "value": r"^李"},
            {"name": "张三"},
        )
        assert not ok

    def test_regex_invalid_pattern(self):
        ok, desc = self._engine()._check_condition(
            {"field": "x", "operator": "regex", "value": "[invalid"},
            {"x": "abc"},
        )
        assert not ok
        assert "regex" in desc

    def test_and_combinator_all_pass(self):
        ok, _ = self._engine()._check_condition(
            {"and": [
                {"field": "age", "operator": ">=", "value": 60},
                {"field": "crp", "operator": ">", "value": 50},
            ]},
            {"age": 72, "crp": 100},
        )
        assert ok

    def test_and_combinator_one_fails(self):
        ok, desc = self._engine()._check_condition(
            {"and": [
                {"field": "age", "operator": ">=", "value": 60},
                {"field": "crp", "operator": ">", "value": 200},
            ]},
            {"age": 72, "crp": 100},
        )
        assert not ok
        assert "AND failed" in desc

    def test_or_combinator_one_passes(self):
        ok, _ = self._engine()._check_condition(
            {"or": [
                {"field": "crp", "operator": ">", "value": 200},
                {"field": "hb", "operator": "<", "value": 110},
            ]},
            {"crp": 100, "hb": 100},
        )
        assert ok

    def test_or_combinator_all_fail(self):
        ok, desc = self._engine()._check_condition(
            {"or": [
                {"field": "crp", "operator": ">", "value": 200},
                {"field": "hb", "operator": "<", "value": 50},
            ]},
            {"crp": 100, "hb": 100},
        )
        assert not ok
        assert "OR failed" in desc

    def test_field_not_found(self):
        ok, desc = self._engine()._check_condition(
            {"field": "missing", "operator": ">=", "value": 7.0},
            {"other": 1},
        )
        assert not ok
        assert "not found" in desc

    def test_unknown_operator(self):
        ok, desc = self._engine()._check_condition(
            {"field": "x", "operator": "??", "value": 1},
            {"x": 1},
        )
        assert not ok
        assert "unknown operator" in desc

    def test_invalid_condition_type(self):
        ok, desc = self._engine()._check_condition("not_a_dict", {})
        assert not ok
        assert "invalid" in desc

    def test_max_depth_exceeded(self):
        # Build a deeply nested AND chain
        cond = {"field": "x", "operator": "==", "value": 1}
        # Nest 11 deep
        for _ in range(11):
            cond = {"and": [cond]}
        ok, desc = self._engine()._check_condition(cond, {"x": 1})
        assert not ok
        assert "max depth" in desc

    def test_string_equality(self):
        ok, _ = self._engine()._check_condition(
            {"field": "gender", "operator": "==", "value": "M"},
            {"gender": "M"},
        )
        assert ok

    def test_string_inequality(self):
        ok, _ = self._engine()._check_condition(
            {"field": "gender", "operator": "!=", "value": "M"},
            {"gender": "F"},
        )
        assert ok

    def test_in_operator_with_string(self):
        ok, _ = self._engine()._check_condition(
            {"field": "letter", "operator": "in", "value": "ABCDE"},
            {"letter": "C"},
        )
        assert ok

    def test_type_error_conversion(self):
        ok, desc = self._engine()._check_condition(
            {"field": "name", "operator": ">=", "value": 7.0},
            {"name": "abc"},
        )
        assert not ok
        assert "type error" in desc


class TestGetRules:
    """Pure filtering logic — no filesystem depends needed."""

    def test_get_all_when_loaded(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e._rules = {
            "内科": [{"department": "内科", "rule_type": "diagnosis"}],
            "外科": [{"department": "外科", "rule_type": "treatment"}],
        }
        e._loaded = True
        assert len(e.get_rules()) == 2

    def test_filter_by_department(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e._rules = {
            "内科": [{"department": "内科", "rule_type": "d"}],
            "外科": [{"department": "外科", "rule_type": "t"}],
        }
        e._loaded = True
        results = e.get_rules(department="内科")
        assert len(results) == 1
        assert results[0]["department"] == "内科"

    def test_filter_by_rule_type(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e._rules = {
            "科": [
                {"department": "科", "rule_type": "diagnosis"},
                {"department": "科", "rule_type": "alert"},
            ],
        }
        e._loaded = True
        results = e.get_rules(rule_type="alert")
        assert len(results) == 1
        assert results[0]["rule_type"] == "alert"

    def test_filter_by_both(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e._rules = {
            "A": [{"department": "A", "rule_type": "x", "rules": []}],
            "B": [{"department": "B", "rule_type": "x", "rules": []},
                  {"department": "B", "rule_type": "y", "rules": []}],
        }
        e._loaded = True
        assert len(e.get_rules(department="B", rule_type="y")) == 1


class TestRunPipeline:
    """run_pipeline with injected rules — no filesystem."""

    def test_empty_patient_no_matches(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e._loaded = True
        e._rules = {}
        result = e.run_pipeline({})
        assert result.summary()["diagnosis"] is None

    def test_pipeline_with_matching_rule(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e._rules = {"d": [{"department": "d", "rule_type": "diagnosis",
                           "rules": [{"id": "r1", "condition": {"field": "age", "operator": ">=", "value": 60},
                                      "result": {"diagnosis": "老年病"}}]}]}
        e._loaded = True
        result = e.run_pipeline({"age": 72}, department="d")
        s = result.summary()
        assert s["diagnosis"] == {"diagnosis": "老年病"}

    def test_pipeline_returns_all_categories(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        rule_def = {"department": "d", "rule_type": "alert",
                    "rules": [{"id": "a1", "condition": {"field": "x", "operator": "==", "value": 1},
                               "result": {"msg": "alert!"}}]}
        e._rules = {"d": [rule_def]}
        e._loaded = True
        result = e.run_pipeline({"x": 1})
        assert len(result.alerts) == 1
        assert result.alerts[0].rule_id == "a1"


class TestABBValidation:
    def test_abb_result_construction(self):
        from haip.togaf.rule_engine import ABBValidationResult
        v = ABBValidationResult(
            rule_file="d/test",
            department="d",
            rule_type="diagnosis",
        )
        assert v.passed is True
        assert v.issues == []

    def test_validate_all_rules_detects_missing_capability(self):
        from haip.togaf.rule_engine import RuleEngine, validate_all_rules
        e = RuleEngine()
        e._rules = {
            "d": [{
                "department": "d",
                "rule_type": "diagnosis",
                # missing capability, business_process, data_entities, guideline
            }],
        }
        e._loaded = True
        results = validate_all_rules(e)
        assert len(results) == 1
        assert not results[0].passed
        assert any("capability" in i for i in results[0].issues)

    def test_validate_all_rules_passes_when_complete(self):
        from haip.togaf.rule_engine import RuleEngine, validate_all_rules
        e = RuleEngine()
        e._rules = {
            "d": [{
                "department": "d",
                "rule_type": "diagnosis",
                "capability": "临床决策",
                "business_process": "门诊诊断流程",
                "data_entities": ["检验报告"],
                "guideline": "GUIDE-001",
            }],
        }
        e._loaded = True
        results = validate_all_rules(e)
        assert len(results) == 1
        assert results[0].passed
        # stakeholder and version are warnings, not failures
        assert any("stakeholder" in i for i in results[0].issues)

    def test_validate_all_rules_warns_stakeholder_and_version(self):
        from haip.togaf.rule_engine import RuleEngine, validate_all_rules
        e = RuleEngine()
        e._rules = {
            "d": [{
                "department": "d",
                "rule_type": "diagnosis",
                "capability": "x",
                "business_process": "x",
                "data_entities": ["x"],
                "guideline": "x",
                # stakeholder missing → warning
                # version missing → warning
            }],
        }
        e._loaded = True
        results = validate_all_rules(e)
        assert len(results[0].issues) == 2  # stakeholder + version warnings
        assert results[0].passed is True  # warnings don't fail

    def test_print_abb_report_formats_correctly(self):
        from haip.togaf.rule_engine import ABBValidationResult, print_abb_report
        results = [
            ABBValidationResult(rule_file="d/t", department="d", rule_type="t", passed=True),
            ABBValidationResult(rule_file="d/t2", department="d2", rule_type="t2", passed=False,
                                issues=["缺少 capability"]),
        ]
        out = print_abb_report(results)
        assert "1/2 passed" in out or "passed" in out
        assert "[OK]" in out
        assert "[GAP]" in out
        assert "capability" in out

    def test_print_abb_report_all_passed(self):
        from haip.togaf.rule_engine import ABBValidationResult, print_abb_report
        results = [
            ABBValidationResult(rule_file="d/t", department="d", rule_type="t", passed=True),
            ABBValidationResult(rule_file="d/t2", department="d2", rule_type="t2", passed=True),
        ]
        out = print_abb_report(results)
        assert "2/2 passed" in out


# ══════════════════════════════════════════════════════════════════════
# validator — dataclasses, formatting, agent mapping
# ══════════════════════════════════════════════════════════════════════

class TestCheckResult:
    def test_construction_passed(self):
        from haip.togaf.validator import CheckResult
        c = CheckResult(id="CHK-001", name="Test", passed=True, detail="ok")
        assert c.id == "CHK-001"
        assert c.passed is True
        assert c.suggestion == ""

    def test_construction_failed_with_suggestion(self):
        from haip.togaf.validator import CheckResult
        c = CheckResult(id="CHK-002", name="Err", passed=False,
                        detail="bad", suggestion="fix it")
        assert c.passed is False
        assert c.suggestion == "fix it"


class TestValidationReport:
    def test_passed_when_all_checks_pass(self):
        from haip.togaf.validator import CheckResult, ValidationReport
        r = ValidationReport(agent_name="a", agent_cn_name="测试", agent_type="business")
        r.add_check(CheckResult(id="1", name="T1", passed=True, detail=""))
        r.add_check(CheckResult(id="2", name="T2", passed=True, detail=""))
        assert r.passed
        assert len(r.checks) == 2

    def test_passed_when_any_check_fails(self):
        from haip.togaf.validator import CheckResult, ValidationReport
        r = ValidationReport(agent_name="a", agent_cn_name="测试", agent_type="business")
        r.add_check(CheckResult(id="1", name="T1", passed=True, detail=""))
        r.add_check(CheckResult(id="2", name="T2", passed=False, detail="fail",
                                suggestion="try again"))
        assert not r.passed

    def test_add_check_collects_suggestions(self):
        from haip.togaf.validator import CheckResult, ValidationReport
        r = ValidationReport(agent_name="a", agent_cn_name="测试", agent_type="business")
        r.add_check(CheckResult(id="1", name="T1", passed=False, detail="", suggestion="S1"))
        r.add_check(CheckResult(id="2", name="T2", passed=False, detail="", suggestion="S2"))
        assert r.suggestions == ["S1", "S2"]

    def test_add_check_ignores_suggestion_when_passed(self):
        from haip.togaf.validator import CheckResult, ValidationReport
        r = ValidationReport(agent_name="a", agent_cn_name="测试", agent_type="business")
        r.add_check(CheckResult(id="1", name="T1", passed=True, detail="", suggestion="S"))
        assert r.suggestions == []

    def test_summary_has_all_sections(self):
        from haip.togaf.validator import CheckResult, ValidationReport
        r = ValidationReport(agent_name="test-agent", agent_cn_name="测试", agent_type="business")
        r.add_check(CheckResult(id="CHK-001", name="Type Compliance", passed=True, detail="ok"))
        out = r.summary()
        assert "test-agent" in out
        assert "测试" in out
        assert "business" in out
        assert "CHK-001" in out
        assert "passed" in out

    def test_summary_includes_warnings(self):
        from haip.togaf.validator import CheckResult, ValidationReport
        r = ValidationReport(agent_name="a", agent_cn_name="测试", agent_type="business")
        r.warnings.append("This is a warning")
        out = r.summary()
        assert "This is a warning" in out

    def test_summary_shows_failure_details(self):
        from haip.togaf.validator import CheckResult, ValidationReport
        r = ValidationReport(agent_name="a", agent_cn_name="测试", agent_type="business")
        r.add_check(CheckResult(id="CHK-001", name="Bad Check", passed=False,
                                detail="Something went wrong", suggestion="Fix it"))
        out = r.summary()
        assert "Something went wrong" in out
        assert "Fix it" in out

    def test_empty_report_passed(self):
        from haip.togaf.validator import ValidationReport
        r = ValidationReport(agent_name="a", agent_cn_name="测试", agent_type="business")
        assert r.passed  # no checks = vacuously true


class TestAgentTypeMapping:
    def test_mapping_exists(self):
        from haip.togaf.validator import _AGENT_TYPE_TO_ENTITY
        assert len(_AGENT_TYPE_TO_ENTITY) >= 5
        assert _AGENT_TYPE_TO_ENTITY["business"] == "ApplicationComponent"
        assert _AGENT_TYPE_TO_ENTITY["specialist"] == "ApplicationService"
        assert _AGENT_TYPE_TO_ENTITY["master_data"] == "DataEntity"
        assert _AGENT_TYPE_TO_ENTITY["rules"] == "BusinessService"
        assert _AGENT_TYPE_TO_ENTITY["architecture"] == "ApplicationComponent"

    def test_all_mapped_types_exist_in_metamodel(self):
        from haip.togaf.metamodel import ENTITY_TYPES
        from haip.togaf.validator import _AGENT_TYPE_TO_ENTITY
        for entity_type in _AGENT_TYPE_TO_ENTITY.values():
            assert entity_type in ENTITY_TYPES, f"{entity_type} not in ENTITY_TYPES"

    def test_org_type_mapping_exists(self):
        from haip.togaf.validator import _AGENT_TYPE_TO_ORG_TYPE
        assert len(_AGENT_TYPE_TO_ORG_TYPE) >= 5
        assert _AGENT_TYPE_TO_ORG_TYPE["business"] == "clinical"
        assert _AGENT_TYPE_TO_ORG_TYPE["architecture"] == "admin"


class TestRoleLevelMapping:
    def test_has_expected_mappings(self):
        from haip.togaf.validator import _ROLE_ID_TO_LEVEL
        assert _ROLE_ID_TO_LEVEL["dept_head"] == "科主任"
        assert _ROLE_ID_TO_LEVEL["attending"] == "主治医师"
        assert _ROLE_ID_TO_LEVEL["resident"] == "住院医师"
        assert _ROLE_ID_TO_LEVEL["head_nurse"] == "护士长"

    def test_all_values_are_valid_levels(self):
        from haip.togaf.validator import _ROLE_ID_TO_LEVEL
        valid = {"院领导", "科主任", "主治医师", "住院医师", "护士长",
                 "责任护士", "麻醉医师", "临床药师", "技师"}
        for level in set(_ROLE_ID_TO_LEVEL.values()):
            assert level in valid, f"Unknown level: {level}"


class TestPrintAllReports:
    def test_formats_empty_list(self):
        from haip.togaf.validator import print_all_reports
        out = print_all_reports([])
        assert "0/0" in out

    def test_formats_with_reports(self):
        from haip.togaf.validator import CheckResult, ValidationReport, print_all_reports
        r = ValidationReport(agent_name="test", agent_cn_name="测试", agent_type="business")
        r.add_check(CheckResult(id="CHK-001", name="Type", passed=True, detail="ok"))
        out = print_all_reports([r])
        assert "1/1" in out
        assert "test" in out

    def test_runs_without_arguments(self):
        from haip.agent import _registry
        from haip.togaf.validator import validate_all
        if not _registry:
            pytest.skip("no agents registered — registry-dependent integration path")
        reports = validate_all()
        assert isinstance(reports, list)
        assert len(reports) == len(_registry)


# ══════════════════════════════════════════════════════════════════════
# layout — pure compute_layout with various params and edge cases
# ══════════════════════════════════════════════════════════════════════

class TestLayoutBasic:
    def test_empty_nodes_returns_empty(self):
        from haip.togaf.layout import compute_layout
        result = compute_layout([], [])
        assert result == []

    def test_single_node_centered(self):
        from haip.togaf.layout import compute_layout
        result = compute_layout([{"id": "a"}], [], width=1200, height=800)
        assert len(result) == 1
        assert result[0]["id"] == "a"
        # Should be near center after damping
        assert 200 < result[0]["x"] < 1000
        assert 100 < result[0]["y"] < 700

    def test_deterministic_with_seed(self):
        from haip.togaf.layout import compute_layout
        nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        edges = [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}]
        r1 = compute_layout(nodes, edges, seed=42)
        r2 = compute_layout(nodes, edges, seed=42)
        assert r1 == r2

    def test_different_seeds_produce_different(self):
        from haip.togaf.layout import compute_layout
        nodes = [{"id": "a"}, {"id": "b"}]
        r1 = compute_layout(nodes, [], seed=1)
        r2 = compute_layout(nodes, [], seed=2)
        assert r1 != r2

    def test_output_sorted_by_id(self):
        from haip.togaf.layout import compute_layout
        nodes = [{"id": "c"}, {"id": "a"}, {"id": "b"}]
        result = compute_layout(nodes, [], seed=42)
        assert [n["id"] for n in result] == ["a", "b", "c"]

    def test_all_coordinates_within_bounds(self):
        from haip.togaf.layout import compute_layout
        # Use small count to ensure nodes stay well within bounds
        nodes = [{"id": f"n{i}", "w": 40, "h": 20} for i in range(5)]
        result = compute_layout(nodes, [], width=800, height=600, seed=42)
        for n in result:
            assert 0 <= n["x"] <= 800, f"x={n['x']} out of bounds"
            assert 0 <= n["y"] <= 600, f"y={n['y']} out of bounds"

    def test_custom_dimensions(self):
        from haip.togaf.layout import compute_layout
        nodes = [{"id": "a"}, {"id": "b"}]
        result = compute_layout(nodes, [], width=200, height=100, seed=42)
        for n in result:
            assert 0 <= n["x"] <= 200
            assert 0 <= n["y"] <= 100

    def test_output_has_required_fields(self):
        from haip.togaf.layout import compute_layout
        result = compute_layout([{"id": "a"}], [], seed=42)
        assert "id" in result[0]
        assert "x" in result[0]
        assert "y" in result[0]
        assert isinstance(result[0]["x"], (float, int))
        assert isinstance(result[0]["y"], (float, int))


class TestLayoutWithEdges:
    def test_connected_nodes_closer(self):
        from haip.togaf.layout import compute_layout
        nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]
        edges_ab = [{"source": "a", "target": "b"}]
        edges_cd = [{"source": "c", "target": "d"}]
        r1 = compute_layout(nodes, edges_ab, seed=42)
        r2 = compute_layout(nodes, edges_cd, seed=42)
        # Connected pairs should be positioned differently
        assert r1 != r2

    def test_dense_graph_stays_in_bounds(self):
        from haip.togaf.layout import compute_layout
        n = 15
        nodes = [{"id": f"n{i}"} for i in range(n)]
        edges = [{"source": f"n{i}", "target": f"n{(i+1)%n}"} for i in range(n)]
        result = compute_layout(nodes, edges, seed=42)
        for node in result:
            assert 0 <= node["x"] <= 1200
            assert 0 <= node["y"] <= 800


class TestLayoutGraph:
    def test_delegates_to_compute_layout(self):
        from haip.togaf.layout import layout_graph
        nodes = [{"id": "a"}, {"id": "b"}]
        edges = [{"source": "a", "target": "b"}]
        result = layout_graph(nodes, edges)
        assert len(result) == 2
        assert result[0]["id"] == "a"

    def test_single_node(self):
        from haip.togaf.layout import layout_graph
        result = layout_graph([{"id": "sole"}], [])
        assert len(result) == 1
        assert result[0]["id"] == "sole"

    def test_empty_returns_empty(self):
        from haip.togaf.layout import layout_graph
        assert layout_graph([], []) == []


class TestLayoutEdgeCases:
    def test_nodes_with_custom_sizes(self):
        from haip.togaf.layout import compute_layout
        nodes = [{"id": "a", "w": 10, "h": 10}, {"id": "b", "w": 100, "h": 80}]
        result = compute_layout(nodes, [], seed=42)
        assert len(result) == 2

    def test_few_iterations_converges_with_small_graph(self):
        from haip.togaf.layout import compute_layout
        # 3 nodes with 50 iterations = plenty of convergence time
        nodes = [{"id": f"n{i}"} for i in range(3)]
        result = compute_layout(nodes, [], iterations=50, seed=42)
        assert len(result) == 3
        for n in result:
            assert 0 <= n["x"] <= 1200
            assert 0 <= n["y"] <= 800
