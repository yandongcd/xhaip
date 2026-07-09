"""Confidence Scorer — 加权置信度评分."""

from __future__ import annotations

from dataclasses import dataclass, field

from haip.guard.citation import Citation


@dataclass
class ConfidenceScore:
    value: float = 0.0          # 0.0-1.0
    level: str = "low"          # high / medium / low / critical
    flagged_for_review: bool = False
    blocked: bool = False
    details: dict[str, float] = field(default_factory=dict)


class ConfidenceScorer:
    """4 因子加权置信度评分。

    Formula:
        source_quality(0.35) + tool_reliability(0.25) + llm_certainty(0.25) + cross_validation(0.15)
    """

    def __init__(
        self,
        source_weight: float = 0.35,
        tool_weight: float = 0.25,
        llm_weight: float = 0.25,
        cross_weight: float = 0.15,
    ):
        self.source_weight = source_weight
        self.tool_weight = tool_weight
        self.llm_weight = llm_weight
        self.cross_weight = cross_weight

    def compute(
        self,
        citations: list[Citation] | None = None,
        tool_results: list[dict] | None = None,
        llm_temperature: float = 0.3,
        cross_validation_consensus: bool = True,
    ) -> ConfidenceScore:
        citations = citations or []
        tool_results = tool_results or []

        sq = self._score_source_quality(citations)
        tr = self._score_tool_reliability(tool_results)
        lc = self._score_llm_certainty(llm_temperature)
        cv = 1.0 if cross_validation_consensus else 0.3

        value = round(
            sq * self.source_weight
            + tr * self.tool_weight
            + lc * self.llm_weight
            + cv * self.cross_weight,
            3,
        )

        level = "critical"
        flagged = True
        blocked = True
        if value >= 0.8:
            level = "high"
            flagged = False
            blocked = False
        elif value >= 0.6:
            level = "medium"
            flagged = False
            blocked = False
        elif value >= 0.3:
            level = "low"
            blocked = False

        return ConfidenceScore(
            value=value,
            level=level,
            flagged_for_review=flagged,
            blocked=blocked,
            details={
                "source_quality": sq,
                "tool_reliability": tr,
                "llm_certainty": lc,
                "cross_validation": cv,
            },
        )

    def _score_source_quality(self, citations: list[Citation]) -> float:
        if not citations:
            return 0.3
        t1_count = sum(1 for c in citations if c.trust_level == "T1")
        verified_count = sum(1 for c in citations if c.verified)
        total = len(citations)
        if t1_count / total >= 0.5:
            return 1.0
        if verified_count / total >= 0.5:
            return 0.8
        return 0.6

    @staticmethod
    def _score_tool_reliability(tool_results: list[dict]) -> float:
        if not tool_results:
            return 0.5
        success = sum(1 for r in tool_results if r.get("success", True))
        return success / len(tool_results)

    @staticmethod
    def _score_llm_certainty(temperature: float) -> float:
        return max(0.4, 1.0 - temperature)
