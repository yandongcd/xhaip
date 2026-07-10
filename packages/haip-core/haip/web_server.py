"""xhaip Web Server — FastAPI 生产级 HTTP API + Web UI.

启动: python -m uvicorn haip.web_server:app --port 8769
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # xhaip root
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital" / "modules"))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from haip.agent import load_from_dir, _registry, get as get_agent  # noqa: E402
from haip.a2a import call as a2a_call, get_history  # noqa: E402
from haip.guard.verifier import GuardVerifier  # noqa: E402
from haip.knowledge.runtime import get_kb  # noqa: E402
from haip.knowledge.cases import CaseManager  # noqa: E402

app = FastAPI(title="xhaip v1.0 API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

YAML_DIR = PROJECT_ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
PATIENTS_FILE = PROJECT_ROOT / "packages" / "haip-hospital" / "data" / "patients.json"

# 启动时加载所有 Agent（含 TOGAF 校验）
def _togaf_on_register(plugin) -> None:
    """TOGAF architecture validation callback — runs on each agent registration."""
    try:
        from haip.togaf.validator import validate_agent
        report = validate_agent(plugin.name, registry=_registry)
        if report and not report.passed:
            failed = [c.id for c in report.checks if not c.passed]
            import sys
            print(f"  [TOGAF] ⚠ {plugin.name}: {len(failed)} checks failed — {failed}", file=sys.stderr)
    except Exception:
        pass  # Silent — TOGAF validation is best-effort at startup

load_from_dir(str(YAML_DIR), on_register=_togaf_on_register)
case_mgr = CaseManager()
if PATIENTS_FILE.exists():
    case_mgr.load(PATIENTS_FILE.parent)
# ── API Endpoints ──

@app.get("/api/agents")
def list_agents():
    """列出所有注册的 Agent 及其工具。"""
    agents = []
    for name, p in _registry.items():
        agents.append({
            "name": p.name, "cn_name": p.cn_name, "type": p.type,
            "port": p.port, "department": p.department, "version": p.version,
            "tools": [{"name": t.name, "description": t.description} for t in p.tools],
            "depends_on": p.depends_on, "sub_agents": p.sub_agents, "parent": p.parent,
        })
    return agents


@app.get("/api/agents/{name}")
def agent_info(name: str):
    """获取单个 Agent 的详细信息。"""
    p = get_agent(name)
    if not p:
        return JSONResponse({"error": f"Agent '{name}' not found"}, 404)
    return {
        "name": p.name, "cn_name": p.cn_name, "type": p.type,
        "port": p.port, "department": p.department, "version": p.version,
        "tools": [{"name": t.name, "description": t.description, "handler": t.handler,
                    "input": t.input} for t in p.tools],
        "guard": {"triggers": p.guard.triggers, "high_risk_scenarios": p.guard.high_risk_scenarios},
        "ui": {"template": p.ui.template, "roles": p.ui.roles, "sidebar": p.ui.sidebar},
    }


@app.post("/api/call")
async def call_tool(request: Request):
    """调用 Agent 工具。POST body: {"agent": "xxx", "tool": "xxx", "params": {...}}"""
    data = await request.json()
    agent = data.get("agent", "")
    tool = data.get("tool", "")
    params = data.get("params", {})
    if not agent or not tool:
        return JSONResponse({"status": "error", "error": "Missing agent or tool"}, 400)
    result = a2a_call(agent, tool, params)
    return result


@app.post("/api/guard")
async def guard_verify(request: Request):
    """对 Agent 输出执行 Guard 安全验证。"""
    data = await request.json()
    output = data.get("output", "")
    scenario = data.get("scenario", "")
    agent_name = data.get("agent", "")
    cross = data.get("cross_agent_outputs", [])
    v = GuardVerifier()
    result = v.verify(output, scenario=scenario, agent_name=agent_name,
                      cross_agent_outputs=cross if cross else None)
    return {
        "passed": result.passed,
        "flags": result.flags,
        "citations": [{"source": c.source, "trust_level": c.trust_level, "verified": c.verified}
                     for c in result.citations],
        "confidence": result.confidence.value if result.confidence else None,
        "requires_human_review": result.requires_human_review,
        "cross_validation_conflict": result.cross_validation_conflict,
    }


@app.get("/api/history")
def history(limit: int = 20):
    """获取 A2A 调用历史。"""
    return get_history(limit)


@app.get("/api/health")
def health():
    return {"status": "ok", "agents_loaded": len(_registry), "version": "1.0.0"}


# ── Knowledge API ──

@app.get("/api/knowledge/stats")
def knowledge_stats():
    kb = get_kb(str(PROJECT_ROOT))
    cases = case_mgr.stats()
    return {"knowledge": kb.stats(), "cases": cases}


@app.get("/api/knowledge/search")
def knowledge_search(q: str = "", limit: int = 20):
    kb = get_kb(str(PROJECT_ROOT))
    g_results = kb.search_guidelines(q) if q else []
    c_results = case_mgr.search(query=q, limit=limit) if q else []
    return {"guidelines": g_results[:limit], "cases": c_results[:limit]}


@app.get("/patients")
def patients_legacy(q: str = "", agent: str = ""):
    """向后兼容 demo 页面的 /patients 端点。"""
    if agent:
        # 按 Agent 兼容的科室过滤
        results = case_mgr.search(query=agent, limit=30) if agent else case_mgr.search(limit=50)
    elif q:
        results = case_mgr.search(query=q, limit=50)
    else:
        results = case_mgr.cases[:50]
    return results


@app.get("/stats")
def stats_legacy():
    """向后兼容 demo 页面的 /stats 端点。"""
    return {"agents_loaded": len(_registry), "call_history": len(get_history(0)),
            "patients_loaded": len(case_mgr.cases)}


# ── Workflow UI ──

@app.get("/workflow/{name}", response_class=HTMLResponse)
def workflow_ui(name: str):
    """工作流感知 UI — 角色过滤 + 阶段进度 + 自动数据传递。"""
    from haip.workflow import get_workflow
    from haip.ui_workflow import render_workflow_ui
    p = get_agent(name)
    if not p:
        return HTMLResponse(f"<h2>Agent '{name}' not found</h2>", 404)
    wf = get_workflow(name)
    if not wf:
        return HTMLResponse(f"<h2>No workflow defined for '{name}'</h2>", 404)
    html = render_workflow_ui(
        name=p.name, cn_name=wf["cn_name"], agent_type=p.type, port=p.port,
        tools=[{"name": t.name, "description": t.description, "input": t.input}
               for t in p.tools],
        workflow_stages=wf["stages"], roles=wf["roles"],
        guard_triggers=p.guard.triggers,
    )
    return HTMLResponse(html)


# ── 专业 Web UI ──

@app.get("/agent/{name}", response_class=HTMLResponse)
def agent_ui(name: str):
    """通用 Agent 专业 UI — 根据 YAML 定义自动渲染。"""
    from haip.ui_render import render_agent_ui
    p = get_agent(name)
    if not p:
        return HTMLResponse(f"<h2>Agent '{name}' not found</h2>", 404)
    html = render_agent_ui(
        name=p.name, cn_name=p.cn_name, agent_type=p.type, port=p.port,
        tools=[{"name": t.name, "description": t.description, "input": t.input}
               for t in p.tools],
        depends_on=p.depends_on, guard_triggers=p.guard.triggers,
        sub_agents=p.sub_agents,
    )
    return HTMLResponse(html)


@app.get("/ortho", response_class=HTMLResponse)
def ortho_ui():
    """创伤骨科专业界面 — 15 Tab 临床工作台。"""
    with open(Path(__file__).parent / "ui_ortho.html", encoding="utf-8") as f:
        return f.read()


@app.get("/pharmacy", response_class=HTMLResponse)
def pharmacy_ui():
    """药剂科专业界面 — 处方审核 + 药物交互可视化。"""
    from haip.ui_pharmacy import PHARMACY_TEMPLATE
    return PHARMACY_TEMPLATE


@app.get("/api/agent-ui/{agent_name}")
def agent_ui_config(agent_name: str):
    """快速 UI 生成器 — 根据 YAML 定义返回 UI 配置。"""
    p = get_agent(agent_name)
    if not p:
        return JSONResponse({"error": "not found"}, 404)
    tabs = []
    for tool in p.tools:
        tabs.append({"id": tool.name, "label": tool.name, "desc": tool.description,
                     "inputs": tool.input})
    return {"agent": p.name, "cn_name": p.cn_name, "type": p.type,
            "tabs": tabs, "roles": p.ui.roles, "sidebar": p.ui.sidebar}


# ── 诊疗流程 UI ──

@app.get("/process/{name}", response_class=HTMLResponse)
def process_ui(name: str):
    """诊疗流程 UI — 动态阶段 + 数字病人 + 角色切换。"""
    from haip.ui_process import render_process_ui
    p = get_agent(name)
    if not p:
        return HTMLResponse(f"<h2>Agent '{name}' not found</h2>", 404)
    html = render_process_ui(
        name=p.name, cn_name=p.cn_name, department=getattr(p, "department", ""),
        agent_type=p.type, roles=p.get_roles(), stages=p.get_stages(),
        guard_triggers=p.guard.triggers if hasattr(p, "guard") else [],
        depends_on=p.depends_on,
    )
    return HTMLResponse(html)


# ── TOGAF Architecture Dashboard ──

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """TOGAF 10 架构治理仪表盘 — 全院 39 科室成熟度热力图。"""
    from haip.togaf.dashboard import render_dashboard
    return HTMLResponse(render_dashboard())


@app.get("/api/dashboard")
def dashboard_api():
    """Dashboard data as JSON."""
    from haip.togaf.dashboard import render_dashboard_json
    return render_dashboard_json()

@app.get("/", response_class=HTMLResponse)
def index():
    """xhaip Web 门户 — Agent 管理 + 工具调用 + 聊天界面。"""
    return HTML_TEMPLATE


HTML_TEMPLATE = (Path(__file__).parent / "templates" / "index.html").read_text(encoding="utf-8")
