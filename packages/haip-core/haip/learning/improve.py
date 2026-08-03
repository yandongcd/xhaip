"""Improvement engine — generates actionable suggestions from analysis results.

Four suggestion types with risk classification:
- citation_new (auto, low risk)
- route_adjust (auto, low risk)
- rule_flag (auto-flag, content change needs approval)
- prompt_optimize (approval, high risk)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from haip.learning.analysis import AnalysisResult

logger = logging.getLogger(__name__)

SUGGESTION_TYPES = ["citation_new", "route_adjust", "rule_flag", "prompt_optimize"]


@dataclass
class LearningSuggestion:
    id: str = ""
    created_at: float = field(default_factory=time.time)
    type: str = ""              # citation_new | route_adjust | rule_flag | prompt_optimize
    target: str = ""            # agent_name | rule_id | route_key
    suggestion: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    risk_level: str = "low"     # low | medium | high
    scope: str = "agent_only"   # agent_only | agent_group | global
    status: str = "pending"     # pending_auto | pending_review | applied | rejected | rolled_back
    applied_at: float | None = None
    rollback_snapshot: dict | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "target": self.target,
            "suggestion": self.suggestion, "evidence": self.evidence,
            "risk_level": self.risk_level, "scope": self.scope,
            "status": self.status, "created_at": self.created_at,
        }


class ImprovementEngine:
    """Generates learning suggestions from analysis results and feedback patterns."""

    def __init__(self, store=None, analysis=None):
        self._store = store
        self._analysis = analysis  # AnalysisEngine | None

    def generate(self, results: list[AnalysisResult], agents: list[str]) -> list[LearningSuggestion]:
        """Generate suggestions from analysis results."""
        suggestions = []

        for r in results:
            suggestions.extend(self._citation_suggestions(r))
            suggestions.extend(self._rule_flag_suggestions(r))
            suggestions.extend(self._prompt_suggestions(r))

        return suggestions

    def _citation_suggestions(self, r: AnalysisResult) -> list[LearningSuggestion]:
        """Auto-suggest adding verified citations to knowledge base."""
        suggestions = []
        for i, citation in enumerate(r.citations_pending[:3]):
            if not citation:
                continue
            suggestions.append(LearningSuggestion(
                id=f"cit_{r.agent}_{i}_{int(time.time())}",
                type="citation_new",
                target=r.agent,
                suggestion={"action": "add_to_kb", "citation": citation, "trust_level": "T3", "source": "auto_extracted"},
                evidence={"agent": r.agent, "ccs": r.ccs_current},
                risk_level="low",
                scope="agent_only",
            ))
        return suggestions

    def _rule_flag_suggestions(self, r: AnalysisResult) -> list[LearningSuggestion]:
        """Flag rules with high failure rates for review."""
        suggestions = []
        if r.ccs_change_7d < -0.05:
            suggestions.append(LearningSuggestion(
                id=f"rule_ccs_decline_{r.agent}_{int(time.time())}",
                type="rule_flag",
                target=r.agent,
                suggestion={"action": "review_rules", "reason": "CCS declined", "detail": f"7-day CCS change: {r.ccs_change_7d:+.3f}"},
                evidence={"ccs_current": r.ccs_current, "ccs_change": r.ccs_change_7d, "top_failures": r.top_failure_reasons},
                risk_level="medium",
                scope="agent_only",
            ))
        return suggestions

    def _prompt_suggestions(self, r: AnalysisResult) -> list[LearningSuggestion]:
        """Suggest prompt optimization when needed."""
        suggestions = []
        if r.ccs_change_7d < -0.1 and r.ccs_current < 0.5:
            suggestions.append(LearningSuggestion(
                id=f"prompt_opt_{r.agent}_{int(time.time())}",
                type="prompt_optimize",
                target=r.agent,
                suggestion={
                    "action": "optimize_prompt",
                    "reason": "CCS significantly degraded",
                    "current_ccs": r.ccs_current,
                    "top_issues": r.top_failure_reasons,
                },
                evidence={"ccs_current": r.ccs_current, "ccs_change": r.ccs_change_7d},
                risk_level="high",
                scope="agent_only",
            ))
        return suggestions
