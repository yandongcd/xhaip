"""X1: Unified pipeline — orchestrates RAG → Agent reasoning → Debate → Guard → Feedback.

Single entry point for coordinated agent execution across all xhaip capabilities.
Handles graceful degradation when components are unavailable.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class UnifiedPipeline:
    """Coordinated execution of RAG → Agent → Debate → Guard → Feedback."""

    def execute(self, patient_id: str, query: str, agents: list[str]) -> dict:
        """Full unified pipeline for a multi-agent request.

        Phase 1: RAG injection (enrich agent prompts)
        Phase 2: Agent reasoning (call_batch)
        Phase 3: Declaration + Conflict + Debate (if debate configured)
        Phase 4: Guard verification (L1-L4, once on final output)
        Phase 5: Feedback collection (record all signals)
        """
        result = {
            "patient_id": patient_id,
            "phase_outputs": {},
            "final_output": None,
            "guard_result": None,
            "feedback_recorded": False,
        }

        # Phase 1: RAG
        rag_context = self._run_rag(query)
        result["phase_outputs"]["rag"] = rag_context

        # Phase 2: Agent reasoning (delegated to existing A2A call_batch)
        agent_outputs = self._run_agent_batch(agents, query, rag_context)
        result["phase_outputs"]["agent"] = agent_outputs

        # Phase 3: Debate
        debate_result = self._run_debate_maybe(patient_id, query, agents, agent_outputs)
        result["phase_outputs"]["debate"] = debate_result

        final_output = debate_result.get("verdict") if debate_result else agent_outputs
        result["final_output"] = final_output

        # Phase 4: Guard
        guard_result = self._run_guard(final_output, agent_outputs)
        result["guard_result"] = guard_result

        # Phase 5: Feedback
        result["feedback_recorded"] = self._run_feedback(
            patient_id, agents, result
        )

        return result

    # ── Phase implementations ──

    def _run_rag(self, query: str) -> dict | None:
        try:
            from haip.rag.pipeline import RAGPipeline
            if not RAGPipeline.ready():
                return None
            # RAGPipeline requires a store — defer to web_server init
            return {"status": "rag_available", "query": query}
        except ImportError:
            return None

    def _run_agent_batch(self, agents: list[str], query: str, rag_context: dict | None):
        from haip.a2a import call_batch, internal_permission_context
        tasks = [{"agent": a, "tool": "default", "params": {"query": query}} for a in agents]
        # 引擎内部编排: 身份在入口层校验, 显式内部上下文
        results = call_batch(tasks, perm_ctx=internal_permission_context())
        return {a: r for a, r in zip(agents, results)} if results else {}

    def _run_debate_maybe(self, patient_id: str, query: str,
                          agents: list[str], agent_outputs: dict):
        debate_agents = set()
        for a in agents:
            try:
                from haip.agent import get as get_agent
                plugin = get_agent(a)
                if plugin and getattr(plugin, 'debate_enabled', False):
                    debate_agents.add(a)
            except Exception:
                logger.debug("Agent %s debate check skipped", a)

        if len(debate_agents) < 2:
            return None

        try:
            from haip.debate.engine import DebateEngine
            from haip.llm import LLMProvider
            llm_config = {"provider": "deepseek"}
            llm = LLMProvider.from_config(llm_config)
            engine = DebateEngine(llm)
            ctx = engine.run(patient_id, query, {
                k: str(v) for k, v in agent_outputs.items() if k in debate_agents
            })
            return {
                "verdict": ctx.final_verdict,
                "consensus": ctx.consensus_reached,
                "debate_triggered": ctx.debate_triggered,
                "conflicts": len(ctx.conflicts),
            }
        except Exception as e:
            logger.warning("Debate skipped: %s", e)
            return None

    def _run_guard(self, final_output, agent_outputs):
        try:
            from haip.guard.verifier import GuardVerifier
            verifier = GuardVerifier()
            result = verifier.verify(
                output=str(final_output),
                cross_agent_outputs=[str(v) for v in agent_outputs.values()],
            )
            return {"passed": result.passed, "flags": result.flags}
        except Exception:
            logger.exception("Guard 验证异常, 阻断通过")
            return {"passed": False, "flags": ["Guard 内部异常"], "blocked": True}

    def _run_feedback(self, patient_id: str, agents: list[str], pipeline_result: dict) -> bool:
        try:
            from haip.learning.collector import FeedbackCollector, FeedbackEvent
            collector = FeedbackCollector()
            for agent in agents:
                collector.record(FeedbackEvent(
                    agent=agent, patient_id=patient_id,
                    event_type="pipeline_complete",
                    event_data={"guard_passed": pipeline_result.get("guard_result", {})},
                    source_tags={"rag_used": bool(pipeline_result.get("phase_outputs", {}).get("rag")),
                                 "debate_triggered": bool(pipeline_result.get("phase_outputs", {}).get("debate"))},
                ))
            return True
        except Exception:
            return False
