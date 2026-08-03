"""Unit tests for pipeline module — UnifiedPipeline and Budget manager."""
import pytest

from haip.pipeline import UnifiedPipeline
from haip.pipeline.budget import CONTEXT_BUDGET, DEFAULT_ALLOCATIONS, ContextBudget


class TestContextBudget:
    def test_default_allocations(self):
        budget = ContextBudget()
        assert budget.remaining > 0
        assert budget.remaining < CONTEXT_BUDGET

    def test_allocate_within_limit(self):
        budget = ContextBudget()
        allocated = budget.allocate("rag_injection", 500)
        assert allocated == 500

    def test_allocate_exceeds_limit(self):
        budget = ContextBudget()
        allocated = budget.allocate("rag_injection", 2000)
        assert allocated == 1000  # capped at DEFAULT_ALLOCATIONS["rag_injection"]

    def test_check_overflow_false(self):
        budget = ContextBudget()
        assert not budget.check_overflow()

    def test_check_overflow_true(self):
        budget = ContextBudget(total=1000)
        budget.resize("system_prompt_base", 2000)
        assert budget.check_overflow()

    def test_suggest_truncation(self):
        budget = ContextBudget(total=1000)
        budget.resize("conversation_history", 800)
        budget.resize("rag_injection", 800)
        suggestion = budget.suggest_truncation()
        assert suggestion == "conversation_history"  # first in priority

    def test_suggest_truncation_none(self):
        budget = ContextBudget()
        suggestion = budget.suggest_truncation()
        assert suggestion is None

    def test_resize(self):
        budget = ContextBudget()
        budget.resize("rag_injection", 500)
        allocated = budget.allocate("rag_injection", 1000)
        assert allocated == 500

    def test_snapshot(self):
        budget = ContextBudget()
        snap = budget.snapshot()
        assert "total" in snap
        assert "allocated" in snap
        assert "remaining" in snap
        assert "overflow" in snap
        assert not snap["overflow"]


class TestUnifiedPipeline:
    def test_execute_empty_agents(self):
        pipeline = UnifiedPipeline()
        result = pipeline.execute("P001", "test query", [])
        assert result["patient_id"] == "P001"
        assert "phase_outputs" in result
        assert result["feedback_recorded"] is True  # succeeds but records nothing

    def test_execute_returns_structure(self):
        pipeline = UnifiedPipeline()
        result = pipeline.execute("P001", "query", ["test_agent"])
        assert "patient_id" in result
        assert "phase_outputs" in result
        assert "final_output" in result
        assert "guard_result" in result
        assert "feedback_recorded" in result

    def test_run_rag_unavailable(self):
        pipeline = UnifiedPipeline()
        result = pipeline._run_rag("test query")
        # RAG may or may not be available depending on environment
        assert result is None or isinstance(result, dict)

    def test_run_agent_batch_empty(self):
        pipeline = UnifiedPipeline()
        result = pipeline._run_agent_batch([], "query", None)
        assert result == {}

    def test_run_debate_maybe_no_agents(self):
        pipeline = UnifiedPipeline()
        result = pipeline._run_debate_maybe("P001", "query", [], {})
        assert result is None

    def test_run_guard_error_handling(self):
        pipeline = UnifiedPipeline()
        result = pipeline._run_guard("test output", {})
        # should not raise, returns error state
        assert isinstance(result, dict)
        assert "passed" in result or "blocked" in result

    def test_run_feedback_no_store(self):
        pipeline = UnifiedPipeline()
        result = pipeline._run_feedback("P001", [], {})
        assert isinstance(result, bool)


class TestPipelineModule:
    def test_budget_constants(self):
        assert CONTEXT_BUDGET == 28000
        assert "rag_injection" in DEFAULT_ALLOCATIONS
        assert "debate_context" in DEFAULT_ALLOCATIONS
        assert DEFAULT_ALLOCATIONS["rag_injection"] == 1000
        assert DEFAULT_ALLOCATIONS["debate_context"] == 1500
