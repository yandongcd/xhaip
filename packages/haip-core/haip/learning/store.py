"""Feedback store — SQLite-backed storage with time-weighted decay.

Stores raw feedback events and aggregated daily stats. Applies time-weighted
decay: 90d×0.5, 180d×0.25, 365d archived. Auto-purges raw events at 180d.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import Any

from haip.learning.collector import FeedbackEvent

logger = logging.getLogger(__name__)

_SECONDS_PER_DAY = 86400


class FeedbackStore:
    """SQLite storage for feedback events with time-weighted aggregation."""

    _writable: bool = False

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def connect(self) -> bool:
        try:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            from haip.schema_version import ensure_version
            ensure_version(self._conn, 1)
            self._create_tables()
            self._ready = True
        except Exception:
            self._ready = False
        return self._ready

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                agent TEXT NOT NULL,
                patient_id TEXT DEFAULT '',
                session_id TEXT DEFAULT '',
                event_type TEXT NOT NULL,
                event_data TEXT DEFAULT '{}',
                severity TEXT DEFAULT 'info',
                source_tags TEXT DEFAULT '{}'
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_agent ON feedback_events(agent)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_type ON feedback_events(event_type)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_time ON feedback_events(timestamp)")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_daily_stats (
                date TEXT NOT NULL,
                agent TEXT NOT NULL,
                total_requests INTEGER DEFAULT 0,
                guard_pass_rate REAL DEFAULT 0,
                hitl_rate REAL DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                avg_citations REAL DEFAULT 0,
                debate_consensus_rate REAL DEFAULT 0,
                ccs REAL DEFAULT 0,
                PRIMARY KEY (date, agent)
            )
        """)

    def insert_event(self, event: FeedbackEvent):
        if not self._conn:
            return
        d = event.to_dict()
        self._conn.execute(
            "INSERT INTO feedback_events(timestamp, agent, patient_id, session_id, event_type, event_data, severity, source_tags) VALUES(?,?,?,?,?,?,?,?)",
            (d["timestamp"], d["agent"], d["patient_id"], d["session_id"],
             d["event_type"], d["event_data"], d["severity"], d["source_tags"]),
        )
        self._conn.commit()

    def query_recent(self, agent: str | None = None, event_type: str | None = None,
                     limit: int = 100) -> list[dict]:
        if not self._conn:
            return []
        where = []
        params = []
        if agent:
            where.append("agent = ?")
            params.append(agent)
        if event_type:
            where.append("event_type = ?")
            params.append(event_type)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = self._conn.execute(
            f"SELECT timestamp, agent, event_type, event_data, severity, source_tags FROM feedback_events {clause} ORDER BY timestamp DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [{"ts": r[0], "agent": r[1], "type": r[2], "data": json.loads(r[3]), "severity": r[4],
                 "tags": json.loads(r[5])} for r in rows]

    def agent_stats(self, agent: str, days: int = 30) -> dict[str, Any]:
        if not self._conn:
            return {}
        cutoff = time.time() - days * _SECONDS_PER_DAY
        rows = self._conn.execute(
            "SELECT event_type, severity, COUNT(*) FROM feedback_events WHERE agent=? AND timestamp>? GROUP BY event_type, severity",
            (agent, cutoff),
        ).fetchall()

        stats = {"total_events": 0, "guard_pass": 0, "guard_fail": 0, "hitl": 0, "debate_wins": 0, "citations_new": 0}
        for row in rows:
            etype, _severity, count = row
            stats["total_events"] += count
            if etype == "guard_pass":
                stats["guard_pass"] += count
            elif etype == "guard_fail":
                stats["guard_fail"] += count
            elif etype == "hitl_override":
                stats["hitl"] += count
            elif etype == "debate_win":
                stats["debate_wins"] += count
            elif etype == "citation_new":
                stats["citations_new"] += count

        total_guard = stats["guard_pass"] + stats["guard_fail"]
        stats["guard_pass_rate"] = round(stats["guard_pass"] / total_guard, 4) if total_guard > 0 else 1.0
        total_req = stats["total_events"]
        stats["hitl_rate"] = round(stats["hitl"] / total_req, 4) if total_req > 0 else 0.0
        return stats

    def compute_ccs(self, agent: str, days: int = 30) -> float:
        """Compute Composite Clinical Score for an agent."""
        s = self.agent_stats(agent, days)
        if not s or s["total_events"] == 0:
            return 0.5
        ccs = (
            0.4 * s["guard_pass_rate"]
            + 0.3 * (1.0 - s["hitl_rate"])
            + 0.2 * min(1.0, s["citations_new"] / max(s["total_events"], 1) * 10)
            + 0.1 * min(1.0, s["debate_wins"] / max(s["total_events"], 1) * 10)
        )
        return round(ccs, 4)

    def time_decayed_weight(self, event_timestamp: float, now: float | None = None) -> float:
        now = now or time.time()
        age_days = (now - event_timestamp) / _SECONDS_PER_DAY
        if age_days > 365:
            return 0.0
        if age_days > 180:
            return 0.25
        if age_days > 90:
            return 0.5
        return 1.0

    def purge_old(self, days: int = 180):
        if self._conn:
            cutoff = time.time() - days * _SECONDS_PER_DAY
            self._conn.execute("DELETE FROM feedback_events WHERE timestamp < ?", (cutoff,))
            self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._ready = False
