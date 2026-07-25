"""Agent Memory & Continuous Learning — 持续探索.

Records agent decisions and outcomes, enabling experience-based improvement.
Lightweight: SQLite-backed, no external dependencies.

Usage:
    memory = AgentMemory()
    memory.record("pharmacy", "P001", {"tool":"assess_nutrition","result":"ok"})
    insights = memory.insights("pharmacy")  # {"success_rate":0.92,"common_errors":[...]}
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import time
from collections import Counter
from typing import Any


class AgentMemory:
    """Persistent agent decision memory with insights generation."""

    def __init__(self, db_path: str = ""):
        if db_path:
            self.db_path = pathlib.Path(db_path)
        else:
            self.db_path = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "xhaip_memory.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    patient_id TEXT NOT NULL,
                    tool TEXT,
                    input_params TEXT,
                    result TEXT,
                    status TEXT NOT NULL DEFAULT 'ok',
                    confidence REAL DEFAULT 0.0,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dec_agent ON decisions(agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dec_time ON decisions(timestamp)")
            conn.commit()

    def record(self, agent: str, patient_id: str, tool: str = "",
               params: dict | None = None, result: dict | None = None,
               status: str = "ok", confidence: float = 0.0):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO decisions (agent, patient_id, tool, input_params, result, status, confidence, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (agent, patient_id, tool,
                 json.dumps(params or {}, ensure_ascii=False),
                 json.dumps(result or {}, ensure_ascii=False),
                 status, confidence, time.time())
            )
            conn.commit()

    def insights(self, agent: str, days: int = 30) -> dict[str, Any]:
        """Generate insights for an agent based on past decisions."""
        cutoff = time.time() - days * 86400
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM decisions WHERE agent = ? AND timestamp > ? ORDER BY timestamp DESC",
                (agent, cutoff)
            ).fetchall()

        if not rows:
            return {"agent": agent, "total_decisions": 0, "insight": "暂无足够数据"}

        total = len(rows)
        ok_count = sum(1 for r in rows if r["status"] == "ok")
        error_count = total - ok_count
        success_rate = ok_count / total if total > 0 else 0

        # Common tools
        tools = Counter(r["tool"] for r in rows if r["tool"])
        common_tools = tools.most_common(5)

        # Average confidence
        confidences = [r["confidence"] for r in rows if r["confidence"] > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Recent errors
        errors = [{"tool": r["tool"], "patient": r["patient_id"], "time": r["timestamp"]}
                  for r in rows if r["status"] != "ok"][:5]

        return {
            "agent": agent,
            "total_decisions": total,
            "success_rate": round(success_rate, 3),
            "error_count": error_count,
            "avg_confidence": round(avg_confidence, 3),
            "common_tools": [{"tool": t, "count": c} for t, c in common_tools],
            "recent_errors": errors,
            "learning_status": "active" if total > 10 else "insufficient_data",
        }

    def global_insights(self) -> dict[str, Any]:
        """Cross-agent insights for TOGAF governance."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT agent, status, COUNT(*) as cnt FROM decisions GROUP BY agent, status").fetchall()

        agent_stats = {}
        for r in rows:
            if r["agent"] not in agent_stats:
                agent_stats[r["agent"]] = {"total": 0, "ok": 0, "error": 0}
            agent_stats[r["agent"]][r["status"]] = r["cnt"]
            agent_stats[r["agent"]]["total"] += r["cnt"]

        # Top performers
        rankings = []
        for agent, stats in agent_stats.items():
            if stats["total"] > 0:
                rate = stats["ok"] / stats["total"]
                rankings.append({"agent": agent, "success_rate": round(rate, 3), "total": stats["total"]})
        rankings.sort(key=lambda x: x["success_rate"], reverse=True)

        return {
            "agents_tracked": len(agent_stats),
            "total_decisions": sum(s["total"] for s in agent_stats.values()),
            "top_performers": rankings[:5],
            "needs_attention": [r for r in rankings if r["success_rate"] < 0.7],
        }


_memory: AgentMemory | None = None


def get_memory() -> AgentMemory:
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory
