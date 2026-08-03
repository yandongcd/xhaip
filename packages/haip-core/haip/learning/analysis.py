"""Analysis engine — batch pattern discovery from feedback store.

Runs hourly (via background thread) to identify:
- Agents with degrading CCS scores
- Rules with high rejection rates
- Routing inefficiencies
- Citation quality trends
- Time-decayed weighted aggregation
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from haip.learning.store import FeedbackStore

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    agent: str = ""
    ccs_trend: list[float] = field(default_factory=list)  # last 7 days
    ccs_current: float = 0.0
    ccs_change_7d: float = 0.0     # positive = improving
    top_failure_reasons: list[str] = field(default_factory=list)
    route_recommendations: list[dict] = field(default_factory=list)
    rules_to_flag: list[str] = field(default_factory=list)
    citations_pending: list[str] = field(default_factory=list)


class AnalysisEngine:
    """Periodic batch analysis of feedback data."""

    def __init__(self, store: FeedbackStore):
        self._store = store
        self._last_run: float = 0

    @property
    def age_seconds(self) -> float:
        return time.time() - self._last_run if self._last_run else float("inf")

    def analyze(self, agents: list[str]) -> list[AnalysisResult]:
        """Run full analysis on all agents. Returns results for each."""
        results = []
        for agent in agents:
            results.append(self._analyze_agent(agent))
        self._last_run = time.time()
        return results

    def _analyze_agent(self, agent: str) -> AnalysisResult:
        result = AnalysisResult(agent=agent)
        result.ccs_current = self._store.compute_ccs(agent, days=7)

        stats_7d = self._store.agent_stats(agent, days=7)
        stats_30d = self._store.agent_stats(agent, days=30)
        if stats_30d and stats_7d:
            ccs_old = (
                0.4 * stats_30d["guard_pass_rate"]
                + 0.3 * (1.0 - stats_30d["hitl_rate"])
            )
            result.ccs_change_7d = round(result.ccs_current - ccs_old, 4)

        recent = self._store.query_recent(agent=agent, event_type="guard_fail", limit=20)
        reasons = {}
        for r in recent:
            tags = r.get("tags", {})
            code = tags.get("guard_failure_code", "unknown")
            reasons[code] = reasons.get(code, 0) + 1
        result.top_failure_reasons = sorted(reasons, key=reasons.get, reverse=True)[:3]

        citations = self._store.query_recent(agent=agent, event_type="citation_new", limit=20)
        result.citations_pending = [
            c.get("data", {}).get("citation", "") for c in citations
        ][:5]

        return result
