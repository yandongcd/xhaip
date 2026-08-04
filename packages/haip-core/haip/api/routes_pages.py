"""页面渲染路由 — 从 web_server 拆出 (P1-6).

/patients /stats /workflow /agent /ortho /ortho-portal /pharmacy /process
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from haip.agent import _registry
from haip.agent import get as get_agent
from haip.patients import load_patients

router = APIRouter(tags=["pages"])

_HERE = Path(__file__).resolve().parent.parent


def _render_workflow(request: Request, name: str) -> str:
    from haip.ui_workflow import build_workflow_ui_context, render_workflow_ui
    p = get_agent(name)
    if not p:
        raise HTTPException(404, detail={"error": f"Agent '{name}' not found"})
    wf_stages, roles = build_workflow_ui_context(p)
    return render_workflow_ui(
        name=p.name, cn_name=p.cn_name, agent_type=p.type, port=p.port,
        tools=[{"name": t.name, "description": t.description} for t in p.tools],
        workflow_stages=wf_stages, roles=roles,
        guard_triggers=p.guard.triggers)


@router.get("/patients")
def patients_legacy(q: str = "", agent: str = ""):
    """[DEPRECATED] 使用 /api/patients/{agent_name} 替代。"""
    from haip.web_server import case_mgr
    if agent:
        # 按 Agent 兼容的科室过滤
        results = case_mgr.search(query=agent, limit=30) if agent else case_mgr.search(limit=50)
    elif q:
        results = case_mgr.search(query=q, limit=50)
    else:
        results = case_mgr.cases[:50]
    return results


@router.get("/stats")
def stats_legacy():
    """[DEPRECATED] 使用 /api/health 替代。"""
    from haip.a2a import get_history
    from haip.web_server import case_mgr
    return {"agents_loaded": len(_registry), "call_history": len(get_history(0)),
            "patients_loaded": len(case_mgr.cases)}


@router.get("/workflow/{name}", response_class=HTMLResponse)
def workflow_ui(request: Request, name: str):
    """工作流感知 UI — 三栏工作台 (角色筛选 + 阶段执行 + 数字病人)."""
    from haip.workflow import get_workflow
    wf = get_workflow(name)
    if not wf:
        raise HTTPException(404, detail={"error": f"No workflow for '{name}'"})
    return HTMLResponse(_render_workflow(request, name))


@router.get("/agent/{name}", response_class=HTMLResponse)
def agent_ui(request: Request, name: str):
    """通用 Agent 专业 UI — Jinja2 模板渲染。"""
    p = get_agent(name)
    if not p:
        raise HTTPException(404, detail={"error": f"Agent '{name}' not found"})
    from haip.web_server import templates
    patients = load_patients(name, limit=50) if name != "metrics" else []
    role_emoji = {
        "attending": "🏥", "resident": "🩺", "surgeon": "🔪",
        "anesthesiologist": "😴", "icu_doctor": "💚", "head_nurse": "👩‍⚕️",
        "instrument_nurse": "🛠️", "rehab_therapist": "🦾",
        "pharmacist": "💊", "technician": "🔬", "head": "👤",
    }
    agent_data = {
        "name": p.name, "cn_name": p.cn_name, "type": p.type, "port": p.port,
        "tools": [{"name": t.name, "description": t.description, "input": t.input} for t in p.tools],
        "depends_on": p.depends_on, "guard": {"triggers": p.guard.triggers},
        "sub_agents": p.sub_agents,
        "stages": p.get_stages(),
        "ui": {
            "roles": [{"id": r["id"], "label": r["label"], "emoji": role_emoji.get(r["id"], "👤")} for r in p.ui.roles],
        },
    }
    patient_list = [{"patient_id": pt.get("patient_id", ""), "name": pt.get("name", "?"), "age": pt.get("age", 0), "diagnosis": pt.get("diagnosis", ""), "department": pt.get("department", ""), "lab_results": pt.get("lab_results", {}), "scenario": pt.get("scenario", "")} for pt in (patients or [])[:50]]
    content = templates.env.get_template("agent.html").render(
        request=request, agent=agent_data, patients=patient_list)
    return HTMLResponse(content)


@router.get("/ortho", response_class=HTMLResponse)
def ortho_ui():
    """创伤骨科专业界面 — 15 Tab 临床工作台。"""
    with open(_HERE / "ui_ortho.html", encoding="utf-8") as f:
        return f.read()


@router.get("/ortho-portal", response_class=HTMLResponse)
def ortho_portal_ui():
    """创伤骨科诊疗门户 — KPI 看板 + AI 诊疗能力卡 + 患者队列 + 流程时间轴。"""
    with open(_HERE / "ui_ortho_portal.html", encoding="utf-8") as f:
        return f.read()


@router.get("/pharmacy", response_class=HTMLResponse)
def pharmacy_ui(request: Request):
    """药剂科专业界面 — TPN 计算器 + 处方审查。"""
    from haip.web_server import templates
    content = templates.env.get_template("pharmacy.html").render(request=request)
    return HTMLResponse(content)


@router.get("/process/{name}", response_class=HTMLResponse)
def process_ui(request: Request, name: str):
    """诊疗流程 UI — 三栏工作台 (角色 tab + 阶段执行)."""
    return HTMLResponse(_render_workflow(request, name))
