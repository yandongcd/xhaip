"""知识库 API — 从 web_server 拆出 (P1-6)."""

from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/stats")
def knowledge_stats():
    from haip.web_server import PROJECT_ROOT, case_mgr, get_kb
    kb = get_kb(str(PROJECT_ROOT))
    cases = case_mgr.stats()
    return {"knowledge": kb.stats(), "cases": cases}


@router.get("/search")
def knowledge_search(q: str = "", limit: int = 20):
    from haip.web_server import PROJECT_ROOT, case_mgr, get_kb
    kb = get_kb(str(PROJECT_ROOT))
    g_results = kb.search_guidelines(q) if q else []
    c_results = case_mgr.search(query=q, limit=limit) if q else []
    return {"guidelines": g_results[:limit], "cases": c_results[:limit]}
