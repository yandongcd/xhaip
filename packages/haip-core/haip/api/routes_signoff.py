"""医生签核工作流 API — 从 web_server 拆出 (P1-6)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from haip.auth.models import Permission
from haip.auth.rbac import require_permission

router = APIRouter(prefix="/api/signoff", tags=["signoff"])


@router.get("/pending")
def signoff_pending(limit: int = 100):
    """待签核队列。"""
    from haip.signoff import get_signoff_manager
    return {"items": get_signoff_manager().list_pending(limit)}


@router.get("/patient/{patient_id}")
def signoff_by_patient(patient_id: str, limit: int = 100):
    """患者维度签核留痕 (病历视角)。"""
    from haip.signoff import get_signoff_manager
    return {"items": get_signoff_manager().list_by_patient(patient_id, limit)}


@router.post("/{signoff_id}/decision")
def signoff_decide(signoff_id: str, request: Request, payload: dict = Body(default_factory=dict),
                   _: dict = Depends(require_permission(Permission.AGENT_EXECUTE))):
    """签核决定: {"decision": "approved|rejected", "reason": "..."}

    签核人身份强制取自认证上下文 (request.state.current_user), 请求体的
    reviewer_id 仅在无认证上下文时 (AUTH_ENABLED=false 的开发模式) 生效 —
    防止伪造签核人 (商用红线)。要求 AGENT_EXECUTE 权限 (医生及以上)。
    """
    user = getattr(request.state, "current_user", None) or {}
    reviewer = user.get("user_id") or payload.get("reviewer_id", "")
    from haip.signoff import get_signoff_manager
    try:
        return get_signoff_manager().decide(
            signoff_id,
            reviewer_id=reviewer,
            decision=payload.get("decision", ""),
            reason=payload.get("reason", ""))
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
