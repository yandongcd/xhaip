"""Rollout manager — gradual deployment with CCS monitoring + auto-rollback.

Changes are rolled out progressively: 5% → 25% → 100% over 6 hours.
At each stage, CCS is monitored. If CCS drops >5% → auto-rollback.
All changes are versioned with rollback snapshots.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from haip.learning.approval import ApprovalGate
from haip.learning.improve import LearningSuggestion

logger = logging.getLogger(__name__)

_ROLLOUT_STAGES = [
    (0.05, 7200),   # 5% for 2 hours
    (0.25, 7200),   # 25% for 2 hours
    (1.0, 7200),    # 100% for 2 hours
]

CCS_DROP_THRESHOLD = 0.05  # 5% drop triggers rollback


@dataclass
class RolloutState:
    suggestion_id: str = ""
    stage_index: int = 0
    traffic_fraction: float = 0.0
    started_at: float = 0.0
    stage_started_at: float = 0.0
    baseline_ccs: float = 0.0
    ccs_history: list[tuple[float, float]] = field(default_factory=list)  # (timestamp, ccs)
    status: str = "pending"  # pending | rolling_out | active | rolled_back | completed
    rollback_reason: str = ""


class RolloutManager:
    """Gradual rollout with CCS-based auto-rollback."""

    def __init__(self, approval: ApprovalGate):
        self._approval = approval
        self._active: dict[str, RolloutState] = {}
        self._monitor_thread: threading.Thread | None = None

    def start_rollout(self, suggestion: LearningSuggestion, baseline_ccs: float) -> RolloutState:
        """Begin gradual rollout of a learning change."""
        state = RolloutState(
            suggestion_id=suggestion.id,
            stage_index=0,
            traffic_fraction=_ROLLOUT_STAGES[0][0],
            started_at=time.time(),
            stage_started_at=time.time(),
            baseline_ccs=baseline_ccs,
            status="rolling_out",
        )
        self._active[suggestion.id] = state
        suggestion.rollback_snapshot = {"baseline_ccs": baseline_ccs, "timestamp": time.time()}
        logger.info("Rollout started: %s at %.0f%%", suggestion.id, state.traffic_fraction * 100)
        return state

    def report_ccs(self, suggestion_id: str, current_ccs: float):
        """Report current CCS for a rolling-out change."""
        state = self._active.get(suggestion_id)
        if not state or state.status != "rolling_out":
            return

        state.ccs_history.append((time.time(), current_ccs))

        drop = (state.baseline_ccs - current_ccs) / state.baseline_ccs if state.baseline_ccs > 0 else 0
        if drop > CCS_DROP_THRESHOLD and current_ccs < state.baseline_ccs:
            logger.warning("CCS drop detected for %s: %.3f->%.3f (%.1f%%)",
                           suggestion_id, state.baseline_ccs, current_ccs, drop * 100)
            self._rollback(suggestion_id, f"CCS dropped {drop:.1%} below baseline")

    def advance_stage(self, suggestion_id: str):
        """Advance to next rollout stage if time has elapsed and CCS is stable."""
        state = self._active.get(suggestion_id)
        if not state or state.status != "rolling_out":
            return
        if state.stage_index >= len(_ROLLOUT_STAGES) - 1:
            state.status = "completed"
            state.traffic_fraction = 1.0
            logger.info("Rollout complete: %s at 100%%", suggestion_id)
            return

        _, duration = _ROLLOUT_STAGES[state.stage_index]
        if time.time() - state.stage_started_at >= duration:
            state.stage_index += 1
            state.traffic_fraction = _ROLLOUT_STAGES[state.stage_index][0]
            state.stage_started_at = time.time()
            logger.info("Rollout advanced: %s → %.0f%%", suggestion_id, state.traffic_fraction * 100)

    def _rollback(self, suggestion_id: str, reason: str):
        """Immediate rollback of a change."""
        state = self._active.get(suggestion_id)
        if state:
            state.status = "rolled_back"
            state.rollback_reason = reason
        logger.warning("ROLLBACK: %s — %s", suggestion_id, reason)

    def active_count(self) -> int:
        return sum(1 for s in self._active.values() if s.status == "rolling_out")

    def should_use_new_version(self, suggestion_id: str) -> bool:
        """Randomized traffic splitting: returns True if request should use new version."""
        state = self._active.get(suggestion_id)
        if not state or state.status not in ("rolling_out", "completed"):
            return False
        if state.status == "completed":
            return True
        import random
        return random.random() < state.traffic_fraction
