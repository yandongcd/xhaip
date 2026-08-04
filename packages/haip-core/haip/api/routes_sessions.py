"""会话管理 API — 从 web_server 拆出 (P1-6).

会话 user 作用域强制取自 JWT 身份, 客户端参数不可信 (IDOR 防护).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


def _get_session_db_path() -> str:
    data_dir = _PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "sessions.db")


def _session_user_id(request: Request) -> str:
    """从 JWT 身份派生会话 user 作用域 — 客户端参数不可信 (IDOR 修复)。

    匿名/无身份请求 (如 dev 免登录之外的兜底) 归入稳定伪用户 "anonymous",
    所有匿名用户共享同一作用域, 但认证用户之间完全隔离。
    """
    user = getattr(request.state, "current_user", None)
    if user and user.get("user_id"):
        return str(user["user_id"])
    return "anonymous"


@router.post("")
def create_session(request: Request, payload: dict = Body(default_factory=dict)):
    """创建新会话. POST body: {"state": {...}} — 用户身份取自 JWT, 忽略 body.user_id."""
    from haip.session.store import SessionService
    svc = SessionService(_get_session_db_path())
    s = svc.create_session(
        user_id=_session_user_id(request),
        state=payload.get("state"),
    )
    return {"session_id": s.id, "created_at": s.last_update}


@router.get("/{session_id}")
def get_session(session_id: str, request: Request):
    """获取会话详情（含 events 和 state）— 会话按当前认证用户作用域隔离."""
    from haip.session.store import SessionService
    svc = SessionService(_get_session_db_path())
    s = svc.get_session(session_id, user_id=_session_user_id(request))
    if s is None:
        raise HTTPException(status_code=404, detail={"error": "Session not found"})
    return {
        "session_id": s.id, "user_id": s.user_id,
        "state": s.state,
        "events": [e.to_dict() for e in s.events[-50:]],
        "last_update": s.last_update,
        "token_estimate": s.token_estimate(),
    }


@router.get("")
def list_sessions(request: Request, limit: int = 20):
    """列出当前认证用户的会话列表 (user 作用域取自 JWT, 忽略客户端参数)."""
    from haip.session.store import SessionService
    svc = SessionService(_get_session_db_path())
    return svc.list_sessions(user_id=_session_user_id(request), limit=limit)


@router.post("/{session_id}/rewind")
def rewind_session(session_id: str, request: Request,
                   payload: dict = Body(default_factory=dict)):
    """回滚会话到指定事件数. POST body: {"keep_events": 5} — 会话归属校验同 get_session."""
    from haip.session.store import SessionService
    svc = SessionService(_get_session_db_path())
    s = svc.get_session(session_id, user_id=_session_user_id(request))
    if s is None:
        raise HTTPException(status_code=404, detail={"error": "Session not found"})
    svc.rewind_session(s, payload.get("keep_events", 0))
    return {"session_id": s.id, "events_remaining": len(s.events)}
