"""Learning module — self-improvement via feedback collection and analysis.

Phase 3 of xhaip intelligence upgrade. Implements:
- FeedbackCollector: embeds in A2A/Guard/Loop to capture signals
- FeedbackStore: SQLite storage with time-weighted decay
- AnalysisEngine: batch pattern discovery
- ImprovementEngine: suggestion generation (citation/rules/prompts/routes)
- ApprovalGate: three-tier approval with anti-fatigue detection
- RolloutManager: gradual deployment with CCS monitoring + auto-rollback
"""

from haip.learning.analysis import AnalysisEngine
from haip.learning.approval import ApprovalGate
from haip.learning.collector import FeedbackCollector, FeedbackEvent
from haip.learning.improve import ImprovementEngine, LearningSuggestion
from haip.learning.rollout import RolloutManager
from haip.learning.store import FeedbackStore

__all__ = [
    "AnalysisEngine",
    "ApprovalGate",
    "FeedbackCollector",
    "FeedbackEvent",
    "FeedbackStore",
    "ImprovementEngine",
    "LearningSuggestion",
    "RolloutManager",
]
