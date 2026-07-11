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
from haip.a2a import call as a2a_call, get_history, call_with_loop  # noqa: E402
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
    """调用 Agent 工具。POST body: {"agent": "xxx", "tool": "xxx", "params": {...}}

    特殊工具名 "reason" 触发 ReAct AgentLoop 模式：
      {"agent": "antiemetic", "tool": "reason", "params": {"query": "评估P046的PONV风险"}}
    等价于直接 mode 参数：
      {"agent": "antiemetic", "tool": "ponv_risk_score", "mode": "reason", "params": {...}}
    """
    data = await request.json()
    agent = data.get("agent", "")
    tool = data.get("tool", "")
    params = data.get("params", {})
    mode = data.get("mode", "")

    if not agent:
        return JSONResponse({"status": "error", "error": "Missing agent"}, 400)
    if not tool and mode != "reason":
        return JSONResponse({"status": "error", "error": "Missing tool"}, 400)

    # R2: reason 模式 → AgentLoop
    if tool == "reason" or mode == "reason":
        query = params.get("query", "") or params.get("message", "")
        max_steps = params.get("max_steps", 5)
        result = call_with_loop(agent, query, max_steps)
        return result

    result = a2a_call(agent, tool, params)
    return result


@app.post("/api/loop/demo")
async def loop_demo(request: Request):
    """Loop Engineering 演示 — 使用 Mock LLM 展示 ReAct 多步推理过程。
    
    返回每步的思考、工具调用和最终综合答案。
    """
    from haip.agent import get as _get_agent
    from haip.llm.mock import MockProvider
    from haip.llm import ChatResponse, ToolCall
    from haip.a2a import call as _a2a_call

    # 模拟 LLM 的多步推理
    class DemoLLM(MockProvider):
        def __init__(self):
            super().__init__({})
            self._step = [0]

        def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
            step = self._step[0]
            self._step[0] += 1
            tool_names = [t["name"] for t in (tools or [])]

            if step == 0 and "ponv_risk_score" in tool_names:
                return ChatResponse(tool_calls=[
                    ToolCall(id="s1", name="ponv_risk_score", arguments={
                        "gender": "F", "smoking": "\u5426",
                        "ponv_history": "\u6709", "motion_sickness": "\u65e0",
                        "opioid_planned": "\u662f", "age": 45,
                    })
                ], content="\u5148\u8bc4\u4f30\u60a3\u8005\u7684 PONV \u98ce\u9669\u7b49\u7ea7\u3002")
            elif step == 1 and "antiemetic_regimen" in tool_names:
                return ChatResponse(tool_calls=[
                    ToolCall(id="s2", name="antiemetic_regimen", arguments={
                        "risk_level": "high", "risk_score": 4,
                    })
                ], content="\u6839\u636e\u9ad8\u98ce\u9669\u7ed3\u679c\uff0c\u63a8\u8350\u6b62\u5410\u7528\u836f\u65b9\u6848\u3002")
            elif step == 2 and "antiemetic_validate" in tool_names:
                return ChatResponse(tool_calls=[
                    ToolCall(id="s3", name="antiemetic_validate", arguments={
                        "regimen": {"drugs": [
                            {"name": "\u5e15\u6d1b\u8bfa\u53f8\u743c", "class": "5-HT3\u53d7\u4f53\u62ee\u6297\u5242"},
                            {"name": "\u5730\u585e\u7c73\u677e", "class": "\u76ae\u8d28\u7c7b\u56fa\u9187"},
                            {"name": "\u6c1f\u54cc\u5229\u591a", "class": "\u591a\u5df4\u80fa\u53d7\u4f53\u62ee\u6297\u5242"},
                        ]}
                    })
                ], content="\u6700\u540e\u5ba1\u6838\u7528\u836f\u65b9\u6848\u662f\u5426\u5b58\u5728\u7981\u5fcc\u8bc1\u3002")
            else:
                return ChatResponse(
                    content="\u60a3\u8005 Apfel \u8bc4\u5206 4 \u5206\uff0cPONV \u98ce\u9669 79%\uff08\u9ad8\u5371\uff09\u3002"
                            "\u63a8\u8350\u4e09\u8054\u7528\u836f\u65b9\u6848\uff1a\u5e15\u6d1b\u8bfa\u53f8\u743c 0.075mg IV\uff08\u9ebb\u9189\u8bf1\u5bfc\u524d\uff09"
                            " + \u5730\u585e\u7c73\u677e 8mg IV\uff08\u9ebb\u9189\u8bf1\u5bfc\u540e\uff09"
                            " + \u6c1f\u54cc\u5229\u591a 0.625mg IV\uff08\u624b\u672f\u7ed3\u675f\u524d\uff09\u3002"
                            "\u7528\u836f\u5ba1\u6838\u901a\u8fc7\uff0c\u65e0\u7981\u5fcc\u8bc1\u3002"
                )

    from haip.loop import AgentLoop

    agent = "antiemetic"
    plugin = _get_agent(agent)
    if not plugin:
        return JSONResponse({"status": "error", "error": "antiemetic agent not loaded"}, 500)

    tools = [{"name": t.name, "description": t.description, "input": t.input}
             for t in plugin.tools]

    def _exec(name, args):
        return _a2a_call(agent, name, args)

    loop = AgentLoop(
        llm=DemoLLM(),
        system_prompt=plugin.prompt.system,
        tool_executor=_exec,
        tools=tools,
        max_steps=5,
        agent_name=agent,
    )
    result = loop.run("\u8bc4\u4f30\u60a3\u8005 PONV \u98ce\u9669\u5e76\u63a8\u8350\u5b8c\u6574\u7528\u836f\u65b9\u6848\uff0c\u786e\u4fdd\u65e0\u7981\u5fcc\u8bc1\u3002")

    return {
        "demo": True,
        "query": "\u8bc4\u4f30\u60a3\u8005 PONV \u98ce\u9669\u5e76\u63a8\u8350\u5b8c\u6574\u7528\u836f\u65b9\u6848\uff0c\u786e\u4fdd\u65e0\u7981\u5fcc\u8bc1\u3002",
        "total_steps": result.steps,
        "duration_ms": result.duration_ms,
        "tool_calls": result.tool_calls,
        "partial_summaries": result.partial_summaries,
        "final_answer": result.reply,
        "explanation": {
            "pattern": "ReAct (\u63a8\u7406 Reasoning + \u6267\u884c Acting) Loop",
            "flow": [
                "Step 1: LLM \u5224\u65ad\u9700\u8981\u8bc4\u5206 \u2192 tool_call: ponv_risk_score",
                "Step 2: LLM \u770b\u5230\u9ad8\u5371\u7ed3\u679c \u2192 tool_call: antiemetic_regimen",
                "Step 3: LLM \u6709\u4e86\u65b9\u6848 \u2192 tool_call: antiemetic_validate",
                "Step 4: LLM \u770b\u5230\u5ba1\u6838\u901a\u8fc7 \u2192 \u7efc\u5408\u56de\u7b54",
            ],
            "key_features": [
                "\u591a\u6b65\u81ea\u4e3b\u89c4\u5212: LLM \u81ea\u884c\u51b3\u5b9a\u8c03\u7528\u54ea\u4e9b\u5de5\u5177\u3001\u4ec0\u4e48\u987a\u5e8f",
                "\u5de5\u5177\u7ed3\u679c\u63a8\u7406: \u6bcf\u6b65 tool result \u56de\u9988\u7ed9 LLM \u4f5c\u4e3a\u4e0b\u4e00\u6b65\u51b3\u7b56\u4f9d\u636e",
                "\u6e29\u5ea6\u9000\u706b: step1=0.3 \u2192 step2=0.4 \u2192 step3+=0.5 \u8d8a\u6df1\u5165\u8d8a\u5141\u8bb8\u63a2\u7d22",
                "Token \u9884\u7b97: \u8d85\u8fc7 32000 tokens \u81ea\u52a8\u4e2d\u6b62",
                "\u7ed3\u679c\u6458\u8981\u5316: tool \u8f93\u51fa\u622a\u65ad\u81f3 500 \u5b57\u7b26\uff0c\u53bb\u9664\u5143\u6570\u636e",
            ],
        },
    }


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




# ── Orthopedic v1 API ──

@app.post("/api/v1/orthopedic/classify")
async def ortho_classify(request: Request):
    """骨折分型 (Garden/Evans/AO)"""
    data = await request.json()
    from modules.orthopedics import assess
    return assess(**data)

@app.post("/api/v1/orthopedic/assess")
async def ortho_assess(request: Request):
    """术前综合评估"""
    data = await request.json()
    from modules.orthopedics import evaluate
    return evaluate(**data)

@app.post("/api/v1/orthopedic/plan")
async def ortho_plan(request: Request):
    """手术方案推荐"""
    data = await request.json()
    from modules.orthopedics import plan
    return plan(**data)

@app.post("/api/v1/orthopedic/timing")
async def ortho_timing(request: Request):
    """T2 手术时机决策"""
    data = await request.json()
    from modules.orthopedics import evaluate_timing
    return evaluate_timing(**data)

@app.post("/api/v1/orthopedic/complications")
async def ortho_complications(request: Request):
    """并发症风险预测"""
    data = await request.json()
    from modules.orthopedics import predict_complications
    return predict_complications(**data)

@app.post("/api/v1/orthopedic/mdt")
async def ortho_mdt(request: Request):
    """MDT 多学科会诊聚合"""
    data = await request.json()
    from modules.orthopedics.mdt import mdt_aggregate
    return mdt_aggregate(**data)

@app.post("/api/v1/orthopedic/pain")
async def ortho_pain(request: Request):
    """疼痛评估"""
    data = await request.json()
    from modules.pain_management import assess_pain
    return assess_pain(**data)

@app.post("/api/v1/orthopedic/rehab")
async def ortho_rehab(request: Request):
    """康复跟踪"""
    data = await request.json()
    from modules.orthopedics.extended import rehab_track
    return rehab_track(**data)

@app.post("/api/v1/orthopedic/followup")
async def ortho_followup(request: Request):
    """随访计划"""
    data = await request.json()
    from modules.orthopedics import followup_plan
    return followup_plan(**data)


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
