"""Approval gate — three-tier approval with anti-fatigue detection.

Tier 1 (auto): low-risk suggestions applied immediately
Tier 2 (batch): low/medium suggestions batched for weekly review
Tier 3 (per-item): high-risk suggestions with individual review
Anti-fatigue: detects rubber-stamping (<5s per item) → flags for second review
"""

from __future__ import annotations

import logging
import time

from haip.learning.improve import LearningSuggestion

logger = logging.getLogger(__name__)


class ApprovalGate:
    """Three-tier approval gate for learning suggestions."""

    def __init__(self):
        self._review_history: list[dict] = []
        self._anti_fatigue_threshold = 5.0  # seconds per item

    def classify(self, suggestion: LearningSuggestion) -> str:
        """Classify a suggestion into approval tier: 'auto' | 'batch' | 'per_item'."""
        if suggestion.risk_level == "low" and suggestion.scope == "agent_only":
            return "auto"
        if suggestion.risk_level in ("low", "medium") and suggestion.scope in ("agent_only", "agent_group"):
            return "batch"
        return "per_item"

    def is_fatigued(self, recent_count: int = 5) -> bool:
        """Check if reviewer is rubber-stamping."""
        recent = self._review_history[-recent_count:]
        if len(recent) < recent_count:
            return False
        avg_gap = sum(r.get("review_seconds", 0) for r in recent) / len(recent)
        return avg_gap < self._anti_fatigue_threshold

    def record_review(self, suggestion_id: str, decision: str, reviewer: str = "default",
                      review_seconds: float = 0):
        """Record a review decision for anti-fatigue tracking."""
        self._review_history.append({
            "id": suggestion_id,
            "decision": decision,
            "reviewer": reviewer,
            "review_seconds": review_seconds,
            "timestamp": time.time(),
        })
        if len(self._review_history) > 100:
            self._review_history = self._review_history[-50:]

    def auto_apply(self, suggestion: LearningSuggestion) -> bool:
        """Attempt to auto-apply a suggestion. Returns True if applied."""
        tier = self.classify(suggestion)
        if tier == "auto":
            suggestion.status = "applied"
            suggestion.applied_at = time.time()
            logger.info("Auto-applied: %s (%s)", suggestion.id, suggestion.type)
            return True
        suggestion.status = "pending_review"
        return False

    def approve(self, suggestion: LearningSuggestion, reviewer: str = "default",
                review_seconds: float = 0) -> bool:
        """Approve a batch/per-item suggestion. Checks for fatigue."""
        if self.is_fatigued():
            logger.warning("Anti-fatigue: flagging %s for second review", suggestion.id)
            suggestion.status = "pending_review"  # re-queues for second review
            return False
        suggestion.status = "applied"
        suggestion.applied_at = time.time()
        self.record_review(suggestion.id, "approved", reviewer, review_seconds)
        return True

    def reject(self, suggestion: LearningSuggestion, reason: str = "",
               reviewer: str = "default", review_seconds: float = 0):
        """Reject a suggestion."""
        suggestion.status = "rejected"
        self.record_review(suggestion.id, f"rejected: {reason}", reviewer, review_seconds)

    def pending(self) -> int:
        """Count pending suggestions across all statuses that need review."""
        return sum(1 for h in self._review_history if h.get("decision", "") == "pending_review")
