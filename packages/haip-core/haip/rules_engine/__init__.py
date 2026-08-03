"""Clinical Rules Engine — unified entry point.

Provides:
    - Expression evaluator for rule conditions
    - Rule arbitration for conflict resolution
    - Impact analysis for guideline updates
    - Change governance workflow
    - YAML-based rule loading
"""

from haip.rules_engine.arbitration import evaluate_rules, register_source
from haip.rules_engine.evaluator import evaluate, register_callback
from haip.rules_engine.governance import (
    approve_change,
    create_change_request,
    get_pending_changes,
    reject_change,
)
from haip.rules_engine.impact import analyze_impact
from haip.rules_engine.models import (
    ArbitrationResult,
    Certainty,
    ChangeRequest,
    EvaluationContext,
    EvidenceRef,
    GuidelineSource,
    ImpactReport,
    Rule,
    RuleSet,
    RuleType,
    SourceTier,
    TrustLevel,
)

__all__ = [
    "ArbitrationResult",
    "Certainty",
    "ChangeRequest",
    "EvaluationContext",
    "EvidenceRef",
    "GuidelineSource",
    "ImpactReport",
    "Rule",
    "RuleSet",
    "RuleType",
    "SourceTier",
    "TrustLevel",
    "analyze_impact",
    "approve_change",
    "create_change_request",
    "evaluate",
    "evaluate_rules",
    "get_pending_changes",
    "register_callback",
    "register_source",
    "reject_change",
]
