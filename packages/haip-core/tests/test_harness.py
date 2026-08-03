"""Tests for harness_diagnosis, harness_proposer, harness_acceptance modules."""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from haip.harness_acceptance import (
    HarnessAcceptance,
    ScoreSnapshot,
)
from haip.harness_diagnosis import (
    DiagnosisConfig,
    DiagnosisOutcome,
    HarnessDiagnosis,
    NormalizedStep,
    StageRecord,
    build_stage_records,
    normalize_trace_steps,
)
from haip.harness_proposer import (
    HOOKS_BY_FAMILY,
    MECHANISM_FAMILIES,
    EditableSurface,
    HarnessProposer,
    Proposal,
    ProposalBundle,
)

# ══════════════════════════════════════════════════════════════════
# HarnessDiagnosis Tests
# ══════════════════════════════════════════════════════════════════


class TestHarnessDiagnosis:
    def test_init_defaults(self):
        d = HarnessDiagnosis()
        assert d.config is not None
        assert d.root.exists()

    def test_with_custom_config(self):
        config = DiagnosisConfig(model_reference="test", timeout_s=60, retries=2)
        d = HarnessDiagnosis(config=config)
        assert d.config.model_reference == "test"
        assert d.config.timeout_s == 60
        assert d.config.retries == 2

    def test_build_outcomes(self):
        d = HarnessDiagnosis()
        executions = [
            {"agent": "pharmacy", "tool": "assess_nutrition", "status": "ok"},
            {"agent": "cardiology", "tool": "evaluate_risk", "status": "error", "result": "handler not found"},
        ]
        outcomes = d._build_outcomes(executions)
        assert len(outcomes) == 2
        assert outcomes[0].passed
        assert not outcomes[1].passed
        assert outcomes[1].failure_message is not None

    def test_simple_diagnosis(self):
        d = HarnessDiagnosis()
        outcome = DiagnosisOutcome(
            case_id="test:tool#0",
            split="train",
            stratum="handler_error",
            status="error",
            failure_message="Agent 'test' tool 'broken' failed: ImportError: No module 'foo'",
        )
        diag = d._simple_diagnosis(outcome)
        assert diag is not None
        assert "analysis" in diag
        assert len(diag["analysis"]) > 0
        analysis = diag["analysis"][0]
        assert analysis["terminal_cause"] in (
            "missing_handler",
            "handler_error",
            "missing_dependency",
            "agent_timeout",
            "guard_missing",
            "citation_missing",
            "role_missing",
            "stage_incomplete",
        )
        assert analysis["criticality"] == "root_cause"

    def test_build_causal_clusters(self):
        d = HarnessDiagnosis()
        outcomes = [
            DiagnosisOutcome(
                case_id="agent1:tool1#1", split="train", stratum="handler", status="error",
                failure_message="ImportError in handler",
            ),
            DiagnosisOutcome(
                case_id="agent1:tool1#2", split="train", stratum="handler", status="error",
                failure_message="ImportError in handler",
            ),
            DiagnosisOutcome(
                case_id="agent2:tool2#3", split="train", stratum="guard", status="error",
                failure_message="Guard missing",
            ),
            DiagnosisOutcome(
                case_id="agent3:tool3#4", split="train", stratum="ok", status="ok",
            ),
        ]
        clusters = d._build_causal_clusters(outcomes)
        assert len(clusters) > 0
        for c in clusters:
            assert "signature" in c
            assert "cases" in c

    def test_write_causal_brief(self):
        d = HarnessDiagnosis()
        outcomes = [
            DiagnosisOutcome(case_id="pass1", split="train", stratum="ok", status="ok"),
            DiagnosisOutcome(case_id="fail1", split="train", stratum="handler", status="error"),
        ]
        clusters = d._build_causal_clusters(outcomes)
        brief = d._write_causal_brief(outcomes, clusters)
        assert "Self-Harness Diagnosis Brief" in brief
        assert "pass1" in brief
        assert "fail1" in brief

    def test_run_no_llm(self):
        d = HarnessDiagnosis(llm=None)
        result = d.run(executions=[])
        assert "format" in result
        assert result["total_executions"] == 0

    def test_run_with_failures(self):
        d = HarnessDiagnosis(llm=None)
        executions = [
            {"agent": "pharmacy", "tool": "assess", "status": "error", "result": "ImportError"},
            {"agent": "pharmacy", "tool": "check", "status": "error", "result": "ImportError"},
        ]
        result = d.run(executions)
        assert result["failed_cases"] == 2
        assert result["clusters_count"] >= 1


class TestNormalizeTrace:
    def test_normalize_empty(self):
        steps = normalize_trace_steps([])
        assert len(steps) == 0

    def test_normalize_single_ai_message(self):
        messages = [
            {"type": "human", "content": "Hello"},
            {"type": "ai", "content": "Hi there"},
        ]
        steps = normalize_trace_steps(messages)
        assert len(steps) == 1
        assert steps[0].step_id == 1
        assert steps[0].kind == "explore"

    def test_normalize_with_tool_calls(self):
        messages = [
            {"type": "human", "content": "Do X"},
            {"type": "ai", "content": "Let me write that.",
             "tool_calls": [{"name": "write_file", "args": {"path": "test.py"}}]},
            {"type": "tool", "name": "write_file", "content": "OK"},
        ]
        steps = normalize_trace_steps(messages)
        assert len(steps) == 1
        assert steps[0].kind == "change"
        assert len(steps[0].tool_calls) == 1
        assert len(steps[0].tool_results) == 1

    def test_normalize_multiple_steps(self):
        messages = [
            {"type": "human", "content": "Task"},
            {"type": "ai", "content": "Step 1"},
            {"type": "ai", "content": "Step 2",
             "tool_calls": [{"name": "edit_file", "args": {}}]},
            {"type": "tool", "name": "edit_file", "content": "done"},
            {"type": "ai", "content": "Step 3"},
        ]
        steps = normalize_trace_steps(messages)
        assert len(steps) == 3
        assert steps[0].kind == "explore"
        assert steps[1].kind == "change"
        assert steps[2].kind == "explore"

    def test_build_stage_records(self):
        steps = [
            NormalizedStep(step_id=1, kind="explore", assistant_summary="a", tool_calls=[], tool_results=[]),
            NormalizedStep(step_id=2, kind="change", assistant_summary="b", tool_calls=[], tool_results=[]),
            NormalizedStep(step_id=3, kind="explore", assistant_summary="c", tool_calls=[], tool_results=[]),
        ]
        records = build_stage_records(steps)
        assert len(records) == 2
        assert records[0].boundary_type == "change"
        assert records[0].boundary_step_id == 2
        assert records[1].boundary_type == "explore"
        assert records[1].boundary_step_id == 3


# ══════════════════════════════════════════════════════════════════
# HarnessProposer Tests
# ══════════════════════════════════════════════════════════════════


class TestHarnessProposer:
    def test_init(self):
        p = HarnessProposer()
        assert p.route_count == 4
        assert p.root.exists()

    def test_init_custom_route_count(self):
        p = HarnessProposer(route_count=6)
        assert p.route_count == 6

    def test_generate_rule_based(self):
        p = HarnessProposer(llm=None, route_count=3)
        bundle = p.generate("Test diagnosis brief")
        assert isinstance(bundle, ProposalBundle)
        assert len(bundle.proposals) == 3

    def test_proposals_are_diverse(self):
        p = HarnessProposer(llm=None, route_count=5)
        bundle = p.generate("Test diagnosis")
        families = {proposal.mechanism_family for proposal in bundle.proposals}
        assert len(families) >= 3

    def test_editable_surface_creation(self):
        s = EditableSurface(
            name="pharmacy",
            kind="agent_yaml",
            target="/path/to/pharmacy.yaml",
            current_value="name: pharmacy",
            filename="pharmacy.yaml",
        )
        d = s.to_prompt_dict()
        assert d["name"] == "pharmacy"
        assert d["kind"] == "agent_yaml"

    def test_proposal_to_dict(self):
        p = Proposal(
            proposal_id="fix-guard",
            title="Add guard triggers",
            selected_cluster="missing_guard",
            selected_surface="guard_triggers",
            mechanism="Add triggers",
            mechanism_family="guard_rule",
            exact_hook="triggers",
            why_distinct="Unique",
            net_gain_hypothesis="Better safety",
            regression_guard="No regression",
            summary="Summary text",
            final_message="Done",
            candidate_values={"triggers": ["诊断决策"]},
        )
        d = p.to_dict()
        assert d["proposal_id"] == "fix-guard"
        assert d["mechanism_family"] == "guard_rule"
        assert "candidate_values" in d

    def test_auto_discover_surfaces(self):
        p = HarnessProposer()
        surfaces = p._auto_discover_surfaces()
        assert isinstance(surfaces, list)

    def test_all_mechanism_families_have_proposals(self):
        p = HarnessProposer(llm=None)
        for family in MECHANISM_FAMILIES:
            proposal = p._rule_based_proposal("test", [], 0, family)
            assert proposal.mechanism_family == family
            assert proposal.proposal_id != ""

    def test_all_hook_families_mapped(self):
        for family in MECHANISM_FAMILIES:
            assert family in HOOKS_BY_FAMILY
            assert len(HOOKS_BY_FAMILY[family]) > 0


# ══════════════════════════════════════════════════════════════════
# HarnessAcceptance Tests
# ══════════════════════════════════════════════════════════════════


class TestHarnessAcceptance:
    def test_init(self):
        a = HarnessAcceptance()
        assert a.root.exists()
        assert a.snapshot_dir.exists() is False or a.snapshot_dir

    def test_evaluate_improvement(self):
        a = HarnessAcceptance()
        baseline = {"train": 70, "heldout": 65}
        candidate = {"train": 75, "heldout": 65}
        result = a.evaluate(baseline, candidate)
        assert result["accepted"]
        assert result["decision"] == "accepted"

    def test_evaluate_rejected_drop(self):
        a = HarnessAcceptance()
        baseline = {"train": 70, "heldout": 65}
        candidate = {"train": 65, "heldout": 65}
        result = a.evaluate(baseline, candidate)
        assert not result["accepted"]
        assert result["decision"] == "rejected"

    def test_evaluate_rejected_no_improvement(self):
        a = HarnessAcceptance()
        baseline = {"train": 70, "heldout": 65}
        candidate = {"train": 70, "heldout": 65}
        result = a.evaluate(baseline, candidate)
        assert not result["accepted"]

    def test_evaluate_improved_both(self):
        a = HarnessAcceptance()
        baseline = {"train": 70, "heldout": 65}
        candidate = {"train": 75, "heldout": 70}
        result = a.evaluate(baseline, candidate)
        assert result["accepted"]

    def test_evaluate_custom_splits(self):
        a = HarnessAcceptance()
        baseline = {"a": 80, "b": 90}
        candidate = {"a": 85, "b": 90}
        result = a.evaluate(baseline, candidate, splits=("a", "b"))
        assert result["accepted"]

    def test_evaluate_missing_split(self):
        a = HarnessAcceptance()
        baseline = {"train": 70}
        candidate = {"train": 75, "heldout": 70}
        result = a.evaluate(baseline, candidate)
        assert result["accepted"]

    def test_build_reason_accepted(self):
        a = HarnessAcceptance()
        reason = a._build_reason(True, ["train"], [])
        assert "accepted" in reason
        assert "train" in reason

    def test_build_reason_rejected(self):
        a = HarnessAcceptance()
        reason = a._build_reason(False, [], ["train"])
        assert "rejected" in reason
        assert "train" in reason


class TestScoreSnapshot:
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ss = ScoreSnapshot(pathlib.Path(tmpdir) / "snapshots")
            assert ss.dir.exists()

    def test_record_and_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ss = ScoreSnapshot(pathlib.Path(tmpdir) / "snapshots")
            ss.record("test", {"metric": 85}, {"info": "v1"})

            latest = ss.latest("test")
            assert latest.get("name") == "test"
            assert latest.get("scores", {}).get("metric") == 85

    def test_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ss = ScoreSnapshot(pathlib.Path(tmpdir) / "snapshots")
            ss.record("test", {"metric": 70})
            ss.record("test", {"metric": 80})
            ss.record("test", {"metric": 90})

            hist = ss.history("test")
            assert len(hist) == 3

    def test_trend_improving(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ss = ScoreSnapshot(pathlib.Path(tmpdir) / "snapshots")
            ss.record("test", {"metric": 70})
            ss.record("test", {"metric": 80})
            ss.record("test", {"metric": 90})

            trend = ss.trend("test", "metric")
            assert trend == "improving"

    def test_trend_declining(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ss = ScoreSnapshot(pathlib.Path(tmpdir) / "snapshots")
            ss.record("test", {"metric": 90})
            ss.record("test", {"metric": 80})
            ss.record("test", {"metric": 70})

            trend = ss.trend("test", "metric")
            assert trend == "declining"

    def test_trend_stable_single(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ss = ScoreSnapshot(pathlib.Path(tmpdir) / "snapshots")
            ss.record("test", {"metric": 85})

            trend = ss.trend("test", "metric")
            assert trend == "stable"

    def test_latest_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ss = ScoreSnapshot(pathlib.Path(tmpdir) / "snapshots")
            result = ss.latest("nonexistent", default={"default": True})
            assert result.get("default") is True


# ══════════════════════════════════════════════════════════════════
# DiagnosisConfig Tests
# ══════════════════════════════════════════════════════════════════


class TestDiagnosisConfig:
    def test_defaults(self):
        config = DiagnosisConfig()
        assert config.model_reference is None
        assert config.timeout_s == 180.0
        assert config.retries == 1

    def test_custom(self):
        config = DiagnosisConfig(model_reference="test-model", timeout_s=60, retries=3)
        d = config.to_dict()
        assert d["model_reference"] == "test-model"
        assert d["timeout_s"] == 60
        assert d["retries"] == 3
