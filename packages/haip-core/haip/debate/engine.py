"""Debate engine — orchestrates multi-agent debate with structured declarations.

Flow:
  1. Declaration extraction (LLM per agent)
  2. Deterministic conflict detection (no LLM)
  3. If conflicts → Round 1 debate (focused on conflict points)
  4. Dual moderator judgment
  5. If split → appeal tiebreaker
  6. Synthesize final MDT recommendation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from haip.debate.conflict import Conflict, ConflictDetector
from haip.debate.declaration import Declaration, DeclarationLayer
from haip.debate.moderator import Moderator, ModeratorVote
from haip.debate.protocol import DebateProtocol
from haip.llm import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class DebateContext:
    patient_id: str = ""
    query: str = ""
    agents: list[str] = field(default_factory=list)
    agent_outputs: dict[str, str] = field(default_factory=dict)
    declarations: list[Declaration] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    debate_triggered: bool = False
    round_count: int = 0
    moderator_votes: tuple[ModeratorVote, ModeratorVote] | None = None
    appeal_used: bool = False
    final_verdict: str = ""
    consensus_reached: bool = False


class DebateEngine:
    """Multi-agent debate orchestrator."""

    _available = False

    def __init__(self, llm: LLMProvider | None = None):
        self._llm = llm
        self._declaration_layer = DeclarationLayer(llm)
        self._conflict_detector = ConflictDetector()
        self._moderator = Moderator(llm)
        self._protocol = DebateProtocol()

    @classmethod
    @property
    def available(cls) -> bool:
        return cls._available

    def run(
        self,
        patient_id: str,
        query: str,
        agent_outputs: dict[str, str],
        agent_roles: dict[str, str] | None = None,
    ) -> DebateContext:
        """Run full debate pipeline. Returns context with final verdict."""
        ctx = DebateContext(
            patient_id=patient_id,
            query=query,
            agents=list(agent_outputs.keys()),
            agent_outputs=agent_outputs,
        )
        agent_roles = agent_roles or {}

        # Phase 1: Extract declarations
        ctx.declarations = self._declaration_layer.extract_batch(ctx.agent_outputs)
        if not ctx.declarations:
            logger.info("No declarations extracted — skipping debate")
            return ctx

        # Phase 2: Detect conflicts
        ctx.conflicts = self._conflict_detector.detect(ctx.declarations)
        if not ctx.conflicts:
            logger.info("No conflicts detected — consensus assumed")
            ctx.consensus_reached = True
            ctx.final_verdict = self._aggregate_no_conflict(ctx)
            return ctx

        # Phase 3: Debate triggered
        ctx.debate_triggered = True
        logger.info("Debate triggered: %d agents, %d conflicts", len(ctx.agents), len(ctx.conflicts))

        decl_text = self._protocol.declarations_text(ctx.declarations)
        conflict_text = self._protocol.conflicts_text(ctx.conflicts)

        # Phase 4: Dual moderator
        vote_a, vote_b = self._moderator.judge(decl_text, conflict_text)
        ctx.moderator_votes = (vote_a, vote_b)

        if vote_a.consensus and vote_b.consensus:
            ctx.consensus_reached = True
            ctx.final_verdict = vote_a.verdict
        elif not vote_a.consensus and not vote_b.consensus:
            ctx.consensus_reached = False
            ctx.final_verdict = f"主持人一致认为需要进一步讨论。\nA: {vote_a.verdict}\nB: {vote_b.verdict}"
        else:
            # Split — appeal
            ctx.appeal_used = True
            final = self._moderator.appeal(vote_a, vote_b, decl_text)
            ctx.consensus_reached = final.consensus
            ctx.final_verdict = final.verdict

        return ctx

    def _aggregate_no_conflict(self, ctx: DebateContext) -> str:
        """Synthesize when all agents agree (no debate needed)."""
        lines = ["## MDT 多学科会诊结论（一致同意）", ""]
        for d in ctx.declarations:
            lines.append(f"- [{d.agent}] {d.metric}: {d.value}")
        return "\n".join(lines)
