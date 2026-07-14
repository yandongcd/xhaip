"""Rule governance — change request workflow, approval/rejection.

Ported from haip-0710's src/agents/rules/governance.py.
"""

from __future__ import annotations

from datetime import datetime

from haip.rules_engine.models import ChangeRequest, ChangeStatus, ImpactReport

_CHANGE_REQUESTS: dict[str, ChangeRequest] = {}


def create_change_request(impact_report: ImpactReport) -> ChangeRequest:
    """Create a new change request from an impact report."""
    request_id = f"cr-{impact_report.source_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cr = ChangeRequest(
        id=request_id,
        impact_report=impact_report,
        status=ChangeStatus.PENDING,
        created_at=datetime.now().isoformat(),
    )
    _CHANGE_REQUESTS[request_id] = cr
    return cr


def get_pending_changes() -> list[ChangeRequest]:
    """Get all pending change requests."""
    return [c for c in _CHANGE_REQUESTS.values() if c.status == ChangeStatus.PENDING]


def get_change_request(request_id: str) -> ChangeRequest | None:
    """Get a specific change request by ID."""
    return _CHANGE_REQUESTS.get(request_id)


def approve_change(request_id: str, reviewed_by: str = "", note: str = "") -> bool:
    """Approve a pending change request."""
    cr = _CHANGE_REQUESTS.get(request_id)
    if not cr or cr.status != ChangeStatus.PENDING:
        return False
    cr.status = ChangeStatus.APPROVED
    cr.reviewed_at = datetime.now().isoformat()
    cr.reviewed_by = reviewed_by
    cr.note = note
    return True


def reject_change(request_id: str, reviewed_by: str = "", reason: str = "") -> bool:
    """Reject a pending change request."""
    cr = _CHANGE_REQUESTS.get(request_id)
    if not cr or cr.status != ChangeStatus.PENDING:
        return False
    cr.status = ChangeStatus.REJECTED
    cr.reviewed_at = datetime.now().isoformat()
    cr.reviewed_by = reviewed_by
    cr.note = reason
    return True


def list_all_changes() -> list[ChangeRequest]:
    """List all change requests regardless of status."""
    return list(_CHANGE_REQUESTS.values())
