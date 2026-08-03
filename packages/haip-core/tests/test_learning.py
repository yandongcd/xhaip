"""Unit tests for learning module — collector, store, analysis, approval, rollout."""
import time

import pytest

from haip.learning.analysis import AnalysisEngine, AnalysisResult
from haip.learning.approval import ApprovalGate
from haip.learning.collector import FeedbackCollector, FeedbackEvent
from haip.learning.improve import ImprovementEngine, LearningSuggestion
from haip.learning.rollout import RolloutManager, RolloutState
from haip.learning.store import FeedbackStore


class TestFeedbackEvent:
    def test_default_values(self):
        e = FeedbackEvent()
        assert e.agent == ""
        assert e.event_type == ""
        assert e.severity == "info"

    def test_to_dict(self):
        e = FeedbackEvent(agent="ortho", patient_id="P001", event_type="guard_pass",
                          event_data={"passed": True}, severity="info")
        d = e.to_dict()
        assert d["agent"] == "ortho"
        assert d["event_type"] == "guard_pass"
        assert isinstance(d["timestamp"], float)

    def test_source_tags(self):
        e = FeedbackEvent(agent="test", event_type="guard_fail",
                          source_tags={"rag_used": True, "guard_layer_failed": 3})
        d = e.to_dict()
        import json
        tags = json.loads(d["source_tags"])
        assert tags["rag_used"] is True


class TestFeedbackCollector:
    def test_disabled_without_store(self):
        collector = FeedbackCollector(store=None)
        assert not collector.enabled

    def test_disable_enable(self):
        collector = FeedbackCollector(store=None)
        collector.disable()
        assert not collector.enabled
        collector.enable()
        assert not collector.enabled  # store is None

    def test_record_without_store_does_not_raise(self):
        collector = FeedbackCollector(store=None)
        e = FeedbackEvent(agent="test", event_type="test")
        collector.record(e)  # should not raise
        assert not collector.enabled  # store=None → disabled, no-op

    def test_record_guard_pass(self):
        store = FeedbackStore(db_path=":memory:")
        assert store.connect()
        collector = FeedbackCollector(store=store)
        collector.record_guard("ortho", "P001", True)
        stats = store.agent_stats("ortho")
        assert stats["guard_pass"] >= 1
        store.close()

    def test_record_guard_fail(self):
        store = FeedbackStore(db_path=":memory:")
        assert store.connect()
        collector = FeedbackCollector(store=store)
        collector.record_guard("ortho", "P001", False, failure_layer=2, failure_code="L2_CITATION")
        stats = store.agent_stats("ortho")
        assert stats["guard_fail"] >= 1
        store.close()

    def test_record_hitl(self):
        store = FeedbackStore(db_path=":memory:")
        assert store.connect()
        collector = FeedbackCollector(store=store)
        collector.record_hitl("ortho", "P001", "medication_error", original="wrong", corrected="right")
        stats = store.agent_stats("ortho")
        assert stats["hitl"] >= 1
        store.close()

    def test_record_debate(self):
        store = FeedbackStore(db_path=":memory:")
        assert store.connect()
        collector = FeedbackCollector(store=store)
        collector.record_debate("ortho", "P001", agent_won=True, consensus=True)
        stats = store.agent_stats("ortho")
        assert stats["debate_wins"] >= 1
        store.close()

    def test_record_citation_new(self):
        store = FeedbackStore(db_path=":memory:")
        assert store.connect()
        collector = FeedbackCollector(store=store)
        collector.record_citation_new("ortho", "NICE NG37 §4", trust_level="T3")
        stats = store.agent_stats("ortho")
        assert stats["citations_new"] >= 1
        store.close()

    def test_record_route(self):
        store = FeedbackStore(db_path=":memory:")
        assert store.connect()
        collector = FeedbackCollector(store=store)
        collector.record_route("ortho", "hip fracture timing", guard_pass=True, latency_ms=250.0)
        stats = store.agent_stats("ortho")
        assert stats["total_events"] >= 1
        store.close()


class TestFeedbackStore:
    def test_connect_memory(self):
        store = FeedbackStore(db_path=":memory:")
        assert store.connect()
        assert store.ready
        store.close()
        assert not store.ready

    def test_insert_and_query(self):
        store = FeedbackStore(db_path=":memory:")
        store.connect()
        e = FeedbackEvent(agent="cardio", patient_id="P002", event_type="guard_pass",
                          event_data={"score": 0.95})
        store.insert_event(e)
        results = store.query_recent(agent="cardio", limit=10)
        assert len(results) >= 1
        assert results[0]["agent"] == "cardio"
        store.close()

    def test_agent_stats(self):
        store = FeedbackStore(db_path=":memory:")
        store.connect()
        collector = FeedbackCollector(store=store)
        collector.record_guard("test", "P001", True)
        collector.record_guard("test", "P002", False, failure_layer=1)
        stats = store.agent_stats("test", days=30)
        assert stats["total_events"] >= 2
        assert "guard_pass_rate" in stats
        store.close()

    def test_compute_ccs(self):
        store = FeedbackStore(db_path=":memory:")
        store.connect()
        collector = FeedbackCollector(store=store)
        for _ in range(10):
            collector.record_guard("test", "P001", True)
        ccs = store.compute_ccs("test", days=7)
        assert 0.0 <= ccs <= 1.0
        store.close()

    def test_ccs_zero_events(self):
        store = FeedbackStore(db_path=":memory:")
        store.connect()
        ccs = store.compute_ccs("nonexistent", days=7)
        assert ccs == 0.5
        store.close()

    def test_time_decayed_weight(self):
        store = FeedbackStore(db_path=":memory:")
        now = time.time()
        assert store.time_decayed_weight(now) == 1.0
        assert store.time_decayed_weight(now - 95 * 86400) == 0.5
        assert store.time_decayed_weight(now - 185 * 86400) == 0.25
        assert store.time_decayed_weight(now - 400 * 86400) == 0.0

    def test_purge_old(self):
        store = FeedbackStore(db_path=":memory:")
        store.connect()
        store.insert_event(FeedbackEvent(
            agent="old", event_type="guard_pass", timestamp=time.time() - 400 * 86400))
        store.purge_old(days=180)
        remaining = store.query_recent(agent="old")
        assert remaining == [], f"expected purge, got {remaining}"
        store.close()


class TestAnalysisEngine:
    def test_analyze_empty_store(self):
        store = FeedbackStore(db_path=":memory:")
        store.connect()
        engine = AnalysisEngine(store)
        results = engine.analyze(["test_agent"])
        assert len(results) == 1
        assert results[0].agent == "test_agent"
        assert results[0].ccs_current == 0.5
        store.close()

    def test_analyze_with_data(self):
        store = FeedbackStore(db_path=":memory:")
        store.connect()
        collector = FeedbackCollector(store=store)
        for _ in range(5):
            collector.record_guard("ortho", "P001", True)
        for _ in range(1):
            collector.record_guard("ortho", "P002", False, failure_layer=2, failure_code="L2_CITATION")
            collector.record_citation_new("ortho", "ref1")

        engine = AnalysisEngine(store)
        results = engine.analyze(["ortho"])
        assert len(results) == 1
        assert results[0].ccs_current > 0
        assert len(results[0].top_failure_reasons) >= 1
        assert results[0].citations_pending is not None
        store.close()

    def test_age_seconds(self):
        store = FeedbackStore(db_path=":memory:")
        engine = AnalysisEngine(store)
        assert engine.age_seconds > 0
        engine.analyze(["test"])
        assert engine.age_seconds < 1


class TestLearningSuggestion:
    def test_dataclass_defaults(self):
        s = LearningSuggestion()
        assert s.status == "pending"
        assert s.risk_level == "low"
        assert s.scope == "agent_only"

    def test_to_dict(self):
        s = LearningSuggestion(id="S1", type="citation_new", target="ortho",
                               suggestion={"ref": "NICE NG37"})
        d = s.to_dict()
        assert d["id"] == "S1"
        assert d["type"] == "citation_new"
        assert d["target"] == "ortho"


class TestImprovementEngine:
    def test_generate_from_analysis(self):
        result = AnalysisResult(agent="ortho", ccs_current=0.75, ccs_change_7d=-0.1,
                                top_failure_reasons=["L2_CITATION"],
                                citations_pending=["ref1", "ref2"])
        engine = ImprovementEngine()
        suggestions = engine.generate([result], ["ortho"])
        assert len(suggestions) >= 1

    def test_empty_results(self):
        engine = ImprovementEngine()
        suggestions = engine.generate([], [])
        assert suggestions == []


class TestApprovalGate:
    def test_classify_auto(self):
        gate = ApprovalGate()
        s = LearningSuggestion(type="citation_new", risk_level="low", scope="agent_only")
        assert gate.classify(s) == "auto"

    def test_classify_batch(self):
        gate = ApprovalGate()
        s = LearningSuggestion(type="rule_flag", risk_level="medium", scope="agent_group")
        assert gate.classify(s) == "batch"

    def test_classify_per_item(self):
        gate = ApprovalGate()
        s = LearningSuggestion(type="prompt_optimize", risk_level="high", scope="global")
        assert gate.classify(s) == "per_item"

    def test_not_fatigued_initially(self):
        gate = ApprovalGate()
        assert not gate.is_fatigued()

    def test_fatigue_detection(self):
        gate = ApprovalGate()
        for _ in range(5):
            gate.record_review("S1", "approved", review_seconds=1.0)
        assert gate.is_fatigued()

    def test_not_fatigued_with_slow_review(self):
        gate = ApprovalGate()
        for _ in range(5):
            gate.record_review("S1", "approved", review_seconds=10.0)
        assert not gate.is_fatigued()


class TestRolloutManager:
    def test_start_rollout(self):
        gate = ApprovalGate()
        manager = RolloutManager(gate)
        s = LearningSuggestion(id="S1", type="citation_new")
        state = manager.start_rollout(s, baseline_ccs=0.8)
        assert state.suggestion_id == "S1"
        assert state.status == "rolling_out"
        assert state.baseline_ccs == 0.8

    def test_rollout_state_drop_trigger(self):
        state = RolloutState(baseline_ccs=0.8)
        state.ccs_history = [(time.time(), 0.75)]  # 6.25% drop
        from haip.learning.rollout import CCS_DROP_THRESHOLD
        current = 0.75
        drop_pct = (state.baseline_ccs - current) / state.baseline_ccs
        assert drop_pct > CCS_DROP_THRESHOLD

    def test_rollout_state_no_drop(self):
        state = RolloutState(baseline_ccs=0.8)
        current = 0.79  # 1.25% drop
        from haip.learning.rollout import CCS_DROP_THRESHOLD
        drop_pct = (state.baseline_ccs - current) / state.baseline_ccs
        assert drop_pct < CCS_DROP_THRESHOLD


class TestLearningModuleImports:
    def test_init_exports(self):
        from haip.learning import (
            AnalysisEngine,
            ApprovalGate,
            FeedbackCollector,
            FeedbackEvent,
            FeedbackStore,
            ImprovementEngine,
            LearningSuggestion,
            RolloutManager,
        )
        assert FeedbackCollector is not None
        assert FeedbackStore is not None
        assert AnalysisEngine is not None
        assert ImprovementEngine is not None
        assert ApprovalGate is not None
        assert RolloutManager is not None
