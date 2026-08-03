"""Unit tests for debate module — declaration extraction, conflict detection, moderator, engine."""
import pytest

from haip.debate.conflict import Conflict, ConflictDetector
from haip.debate.declaration import Declaration, DeclarationLayer
from haip.debate.engine import DebateContext, DebateEngine
from haip.debate.moderator import Moderator, ModeratorVote
from haip.debate.protocol import DebateProtocol


class TestDeclaration:
    def test_dataclass_fields(self):
        d = Declaration(id="D1", agent="ortho", metric="surgical_timing", value="urgent",
                        category="urgent", evidence="NICE NG37", confidence=0.9)
        assert d.agent == "ortho"
        assert d.category == "urgent"
        assert d.confidence == 0.9

    def test_to_dict(self):
        d = Declaration(id="D1", agent="cardio", metric="risk_level", value="high",
                        category="high", evidence="ACC/AHA", confidence=0.8)
        result = d.to_dict()
        assert result["id"] == "D1"
        assert result["agent"] == "cardio"
        assert result["confidence"] == 0.8

    def test_default_values(self):
        d = Declaration(id="D1", agent="test", metric="unknown", value="?",
                        category="unknown")
        assert d.evidence == ""
        assert d.confidence == 0.5


class TestDeclarationLayer:
    def test_available_false_without_llm(self):
        layer = DeclarationLayer(llm=None)
        assert not layer.available

    def test_extract_empty_text(self):
        layer = DeclarationLayer(llm=None)
        result = layer.extract("ortho", "")
        assert len(result) == 1
        assert result[0].value == "unable_to_extract"

    def test_extract_batch(self):
        layer = DeclarationLayer(llm=None)
        outputs = {"ortho": "", "cardio": ""}
        result = layer.extract_batch(outputs)
        assert len(result) == 2


class TestConflictDetector:
    def test_no_conflict_when_same_category_value(self):
        detector = ConflictDetector()
        decls = [
            Declaration(id="D1", agent="A", metric="surgical_timing", value="urgent", category="urgent"),
            Declaration(id="D2", agent="B", metric="surgical_timing", value="urgent", category="urgent"),
        ]
        conflicts = detector.detect(decls)
        assert len(conflicts) == 0

    def test_conflict_different_categories(self):
        detector = ConflictDetector()
        decls = [
            Declaration(id="D1", agent="A", metric="surgical_timing", value="urgent", category="urgent"),
            Declaration(id="D2", agent="B", metric="surgical_timing", value="elective", category="elective"),
        ]
        conflicts = detector.detect(decls)
        assert len(conflicts) == 1
        assert conflicts[0].agent_a == "A"
        assert conflicts[0].agent_b == "B"

    def test_conflict_risk_level_high_vs_low(self):
        detector = ConflictDetector()
        decls = [
            Declaration(id="D1", agent="A", metric="risk_level", value="high", category="high"),
            Declaration(id="D2", agent="B", metric="risk_level", value="low", category="low"),
        ]
        conflicts = detector.detect(decls)
        assert len(conflicts) == 1
        assert conflicts[0].metric == "risk_level"

    def test_no_conflict_different_metrics(self):
        detector = ConflictDetector()
        decls = [
            Declaration(id="D1", agent="A", metric="surgical_timing", value="urgent", category="urgent"),
            Declaration(id="D2", agent="B", metric="risk_level", value="high", category="high"),
        ]
        conflicts = detector.detect(decls)
        assert len(conflicts) == 0

    def test_treatment_avoid_vs_recommend(self):
        detector = ConflictDetector()
        decls = [
            Declaration(id="D1", agent="A", metric="treatment", value="use drug X", category="recommend"),
            Declaration(id="D2", agent="B", metric="treatment", value="avoid drug X", category="avoid"),
        ]
        conflicts = detector.detect(decls)
        assert len(conflicts) == 1

    def test_unknown_category_ignored(self):
        detector = ConflictDetector()
        decls = [
            Declaration(id="D1", agent="A", metric="surgical_timing", value="?", category="unknown"),
            Declaration(id="D2", agent="B", metric="surgical_timing", value="urgent", category="urgent"),
        ]
        conflicts = detector.detect(decls)
        assert len(conflicts) == 0

    def test_conflict_summary(self):
        c = Conflict(decl_a_id="D1", decl_b_id="D2", agent_a="A", agent_b="B",
                     metric="surgical_timing", value_a="urgent", value_b="elective",
                     category_a="urgent", category_b="elective")
        summary = c.summary()
        assert "A" in summary and "B" in summary
        assert "urgent" in summary and "elective" in summary


class TestDebateProtocol:
    def test_declarations_text(self):
        protocol = DebateProtocol()
        decls = [Declaration(id="D1", agent="A", metric="risk", value="high", category="high")]
        text = protocol.declarations_text(decls)
        assert "[D1]" in text
        assert "A" in text

    def test_declarations_text_filter_by_agent(self):
        protocol = DebateProtocol()
        decls = [
            Declaration(id="D1", agent="A", metric="risk", value="high", category="high"),
            Declaration(id="D2", agent="B", metric="risk", value="low", category="low"),
        ]
        text = protocol.declarations_text(decls, include_agent="A")
        assert "D1" in text
        assert "D2" not in text

    def test_declarations_text_empty(self):
        protocol = DebateProtocol()
        text = protocol.declarations_text([])
        assert "无声明" in text

    def test_conflicts_text(self):
        protocol = DebateProtocol()
        c = Conflict(decl_a_id="D1", decl_b_id="D2", agent_a="A", agent_b="B",
                     metric="surgical_timing", value_a="urgent", value_b="elective",
                     category_a="urgent", category_b="elective")
        text = protocol.conflicts_text([c])
        assert "A" in text and "B" in text
        assert "检测到以下冲突" in text

    def test_conflicts_text_empty(self):
        protocol = DebateProtocol()
        text = protocol.conflicts_text([])
        assert "未检测到冲突" in text

    def test_compact_declarations(self):
        protocol = DebateProtocol()
        decls = [Declaration(id="D1", agent="A", metric="risk", value="high", category="high")]
        json_str = protocol.compact_declarations(decls)
        assert '"D1"' in json_str

    def test_build_debate_prompt(self):
        protocol = DebateProtocol()
        decls = [Declaration(id="D1", agent="A", metric="risk", value="high", category="high")]
        conflicts = [Conflict(decl_a_id="D1", decl_b_id="D2", agent_a="A", agent_b="B",
                              metric="risk", value_a="high", value_b="low",
                              category_a="high", category_b="low")]
        prompt = protocol.build_debate_prompt("A", "骨科", [decls[0]], decls, conflicts)
        assert "骨科" in prompt
        assert "D1" in prompt

    def test_synthesize_final_consensus(self):
        protocol = DebateProtocol()
        decls = [Declaration(id="D1", agent="A", metric="risk", value="high", category="high")]
        result = protocol.synthesize_final("建议紧急手术", decls, True, False)
        assert "MDT 多学科会诊结论" in result
        assert "建议紧急手术" in result
        assert "一致裁决" in result

    def test_synthesize_final_appeal(self):
        protocol = DebateProtocol()
        result = protocol.synthesize_final("建议手术", [], False, True)
        assert "上诉裁决" in result


class TestModerator:
    def test_available_false_without_llm(self):
        moderator = Moderator(llm=None)
        assert not moderator.available

    def test_judge_without_llm_returns_empty(self):
        moderator = Moderator(llm=None)
        a, b = moderator.judge("test", "")
        assert not a.consensus
        assert not b.consensus

    def test_appeal_without_llm_returns_first(self):
        moderator = Moderator(llm=None)
        v_a = ModeratorVote(consensus=True, verdict="agree")
        v_b = ModeratorVote(consensus=False, verdict="disagree")
        result = moderator.appeal(v_a, v_b, "test")
        assert result.consensus
        assert result.verdict == "agree"

    def test_parse_json_with_markdown(self):
        text = '```json\n{"consensus": true, "verdict": "test"}\n```'
        result = Moderator._parse_json(text)
        assert result["consensus"] is True
        assert result["verdict"] == "test"

    def test_parse_json_plain(self):
        result = Moderator._parse_json('{"consensus": false, "verdict": "no"}')
        assert result["consensus"] is False

    def test_moderator_vote_to_dict(self):
        v = ModeratorVote(consensus=True, verdict="v", rationale="r",
                          risk_assessment="low", resolved_conflicts=["c1"],
                          critical_concerns=["cc1"])
        d = v.to_dict()
        assert d["consensus"] is True
        assert d["verdict"] == "v"


class TestDebateEngine:
    def test_engine_without_llm(self):
        engine = DebateEngine(llm=None)
        ctx = engine.run("P001", "query", {"ortho": "urgent", "cardio": "elective"}, {})
        assert ctx.patient_id == "P001"
        assert len(ctx.agents) == 2

    def test_engine_no_outputs(self):
        engine = DebateEngine(llm=None)
        ctx = engine.run("P001", "query", {}, {})
        assert not ctx.declarations
        assert not ctx.debate_triggered

    def test_debate_context_defaults(self):
        ctx = DebateContext()
        assert ctx.patient_id == ""
        assert ctx.agents == []
        assert not ctx.debate_triggered

    def test_aggregate_no_conflict(self):
        engine = DebateEngine(llm=None)
        decls = [
            Declaration(id="D1", agent="A", metric="risk", value="high", category="high"),
            Declaration(id="D2", agent="B", metric="risk", value="high", category="high"),
        ]
        ctx = DebateContext(patient_id="P001", declarations=decls)
        result = engine._aggregate_no_conflict(ctx)
        assert "一致同意" in result
        assert "A" in result


class TestDebateModuleImports:
    def test_init_exports(self):
        from haip.debate import (
            Conflict,
            ConflictDetector,
            DebateContext,
            DebateEngine,
            DebateProtocol,
            Declaration,
            DeclarationLayer,
            Moderator,
            ModeratorVote,
        )
        assert Declaration is not None
        assert ConflictDetector is not None
        assert DebateEngine is not None
        assert Moderator is not None
        assert DebateProtocol is not None
