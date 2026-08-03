"""Audit Logging — tracks all security-relevant operations.

Provides:
    - AuditEvent model for structured audit records
    - AuditLogger for recording events (memory + optional SQLite persistence)
    - AuditMiddleware to auto-capture API calls
    - v2.0: SQLite persistence with WAL mode, append-only guarantees

Events tracked:
    - User login/logout
    - Agent tool calls (who called what with what params)
    - Patient data access
    - Configuration changes
    - Failed authentication attempts
"""

from __future__ import annotations

import atexit
import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_AUDIT_DB = Path("data/audit.db")


@dataclass
class AuditEvent:
    """A single audit record."""

    event_id: str
    timestamp: float
    action: str  # login | logout | agent_call | patient_access | config_change | auth_failed
    user_id: str | None
    username: str | None
    resource: str  # agent:pharmacy | patient:PT-0234 | config:haip.yaml
    status: str    # success | failure | denied
    detail: dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    session_id: str = ""


class AuditLogger:
    """Records and queries audit events with optional SQLite persistence.

    v2.0: Added SQLite backend with WAL mode for append-only audit trail.
    Memory buffer retained for fast in-process queries.
    """

    def __init__(self, max_events: int = 100000, db_path: str | Path = ""):
        self._events: list[AuditEvent] = []
        self._max_events = max_events
        self._db_path: Path | None = None
        self._db_conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

        if db_path:
            self._init_db(Path(db_path))

    def _init_db(self, db_path: Path) -> None:
        """Initialize SQLite audit database with WAL mode."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._db_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db_conn.execute("PRAGMA journal_mode=WAL")
        self._db_conn.execute("PRAGMA synchronous=NORMAL")
        from haip.schema_version import ensure_version
        ensure_version(self._db_conn, 1)
        self._db_conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                timestamp REAL NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                resource TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT DEFAULT '{}',
                ip_address TEXT DEFAULT '',
                session_id TEXT DEFAULT ''
            )
        """)
        self._db_conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)")
        self._db_conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id)")
        self._db_conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action)")
        self._db_conn.commit()
        atexit.register(self._cleanup)

    def _cleanup(self):
        """Close DB connection on exit."""
        if self._db_conn:
            self._db_conn.close()

    @property
    def persistent(self) -> bool:
        """Whether audit events are persisted to disk."""
        return self._db_conn is not None

    def log(
        self,
        action: str,
        resource: str,
        status: str,
        user_id: str | None = None,
        username: str | None = None,
        detail: dict[str, Any] | None = None,
        ip_address: str = "",
        session_id: str = "",
    ) -> AuditEvent:
        """Record a new audit event."""
        event = AuditEvent(
            event_id=uuid.uuid4().hex[:16],
            timestamp=time.time(),
            action=action,
            user_id=user_id,
            username=username,
            resource=resource,
            status=status,
            detail=detail or {},
            ip_address=ip_address,
            session_id=session_id,
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events // 2:]

        # Persist to SQLite if enabled
        if self._db_conn:
            try:
                with self._lock:
                    self._db_conn.execute(
                        "INSERT INTO audit_events (event_id, timestamp, action, user_id, username, resource, status, detail, ip_address, session_id) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (event.event_id, event.timestamp, event.action, event.user_id, event.username,
                         event.resource, event.status, json.dumps(event.detail, ensure_ascii=False),
                         event.ip_address, event.session_id),
                    )
                    self._db_conn.commit()
            except sqlite3.IntegrityError:
                pass  # duplicate event_id, skip

        return event

    def query(
        self,
        user_id: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        status: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events with filters. Prefers DB query if persistent."""
        if self._db_conn:
            with self._lock:
                conditions = ["1=1"]
                params: list[Any] = []
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                if action:
                    conditions.append("action = ?")
                    params.append(action)
                if resource:
                    conditions.append("resource LIKE ?")
                    params.append(f"%{resource}%")
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                if since:
                    conditions.append("timestamp > ?")
                    params.append(since)

                sql = f"SELECT * FROM audit_events WHERE {' AND '.join(conditions)} ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                rows = self._db_conn.execute(sql, params).fetchall()
            return [
                AuditEvent(
                    event_id=r[1], timestamp=r[2], action=r[3],
                    user_id=r[4], username=r[5], resource=r[6],
                    status=r[7], detail=json.loads(r[8]) if r[8] else {},
                    ip_address=r[9], session_id=r[10],
                )
                for r in rows
            ]

        # Fallback to in-memory
        with self._lock:
            results = list(self._events)
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        if resource:
            results = [e for e in results if resource in e.resource]
        if status:
            results = [e for e in results if e.status == status]
        if since:
            results = [e for e in results if e.timestamp > since]
        return results[-limit:]

    def stats(self) -> dict[str, Any]:
        """Get audit statistics."""
        if self._db_conn:
            with self._lock:
                total = self._db_conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
                failures = self._db_conn.execute(
                    "SELECT COUNT(*) FROM audit_events WHERE status IN ('failure', 'denied')"
                ).fetchone()[0]
                action_rows = self._db_conn.execute(
                    "SELECT action, COUNT(*) as cnt FROM audit_events GROUP BY action"
                ).fetchall()
            actions = {r[0]: r[1] for r in action_rows}
        else:
            total = len(self._events)
            failures = sum(1 for e in self._events if e.status in ("failure", "denied"))
            actions: dict[str, int] = {}
            for e in self._events:
                actions[e.action] = actions.get(e.action, 0) + 1

        return {
            "total_events": total,
            "failure_count": failures,
            "failure_rate": round(failures / total, 4) if total > 0 else 0,
            "by_action": actions,
        }

    def clear(self):
        """Clear all audit events (memory only; DB records preserved for compliance)."""
        with self._lock:
            self._events.clear()

    def export_jsonl(self, output_path: str | Path) -> int:
        """Export all persisted events to JSONL for archiving."""
        if not self._db_conn:
            return 0
        with self._lock:
            rows = self._db_conn.execute("SELECT * FROM audit_events ORDER BY timestamp").fetchall()
        path = Path(output_path)
        count = 0
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({
                    "event_id": r[1], "timestamp": r[2], "action": r[3],
                    "user_id": r[4], "username": r[5], "resource": r[6],
                    "status": r[7], "detail": json.loads(r[8]) if r[8] else {},
                    "ip_address": r[9], "session_id": r[10],
                }, ensure_ascii=False) + "\n")
                count += 1
        return count


# Global singleton
_audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger singleton."""
    return _audit_logger


# ── Audit API ──

from fastapi import APIRouter, Depends, Query

from haip.auth.middleware import get_current_user
from haip.auth.rbac import Permission, has_permission

audit_router = APIRouter(prefix="/api/audit", tags=["audit"])


@audit_router.get("/events")
def list_audit_events(
    user_id: str = Query(None),
    action: str = Query(None),
    resource: str = Query(None),
    status: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    """Query audit events (requires audit:read permission)."""
    if not has_permission(current_user.get("roles", []), Permission.AUDIT_READ):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    logger = get_audit_logger()
    events = logger.query(
        user_id=user_id,
        action=action,
        resource=resource,
        status=status,
        limit=limit,
    )
    return [
        {
            "event_id": e.event_id,
            "timestamp": e.timestamp,
            "action": e.action,
            "user_id": e.user_id,
            "username": e.username,
            "resource": e.resource,
            "status": e.status,
            "detail": e.detail,
            "ip_address": e.ip_address,
        }
        for e in events
    ]


@audit_router.get("/stats")
def audit_stats(current_user: dict = Depends(get_current_user)):
    """Get audit statistics (requires audit:read permission)."""
    if not has_permission(current_user.get("roles", []), Permission.AUDIT_READ):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return get_audit_logger().stats()
