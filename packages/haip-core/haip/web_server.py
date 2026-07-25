"""xhaip Web Server — FastAPI 生产级 HTTP API + Web UI.

启动: python -m uvicorn haip.web_server:app --port 8769
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # xhaip root
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital" / "modules"))

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from haip.agent import load_from_dir, _registry, get as get_agent  # noqa: E402
from haip.a2a import call as a2a_call, get_history, call_with_loop, stream_events  # noqa: E402
from haip.guard.verifier import GuardVerifier  # noqa: E402
from haip.knowledge.runtime import get_kb  # noqa: E402
from haip.knowledge.cases import CaseManager  # noqa: E402

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    return os.environ.get("HAIP_ENV", "development") == "production"


def _get_cors_origins() -> list[str]:
    """Resolve CORS allow origins: config.server.cors_origins in production, else ['*'].
    In production, if config still says ['*'], fall back to ['http://localhost:8769'].
    """
    if not _is_production():
        return ["*"]
    try:
        from haip.config import get_config
        origins = get_config().get("server.cors_origins", ["http://localhost:8769"])
        if origins == ["*"] or "*" in origins:
            logger.warning(
                "生产环境 CORS 仍为 ['*'], 已强制回退到 localhost (请修正 config/haip.yaml)")
            return ["http://localhost:8769"]
        return origins
    except Exception:
        logger.warning("加载 CORS 配置失败, 回退到 localhost", exc_info=True)
        return ["http://localhost:8769"]


def _get_rate_limit_config() -> dict:
    """Resolve rate limit settings.
    Production: default enabled. Development: default disabled (overridable by config key).
    """
    prod = _is_production()
    try:
        from haip.config import get_config
        sec = get_config().get_section("security")
        if prod:
            enabled = True
        else:
            enabled = bool(sec.get("rate_limit_enabled", False))
        return {
            "enabled": enabled,
            "rate": sec.get("rate_limit_per_minute", 100),
            "burst": sec.get("rate_limit_burst", 20),
            "window": sec.get("rate_limit_window_sec", 60),
        }
    except Exception:
        return {
            "enabled": prod,
            "rate": 100,
            "burst": 20,
            "window": 60,
        }


def _seed_default_admin():
    """Create default admin user if no users exist."""
    from haip.auth import get_auth_service
    auth = get_auth_service()
    if not auth.list_users():
        admin_pass = os.environ.get("HAIP_ADMIN_PASSWORD", "Admin@123456")
        doctor_pass = os.environ.get("HAIP_DOCTOR_PASSWORD", "Doctor@123")
        try:
            auth.create_user(
                username="admin",
                password=admin_pass,
                display_name="系统管理员",
                roles=["admin"],
            )
        except ValueError as e:
            logger.warning("admin 默认用户创建失败: %s", e)
        try:
            auth.create_user(
                username="doctor",
                password=doctor_pass,
                display_name="演示医生",
                roles=["doctor"],
            )
        except ValueError as e:
            logger.warning("doctor 默认用户创建失败: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 安全基线检查 (HAIP_ENV=production 时违规阻断启动)
    from haip.security_baseline import check_security_baseline
    check_security_baseline()
    _seed_default_admin()
    from haip.auth import get_auth_service
    get_auth_service().seed_demo_identities()
    # Initialize default tenant
    from haip.tenants import init_default_tenant
    init_default_tenant()
    # Initialize database
    try:
        from haip.database import init_database, create_tables
        init_database()
        await create_tables()
    except Exception:
        logger.warning("数据库初始化失败 (非生产环境可忽略)", exc_info=True)
    yield
    # Shutdown
    try:
        from haip.database import close_database
        await close_database()
    except Exception:
        logger.debug("数据库关闭异常", exc_info=True)


app = FastAPI(title="xhaip v1.2 API", version="1.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware — validates JWT on protected routes
from haip.auth.middleware import AuthMiddleware  # noqa: E402
app.add_middleware(AuthMiddleware)

# Audit middleware — records all API calls
from haip.audit.middleware import AuditMiddleware  # noqa: E402
app.add_middleware(AuditMiddleware)

# Metrics middleware — records HTTP request metrics
from haip.metrics import MetricsMiddleware  # noqa: E402
app.add_middleware(MetricsMiddleware)

# Rate limit middleware — production-default enabled
from haip.rate_limit import RateLimitMiddleware  # noqa: E402
rl_cfg = _get_rate_limit_config()
app.add_middleware(
    RateLimitMiddleware,
    rate=rl_cfg["rate"],
    burst=rl_cfg["burst"],
    window=rl_cfg["window"],
    enabled=rl_cfg["enabled"],
)

# Auth API router
from haip.auth import auth_router  # noqa: E402
app.include_router(auth_router)

# Audit API router
from haip.audit import audit_router  # noqa: E402
app.include_router(audit_router)

# Prometheus metrics endpoint
from haip.metrics import setup_metrics  # noqa: E402
setup_metrics(app)

# FHIR API router
from haip.fhir import fhir_router  # noqa: E402
app.include_router(fhir_router)

# Tenant API router
from haip.tenants.api import tenant_router  # noqa: E402
app.include_router(tenant_router)

# License API router
from haip.licensing.api import license_router  # noqa: E402
app.include_router(license_router)

# TOGAF template API
from haip.togaf.templates.engine import get_togaf_engine  # noqa: E402
togaf_engine = get_togaf_engine()


@app.get("/api/togaf/templates")
def list_togaf_templates():
    """List all available TOGAF architecture templates."""
    return togaf_engine.list_all()


@app.get("/api/togaf/templates/{template_id}")
def render_togaf_template(template_id: str):
    """Render a TOGAF template as HTML."""
    html = togaf_engine.render(template_id)
    if html is None:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": f"Template not found: {template_id}"}, 404)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)


@app.get("/api/leanix/export")
def leanix_export():
    """Export LeanIX fact sheets as JSON."""
    from haip.togaf.leanix import auto_discover
    exporter = auto_discover()
    return exporter.to_leanix_json()

# Prometheus metrics endpoint
from haip.metrics import setup_metrics  # noqa: E402
setup_metrics(app)

# Structured logging — setup on import
try:
    from haip.logging_utils import setup_logging
    setup_logging()
except ImportError:
    pass
except Exception:
    logger.debug("logging_utils 初始化失败", exc_info=True)

YAML_DIR = PROJECT_ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
from haip.patients import PATIENTS_FILE  # noqa: E402  # 患者数据路径单一真相源

# 启动时加载所有 Agent（含 TOGAF 校验）
load_from_dir(str(YAML_DIR))
# Initialize A2A service auth secrets for all agents
try:
    from haip.a2a.auth import init_agent_secrets
    from haip.agent import _registry as _agent_registry
    init_agent_secrets(list(_agent_registry.keys()))
except ImportError:
    logger.debug("A2A auth secrets 模块不可用, 跳过")
except Exception:
    logger.warning("A2A auth secrets 初始化失败", exc_info=True)
# TOGAF validation — run after all agents loaded so CHK-004 dependency graph sees full registry
try:
    from haip.togaf.validator import validate_all  # noqa: E402
    reports = validate_all(registry=_registry)
    for r in reports:
        if not r.passed:
            failed = [c.id for c in r.checks if not c.passed]
            logger.info(
                "TOGAF [WARN] %s: %d checks failed — %s", r.agent_name, len(failed), failed)
except ImportError:
    pass
except Exception:
    logger.warning("TOGAF validation 失败", exc_info=True)
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


# ── SSE 流式端点 (v1.2) ──

@app.get("/api/sse")
async def stream_get(request: Request):
    """SSE GET 端点 — 用于浏览器 EventSource.

    Query params: ?agent=antiemetic&query=评估PONV&max_steps=5&session_id=xxx
    """
    agent = request.query_params.get("agent", "")
    query = request.query_params.get("query", "")
    max_steps = int(request.query_params.get("max_steps", "5"))
    session_id = request.query_params.get("session_id", "default")
    user_id = request.query_params.get("user_id", "default")

    if not agent or not query:
        return JSONResponse({"status": "error", "error": "Missing agent or query"}, 400)

    return StreamingResponse(
        stream_events(agent, query, max_steps, session_id, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/stream-demo", response_class=HTMLResponse)
def stream_demo():
    """SSE 流式调试页面 — 实时查看 Agent 推理过程的每个 Event."""
    return (Path(__file__).parent / "templates" / "stream.html").read_text(encoding="utf-8")


# ── API Key 配置 (web 端 DEEPSEEK_API_KEY 管理) ──

@app.get("/api/config/llm")
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


@app.post("/api/config/llm")
async def llm_config_set(request: Request):
    """设置 API key: {"api_key": "sk-...", "clear": false}。持久化到 data/llm_key.json。"""
    data = await request.json()
    from haip.api_key_store import clear_api_key, set_api_key
    if data.get("clear"):
        clear_api_key()
        return {"status": "ok", "configured": False, "message": "API key 已清除"}
    key = data.get("api_key", "").strip()
    if not key:
        return JSONResponse({"status": "error", "error": "api_key 不能为空"}, 400)
    set_api_key(key)
    return {"status": "ok", "configured": True, "masked_key": key[:3] + "***" + key[-4:],
            "message": "API key 已保存, 下次 LLM 调用生效"}


@app.post("/api/stream")
async def stream_call(request: Request):
    """SSE 流式 AgentLoop — 每步实时推送 Event (state_delta + content).

    前端通过 EventSource 接收:
      event: step
      data: {"author":"assistant","content":"...","state_delta":{...}}

    POST body: {"agent": "antiemetic", "query": "评估PONV风险", "max_steps": 5,
                "session_id": "optional"}
    """
    data = await request.json()
    agent = data.get("agent", "")
    query = data.get("query", "") or data.get("params", {}).get("query", "")
    max_steps = data.get("max_steps", 5)
    session_id = data.get("session_id", "default")
    user_id = data.get("user_id", "default")

    if not agent or not query:
        return JSONResponse({"status": "error", "error": "Missing agent or query"}, 400)

    return StreamingResponse(
        stream_events(agent, query, max_steps, session_id, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Session API (v1.2) ──

@app.post("/api/sessions")
async def create_session(request: Request):
    """创建新会话. POST body: {"user_id": "doctor1", "state": {...}}"""
    from haip.session.store import SessionService
    data = await request.json()
    svc = SessionService(_get_session_db_path())
    s = svc.create_session(
        user_id=data.get("user_id", "default"),
        state=data.get("state"),
    )
    return {"session_id": s.id, "created_at": s.last_update}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, user_id: str = "default"):
    """获取会话详情（含 events 和 state）."""
    from haip.session.store import SessionService
    svc = SessionService(_get_session_db_path())
    s = svc.get_session(session_id, user_id=user_id)
    if s is None:
        return JSONResponse({"error": "Session not found"}, 404)
    return {
        "session_id": s.id, "user_id": s.user_id,
        "state": s.state,
        "events": [e.to_dict() for e in s.events[-50:]],
        "last_update": s.last_update,
        "token_estimate": s.token_estimate(),
    }


@app.get("/api/sessions")
async def list_sessions(user_id: str = "default", limit: int = 20):
    """列出用户的会话列表."""
    from haip.session.store import SessionService
    svc = SessionService(_get_session_db_path())
    return svc.list_sessions(user_id=user_id, limit=limit)


@app.post("/api/sessions/{session_id}/rewind")
async def rewind_session(session_id: str, request: Request):
    """回滚会话到指定事件数. POST body: {"keep_events": 5}"""
    from haip.session.store import SessionService
    data = await request.json()
    svc = SessionService(_get_session_db_path())
    s = svc.get_session(session_id)
    if s is None:
        return JSONResponse({"error": "Session not found"}, 404)
    svc.rewind_session(s, data.get("keep_events", 0))
    return {"session_id": s.id, "events_remaining": len(s.events)}


def _get_session_db_path() -> str:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "sessions.db")


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


GUIDELINE_DIRS = [
    PROJECT_ROOT / "packages" / "haip-hospital" / "knowledge" / "guidelines",
    PROJECT_ROOT / "knowledge" / "guidelines",
]

_citation_engine = None


def _get_citation_engine():
    """模块级单例 — 索引指南资产库, 供 /api/guard 引文验证。"""
    global _citation_engine
    if _citation_engine is None:
        from haip.guard.citation import CitationEngine
        engine = CitationEngine()
        for d in GUIDELINE_DIRS:
            if d.exists():
                engine.index_guidelines(d)
        _citation_engine = engine
    return _citation_engine


@app.post("/api/guard")
async def guard_verify(request: Request):
    """对 Agent 输出执行 Guard 安全验证。需人工复核时自动创建签核单。"""
    data = await request.json()
    output = data.get("output", "")
    scenario = data.get("scenario", "")
    agent_name = data.get("agent", "")
    patient_id = data.get("patient_id", "")
    cross = data.get("cross_agent_outputs", [])
    v = GuardVerifier(citation_engine=_get_citation_engine())
    result = v.verify(output, scenario=scenario, agent_name=agent_name,
                      cross_agent_outputs=cross if cross else None)
    signoff_id = ""
    if result.requires_human_review:
        try:
            from haip.signoff import get_signoff_manager
            signoff_id = get_signoff_manager().create(
                agent=agent_name, tool=scenario or "guard",
                patient_id=patient_id, output_summary=output,
                risk_level="high" if not result.passed else "medium")
        except Exception as e:
            logging.getLogger(__name__).warning("签核单创建失败: %s", e)
    return {
        "passed": result.passed,
        "flags": result.flags,
        "citations": [{"source": c.source, "trust_level": c.trust_level, "verified": c.verified}
                     for c in result.citations],
        "confidence": result.confidence.value if result.confidence else None,
        "requires_human_review": result.requires_human_review,
        "cross_validation_conflict": result.cross_validation_conflict,
        "signoff_id": signoff_id,
    }


# ── 医生签核工作流 (M3 / C1) ──

@app.get("/api/signoff/pending")
def signoff_pending(limit: int = 100):
    """待签核队列。"""
    from haip.signoff import get_signoff_manager
    return {"items": get_signoff_manager().list_pending(limit)}


@app.get("/api/signoff/patient/{patient_id}")
def signoff_by_patient(patient_id: str, limit: int = 100):
    """患者维度签核留痕 (病历视角)。"""
    from haip.signoff import get_signoff_manager
    return {"items": get_signoff_manager().list_by_patient(patient_id, limit)}


@app.post("/api/signoff/{signoff_id}/decision")
async def signoff_decide(signoff_id: str, request: Request):
    """签核决定: {"decision": "approved|rejected", "reason": "..."}

    签核人身份强制取自认证上下文 (request.state.current_user), 请求体的
    reviewer_id 仅在无认证上下文时 (AUTH_ENABLED=false 的开发模式) 生效 —
    防止伪造签核人 (商用红线)。
    """
    data = await request.json()
    user = getattr(request.state, "current_user", None) or {}
    reviewer = user.get("user_id") or data.get("reviewer_id", "")
    from haip.signoff import get_signoff_manager
    try:
        return get_signoff_manager().decide(
            signoff_id,
            reviewer_id=reviewer,
            decision=data.get("decision", ""),
            reason=data.get("reason", ""))
    except ValueError as e:
        return JSONResponse({"status": "error", "error": str(e)}, 400)


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


@app.get("/ortho-portal", response_class=HTMLResponse)
def ortho_portal_ui():
    """创伤骨科诊疗门户 — KPI 看板 + AI 诊疗能力卡 + 患者队列 + 流程时间轴。"""
    with open(Path(__file__).parent / "ui_ortho_portal.html", encoding="utf-8") as f:
        return f.read()


@app.get("/pharmacy", response_class=HTMLResponse)
def pharmacy_ui():
    """药剂科专业界面 — 处方审核 + 药物交互可视化。"""
    from haip.ui_pharmacy import render_pharmacy_ui
    return render_pharmacy_ui()


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


# ── Home Redirect — role-based routing (R1a) ──

@app.get("/home")
def home_redirect(request: Request):
    """Role-based home redirect for 12 portal identities.

    Priority: Bearer JWT roles > ?role= > ?identity= (mapped via PORTAL_IDENTITY_ROLES).
    """
    from fastapi.responses import RedirectResponse
    from haip.auth.models import PORTAL_IDENTITY_ROLES

    role: str | None = None

    # Priority 1: Bearer JWT
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from haip.auth.jwt import decode_token
            payload = decode_token(auth_header[7:])
            roles = payload.get("roles", [])
            if roles:
                role = roles[0]
        except Exception as e:
            logging.getLogger(__name__).debug("/home JWT 解析失败, 回退 query 参数: %s", e)

    # Priority 2: ?role= query param
    if role is None:
        role = request.query_params.get("role")

    # Priority 3: ?identity= query param → map via PORTAL_IDENTITY_ROLES
    if role is None:
        identity = request.query_params.get("identity")
        if identity and identity in PORTAL_IDENTITY_ROLES:
            role = PORTAL_IDENTITY_ROLES[identity]

    if role is None:
        return RedirectResponse(url="/", status_code=302)

    # Role → URL mapping (agent routes confirmed against agents/definitions/)
    ROLE_ROUTES: dict[str, str] = {
        "leadership": "/dashboard",
        "dept_head": "/dashboard",
        "pharmacist": "/pharmacy",
        "head_nurse": "/agent/nurse-general",
        "nurse": "/agent/nurse-general",
        "anesthesiologist": "/agent/anesthesia-risk",
        "med_tech": "/agent/lab-critical-value",
        "intern": "/agent/education",
        "resident": "/",
        "doctor": "/",
        "admin": "/",
    }

    target = ROLE_ROUTES.get(role, "/")
    return RedirectResponse(url=target, status_code=302)


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
