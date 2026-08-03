"""Feedback collector — captures structured signals from A2A/Guard/Loop.

Low-overhead per-request event recording. All events carry source_tags
for root cause analysis (distinguishing agent quality vs RAG context vs moderator bias).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEvent:
    timestamp: float = field(default_factory=time.time)
    agent: str = ""
    patient_id: str = ""
    session_id: str = ""
    event_type: str = ""                # guard_pass | guard_fail | hitl_override | debate_win | citation_new | rule_triggered | route_used | rag_miss
    event_data: dict = field(default_factory=dict)
    severity: str = "info"              # info | warning | critical
    source_tags: dict = field(default_factory=dict)
    # source_tags keys: rag_used, rag_top_score, debate_triggered, debate_consensus,
    #                   moderator_split, guard_layer_failed, guard_failure_code

    def to_dict(self) -> dict:
        import json
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "patient_id": self.patient_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "event_data": json.dumps(self.event_data, ensure_ascii=False),
            "severity": self.severity,
            "source_tags": json.dumps(self.source_tags, ensure_ascii=False),
        }


class FeedbackCollector:
    """Per-request feedback signal collector. Embeds in A2A/Guard/Loop."""

    def __init__(self, store=None):
        self._store = store
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled and self._store is not None

    def disable(self):
        self._enabled = False

    def enable(self):
        self._enabled = True

    def record(self, event: FeedbackEvent):
        """Record a single feedback event."""
        if not self.enabled:
            return
        try:
            self._store.insert_event(event)
        except Exception as e:
            logger.debug("Feedback record skipped: %s", e)

    def record_guard(self, agent: str, patient_id: str, passed: bool, failure_layer: int | None = None,
                     failure_code: str | None = None, source_tags: dict | None = None):
        """Record guard verification result."""
        self.record(FeedbackEvent(
            agent=agent, patient_id=patient_id,
            event_type="guard_pass" if passed else "guard_fail",
            event_data={"passed": passed, "layer": failure_layer, "code": failure_code or ""},
            severity="info" if passed else ("critical" if failure_layer == 1 else "warning"),
            source_tags=source_tags or {},
        ))

    def record_hitl(self, agent: str, patient_id: str, correction_type: str, original: str = "",
                    corrected: str = "", source_tags: dict | None = None):
        """Record human-in-the-loop correction."""
        self.record(FeedbackEvent(
            agent=agent, patient_id=patient_id,
            event_type="hitl_override",
            event_data={"correction_type": correction_type, "original_len": len(original), "corrected_len": len(corrected)},
            severity="warning",
            source_tags=source_tags or {},
        ))

    def record_debate(self, agent: str, patient_id: str, agent_won: bool, consensus: bool,
                      moderator_split: bool = False, source_tags: dict | None = None):
        """Record debate outcome."""
        self.record(FeedbackEvent(
            agent=agent, patient_id=patient_id,
            event_type="debate_win" if agent_won else "debate_loss",
            event_data={"agent_won": agent_won, "consensus": consensus, "moderator_split": moderator_split},
            severity="info",
            source_tags=source_tags or {},
        ))

    def record_citation_new(self, agent: str, citation_ref: str, trust_level: str = "T3",
                            source_tags: dict | None = None):
        """Record a new citation discovered from agent output."""
        self.record(FeedbackEvent(
            agent=agent, patient_id="",
            event_type="citation_new",
            event_data={"citation": citation_ref, "trust_level": trust_level},
            severity="info",
            source_tags=source_tags or {},
        ))

    def record_route(self, agent: str, query: str, guard_pass: bool, latency_ms: float = 0,
                     source_tags: dict | None = None):
        """Record routing decision outcome."""
        self.record(FeedbackEvent(
            agent=agent, patient_id="",
            event_type="route_used",
            event_data={"query": query[:200], "guard_pass": guard_pass, "latency_ms": latency_ms},
            severity="info",
            source_tags=source_tags or {},
        ))
