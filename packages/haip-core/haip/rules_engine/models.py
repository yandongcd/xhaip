"""Clinical Rules Engine — models, constants, and evaluation context.

Ported from haip-0710's src/agents/rules/models.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TrustLevel(Enum):
    """Guideline trust level."""
    T1 = "T1"  # National/NHC level
    T2 = "T2"  # Society/specialty level
    T3 = "T3"  # Hospital/internal level


class SourceTier(Enum):
    """Evidence source tier."""
    L1 = "L1"  # Meta-analysis / Systematic review
    L2 = "L2"  # RCT
    L3 = "L3"  # Cohort / Case-control
    L4 = "L4"  # Case series
    L5 = "L5"  # Expert opinion


class Certainty(Enum):
    """Rule certainty level."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class RuleType(Enum):
    """Type of clinical rule."""
    DETERMINISTIC = "deterministic"  # Always applies when condition met
    PROBABILISTIC = "probabilistic"  # Applies with probability
    THRESHOLD = "threshold"          # Applies above/below threshold
    COMPOSITE = "composite"          # Combines multiple sub-rules


class ChangeType(Enum):
    """Types of rule changes for impact analysis."""
    THRESHOLD_MODIFIED = "threshold_modified"
    CONCLUSION_CHANGED = "conclusion_changed"
    NEW_RULE_ADDED = "new_rule_added"
    RULE_REMOVED = "rule_removed"
    EXCEPTION_ADDED = "exception_added"
    EVIDENCE_UPDATED = "evidence_updated"
    CERTAINTY_CHANGED = "certainty_changed"
    SOURCE_SUPERSEDED = "source_superseded"


class ChangeStatus(Enum):
    """Status of a change request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ── Core Data Classes ──


@dataclass
class EvidenceRef:
    """Reference to an evidence source."""
    source_id: str
    chapter: str = ""
    quote: str = ""
    confidence: float = 1.0


@dataclass
class Rule:
    """A single clinical decision rule."""
    id: str
    decision_point: str
    conclusion: str
    condition_expr: str = ""
    condition_eval: str = ""
    rule_type: RuleType = RuleType.DETERMINISTIC
    certainty: Certainty = Certainty.MODERATE
    evidence: list[EvidenceRef] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class RuleSet:
    """A collection of related clinical rules."""
    id: str
    domain: str
    decision_points: list[str]
    sources: list[str]
    rules: list[Rule]
    version: str = "1.0"
    trust_level: TrustLevel = TrustLevel.T2
    owner: str = ""


@dataclass
class GuidelineSource:
    """A clinical guideline source."""
    id: str
    name: str
    tier: SourceTier
    version: str
    publish_date: str
    publisher: str = ""
    language: str = ""
    admin_priority: int = 999
    status: str = "active"
    superseded_by: str = ""


@dataclass
class EvaluationContext:
    """Evaluation context for rule conditions."""
    values: dict[str, Any]

    def get(self, path: str, default: Any = None) -> Any:
        """Get a value by dot-separated path."""
        parts = path.split(".")
        val = self.values
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            elif isinstance(val, list) and p.isdigit():
                val = val[int(p)]
            else:
                return default
            if val is None:
                return default
        return val


@dataclass
class Conflict:
    """A conflict between multiple matching rules."""
    rule_ids: list[str]
    decision_point: str
    conclusions: list[str]
    context: EvaluationContext
    strategy_applied: str = ""


@dataclass
class ArbitrationResult:
    """Result of rule arbitration."""
    winner_rule_id: str
    conclusion: str
    certainty: Certainty
    reasoning: str
    chain: list[str] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    overridden_by_admin: bool = False
    strategy_used: str = ""


@dataclass
class RuleDiff:
    """Difference between two rule versions."""
    rule_id: str
    change_type: ChangeType
    old_value: str = ""
    new_value: str = ""
    impact_level: str = "medium"
    status: ChangeStatus = ChangeStatus.PENDING


@dataclass
class ImpactReport:
    """Report on the impact of a guideline update."""
    source_id: str
    old_version: str
    new_version: str
    affected_rules: list[RuleDiff]
    summary: dict[str, int] = field(default_factory=dict)


@dataclass
class ChangeRequest:
    """A change request for rule governance."""
    id: str
    impact_report: ImpactReport
    status: ChangeStatus = ChangeStatus.PENDING
    created_at: str = ""
    reviewed_at: str = ""
    reviewed_by: str = ""
    note: str = ""
