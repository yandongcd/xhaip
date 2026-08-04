"""LLM 配置与流式端点 — 从 web_server 拆出 (P1-6)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from haip.auth.models import Permission
from haip.auth.rbac import require_permission

router = APIRouter(tags=["llm"])


class LLMConfigRequest(BaseModel):
    api_key: str = Field(default="", description="DeepSeek API Key")
    clear: bool = Field(default=False, description="是否清除已保存的Key")


class StreamRequest(BaseModel):
    agent: str = Field(..., min_length=1, description="Agent名称")
    query: str = Field(default="", description="用户查询")
    max_steps: int = Field(default=5, ge=1, le=50, description="最大推理步数")
    session_id: str = Field(default="default", description="会话ID")
    user_id: str = Field(default="default", description="用户ID")
    mode: str = Field(default="", description="调用模式 (reason)")
    params: dict = Field(default={}, description="工具参数(包含 query 备用)")


@router.get("/api/sse")
async def stream_get(request: Request):
    """SSE GET 端点 — 用于浏览器 EventSource.

    Query params: ?agent=antiemetic&query=评估PONV&max_steps=5&session_id=xxx
    """
    from haip.web_server import stream_events

    agent = request.query_params.get("agent", "")
    query = request.query_params.get("query", "")
    max_steps = int(request.query_params.get("max_steps", "5"))
    session_id = request.query_params.get("session_id", "default")
    user_id = request.query_params.get("user_id", "default")

    if not agent or not query:
        raise HTTPException(status_code=400, detail={"status": "error", "error": "Missing agent or query"})

    from haip.a2a import permission_context_from_user
    perm_ctx = permission_context_from_user(
        getattr(request.state, "current_user", None))

    return StreamingResponse(
        stream_events(agent, query, max_steps, session_id, user_id, perm_ctx=perm_ctx),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream-demo", response_class=HTMLResponse)
def stream_demo():
    """SSE 流式调试页面 — 实时查看 Agent 推理过程的每个 Event."""
    return (Path(__file__).resolve().parent.parent / "templates" / "stream.html").read_text(encoding="utf-8")


@router.get("/api/config/llm")
def llm_config_status():
    """LLM 配置状态 (API key 是否已配置, 不暴露实际值)。"""
    from haip.api_key_store import get_api_key
    key = get_api_key()
    return {
        "configured": bool(key),
        "provider": "deepseek",
        "model": "deepseek-chat",
        "masked_key": (key[:3] + "***" + key[-4:]) if len(key) > 8 else "",
    }


@router.post("/api/config/llm")
def llm_config_set(body: LLMConfigRequest, _: dict = Depends(require_permission(Permission.ADMIN_CONFIG))):
    """设置 API key。持久化到 data/llm_key.json。仅 ADMIN_CONFIG 权限。"""
    from haip.api_key_store import clear_api_key, set_api_key
    if body.clear:
        clear_api_key()
        return {"status": "ok", "configured": False, "message": "API key 已清除"}
    key = body.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail={"status": "error", "error": "api_key 不能为空"})
    set_api_key(key)
    return {"status": "ok", "configured": True, "masked_key": key[:3] + "***" + key[-4:],
            "message": "API key 已保存, 下次 LLM 调用生效"}


@router.post("/api/stream")
async def stream_call(body: StreamRequest, request: Request):
    """SSE 流式 AgentLoop — 每步实时推送 Event.

    POST body: {"agent": "antiemetic", "query": "评估PONV风险", "max_steps": 5}
    """
    from haip.web_server import stream_events

    agent = body.agent
    query = body.query or body.params.get("query", "")
    max_steps = body.max_steps
    session_id = body.session_id
    # 会话 user 作用域取自 JWT 身份 (body.user_id 保持兼容但不可信, 忽略之)
    _user = getattr(request.state, "current_user", None)
    user_id = str(_user["user_id"]) if _user and _user.get("user_id") else "anonymous"

    if not agent or not query:
        raise HTTPException(status_code=400, detail={"status": "error", "error": "Missing agent or query"})

    from haip.a2a import permission_context_from_user
    perm_ctx = permission_context_from_user(
        getattr(request.state, "current_user", None))

    return StreamingResponse(stream_events(agent, query, max_steps, session_id, user_id, perm_ctx=perm_ctx),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
