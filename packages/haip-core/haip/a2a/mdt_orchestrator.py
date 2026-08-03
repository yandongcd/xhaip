"""MDT Orchestrator — Parallel A2A fan-out, collect, resolve.

Coordinates multiple agents to participate in an MDT session.
Uses ThreadPoolExecutor for parallel agent calls with timeout.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

from haip.a2a.mdt_protocol import (
    MDTOpinion,
    MDTProtocol,
    MDTSession,
    MDTStatus,
)

# Default timeout per agent (seconds)
DEFAULT_AGENT_TIMEOUT = 30
DEFAULT_MAX_WORKERS = 8


class MDTOrchestrator:
    """Orchestrate multi-agent MDT sessions."""

    def __init__(self, max_workers: int = DEFAULT_MAX_WORKERS):
        self.max_workers = max_workers

    def run_session(
        self,
        patient_id: str,
        question: str,
        participants: list[str],
        context: dict[str, Any] | None = None,
        timeout: int = 300,
        agent_call_fn=None,
        timeline_id: str | None = None,
        sub_windows: list[Any] | None = None,
    ) -> MDTSession:
        """Run a complete MDT session.

        Args:
            patient_id: Patient identifier
            question: Clinical question for MDT
            participants: List of agent names to invite
            context: Patient data context (labs, imaging, history)
            timeout: Max seconds for entire session
            agent_call_fn: Function(agent_name, patient_id, question) → dict
                          If None, uses A2A call.
            timeline_id: Optional time-window parent timeline id (haip.time_window).
                        When set, a composite window is registered for this session
                        and the verdict is attached to the session on completion.
            sub_windows: Optional list of SubWindowSpec per participant; defaults
                        to one parallel sub-window per participant using the parent
                        deadline.

        Returns:
            MDTSession with all opinions, divergences, and consensus.
        """
        session = MDTSession(
            patient_id=patient_id,
            question=question,
            context=context or {},
            participants=participants,
            timeout_seconds=timeout,
        )

        # Phase 0: Register composite time window (if timeline requested)
        parent_token: str | None = None
        if timeline_id:
            parent_token = self._register_composite(
                patient_id, participants, timeline_id, sub_windows,
            )

        # Phase 1: Collect opinions in parallel
        session.status = MDTStatus.COLLECTING
        self._collect_opinions(session, agent_call_fn)

        # Phase 2: Detect divergence
        session.status = MDTStatus.DIVERGENCE_CHECK
        session.divergences = MDTProtocol.detect_divergence(session)

        # Phase 3: Resolve
        if session.divergences:
            session.status = MDTStatus.RESOLVING
            session.consensus = MDTProtocol.resolve(session)
            if not session.consensus:
                session.status = MDTStatus.DEADLOCKED
            else:
                session.status = MDTStatus.CONSENSUS
        else:
            session.status = MDTStatus.CONSENSUS
            session.consensus = MDTProtocol.resolve(session)

        # Phase 4: Complete
        if session.status != MDTStatus.DEADLOCKED:
            session.status = MDTStatus.COMPLETED
        session.resolved_at = time.time()

        # Phase 5: Resolve composite window verdict (time_window integration)
        if parent_token:
            self._resolve_composite_verdict(session, parent_token)

        return session

    def _register_composite(
        self,
        patient_id: str,
        participants: list[str],
        timeline_id: str,
        sub_windows: list[Any] | None,
    ) -> str | None:
        """Register a composite time window for this MDT session (best effort)."""
        try:
            from haip.time_window.engine import register_composite_window
            from haip.time_window.models import CompositeWindowSpec, SubWindowMode, SubWindowSpec
            from haip.time_window.registry import get_timeline

            parent = get_timeline(timeline_id)
            if parent is None:
                return None  # unknown timeline — no window tracking

            if sub_windows is None:
                sub_windows = [
                    SubWindowSpec(
                        member_agent_id=agent,
                        timeline_id=timeline_id,
                        mode=SubWindowMode.PARALLEL,
                        deadline_hours=parent.deadline.value,
                    )
                    for agent in participants
                ]

            composite = register_composite_window(
                patient_id,
                CompositeWindowSpec(
                    parent_timeline_id=timeline_id,
                    sub_windows=sub_windows,
                ),
            )
            return composite.parent_token
        except Exception:
            return None

    def _resolve_composite_verdict(self, session: MDTSession, parent_token: str) -> None:
        """Attach time-window verdict to the session (best effort)."""
        try:
            from haip.time_window.engine import resolve_composite_verdict

            high_risk = sum(1 for o in session.opinions if o.risks)
            medium_risk = sum(1 for o in session.opinions if o.evidence_level in ("T2", "T3"))
            verdict = resolve_composite_verdict(parent_token, high_risk, medium_risk)
            if isinstance(verdict, dict) and "error" not in verdict:
                session.window_verdict = verdict
                session.window_escalated = (
                    verdict.get("verdict") == "delayed"
                    or bool(verdict.get("escalated_windows"))
                )
        except Exception:
            pass

    def _collect_opinions(
        self, session: MDTSession, agent_call_fn=None
    ) -> None:
        """Fan out MDT question to all participant agents in parallel."""
        if agent_call_fn is None:
            agent_call_fn = self._default_agent_call

        agent_timeout = min(
            DEFAULT_AGENT_TIMEOUT,
            session.timeout_seconds // max(len(session.participants), 1),
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for agent_name in session.participants:
                future = executor.submit(
                    agent_call_fn, agent_name, session.patient_id, session.question, session.context
                )
                futures[future] = agent_name

            for future in futures:
                agent_name = futures[future]
                try:
                    result = future.result(timeout=agent_timeout)
                    opinion = self._parse_agent_response(agent_name, result)
                    session.add_opinion(opinion)
                except FutureTimeout:
                    session.add_opinion(MDTOpinion(
                        agent_name=agent_name,
                        recommendation=f"[TIMEOUT] {agent_name} 未在 {agent_timeout}s 内响应",
                        confidence=0.0,
                    ))
                except Exception as e:
                    session.add_opinion(MDTOpinion(
                        agent_name=agent_name,
                        recommendation=f"[ERROR] {agent_name}: {str(e)[:200]}",
                        confidence=0.0,
                    ))

    def _default_agent_call(
        self, agent_name: str, patient_id: str, question: str, context: dict
    ) -> dict:
        """Default A2A agent call (in-process via importlib)."""
        try:
            from haip.a2a import call as a2a_call
            result = a2a_call(agent_name, "participate_mdt", {
                "session_id": "",
                "patient_id": patient_id,
                "question": question,
                **context,
            })
            return result if isinstance(result, dict) else {"output": str(result)}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _parse_agent_response(self, agent_name: str, result: dict) -> MDTOpinion:
        """Parse an agent's A2A response into an MDTOpinion."""
        if "error" in result:
            return MDTOpinion(
                agent_name=agent_name,
                recommendation=f"[ERROR] {result['error']}",
                confidence=0.0,
            )

        # Try to extract structured fields
        recommendation = ""
        if "summary" in result:
            recommendation = result["summary"]
        elif "output" in result:
            recommendation = str(result["output"])
        elif "recommendations" in result:
            recs = result["recommendations"]
            recommendation = recs[0] if isinstance(recs, list) and recs else str(recs)

        return MDTOpinion(
            agent_name=agent_name,
            recommendation=recommendation or f"{agent_name} 评估完成",
            evidence_level=result.get("evidence_level", "T2"),
            confidence=result.get("confidence", 0.5),
            citations=result.get("citations", result.get("guideline_refs", [])),
            risks=result.get("alerts", result.get("risks", [])),
            notes=result.get("detail", ""),
        )


# ── Global singleton ──────────────────────────────────────────────

_singleton_state: dict = {}


def get_mdt_orchestrator() -> MDTOrchestrator:
    from haip._singleton import locked_singleton
    return locked_singleton(MDTOrchestrator, _singleton_state, "orchestrator")
