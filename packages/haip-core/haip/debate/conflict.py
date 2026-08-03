"""Conflict detector — deterministic comparison of structured declarations.

No LLM involved — pure structural comparison. Detects when two agents
declare mutually exclusive categories for the same metric.
This eliminates the Guard-Debate circular dependency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from haip.debate.declaration import Declaration

logger = logging.getLogger(__name__)

_EXCLUSIVE_PAIRS: dict[str, set[tuple[str, ...]]] = {
    "surgical_timing": {
        ("elective", "emergency"), ("elective", "urgent"), ("emergency", "urgent"),
    },
    "risk_level": {
        ("high", "low"), ("high", "medium"), ("low", "medium"),
    },
    "diagnosis": set(),
    "treatment": {
        ("avoid", "recommend"),
    },
}


@dataclass
class Conflict:
    decl_a_id: str
    decl_b_id: str
    agent_a: str
    agent_b: str
    metric: str
    value_a: str
    value_b: str
    category_a: str
    category_b: str
    conflict_type: str = "category_mismatch"
    resolved: bool = False
    resolution: str = ""

    def summary(self) -> str:
        return (
            f"[{self.agent_a}] {self.metric}={self.value_a}({self.category_a}) "
            f"vs [{self.agent_b}] {self.metric}={self.value_b}({self.category_b})"
        )


class ConflictDetector:
    """Deterministic conflict detection between agent declarations.

    Pure structural comparison — no LLM. Detects:
    - Category mismatches on same metric (e.g., agent A: urgent, agent B: elective)
    - Value disagreements on same metric+category
    """

    def detect(self, declarations: list[Declaration]) -> list[Conflict]:
        """Find conflicts in a set of declarations from multiple agents."""
        conflicts = []
        agents = sorted({d.agent for d in declarations if d.category != "unknown"})

        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                a_decls = [d for d in declarations if d.agent == agents[i]]
                b_decls = [d for d in declarations if d.agent == agents[j]]
                for ad in a_decls:
                    for bd in b_decls:
                        if ad.metric != bd.metric:
                            continue
                        if self._is_conflict(ad, bd):
                            conflicts.append(Conflict(
                                decl_a_id=ad.id, decl_b_id=bd.id,
                                agent_a=agents[i], agent_b=agents[j],
                                metric=ad.metric,
                                value_a=ad.value, value_b=bd.value,
                                category_a=ad.category, category_b=bd.category,
                            ))

        logger.info("Conflict detection: %d declarations → %d conflicts", len(declarations), len(conflicts))
        return conflicts

    @staticmethod
    def _is_conflict(a: Declaration, b: Declaration) -> bool:
        if a.category == "unknown" or b.category == "unknown":
            return False
        if a.category == b.category and a.value == b.value:
            return False

        exclusive_set = _EXCLUSIVE_PAIRS.get(a.metric)
        if exclusive_set is None:
            return a.category != b.category

        pair = tuple(sorted([a.category, b.category]))
        return pair in exclusive_set
