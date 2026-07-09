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


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip v1.0 — Hospital AI Platform</title>
<style>
/* ===== Gold Standard Design Tokens (radiology-cockpit SKILL) ===== */
:root{--bg:#1c1c1e;--card-bg:#2c2c2e;--text:#f5f5f7;--text-secondary:#a1a1a6;--accent:#0a84ff;--danger:#ff453a;--warning:#ff9f0a;--success:#30d158;--purple:#bf5af2;--green:#30d158;--yellow:#ff9f0a;--red:#ff453a;--border:#38383a;--glow:rgba(10,132,255,.08);--bg-gradient:radial-gradient(ellipse at 50% 0%,var(--card-bg) 0%,var(--bg) 60%)}
body.light{--bg:#f2f2f7;--card-bg:#ffffff;--text:#1c1c1e;--text-secondary:#6e6e73;--accent:#007aff;--danger:#ff3b30;--warning:#ff9500;--success:#34c759;--purple:#af52de;--green:#34c759;--yellow:#ff9500;--red:#ff3b30;--border:#e5e5ea;--bg-gradient:radial-gradient(ellipse at 50% 0%,#ffffff 0%,#f2f2f7 60%)}
body.light .sidebar{background:var(--card-bg);border-right:1px solid var(--border)}
body.light .sidebar h2{color:var(--text)}
body.light .agent-item{color:var(--text-secondary);border-bottom:1px solid var(--border)}
body.light .agent-item .meta{color:var(--text-secondary)}
body.light .agent-item:hover{background:rgba(0,122,255,.04);color:var(--text)}
body.light .header-btn:hover{background:var(--accent);color:#fff}
body.light .agent-item.active{background:rgba(0,122,255,.08);border-left-color:var(--accent);color:var(--text)}
body.light .tag-biz{background:rgba(0,122,255,.12);color:var(--accent)}
body.light .tag-spec{background:rgba(52,199,89,.12);color:var(--success)}
body.light .tag-master{background:rgba(175,82,222,.12);color:var(--purple)}
body.light .result-panel{background:var(--bg);color:var(--text);border-left:1px solid var(--border)}
body.light .chat-agent{background:var(--card-bg);border:1px solid var(--border)}
body.light .section-label{color:var(--text-secondary)}
body.light #sidebar-stats{color:var(--text-secondary);border-top:1px solid var(--border)}
body.light .header-btn:hover{background:var(--accent);color:#fff}
*{margin:0;padding:0;box-sizing:border-box}
::selection{background:var(--accent);color:#fff}
body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text','PingFang SC','Microsoft YaHei','Helvetica Neue',sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;background:var(--bg-gradient);color:var(--text);display:flex;height:100vh;overflow:hidden;letter-spacing:-.01em;transition:background .3s ease,color .3s ease}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}

/* Sidebar */
.sidebar{width:260px;background:linear-gradient(180deg,#1a1a1a,#2B2B2B);color:#fff;display:flex;flex-direction:column;overflow-y:auto;transition:all .3s ease}
.sidebar h2{padding:16px;font-size:16px;font-weight:600;letter-spacing:-.02em;border-bottom:1px solid rgba(255,255,255,.1)}
.agent-list{flex:1;overflow-y:auto}
.agent-item{padding:12px 16px;cursor:pointer;border-bottom:1px solid rgba(255,255,255,.05);transition:background .15s;color:#fff}
.agent-item:hover{background:rgba(255,255,255,.08)}
.agent-item.active{background:rgba(10,132,255,.2);border-left:3px solid var(--accent)}
.agent-item .name{font-size:13px;font-weight:600}
.agent-item .meta{font-size:10px;color:rgba(255,255,255,.5);margin-top:2px}
.tag{display:inline-block;padding:1px 6px;border-radius:10px;font-size:9px;margin-right:4px;font-weight:600}
.tag-biz{background:rgba(10,132,255,.3);color:#93C5FD}
.tag-spec{background:rgba(48,209,88,.3);color:#86EFAC}
.tag-master{background:rgba(191,90,242,.3);color:#C4B5FD}
.section-label{padding:8px 16px;font-size:10px;color:rgba(255,255,255,.4);text-transform:uppercase;letter-spacing:.04em;font-weight:500}

/* Main */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.main-header{height:52px;padding:0 20px;background:var(--card-bg);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;font-size:15px;font-weight:600;flex-shrink:0;-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px)}
.header-btn{padding:5px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card-bg);color:var(--text);cursor:pointer;font-size:11px;font-weight:500;font-family:inherit;transition:all .15s}
.header-btn:hover{background:var(--accent);color:#fff;border-color:var(--accent);transform:scale(1.02)}
.header-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}

/* Left panel - tools */
.tool-panel{flex:1;padding:16px 20px;overflow-y:auto;display:flex;flex-direction:column;gap:12px}
.tool-panel h3{font-size:13px;color:var(--accent);font-weight:600}
.tool-panel select,.tool-panel textarea,.tool-panel input{padding:8px 12px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:13px;width:100%;font-family:inherit;outline:none;transition:border-color .15s}
.tool-panel select:focus,.tool-panel textarea:focus,.tool-panel input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(10,132,255,.12)}
.tool-panel textarea{height:100px;font-family:'SF Mono',SFMono-Regular,Consolas,monospace;resize:vertical;line-height:1.5}
.btn{padding:8px 18px;border:none;border-radius:8px;font-size:13px;font-weight:590;cursor:pointer;font-family:inherit;transition:all .12s ease}
.btn:active{transform:scale(.96)}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{opacity:.9;box-shadow:0 4px 12px rgba(10,132,255,.3)}
.btn-secondary{background:var(--purple);color:#fff}.btn-secondary:hover{opacity:.9}
.row{display:flex;gap:8px;align-items:center}

/* Right panel - result */
.result-panel{width:460px;background:var(--bg);color:var(--text);padding:16px 20px;overflow-y:auto;font-family:'SF Mono',SFMono-Regular,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;border-left:1px solid var(--border)}
.result-panel .ok{color:var(--success)}.result-panel .err{color:var(--danger)}.result-panel .key{color:var(--accent)}

/* Tabs */
.tabs{display:flex;gap:2px;background:var(--bg);border-radius:10px;padding:3px;margin-bottom:12px}
.tab{padding:7px 16px;border:none;background:transparent;font-size:12px;color:var(--text-secondary);cursor:pointer;border-radius:8px;font-weight:500;font-family:inherit;transition:all .15s cubic-bezier(0.4,0,0.2,1)}
.tab:hover{color:var(--text)}
.tab.active{background:var(--accent);color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.tab-content{display:none}
.tab-content.active{display:block;animation:fadeIn .15s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}

/* Chat */
.chat{flex:1;display:flex;flex-direction:column}
.chat-messages{flex:1;overflow-y:auto;padding:12px 0;display:flex;flex-direction:column;gap:10px}
.chat-msg{padding:10px 14px;border-radius:12px;font-size:13px;max-width:85%;line-height:1.5}
.chat-user{align-self:flex-end;background:var(--accent);color:#fff;border-bottom-right-radius:4px}
.chat-agent{align-self:flex-start;background:var(--card-bg);color:var(--text);border:1px solid var(--border);border-bottom-left-radius:4px}
.chat-input{padding:10px 0 0;border-top:1px solid var(--border);display:flex;gap:8px}
.chat-input input{flex:1;padding:8px 12px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.chat-input input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(10,132,255,.12)}
.chat-input input::placeholder{color:var(--text-secondary)}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#060d14}
.badge-green{background:var(--green)}.badge-yellow{background:var(--warning)}.badge-red{background:var(--red)}.badge-purple{background:var(--purple)}
.status-bar{padding:6px 20px;font-size:11px;color:var(--text-secondary);border-top:1px solid var(--border);background:var(--card-bg);display:flex;justify-content:space-between;flex-shrink:0}
</style>
</head>
<body>
<div class="sidebar">
  <h2>🏥 xhaip v1.0</h2>
  <div class="agent-list" id="agent-list"></div>
  <div style="padding:12px 16px;font-size:10px;color:rgba(255,255,255,.3);border-top:1px solid rgba(255,255,255,.1)" id="sidebar-stats"></div>
</div>
<div class="main">
  <div class="main-header">
    <span id="main-header">选择 Agent 开始</span>
    <button class="header-btn" id="btn-theme" onclick="toggleTheme()">🌙 黑夜</button>
  </div>
  <div class="content">
    <div class="tool-panel" id="tool-panel" style="display:none">
      <div class="tabs">
        <button class="tab active" onclick="switchTab('tools')">工具调用</button>
        <button class="tab" onclick="switchTab('chat')">聊天</button>
        <button class="tab" onclick="switchTab('guard')">Guard</button>
        <button class="tab" onclick="switchTab('meta')">元信息</button>
      </div>
      <div class="tab-content active" id="tab-tools">
        <h3>工具调用</h3>
        <select id="tool-select" onchange="onToolChange()"><option>-- 选择工具 --</option></select>
        <textarea id="params-input">{"patient_id":"P001"}</textarea>
        <div class="row">
          <button class="btn btn-primary" onclick="callTool()">执行</button>
          <button class="btn btn-secondary" onclick="guardVerify()">Guard 验证</button>
        </div>
      </div>
      <div class="tab-content" id="tab-chat">
        <div class="chat" style="flex:1;min-height:200px">
          <div class="chat-messages" id="chat-messages">
            <div class="chat-msg chat-agent">你好! 我是 AI 助手, 请描述你的问题。</div>
          </div>
          <div class="chat-input">
            <input id="chat-input" placeholder="输入消息..." onkeypress="if(event.key==='Enter')sendChat()">
            <button class="btn btn-primary" onclick="sendChat()">发送</button>
          </div>
        </div>
      </div>
      <div class="tab-content" id="tab-guard">
        <h3>Guard 安全验证</h3>
        <textarea id="guard-input" style="height:120px" placeholder="粘贴 Agent 输出进行安全验证...">建议进行 THA 手术, 时机 48h 内。参考: NICE NG37</textarea>
        <select id="guard-scenario" style="margin-top:8px">
          <option value="手术方案">手术方案</option><option value="抗凝管理">抗凝管理</option>
          <option value="麻醉评估">麻醉评估</option><option value="MDT分歧">MDT分歧</option>
        </select>
        <button class="btn btn-primary" style="margin-top:8px" onclick="runGuard()">运行 Guard</button>
      </div>
      <div class="tab-content" id="tab-meta">
        <h3>Agent 元信息</h3>
        <div id="meta-content" style="font-size:12px;color:var(--text-secondary);line-height:1.8"></div>
      </div>
    </div>
    <div class="result-panel" id="result-panel">选择 Agent 和工具后执行调用, 结果将在此显示。</div>
  </div>
  <div class="status-bar">
    <span id="status-left">就绪</span>
    <span id="status-right"></span>
  </div>
</div>

<script>
let currentAgent = null;
let agents = [];

(function(){var t=localStorage.getItem('xhaip_theme')||'dark';if(t==='light'){document.body.classList.add('light');document.getElementById('btn-theme').textContent='☀️ 白天'}})();
function toggleTheme(){var isLight=document.body.classList.toggle('light');localStorage.setItem('xhaip_theme',isLight?'light':'dark');document.getElementById('btn-theme').textContent=isLight?'☀️ 白天':'🌙 黑夜'}

async function init() {
  const r = await fetch('/api/agents');
  agents = await r.json();
  renderSidebar();
  document.getElementById('sidebar-stats').textContent = agents.length + ' agents loaded';
  document.getElementById('status-right').textContent = 'API v1.0 | ' + agents.length + ' agents';
}

function renderSidebar() {
  const groups = {business:[], specialist:[], master_data:[]};
  agents.forEach(a => groups[a.type]?.push(a));
  let html = '';
  for (const [type, label, tag] of [['business','Business','tag-biz'],['specialist','Specialist','tag-spec'],['master_data','Master Data','tag-master']]) {
    html += '<div class="section-label">'+label+'</div>';
    groups[type].forEach(a => {
      html += '<div class="agent-item" onclick="selectAgent(\''+a.name+'\')" id="item-'+a.name+'">';
      html += '<div class="name"><span class="tag '+tag+'">'+a.type.substring(0,4)+'</span> '+a.cn_name+'</div>';
      html += '<div class="meta">'+a.name+' | '+a.tools.length+' tools</div></div>';
    });
  }
  document.getElementById('agent-list').innerHTML = html;
}

function selectAgent(name) {
  document.querySelectorAll('.agent-item').forEach(el => el.classList.remove('active'));
  document.getElementById('item-'+name)?.classList.add('active');
  currentAgent = agents.find(a => a.name === name);
  document.getElementById('main-header').textContent = currentAgent.cn_name + ' (' + currentAgent.name + ')';
  document.getElementById('tool-panel').style.display = 'flex';
  document.getElementById('result-panel').textContent = 'Agent 已加载: ' + currentAgent.cn_name;

  const sel = document.getElementById('tool-select');
  sel.innerHTML = '<option value="">-- 选择工具 --</option>';
  currentAgent.tools.forEach(t => {
    sel.innerHTML += '<option value="'+t.name+'">'+t.name+': '+t.description+'</option>';
  });

  // Meta
  fetch('/api/agents/'+name).then(r=>r.json()).then(data => {
    document.getElementById('meta-content').innerHTML = '<pre style="font-size:11px">'+JSON.stringify(data,null,2)+'</pre>';
  });

  document.getElementById('status-left').textContent = '已选择: ' + currentAgent.cn_name;
}

function onToolChange() {
  const tool = document.getElementById('tool-select').value;
  if (!tool) return;
  const t = currentAgent.tools.find(x=>x.name===tool);
  if (t && t.input) {
    document.getElementById('params-input').value = JSON.stringify(t.input,null,2);
  }
}

async function callTool() {
  const tool = document.getElementById('tool-select').value;
  if (!tool || !currentAgent) return;
  document.getElementById('result-panel').textContent = '调用中...';
  let params = {};
  try { params = JSON.parse(document.getElementById('params-input').value); } catch(e) {
    document.getElementById('result-panel').textContent = 'JSON 格式错误: '+e.message; return;
  }
  const r = await fetch('/api/call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent:currentAgent.name,tool:tool,params:params})});
  const data = await r.json();
  document.getElementById('result-panel').textContent = JSON.stringify(data,null,2);
  document.getElementById('status-left').textContent = data.status==='ok'?'调用成功':'调用失败';
}

async function guardVerify() {
  const r = await fetch('/api/guard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
    output: document.getElementById('guard-input').value,
    scenario: document.getElementById('guard-scenario').value,
    agent: currentAgent?.name||''
  })});
  const data = await r.json();
  document.getElementById('result-panel').textContent = JSON.stringify(data,null,2);
}

async function runGuard() { await guardVerify(); }

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelector('.tab[onclick*="'+tab+'"]').classList.add('active');
  document.getElementById('tab-'+tab).classList.add('active');
}

async function sendChat() {
  const msg = document.getElementById('chat-input').value.trim();
  if (!msg) return;
  addChatMsg('user', msg);
  document.getElementById('chat-input').value = '';
  if (!currentAgent) { addChatMsg('agent','请先选择一个 Agent'); return; }
  const r = await fetch('/api/call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
    agent: currentAgent.name,
    tool: currentAgent.tools[0]?.name || '',
    params: {query:msg}
  })});
  const data = await r.json();
  const reply = data.status==='ok' ? JSON.stringify(data,null,2).slice(0,500) : 'Error: '+data.error;
  addChatMsg('agent', reply);
}

function addChatMsg(role, text) {
  const div = document.createElement('div');
  div.className = 'chat-msg chat-'+role;
  div.textContent = text;
  document.getElementById('chat-messages').appendChild(div);
  div.scrollIntoView();
}

init();
</script>
</body>
</html>"""
