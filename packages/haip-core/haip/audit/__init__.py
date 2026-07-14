"""Audit Logging — tracks all security-relevant operations.

Provides:
    - AuditEvent model for structured audit records
    - AuditLogger for recording events
    - AuditMiddleware to auto-capture API calls
    - In-memory store (PostgreSQL-backed in P1)

Events tracked:
    - User login/logout
    - Agent tool calls (who called what with what params)
    - Patient data access
    - Configuration changes
    - Failed authentication attempts
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AuditEvent:
    """A single audit record."""

    event_id: str
    timestamp: float
    action: str  # login | logout | agent_call | patient_access | config_change | auth_failed
    user_id: Optional[str]
    username: Optional[str]
    resource: str  # agent:pharmacy | patient:PT-0234 | config:haip.yaml
    status: str    # success | failure | denied
    detail: dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    session_id: str = ""


class AuditLogger:
    """Records and queries audit events."""

    def __init__(self, max_events: int = 100000):
        self._events: list[AuditEvent] = []
        self._max_events = max_events

    def log(
        self,
        action: str,
        resource: str,
        status: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        detail: Optional[dict[str, Any]] = None,
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
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events // 2:]
        return event

    def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events with filters."""
        results = self._events
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
        """Clear all audit events."""
        self._events.clear()


# Global singleton
_audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger singleton."""
    return _audit_logger


# ── Audit API ──

from fastapi import APIRouter, Depends, Query

from haip.auth.middleware import get_current_user
from haip.auth.rbac import has_permission, Permission

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
