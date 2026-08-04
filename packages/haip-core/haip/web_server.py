"""xhaip Web Server — FastAPI 生产级 HTTP API + Web UI.

启动: python -m uvicorn haip.web_server:app --port 8769
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # xhaip root
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital" / "modules"))

from contextlib import asynccontextmanager

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from haip.a2a import call as a2a_call
from haip.a2a import call_with_loop, get_history, stream_events
from haip.agent import _registry, load_from_dir
from haip.agent import get as get_agent
from haip.guard.verifier import GuardVerifier
from haip.knowledge.cases import CaseManager
from haip.knowledge.runtime import get_kb

logger = logging.getLogger(__name__)


# ── API Request Models ──

class CallRequest(BaseModel):
    agent: str = Field(..., min_length=1, description="Agent名称")
    tool: str = Field(default="", description="工具名称")
    params: dict = Field(default={}, description="工具参数")
    mode: str = Field(default="", description="调用模式 (空=直接调用, reason=ReAct循环)")


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



class GuardRequest(BaseModel):
    output: str = Field(default="", description="Agent输出文本")
    scenario: str = Field(default="", description="临床场景")
    agent: str = Field(default="", description="Agent名称")
    patient_id: str = Field(default="", description="患者ID")
    cross_agent_outputs: list[str] = Field(default=[], description="交叉验证Agent输出")


# ── Endpoints ──


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
        admin_pass = os.environ.get("HAIP_ADMIN_PASSWORD", "")
        doctor_pass = os.environ.get("HAIP_DOCTOR_PASSWORD", "")
        if _is_production():
            if not admin_pass:
                logger.error("HAIP_ADMIN_PASSWORD 未设置，生产环境拒绝创建默认用户")
                return
        if not admin_pass:
            admin_pass = "Admin@123456"
        if not doctor_pass:
            doctor_pass = "Doctor@123"
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
    # License 校验 (生产模式无效/过期 → 阻断启动; 开发模式仅告警)
    from haip.licensing import enforce_startup
    enforce_startup()
    _seed_default_admin()
    from haip.auth import get_auth_service
    get_auth_service().seed_demo_identities()
    # Initialize default tenant
    from haip.tenants import init_default_tenant
    init_default_tenant()
    # Initialize database
    try:
        from haip.database import create_tables, init_database
        init_database()
        await create_tables()
    except Exception:
        logger.warning("数据库初始化失败 (非生产环境可忽略)", exc_info=True)
    # Initialize RAG indices (Phase 1 — background, non-blocking)
    try:
        import threading
        t = threading.Thread(target=_init_rag, daemon=True)
        t.start()
    except Exception:
        logger.debug("RAG 初始化跳过", exc_info=True)
    yield
    # ── Graceful shutdown ──
    try:
        from haip.database import close_database
        await close_database()
    except Exception:
        logger.debug("数据库关闭异常", exc_info=True)
    try:
        from haip.auth import get_auth_service
        await get_auth_service().close()
    except Exception:
        logger.debug("Auth 服务关闭异常", exc_info=True)
    try:
        from haip.knowledge.runtime import get_kb
        kb = get_kb()
        if hasattr(kb, 'close'):
            kb.close()
    except Exception:
        logger.debug("Knowledge store 关闭异常", exc_info=True)
    try:
        from haip.session import SessionService
        if hasattr(SessionService, 'close'):
            if SessionService is not None:
                await SessionService.close()
    except Exception:
        logger.debug("Session service 关闭异常", exc_info=True)


app = FastAPI(title="xhaip v1.2 API", version="1.2.0", lifespan=lifespan)

# ── 按域拆分路由 (P1-6) ──
from haip.api import routes_knowledge, routes_ortho, routes_signoff

app.include_router(routes_ortho.router)
app.include_router(routes_signoff.router)
app.include_router(routes_knowledge.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 校验失败 → 400 (缺必需字段/类型错误视为客户端错误)."""
    from fastapi.responses import JSONResponse

    errors = [
        f"{'.'.join(str(x) for x in e['loc'] if x != 'body')}: {e['msg']}"
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content={"status": "error", "error": "; ".join(errors) or "Invalid request"},
    )

# Static files (CSS/JS)
from pathlib import Path as _Path

_static_dir = _Path(__file__).parent / "static"
if _static_dir.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Jinja2 templates for server-rendered pages
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = _Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware — records all API calls
from haip.audit.middleware import AuditMiddleware

app.add_middleware(AuditMiddleware)

# Metrics middleware — records HTTP request metrics
from haip.metrics import MetricsMiddleware

app.add_middleware(MetricsMiddleware)

# Rate limit middleware — production-default enabled
from haip.rate_limit import RateLimitMiddleware

rl_cfg = _get_rate_limit_config()
app.add_middleware(
    RateLimitMiddleware,
    rate=rl_cfg["rate"],
    burst=rl_cfg["burst"],
    window=rl_cfg["window"],
    enabled=rl_cfg["enabled"],
)

# Auth middleware — validates JWT on protected routes.
# 必须最后添加: Starlette 按添加顺序的逆序构建中间件栈, 最后添加的在外层先执行。
# 因此 Auth 最先运行并填充 request.state.current_user, 之后 Audit / RateLimit
# 读取用户身份时才不会拿到 None (IDOR 无关的 P1-2 中间件顺序修复)。
from haip.auth.middleware import AuthMiddleware
from haip.auth.models import Permission
from haip.auth.rbac import require_permission

app.add_middleware(AuthMiddleware)

# Auth API router
from haip.auth import auth_router

app.include_router(auth_router)

# Audit API router
from haip.audit import audit_router

app.include_router(audit_router)

# Prometheus metrics endpoint
from haip.metrics import setup_metrics

setup_metrics(app)

# FHIR API router
from haip.fhir import fhir_router

app.include_router(fhir_router)

# Tenant API router
from haip.tenants.api import tenant_router

app.include_router(tenant_router)

# License API router
from haip.licensing.api import license_router

app.include_router(license_router)

# ---- Patient API (async loading) ----
@app.get("/api/patients/{agent_name}")
def get_patients(agent_name: str, limit: int = 50, offset: int = 0):
    """Async patient loading with pagination — 使用共享 mtime 缓存."""
    from haip.patients import load_all_patients

    patients = load_all_patients()
    # Filter compatible patients
    compatible = []
    for p in patients:
        compat = p.get("compatible_agents", [])
        dept = p.get("department", "")
        if not compat or agent_name in compat or \
           agent_name.replace("-","") in dept.replace(" ","").lower():
            compatible.append({
                "patient_id": p.get("patient_id", ""),
                "name": p.get("name", p.get("patient_name", "")),
                "age": p.get("age", p.get("age_years", "")),
                "gender": p.get("gender", p.get("sex", "")),
                "diagnosis": p.get("diagnosis", p.get("primary_diagnosis", "")),
                "department": dept,
                "scenario": p.get("scenario", p.get("clinical_scenario", "")),
                "urgency": p.get("urgency", "normal"),
                "lab_results": p.get("lab_results", {}),
                "present": p.get("present", p.get("history_of_present_illness", "")),
                "followup": p.get("followup", ""),
                "plan": p.get("plan", ""),
                "execution": p.get("execution", ""),
                "assessments": p.get("assessments", []),
            })

    total = len(compatible)
    page = compatible[offset:offset + limit]
    return {"total": total, "patients": page, "offset": offset, "limit": limit}

# ---- ClinicalHarness 审计 ----
@app.get("/api/harness")
def harness_report():
    from haip.clinical_harness import ClinicalHarness
    return ClinicalHarness().run()

# ---- MetaHarness 五能力统一自检 ----
@app.get("/api/meta-harness")
def meta_harness_report():
    from haip.meta_harness import get_meta_harness
    return get_meta_harness().run_full_cycle()

# ---- Autonomous Decision ----
@app.post("/api/decide/{agent_name}")
def decide(agent_name: str, payload: dict = Body(default_factory=dict)):
    """自主决策: POST patient data, get clinical decision."""
    from haip.decision import get_decision_engine
    engine = get_decision_engine()
    return engine.decide(agent_name, payload)

# ---- Intelligent Planning ----
@app.post("/api/plan/{agent_name}")
def plan_workflow(agent_name: str, payload: dict = Body(default_factory=dict)):
    """智能规划: POST patient data, get dynamic workflow plan."""
    from haip.planner import get_workflow_planner
    planner = get_workflow_planner()
    return planner.plan(agent_name, payload)

# ---- Agent Memory & Insights ----
@app.get("/api/memory/insights/{agent_name}")
def agent_insights(agent_name: str):
    """Agent持续探索 — 决策历史洞察."""
    from haip.memory import get_memory
    return get_memory().insights(agent_name)

@app.get("/api/memory/global")
def global_insights():
    """全量Agent学习洞察 — TOGAF治理用."""
    from haip.memory import get_memory
    return get_memory().global_insights()

# ---- TOGAF Architecture Governance ----
_togaf_cache: dict | None = None
_togaf_cache_time: float = 0.0
_togaf_cache_ttl: float = 30.0
_togaf_cache_lock = threading.Lock()


@app.get("/api/togaf/governance")
def togaf_governance():
    """TOGAF架构治理视图 — Agent复用度、架构合规、原则应用 (30s TTL 缓存)."""
    global _togaf_cache, _togaf_cache_time

    now = time.monotonic()
    with _togaf_cache_lock:
        if _togaf_cache is not None and now - _togaf_cache_time < _togaf_cache_ttl:
            return _togaf_cache

    from collections import Counter
    from pathlib import Path as _Pth

    import yaml

    defs_dir = _Pth(__file__).resolve().parent.parent.parent.parent / "packages/haip-hospital/agents/definitions"

    # Agent reuse analysis
    deps_count = Counter()
    agent_types = Counter()
    stage_counts = []
    guard_agents = 0

    for yf in sorted(defs_dir.glob("*.yaml")):
        if yf.name.startswith("_") or ".deprecated" in yf.name or ".internal" in yf.name:
            continue
        with open(yf, encoding="utf-8") as f:
            a = yaml.safe_load(f)
        t = a.get("type", "business")
        agent_types[t] += 1
        stage_counts.append(len(a.get("stages", [])))
        if a.get("guard", {}).get("triggers"):
            guard_agents += 1
        for dep in a.get("depends_on", []):
            deps_count[dep.get("agent", "")] += 1

    # TOGAF principles applied
    principles = [
        {"id": "P1", "name": "YAML驱动Agent定义", "status": "applied", "metric": f"{len(list(defs_dir.glob('*.yaml')))} 个YAML定义"},
        {"id": "P2", "name": "引擎独立包", "status": "applied", "metric": "haip-core pip installable"},
        {"id": "P3", "name": "Guard门控安全", "status": "applied", "metric": f"{guard_agents}/{len(list(defs_dir.glob('*.yaml')))} Agent启用Guard"},
        {"id": "P4", "name": "Agent可复用", "status": "applied", "metric": f"{len([d for d,c in deps_count.items() if c>1])} 个Agent被多个Agent复用"},
        {"id": "P5", "name": "知识库SQLite版本化", "status": "applied", "metric": "56 指南 + 184 规则"},
        {"id": "P6", "name": "自主决策能力", "status": "applied", "metric": "DecisionEngine 规则驱动"},
        {"id": "P7", "name": "智能规划能力", "status": "applied", "metric": "WorkflowPlanner 动态生成"},
    ]

    result = {
        "agents_total": len(list(defs_dir.glob("*.yaml"))),
        "agent_types": dict(agent_types),
        "avg_stages": round(sum(stage_counts) / len(stage_counts), 1) if stage_counts else 0,
        "guard_coverage": f"{guard_agents}/{len(list(defs_dir.glob('*.yaml')))}",
        "most_reused": deps_count.most_common(5),
        "principles": principles,
        "compliance_score": 100,
    }
    with _togaf_cache_lock:
        _togaf_cache = result
        _togaf_cache_time = now
    return result

# ---- Health Check ----
@app.get("/api/health")
def health_check():
    """Liveness/readiness probe — checks DB, knowledge store, agent registry, subsystems."""
    from haip.agent import list_all
    agents = list_all()
    checks = {
        "status": "ok",
        "version": "1.2.0",
        "agents_loaded": len(agents),
        "database": "ok",
        "knowledge": "ok",
        "circuit": "ok",        # Phase 0.1: fail-closed
        "index": "unknown",     # Phase 1: RAG vector index
        "debate": "unknown",    # Phase 2: debate engine
        "learning": "unknown",  # Phase 3: self-learning
        "healthy": True,
    }

    # Database
    try:
        from haip.database import _engine
        if _engine is None:
            checks["database"] = "not-initialized"
            checks["healthy"] = False
    except Exception:
        checks["database"] = "error"
        checks["healthy"] = False

    # Knowledge store
    try:
        from haip.knowledge.runtime import get_kb
        get_kb()
    except Exception:
        checks["knowledge"] = "error"

    # Fail-closed circuit (Phase 0.1)
    try:
        from haip.llm import LLMProvider
        test_cfg = {"provider": "fail-closed", "mode": "test"}
        test_llm = LLMProvider.from_config(test_cfg)
        test_resp = test_llm.chat([{"role": "user", "content": "health check"}])
        if test_resp.model != "fail-closed":
            checks["circuit"] = "unexpected-provider"
    except Exception:
        checks["circuit"] = "error"

    # Future subsystems probe (lazy init — report "unknown" until activated)
    try:
        from haip.rag.pipeline import RAGPipeline  # type: ignore[import-untyped]
        checks["index"] = "ok" if RAGPipeline._index_ready else "building"
    except ImportError:
        pass

    try:
        from haip.debate.engine import DebateEngine  # type: ignore[import-untyped]
        checks["debate"] = "ok" if DebateEngine._available else "disabled"
    except ImportError:
        pass

    try:
        from haip.learning.store import FeedbackStore  # type: ignore[import-untyped]
        checks["learning"] = "ok" if getattr(FeedbackStore, '_writable', False) else "disabled"
    except (ImportError, AttributeError):
        pass  # optional subsystem not installed / not yet initialized

    return checks


def _init_rag():
    """Background RAG index builder (Phase 1). Non-blocking, graceful degradation."""
    try:
        from pathlib import Path

        from haip.rag.bm25 import BM25Index
        from haip.rag.embedding import EmbeddingProvider
        from haip.rag.index_builder import IndexBuilder
        from haip.rag.vector_store import VectorStore

        root = Path(__file__).resolve().parent.parent.parent.parent
        kb_dir = root / "packages" / "haip-hospital" / "knowledge"
        patients_f = root / "packages" / "haip-hospital" / "data" / "patients.json"

        EmbeddingProvider.load()
        vs = VectorStore(":memory:")
        bm = BM25Index(":memory:")
        if vs.connect() and bm.connect():
            builder = IndexBuilder(vs, bm, str(kb_dir), str(patients_f))
            count = builder.build()
            logger.info("RAG indices built: %d rows", count)
        else:
            logger.warning("RAG storage init failed — search will be BM25-only")
    except Exception:
        logger.warning("RAG init failed, running without semantic search", exc_info=True)

# TOGAF template API
from haip.togaf.templates.engine import get_togaf_engine

togaf_engine = get_togaf_engine()


@app.get("/api/togaf/templates")
def list_togaf_templates():
    """List all available TOGAF architecture templates."""
    return togaf_engine.list_all()


@app.get("/togaf/templates/{template_id}", response_class=HTMLResponse)
def render_togaf_template(template_id: str):
    """Render a TOGAF template as HTML."""
    html = togaf_engine.render(template_id)
    if html is None:
        raise HTTPException(status_code=404, detail={"error": f"Template not found: {template_id}"})
    return HTMLResponse(html)


@app.get("/api/leanix/export")
def leanix_export():
    """Export LeanIX fact sheets as JSON."""
    from haip.togaf.leanix import auto_discover
    exporter = auto_discover()
    return exporter.to_leanix_json()

# Structured logging — setup on import
try:
    from haip.logging_utils import setup_logging
    setup_logging()
except ImportError:
    pass
except Exception:
    logger.debug("logging_utils 初始化失败", exc_info=True)

YAML_DIR = PROJECT_ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
from haip.patients import PATIENTS_FILE  # 患者数据路径单一真相源

# 启动时加载 Agent（支持 XHAIP_AGENT_NAME 精简部署）
_agent_filter = os.environ.get("XHAIP_AGENT_NAME", "")
load_from_dir(str(YAML_DIR), agent_filter=_agent_filter)
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
    from haip.togaf.validator import validate_all
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
        raise HTTPException(status_code=404, detail={"error": f"Agent '{name}' not found"})
    return {
        "name": p.name, "cn_name": p.cn_name, "type": p.type,
        "port": p.port, "department": p.department, "version": p.version,
        "tools": [{"name": t.name, "description": t.description, "handler": t.handler,
                    "input": t.input} for t in p.tools],
        "guard": {"triggers": p.guard.triggers, "high_risk_scenarios": p.guard.high_risk_scenarios},
        "ui": {"template": p.ui.template, "roles": p.ui.roles, "sidebar": p.ui.sidebar},
    }


@app.post("/api/call")
def call_tool(body: CallRequest, request: Request):
    """调用 Agent 工具。

    特殊工具名 "reason" 触发 ReAct AgentLoop 模式。
    A2A 执行身份取自请求用户 (request.state.current_user), 权限 fail-closed。
    """
    from haip.a2a import permission_context_from_user
    perm_ctx = permission_context_from_user(
        getattr(request.state, "current_user", None))

    agent = body.agent
    tool = body.tool
    params = body.params
    mode = body.mode

    if not agent:
        raise HTTPException(status_code=400, detail={"status": "error", "error": "Missing agent"})
    if not tool:
        raise HTTPException(status_code=400, detail={"status": "error", "error": "Missing tool"})

    # R2: reason 模式 → AgentLoop
    if tool == "reason" or mode == "reason":
        query = params.get("query", "") or params.get("message", "")
        max_steps = params.get("max_steps", 5)
        result = call_with_loop(agent, query, max_steps, perm_ctx=perm_ctx)
        return result

    result = a2a_call(agent, tool, params, perm_ctx=perm_ctx)
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


@app.post("/api/stream")
async def stream_call(body: StreamRequest, request: Request):
    """SSE 流式 AgentLoop — 每步实时推送 Event。

    POST body: {"agent": "antiemetic", "query": "评估PONV风险", "max_steps": 5}
    """
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


# ── Session API (v1.2) ──

def _session_user_id(request: Request) -> str:
    """从 JWT 身份派生会话 user 作用域 — 客户端参数不可信 (IDOR 修复)。

    匿名/无身份请求 (如 dev 免登录之外的兜底) 归入稳定伪用户 "anonymous",
    所有匿名用户共享同一作用域, 但认证用户之间完全隔离。
    """
    user = getattr(request.state, "current_user", None)
    if user and user.get("user_id"):
        return str(user["user_id"])
    return "anonymous"


@app.post("/api/sessions")
def create_session(request: Request, payload: dict = Body(default_factory=dict)):
    """创建新会话. POST body: {"state": {...}} — 用户身份取自 JWT, 忽略 body.user_id."""
    from haip.session.store import SessionService
    svc = SessionService(_get_session_db_path())
    s = svc.create_session(
        user_id=_session_user_id(request),
        state=payload.get("state"),
    )
    return {"session_id": s.id, "created_at": s.last_update}

@app.get("/api/sessions/{session_id}")
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


@app.get("/api/sessions")
def list_sessions(request: Request, limit: int = 20):
    """列出当前认证用户的会话列表 (user 作用域取自 JWT, 忽略客户端参数)."""
    from haip.session.store import SessionService
    svc = SessionService(_get_session_db_path())
    return svc.list_sessions(user_id=_session_user_id(request), limit=limit)


@app.post("/api/sessions/{session_id}/rewind")
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


def _get_session_db_path() -> str:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "sessions.db")


@app.post("/api/loop/demo")
def loop_demo():
    """Loop Engineering 演示 — 使用 Mock LLM 展示 ReAct 多步推理过程。
    
    返回每步的思考、工具调用和最终综合答案。
    """
    from haip.a2a import call as _a2a_call
    from haip.a2a import internal_permission_context
    from haip.agent import get as _get_agent
    from haip.llm import DEFAULT_MAX_TOKENS, ChatResponse, ToolCall
    from haip.llm.mock import MockProvider

    # 模拟 LLM 的多步推理
    class DemoLLM(MockProvider):
        def __init__(self):
            super().__init__({})
            self._step = [0]

        def chat(self, messages, tools=None, temperature=0.3, max_tokens=DEFAULT_MAX_TOKENS):
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
        raise HTTPException(status_code=500, detail={"status": "error", "error": "antiemetic agent not loaded"})

    tools = [{"name": t.name, "description": t.description, "input": t.input}
             for t in plugin.tools]

    def _exec(name, args):
        # loop_demo: 显式引擎内部上下文 (demo 端点, 身份已在演示语境中)
        return _a2a_call(agent, name, args,
                         perm_ctx=internal_permission_context())

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
def guard_verify(body: GuardRequest):
    """对 Agent 输出执行 Guard 安全验证。需人工复核时自动创建签核单。"""
    output = body.output
    scenario = body.scenario
    agent_name = body.agent
    patient_id = body.patient_id
    cross = body.cross_agent_outputs
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


# ── 医生签核工作流 (M3 / C1) — 已拆分至 haip/api/routes_signoff.py ──

@app.get("/api/history")
def history(limit: int = 20):
    """获取 A2A 调用历史。"""
    return get_history(limit)


# ── Knowledge API — 已拆分至 haip/api/routes_knowledge.py ──

@app.get("/api/agents/{name}/knowledge")
def agent_knowledge(name: str):
    """Return knowledge base references for a specific agent."""
    agent_path = PROJECT_ROOT / "packages" / "haip-hospital" / "agents" / "definitions" / f"{name}.yaml"
    if not agent_path.exists():
        return {"error": f"Agent {name} not found", "guidelines": [], "rules": []}

    import yaml
    data = yaml.safe_load(agent_path.read_text(encoding="utf-8"))

    # Extract knowledge references from the handler module
    guidelines: list[str] = []
    rules: list[str] = []
    kb_stats = {"guidelines_count": 0, "rules_count": 0}

    try:
        import importlib
        module_name = f"modules.{name.replace('-', '_')}"
        mod = importlib.import_module(module_name)
        agent_obj = getattr(mod, "_agent", None)
        if agent_obj and hasattr(agent_obj, "rule_engine"):
            gs = getattr(mod, "_GUIDELINES", [])
            guidelines = gs if isinstance(gs, list) else []
            try:
                all_rules = agent_obj.rule_engine.get_rules()
                rules = [r.get("name", str(r)) for r in (all_rules or [])]
            except Exception:
                logger.debug("agent rule_engine.get_rules() failed for %s", name, exc_info=True)
    except Exception:
        logger.debug("agent knowledge module load failed for %s", name, exc_info=True)

    # Also fetch from knowledge runtime
    try:
        kb = get_kb(str(PROJECT_ROOT))
        kb_stats = kb.stats()
    except Exception:
        logger.debug("knowledge runtime stats failed", exc_info=True)

    return {
        "agent": name,
        "guidelines": guidelines,
        "guidelines_count": len(guidelines),
        "rules": rules,
        "rules_count": len(rules),
        "knowledge_stats": kb_stats,
    }


@app.get("/patients")
def patients_legacy(q: str = "", agent: str = ""):
    """[DEPRECATED] 使用 /api/patients/{agent_name} 替代。"""
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
    """[DEPRECATED] 使用 /api/health 替代。"""
    return {"agents_loaded": len(_registry), "call_history": len(get_history(0)),
            "patients_loaded": len(case_mgr.cases)}


# ── Workflow UI ──

@app.get("/workflow/{name}", response_class=HTMLResponse)
def workflow_ui(request: Request, name: str):
    """工作流感知 UI — 三栏工作台 (角色筛选 + 阶段执行 + 数字病人)."""
    p = get_agent(name)
    if not p:
        raise HTTPException(404, detail={"error": f"Agent '{name}' not found"})
    from haip.workflow import get_workflow
    wf = get_workflow(name)
    if not wf:
        raise HTTPException(404, detail={"error": f"No workflow for '{name}'"})
    from haip.ui_workflow import build_workflow_ui_context, render_workflow_ui
    wf_stages, roles = build_workflow_ui_context(p)
    html = render_workflow_ui(
        name=p.name, cn_name=p.cn_name, agent_type=p.type, port=p.port,
        tools=[{"name": t.name, "description": t.description} for t in p.tools],
        workflow_stages=wf_stages, roles=roles,
        guard_triggers=p.guard.triggers)
    return HTMLResponse(html)


# ── 专业 Web UI ──

@app.get("/agent/{name}", response_class=HTMLResponse)
def agent_ui(request: Request, name: str):
    """通用 Agent 专业 UI — Jinja2 模板渲染。"""
    from haip.patients import load_patients
    p = get_agent(name)
    if not p:
        raise HTTPException(404, detail={"error": f"Agent '{name}' not found"})
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
    patient_list = [{"patient_id": pt.get("patient_id",""), "name": pt.get("name","?"), "age": pt.get("age",0), "diagnosis": pt.get("diagnosis",""), "department": pt.get("department",""), "lab_results": pt.get("lab_results",{}), "scenario": pt.get("scenario","")} for pt in (patients or [])[:50]]
    content = templates.env.get_template("agent.html").render(
        request=request, agent=agent_data, patients=patient_list)
    return HTMLResponse(content)


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
def pharmacy_ui(request: Request):
    """药剂科专业界面 — TPN 计算器 + 处方审查。"""
    content = templates.env.get_template("pharmacy.html").render(request=request)
    return HTMLResponse(content)


@app.get("/api/agent-ui/{agent_name}")
def agent_ui_config(agent_name: str):
    """快速 UI 生成器 — 根据 YAML 定义返回 UI 配置。"""
    p = get_agent(agent_name)
    if not p:
        raise HTTPException(status_code=404, detail={"error": "not found"})
    tabs = []
    for tool in p.tools:
        tabs.append({"id": tool.name, "label": tool.name, "desc": tool.description,
                     "inputs": tool.input})
    return {"agent": p.name, "cn_name": p.cn_name, "type": p.type,
            "tabs": tabs, "roles": p.ui.roles, "sidebar": p.ui.sidebar}


# ── 诊疗流程 UI ──

@app.get("/process/{name}", response_class=HTMLResponse)
def process_ui(request: Request, name: str):
    """诊疗流程 UI — 三栏工作台 (角色 tab + 阶段执行)."""
    p = get_agent(name)
    if not p:
        raise HTTPException(404, detail={"error": f"Agent '{name}' not found"})
    from haip.ui_workflow import build_workflow_ui_context, render_workflow_ui
    wf_stages, roles = build_workflow_ui_context(p)
    html = render_workflow_ui(
        name=p.name, cn_name=p.cn_name, agent_type=p.type, port=p.port,
        tools=[{"name": t.name, "description": t.description} for t in p.tools],
        workflow_stages=wf_stages, roles=roles,
        guard_triggers=p.guard.triggers)
    return HTMLResponse(html)




# ── Orthopedic v1 API — 已拆分至 haip/api/routes_ortho.py ──

# ── TOGAF Architecture Dashboard ──

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    """TOGAF 10 架构治理仪表盘 — 全院 39 科室成熟度热力图。"""
    from haip.togaf.dashboard import _load_analysis_data
    data = _load_analysis_data()
    template = templates.env.get_template("dashboard/index.html")
    content = template.render(request=request, DASHBOARD_DATA=data)
    return HTMLResponse(content)


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
def index(request: Request):
    """xhaip Web 门户 — Agent 管理 + 工具调用 + 聊天界面。"""
    content = templates.env.get_template("index.html").render(request=request)
    return HTMLResponse(content)
