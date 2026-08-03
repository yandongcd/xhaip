"""MDT Protocol Layer — Multi-Disciplinary Team collaboration protocol.

v2.0: Replaces standalone mdt Agent with a collaboration protocol.
Expert review (10 rounds, 8 hospitals): MDT is a collaboration mechanism, not an agent.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MDTStatus(str, Enum):
    PENDING = "pending"
    COLLECTING = "collecting"
    DIVERGENCE_CHECK = "divergence_check"
    RESOLVING = "resolving"
    CONSENSUS = "consensus"
    DEADLOCKED = "deadlocked"  # cannot resolve, escalate to HITL
    COMPLETED = "completed"
    TIMEOUT = "timeout"


class ConflictType(str, Enum):
    DIAGNOSIS = "diagnosis"        # diagnostic disagreement
    TREATMENT = "treatment"         # treatment choice disagreement
    TIMING = "timing"               # surgical timing / urgency
    RISK = "risk"                   # risk assessment level
    CONTRAINDICATION = "contraindication"  # one agent flags contraindication
    EVIDENCE = "evidence"           # conflicting guideline recommendations


@dataclass
class MDTOpinion:
    """A single agent's opinion in an MDT session."""

    agent_name: str
    recommendation: str                          # concise clinical recommendation
    evidence_level: str = "T2"                    # T1 (guideline) / T2 (consensus) / T3 (experience)
    confidence: float = 0.5                       # 0.0 - 1.0
    citations: list[str] = field(default_factory=list)  # supporting guideline references
    risks: list[str] = field(default_factory=list)      # identified risks
    alternatives: list[str] = field(default_factory=list)  # alternative approaches
    notes: str = ""                               # free-text context


@dataclass
class MDTDivergenceReport:
    """Detected conflicts between MDT opinions."""

    conflict_type: ConflictType
    agent_a: str
    agent_b: str
    statement_a: str
    statement_b: str
    severity: str = "medium"  # low / medium / high / critical
    resolution_strategy: str = ""  # proposed how to resolve


@dataclass
class MDTSession:
    """A multi-disciplinary team consultation session."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    patient_id: str = ""
    question: str = ""                             # the clinical question for MDT
    context: dict[str, Any] = field(default_factory=dict)  # patient data, labs, imaging
    participants: list[str] = field(default_factory=list)   # list of agent names
    opinions: list[MDTOpinion] = field(default_factory=list)
    divergences: list[MDTDivergenceReport] = field(default_factory=list)
    consensus: str = ""
    status: MDTStatus = MDTStatus.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0
    timeout_seconds: int = 300                      # max wait for all agents

    def add_opinion(self, opinion: MDTOpinion) -> None:
        self.opinions.append(opinion)

    def all_responded(self) -> bool:
        return len(self.opinions) >= len(self.participants)

    def get_opinion(self, agent_name: str) -> MDTOpinion | None:
        for o in self.opinions:
            if o.agent_name == agent_name:
                return o
        return None


# ── MDT Protocol ──────────────────────────────────────────────────

class MDTProtocol:
    """Core MDT collaboration protocol.

    Lifecycle:
        initiate → collect_opinions (parallel A2A calls) → detect_divergence
        → (if diverged) resolve → (if deadlocked) escalate_to_hitl
        → consensus → complete
    """

    # Conflict detection rules: pairs of keywords that signal clinical divergence
    DIVERGENCE_PAIRS: list[tuple[str, str]] = [
        ("手术", "保守"),
        ("高风险", "低风险"),
        ("急诊", "择期"),
        ("立即", "暂缓"),
        ("全麻", "区域麻醉"),
        ("根治", "保肢"),
        ("截肢", "保肢"),
        ("积极治疗", "姑息治疗"),
        ("推荐", "禁忌"),
    ]

    # Resolution strategies in priority order
    RESOLUTION_STRATEGIES = [
        "t1_priority",       # T1 (national guideline) evidence wins
        "specialty_weight",  # primary specialty agent has higher weight
        "consensus_vote",    # majority vote among participants
        "hitl_escalation",   # escalate to human MDT chair
    ]

    @classmethod
    def detect_divergence(cls, session: MDTSession) -> list[MDTDivergenceReport]:
        """Detect clinical conflicts between agent opinions."""
        reports = []
        opinions = session.opinions
        if len(opinions) < 2:
            return reports

        for i in range(len(opinions)):
            for j in range(i + 1, len(opinions)):
                oa, ob = opinions[i], opinions[j]
                conflict = cls._check_conflict(oa, ob)
                if conflict:
                    reports.append(conflict)

        return reports

    @classmethod
    def _check_conflict(cls, a: MDTOpinion, b: MDTOpinion) -> MDTDivergenceReport | None:
        """Check if two opinions are in conflict."""
        # 1. Confidence-based: both confident but differ
        if a.confidence > 0.6 and b.confidence > 0.6:
            # 2. Keyword-based divergence
            for kw_a, kw_b in cls.DIVERGENCE_PAIRS:
                if kw_a in a.recommendation and kw_b in b.recommendation:
                    return MDTDivergenceReport(
                        conflict_type=cls._classify_conflict(kw_a, kw_b),
                        agent_a=a.agent_name,
                        agent_b=b.agent_name,
                        statement_a=a.recommendation,
                        statement_b=b.recommendation,
                        severity="medium",
                        resolution_strategy="t1_priority",
                    )
                if kw_b in a.recommendation and kw_a in b.recommendation:
                    return MDTDivergenceReport(
                        conflict_type=cls._classify_conflict(kw_b, kw_a),
                        agent_a=a.agent_name,
                        agent_b=b.agent_name,
                        statement_a=a.recommendation,
                        statement_b=b.recommendation,
                        severity="medium",
                        resolution_strategy="t1_priority",
                    )

        # 3. Evidence-level conflict: different T levels
        if a.evidence_level == "T1" and b.evidence_level in ("T2", "T3"):
            if a.recommendation != b.recommendation:
                return MDTDivergenceReport(
                    conflict_type=ConflictType.EVIDENCE,
                    agent_a=a.agent_name,
                    agent_b=b.agent_name,
                    statement_a=f"[T1] {a.recommendation}",
                    statement_b=f"[{b.evidence_level}] {b.recommendation}",
                    severity="low",
                    resolution_strategy="t1_priority",
                )

        return None

    @classmethod
    def _classify_conflict(cls, risk_kw: str, safe_kw: str) -> ConflictType:
        if risk_kw in ("手术", "保守", "根治", "保肢", "截肢", "积极治疗", "姑息治疗"):
            return ConflictType.TREATMENT
        if risk_kw in ("急诊", "择期", "立即", "暂缓"):
            return ConflictType.TIMING
        if risk_kw in ("高风险", "低风险"):
            return ConflictType.RISK
        return ConflictType.DIAGNOSIS

    @classmethod
    def resolve(cls, session: MDTSession) -> str:
        """Attempt to resolve divergences and reach consensus.

        Returns consensus text or empty string if deadlocked.
        """
        if not session.divergences:
            # No conflicts: aggregate opinions
            high_conf = [o for o in session.opinions if o.confidence >= 0.5]
            if high_conf:
                return " | ".join(o.recommendation for o in high_conf)
            return " | ".join(o.recommendation for o in session.opinions)

        # Has conflicts: try resolution strategies
        for strategy in cls.RESOLUTION_STRATEGIES:
            result = cls._try_strategy(strategy, session)
            if result:
                return result

        return ""  # deadlocked — need HITL

    @classmethod
    def _try_strategy(cls, strategy: str, session: MDTSession) -> str:
        if strategy == "t1_priority":
            t1_opinions = [o for o in session.opinions if o.evidence_level == "T1"]
            if t1_opinions and t1_opinions[0].confidence > 0.5:
                return f"[T1优先] {t1_opinions[0].recommendation}"

        elif strategy == "consensus_vote":
            conf_gt_6 = [o for o in session.opinions if o.confidence > 0.6]
            if len(conf_gt_6) > len(session.opinions) / 2:
                return f"[多数共识] {conf_gt_6[0].recommendation}"

        elif strategy == "hitl_escalation":
            return ""  # signal deadlock → human intervention needed

        return ""


# ── Agent-side interface ──────────────────────────────────────────

def participate_mdt(session: MDTSession, agent_name: str,
                    recommendation: str, **kwargs) -> MDTOpinion:
    """Convenience function for agents to submit their MDT opinion.

    Usage in agent handler:
        opinion = participate_mdt(session, "orthopedic-surgery",
            recommendation="建议48h内行PFNA内固定",
            evidence_level="T1",
            confidence=0.85,
            citations=["国家卫健委2022版指南"],
            risks=["心血管风险中等", "抗凝需桥接"],
            alternatives=["DHS滑动髋螺钉(备选)"])
    """
    return MDTOpinion(
        agent_name=agent_name,
        recommendation=recommendation,
        evidence_level=kwargs.get("evidence_level", "T2"),
        confidence=kwargs.get("confidence", 0.5),
        citations=kwargs.get("citations", []),
        risks=kwargs.get("risks", []),
        alternatives=kwargs.get("alternatives", []),
        notes=kwargs.get("notes", ""),
    )
