"""Clinical Rules Engine — unified entry point.

Provides:
    - Expression evaluator for rule conditions
    - Rule arbitration for conflict resolution
    - Impact analysis for guideline updates
    - Change governance workflow
    - YAML-based rule loading
"""

from haip.rules_engine.evaluator import evaluate, register_callback
from haip.rules_engine.arbitration import evaluate_rules, register_source
from haip.rules_engine.impact import analyze_impact
from haip.rules_engine.governance import (
    create_change_request,
    get_pending_changes,
    approve_change,
    reject_change,
)
from haip.rules_engine.models import (
    Rule,
    RuleSet,
    EvidenceRef,
    TrustLevel,
    Certainty,
    RuleType,
    EvaluationContext,
    GuidelineSource,
    SourceTier,
    ArbitrationResult,
    ImpactReport,
    ChangeRequest,
)

__all__ = [
    "evaluate",
    "register_callback",
    "evaluate_rules",
    "register_source",
    "analyze_impact",
    "create_change_request",
    "get_pending_changes",
    "approve_change",
    "reject_change",
    "Rule",
    "RuleSet",
    "EvidenceRef",
    "TrustLevel",
    "Certainty",
    "RuleType",
    "EvaluationContext",
    "GuidelineSource",
    "SourceTier",
    "ArbitrationResult",
    "ImpactReport",
    "ChangeRequest",
]
