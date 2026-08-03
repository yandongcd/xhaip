"""A2A Dispatcher — Agent 间进程内调度 (统一 dispatch_entry).

与老系统的区别:
  - 老系统: 每个 Agent 手写 dispatch_entry 函数做路由
  - 新系统: 引擎根据 YAML 的 handler 字段自动完成 import → call → format
"""

from __future__ import annotations

import importlib
import json as _json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from haip.agent import get as get_agent

logger = logging.getLogger(__name__)


_agent_cache: dict[str, Any] = {}       # module cache: module_path → module_obj
_call_history: list[dict[str, Any]] = []
_cache_lock = threading.Lock()


def _is_test_mode() -> bool:
    return os.environ.get("HAIP_TEST_MODE", "").strip().lower() == "true"


def permission_context_from_user(user: dict | None):
    """把 HTTP 层的 current_user 映射为 A2A 执行身份 (PermissionContext).

    user 形如 auth/middleware 注入的 dict:
    {user_id, username, roles, permissions, tenant_id, ...}.
    返回 None 表示无身份 — call() 将 fail-closed 拒绝。
    """
    if not user:
        return None
    try:
        from haip.permission import PermissionContext
    except ImportError:
        return None
    roles = user.get("roles") or []
    role = str(roles[0]) if roles else ""
    return PermissionContext(
        user_id=str(user.get("user_id", "")),
        role=role,
        agent_id=str(user.get("user_id", "")),
        department=str(user.get("department", "")),
        is_emergency=bool(user.get("is_emergency", False)),
    )


def internal_permission_context():
    """显式构造的引擎内部调用上下文 (免鉴权)。

    仅供引擎内部路径使用 (orchestrator / pipeline / transport / CLI / MCP /
    eval / meta_harness 等) — 这些路径的调用方身份已在入口层 (HTTP 中间件 /
    显式启动命令) 校验, 内部编排不重复鉴权。生产 HTTP 路径禁止使用本上下文,
    必须由 permission_context_from_user() 构造用户身份。
    """
    from haip.permission import PermissionContext
    return PermissionContext(user_id="engine", role="admin", agent_id="engine")


def _default_permission_context():
    """perm_ctx=None 时的默认上下文。

    仅测试模式返回显式 permissive 上下文 (与 auth/middleware 的 test-user
    放行语义一致); 非测试模式返回 None → call() fail-closed 拒绝
    (身份缺失不得静默放行)。
    """
    if _is_test_mode():
        from haip.permission import PermissionContext
        return PermissionContext(user_id="test-user", role="admin", agent_id="test")
    return None


def _enforce_permission(pc, agent: str, tool: str) -> str:
    """A2A 权限校验 — fail-closed. 返回 "" 表示允许, 否则返回错误码。"""
    try:
        from haip.permission import PermissionContext, get_permission_manager
        if isinstance(pc, dict):
            pc = PermissionContext(**{k: pc.get(k, "") for k in
                ("user_id", "role", "agent_id", "department", "is_emergency")})
        pm = get_permission_manager()  # D2: 进程级单例, 审计落盘
        if not pm.can_call_agent(pc, agent, tool):
            pm.log_access(pc, "A2A_call", f"{agent}.{tool}", "deny", "no policy/role grant")
            return "PERMISSION_DENIED"
        pm.log_access(pc, "A2A_call", f"{agent}.{tool}", "allow")
        return ""
    except ImportError:
        # fail-closed: 权限模块不可用绝不 allow-all
        logger.error("Permission module not available — A2A call denied (fail-closed)")
        return "PERMISSION_UNAVAILABLE"


def _check_version(requirement: str, actual: str) -> bool:
    """简单的语义版本约束校验。支持 >=1.0, ==1.0, 1.0 (exact)."""
    req = requirement.strip()
    if req.startswith(">="):
        target = req[2:].strip()
        return _version_tuple(actual) >= _version_tuple(target)
    if req.startswith("=="):
        target = req[2:].strip()
        return _version_tuple(actual) == _version_tuple(target)
    if req.startswith(">") and not req.startswith(">="):
        target = req[1:].strip()
        return _version_tuple(actual) > _version_tuple(target)
    # bare version: exact match
    return _version_tuple(actual) == _version_tuple(req)


def _version_tuple(v: str) -> tuple:
    try:
        parts = [int(x) for x in v.split(".")[:3]]
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _validate_depends(caller_name: str, target_agent: str) -> str:
    """校验调用方对目标 Agent 的版本依赖。返回空字符串表示通过，否则返回错误描述。"""
    if not caller_name or not target_agent:
        return ""
    caller = get_agent(caller_name)
    if caller is None or not caller.depends_on:
        return ""
    target = get_agent(target_agent)
    if target is None:
        return ""
    for dep in caller.depends_on:
        dep_agent = dep.get("agent", "")
        dep_version = dep.get("version", "")
        if dep_agent == target_agent and dep_version:
            if not _check_version(dep_version, target.version):
                return (
                    f"Version mismatch: {caller_name} requires {target_agent}"
                    f" {dep_version}, but found {target.version}"
                )
    return ""


def call(agent: str, tool: str, params: dict[str, Any] | None = None,
         workflow_id: str = "", caller_agent: str = "",
         perm_ctx: Any = None) -> dict[str, Any]:
    """调用目标 Agent 的工具。

    引擎自动完成:
      1. 查 DomainPlugin → 获取 tool 的 handler 路径
      2. importlib 动态加载模块（首次缓存）
      3. 调用业务函数
      4. 均一化返回 {"status": "ok"/"error", ...}
    """
    params = dict(params or {})
    t0 = time.perf_counter()

    # ── L2 agentic 路由: tool 为空 / __reason__ / chat → LLM 推理模式下发 ──
    if not tool or tool in ("__reason__", "chat"):
        query = params.pop("query", "") or params.pop("message", "") or params.pop("prompt", "")
        if not query:
            # 无可读文本: 用 params JSON 作为推理输入
            query = _json.dumps(params, ensure_ascii=False)
        if not query:
            return {"status": "error", "error": "agentic path 需要 query/message/prompt 参数"}
        return reason(agent, query, max_steps=params.pop("max_steps", 5), perm_ctx=perm_ctx, provider=None)

    plugin = get_agent(agent)
    if plugin is None:
        err = {"status": "error", "error": f"Unknown agent: {agent}"}
        _record(agent, tool, "error", str(err), 0, workflow_id)
        return err

    # Version dependency enforcement
    if caller_agent:
        verr = _validate_depends(caller_agent, agent)
        if verr:
            err = {"status": "error", "error": verr, "code": "VERSION_MISMATCH"}
            _record(agent, tool, "error", verr, 0, workflow_id)
            return err

    # Permission enforcement (A2A) — fail-closed
    pc = perm_ctx if perm_ctx is not None else _default_permission_context()
    if pc is None:
        # 非测试模式且未提供身份 → 拒绝 (不得静默放行)
        err = {"status": "error", "error": "Permission check unavailable: no identity context",
               "code": "PERMISSION_REQUIRED",
               "detail": f"Cannot call {agent}.{tool} without identity"}
        _record(agent, tool, "error", "Permission denied", 0, workflow_id)
        return err
    perr = _enforce_permission(pc, agent, tool)
    if perr:
        err = {"status": "error", "error": "Permission denied", "code": perr,
               "detail": f"Cannot call {agent}.{tool}"}
        _record(agent, tool, "error", "Permission denied", 0, workflow_id)
        return err

    tool_def = _find_tool(plugin, tool)
    if tool_def is None:
        err = {"status": "error", "error": f"Agent '{agent}' has no tool: {tool}"}
        _record(agent, tool, "error", str(err), 0, workflow_id)
        return err

    handler = tool_def.handler  # e.g. "pharmacy.assessment.nutrition_risk"
    module_name, func_name = handler.rsplit(".", 1)

    try:
        if handler not in _agent_cache:
            with _cache_lock:
                if handler not in _agent_cache:
                    if len(_agent_cache) > 200:
                        _agent_cache.clear()  # Reset on excessive caching
                    _agent_cache[handler] = importlib.import_module(module_name)
        fn = getattr(_agent_cache[handler], func_name)
        # Coerce param types from YAML input schema (form inputs are always strings)
        if tool_def.input and params:
            keys_to_drop = []
            for k, pt in tool_def.input.items():
                if k in params and isinstance(params[k], str):
                    if not params[k].strip():
                        keys_to_drop.append(k)  # Empty string → use function default
                        continue
                    try:
                        if pt in ("int", "integer"):
                            params[k] = int(params[k])
                        elif pt in ("float", "number", "double"):
                            params[k] = float(params[k])
                        elif pt == "bool":
                            params[k] = params[k].lower() in ("true", "1", "yes")
                    except (ValueError, TypeError):
                        pass
            for k in keys_to_drop:
                params.pop(k, None)
        result = fn(**params)
    except ModuleNotFoundError as e:
        elapsed = (time.perf_counter() - t0) * 1000
        err = {"status": "error", "error": f"Handler module not found: {module_name} ({e})"}
        _record(agent, tool, "error", str(err), elapsed, workflow_id)
        return err
    except AttributeError as e:
        elapsed = (time.perf_counter() - t0) * 1000
        err = {"status": "error", "error": f"Function not found: {func_name} in {module_name} ({e})"}
        _record(agent, tool, "error", str(err), elapsed, workflow_id)
        return err
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        err = {"status": "error", "error": str(e)}
        _record(agent, tool, "error", str(e), elapsed, workflow_id)
        return err

    elapsed = (time.perf_counter() - t0) * 1000
    if isinstance(result, dict):
        result.setdefault("status", "ok")
        result["agent"] = agent
        result["elapsed_ms"] = round(elapsed, 2)
    else:
        result = {"status": "ok", "result": result, "agent": agent,
                  "elapsed_ms": round(elapsed, 2)}
    _record(agent, tool, result.get("status", "ok"), "", elapsed, workflow_id, result=result)
    return result


def call_batch(tasks: list[dict], max_workers: int = 8, perm_ctx: Any = None) -> list[dict]:
    """批量并行调用。

    tasks: [{"agent": ..., "tool": ..., "params": {...}}, ...]
    max_workers: 线程池最大工作线程数 (默认 8)。
    perm_ctx: 调用身份 (PermissionContext) — 与 call() 一致, 缺省时 fail-closed。
    """
    results: list[dict | None] = [None] * len(tasks)

    def _run(idx: int, task: dict) -> tuple[int, dict]:
        return idx, call(
            agent=task["agent"],
            tool=task["tool"],
            params=task.get("params", {}),
            workflow_id=task.get("workflow_id", ""),
            perm_ctx=perm_ctx,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run, i, task): i
            for i, task in enumerate(tasks)
        }
        for future in as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    return [r for r in results if r is not None]


def _find_tool(plugin, tool_name: str):
    for t in plugin.tools:
        if t.name == tool_name:
            return t
    return None


def _record(agent: str, tool: str, status: str, error: str,
             elapsed_ms: float, workflow_id: str = "",
             result: dict[str, Any] | None = None) -> None:
    entry: dict[str, Any] = {
        "agent": agent, "tool": tool, "status": status,
        "error": error, "elapsed_ms": round(elapsed_ms, 2),
        "workflow_id": workflow_id,
    }

    # ── TOGAF ABB 映射记录 ──
    try:
        from haip.agent import get as _get_agent
        plugin = _get_agent(agent)
        if plugin is not None:
            entry["togaf_abb"] = {
                "ApplicationComponent": agent,
                "ApplicationService": tool,
                "OrganizationUnit": getattr(plugin, "department", ""),
            }
    except ImportError:
        pass
    except Exception:
        logger.debug("TOGAF ABB 映射记录失败", exc_info=True)

    with _cache_lock:
        _call_history.append(entry)

        # Prune to prevent unbounded growth
        if len(_call_history) > 1000:
            _call_history[:] = _call_history[-500:]

    # ── Agent Memory Recording (持续探索) ──
    try:
        from haip.memory import get_memory
        get_memory().record(agent, "", tool, status=status)
    except Exception:
        logger.debug("Agent Memory 记录失败 (非致命)", exc_info=True)

    # ── Audit logging ──
    try:
        from haip.audit import get_audit_logger
        audit = get_audit_logger()
        audit.log(
            action="agent_call",
            resource=f"agent:{agent}.{tool}",
            status=status,
            detail={"tool": tool, "elapsed_ms": elapsed_ms, "error": error},
        )
    except ImportError:
        pass
    except Exception:
        logger.debug("Audit logging 写入失败", exc_info=True)

    # ── L6: Evolution production hook (fire-and-forget, 非阻塞) ──
    try:
        from haip.evolution.hook import evolution_hook
        evolution_hook(agent, tool, status, result)
    except Exception:
        pass


def get_history(limit: int = 20) -> list[dict[str, Any]]:
    with _cache_lock:
        return _call_history[-limit:]


def clear_history() -> None:
    with _cache_lock:
        _call_history.clear()


# ── ReAct Loop 集成 ──

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z0-9_]+)\}")


def _interpolate_env(value: Any) -> Any:
    """把配置值中的 ${ENV_NAME} 替换为环境变量值 (缺失 → 空串)。"""
    if isinstance(value, str):
        return _ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
    return value


def _load_llm_config() -> dict[str, Any]:
    """加载 LLM 配置（从 config/llm.yaml, 含环境变量插值, mtime 缓存）。

    env 指纹: DEEPSEEK_API_KEY / HAIP_ENV 变化时立即失效缓存,
    避免 TTL/mtime 缓存返回旧 env 插值 (测试与运行时切换 key 的 401 根因).
    """
    env_fp = (os.environ.get("DEEPSEEK_API_KEY", ""), os.environ.get("HAIP_ENV", ""))
    if env_fp != getattr(_load_llm_config, "_env_fingerprint", ("", "")):
        _load_llm_config._cache = {}  # type: ignore[attr-defined]
        _load_llm_config._file_mtime = 0.0  # type: ignore[attr-defined]
        _load_llm_config._cache_time = 0.0  # type: ignore[attr-defined]
        _load_llm_config._env_fingerprint = env_fp  # type: ignore[attr-defined]

    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "config" / "llm.yaml",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "llm.yaml",
    ]
    now = time.time()
    if _load_llm_config._cache_time > 0 and now - _load_llm_config._cache_time < 5:
        return _load_llm_config._cache
    for p in candidates:
        if p.exists():
            try:
                mtime = p.stat().st_mtime
                if mtime == _load_llm_config._file_mtime and _load_llm_config._cache:
                    _load_llm_config._cache_time = now
                    return _load_llm_config._cache
                with open(p, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f).get("llm", {})
            except (OSError, yaml.YAMLError) as e:
                logger.warning("LLM 配置读取失败: %s, 降级 MockProvider", e)
                return {"provider": "mock", "mock_responses": True}
            cfg = {k: _interpolate_env(v) for k, v in cfg.items()}
            if not cfg.get("api_key"):
                try:
                    from haip.api_key_store import get_api_key
                    pk = get_api_key()
                    if pk:
                        cfg["api_key"] = pk
                except ImportError:
                    pass
                except Exception:
                    logger.debug("api_key_store 读取失败", exc_info=True)
            _load_llm_config._cache = cfg
            _load_llm_config._file_mtime = mtime
            _load_llm_config._cache_time = now
            return cfg
    return {"provider": "mock", "mock_responses": True}


_load_llm_config._cache: dict[str, Any] = {}  # type: ignore[attr-defined]
_load_llm_config._cache_time: float = 0.0  # type: ignore[attr-defined]
_load_llm_config._file_mtime: float = 0.0  # type: ignore[attr-defined]
_load_llm_config._env_fingerprint = ("", "")  # type: ignore[attr-defined]


def _build_loop_components(agent: str, perm_ctx: Any = None):
    """构建 AgentLoop 所需组件 (共享逻辑).

    perm_ctx: ReAct 循环内 A2A 工具调用的身份上下文 (HTTP 路径由
    request.state.current_user 构造并透传; 引擎内部路径显式传
    internal_permission_context())。
    """
    plugin = get_agent(agent)
    if plugin is None:
        raise ValueError(f"Unknown agent: {agent}")

    tools = [
        {"name": t.name, "description": t.description, "input": t.input}
        for t in plugin.tools
    ]

    from haip.llm import LLMProvider
    llm_config = _load_llm_config()
    if llm_config.get("provider", "mock") != "mock" and not llm_config.get("api_key"):
        # config 声明的 fallback: 无 API key 时降级 MockProvider, 聊天离线可用
        logger.warning("LLM api_key 未配置 (检查 DEEPSEEK_API_KEY), 降级 MockProvider 离线模式")
        from haip.llm.mock import MockProvider
        llm: LLMProvider = MockProvider({})
    else:
        try:
            llm = LLMProvider.from_config(llm_config)
        except Exception as e:
            logger.debug("LLM 初始化失败, 降级 MockProvider: %s", e)
            from haip.llm.mock import MockProvider
            llm = MockProvider({})

    def _a2a_executor(tool_name: str, tool_args: dict) -> dict:
        return call(agent, tool_name, tool_args, perm_ctx=perm_ctx)

    return plugin, tools, llm, _a2a_executor


def _run_guard(output: str, tool_calls: list, plugin) -> dict:
    """执行 Guard 校验 + Citation 强制 (共享逻辑)."""
    guard_result: dict[str, Any] = {"checked": False, "passed": True, "flags": [],
                                     "citations": [], "blocked_reason": ""}
    guard_cfg = plugin.guard

    try:
        from haip.guard.verifier import GuardVerifier
        verifier = GuardVerifier()
        g = verifier.verify(
            agent_output=output,
            scenario=_detect_scenario_from_text(str(tool_calls)),
            agent_name=plugin.name,
        )
        guard_result.update({
            "checked": True,
            "passed": g.passed,
            "flags": g.flags,
            "requires_human_review": g.requires_human_review,
            "citations": [{"source": c.source, "trust_level": c.trust_level} for c in g.citations],
        })

        if guard_cfg.citation.required and g.citations:
            verified_count = sum(1 for c in g.citations if c.verified)
            if verified_count < guard_cfg.citation.min_sources:
                guard_result["passed"] = False
                guard_result["blocked_reason"] = (
                    f"Citation enforcement: {verified_count}/{guard_cfg.citation.min_sources}"
                    f" verified sources required"
                )
                guard_result["flags"].append(guard_result["blocked_reason"])
            if guard_cfg.citation.min_trust == "T1":
                t1_count = sum(1 for c in g.citations if c.trust_level == "T1")
                if t1_count == 0:
                    guard_result["passed"] = False
                    guard_result["blocked_reason"] = (
                        "Citation enforcement: T1 trust level required,"
                        " but no T1 citations found"
                    )
                    guard_result["flags"].append(guard_result["blocked_reason"])
    except Exception as e:
        logger.exception("Guard 验证异常, 阻断通过")
        guard_result["passed"] = False
        guard_result["flags"].append(f"Guard 内部异常: {e}")
        guard_result["blocked_reason"] = f"Guard 验证管道异常: {e}"

    return guard_result


def _detect_scenario_from_text(text: str) -> str:
    """从工具调用文本中推断高危场景."""
    for kw in ["antiemetic", "ponv", "drug", "regimen", "surgery", "cardiac", "抗凝"]:
        if kw in text.lower():
            return kw
    return ""


def call_with_loop(
    agent: str,
    query: str,
    max_steps: int = 5,
    perm_ctx: Any = None,
    **kwargs,
) -> dict[str, Any]:
    """ReAct AgentLoop — LLM 自主规划调用工具，多步推理。

    Agent 的 tools 通过 A2A call() 执行，而非全局 tool registry。
    每次请求创建新的 AgentLoop 实例，无状态共享，无竞态风险。
    """
    try:
        plugin, tools, llm, _a2a_executor = _build_loop_components(agent, perm_ctx)
    except ValueError as e:
        return {"status": "error", "error": str(e)}

    from haip.loop import AgentLoop

    loop = AgentLoop(
        llm=llm,
        system_prompt=plugin.prompt.system,
        tool_executor=_a2a_executor,
        tools=tools,
        max_steps=max_steps,
        agent_name=agent,
    )
    t0 = time.perf_counter()
    result = loop.run(query)
    elapsed = round((time.perf_counter() - t0) * 1000, 2)

    guard_result = _run_guard(result.reply, result.tool_calls, plugin)

    # Guard gating: if not passed, block response
    if not guard_result["passed"]:
        return {
            "status": "blocked",
            "reply": result.reply,
            "steps": result.steps,
            "tool_calls": result.tool_calls,
            "duration_ms": elapsed,
            "tokens": {"input": result.input_tokens, "output": result.output_tokens},
            "guard": guard_result,
            "error": f"Guard verification failed: {'; '.join(guard_result['flags'])}",
        }

    return {
        "status": "ok",
        "reply": result.reply,
        "steps": result.steps,
        "tool_calls": result.tool_calls,
        "duration_ms": elapsed,
        "tokens": {"input": result.input_tokens, "output": result.output_tokens},
        "error": result.error or None,
        "guard": guard_result,
    }


# ── Async Streaming Loop (v1.2) ──

async def call_with_loop_async(
    agent: str,
    query: str,
    max_steps: int = 5,
    session_id: str = "default",
    user_id: str = "default",
    use_session_service: bool = False,
    db_path: str = ":memory:",
    perm_ctx: Any = None,
) -> dict[str, Any]:
    """异步 ReAct AgentLoop — 支持 state_delta + session 持久化."""
    try:
        plugin, tools, llm, _a2a_executor = _build_loop_components(agent, perm_ctx)
    except ValueError as e:
        return {"status": "error", "error": str(e)}

    from haip.loop import AsyncAgentLoop
    from haip.loop.context import InvocationContext
    from haip.session.store import InMemorySessionService, SessionService

    if use_session_service:
        from pathlib import Path as _Path
        db_path_actual = db_path
        if db_path_actual == ":memory:":
            db_path_actual = str(_Path(__file__).parent.parent.parent.parent / "data" / "sessions.db")
        session_svc = SessionService(db_path_actual)
    else:
        session_svc = InMemorySessionService()

    session = session_svc.get_or_create_session(session_id, user_id=user_id)
    invocation_id = session_svc.begin_invocation(session)
    ctx = InvocationContext(
        session=session, agent_name=agent,
        invocation_id=invocation_id, session_service=session_svc,
    )

    loop = AsyncAgentLoop(
        llm=llm, system_prompt=plugin.prompt.system,
        tool_executor=_a2a_executor, tools=tools,
        max_steps=max_steps, agent_name=agent, ctx=ctx,
    )

    t0 = time.perf_counter()
    events = []
    final_reply = ""
    final_error = ""
    steps = 0

    async for evt in loop.run(query):
        events.append(evt.to_dict())
        if evt.turn_complete:
            final_reply = evt.content
            final_error = evt.error or ""
        if evt.role == "assistant" and not evt.turn_complete:
            steps += 1

    session_svc.end_invocation(session)
    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    guard_result = _run_guard(final_reply, [], plugin)

    # Guard gating: 与同步 call_with_loop 一致 — 未通过则 status=blocked
    if not guard_result["passed"]:
        status = "blocked"
        error = f"Guard verification failed: {'; '.join(guard_result['flags'])}"
    else:
        status = "ok"
        error = final_error or None

    return {
        "status": status,
        "reply": final_reply,
        "steps": steps,
        "duration_ms": elapsed,
        "events": events,
        "session_id": session_id,
        "invocation_id": invocation_id,
        "error": error,
        "guard": guard_result,
    }


async def stream_events(
    agent: str, query: str, max_steps: int = 5,
    session_id: str = "default", user_id: str = "default",
    perm_ctx: Any = None,
):
    """SSE 事件流生成器 — 每步实时推送 Event (state_delta + content).

    Guard 门控: 最终助手回复产生时先跑与同步路径相同的 Guard 校验,
    未通过则推送 guard_blocked 事件且不发送回复内容。
    """

    try:
        plugin, tools, llm, _a2a_executor = _build_loop_components(agent, perm_ctx)
    except ValueError as e:
        yield f"data: {_json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        return

    from haip.loop import AsyncAgentLoop
    from haip.loop.context import InvocationContext
    from haip.session.store import InMemorySessionService

    session_svc = InMemorySessionService()
    session = session_svc.get_or_create_session(session_id, user_id=user_id)
    invocation_id = session_svc.begin_invocation(session)
    ctx = InvocationContext(
        session=session, agent_name=agent,
        invocation_id=invocation_id, session_service=session_svc,
    )

    loop = AsyncAgentLoop(
        llm=llm, system_prompt=plugin.prompt.system,
        tool_executor=_a2a_executor, tools=tools,
        max_steps=max_steps, agent_name=agent, ctx=ctx,
    )

    tool_names: list[str] = []
    async for evt in loop.run(query):
        evt_dict = evt.to_dict()
        if evt.role == "assistant" and evt.turn_complete and evt.content:
            # Guard gating: 与同步 call_with_loop 相同的校验 (含 citation 强制)
            guard_result = _run_guard(evt.content, tool_names, plugin)
            if not guard_result["passed"]:
                reason = f"Guard verification failed: {'; '.join(guard_result['flags'])}"
                evt_dict.update({
                    "type": "guard_blocked",
                    "reason": reason,
                    "error": reason,
                    "content": "",
                    "guard": guard_result,
                })
                yield f"data: {_json.dumps(evt_dict, ensure_ascii=False)}\n\n"
                break
            evt_dict["guard"] = guard_result
        elif evt.role == "tool":
            tool_names.append(evt.tool_name)
        yield f"data: {_json.dumps(evt_dict, ensure_ascii=False)}\n\n"

    session_svc.end_invocation(session)


def reason(
    agent: str,
    query: str,
    max_steps: int = 5,
    provider: Any = None,
    perm_ctx: Any = None,
) -> dict[str, Any]:
    """Agent 推理模式 — LLM 自主规划并调用工具 (L1 agentic upgrade).

    与 call_with_loop 等价但接受可选 provider/perm_ctx:
    - provider=None → 使用 config/llm.yaml 的默认 provider (生产)
    - provider=MockProvider(...) → 测试/CI 可控
    - perm_ctx 可用于注入权限上下文 (测试/emergency 模式)

    Agent 的 prompt.system + tools 被注入 AgentLoop,
    LLM 在 ReAct 循环中自主决定调用哪个工具、解读结果、迭代决策.
    """
    if provider is not None:
        import haip.llm
        orig = haip.llm.LLMProvider.from_config
        haip.llm.LLMProvider.from_config = lambda cfg: provider  # type: ignore[method-assign,assignment]
        try:
            return call_with_loop(agent, query, max_steps=max_steps, perm_ctx=perm_ctx)
        finally:
            haip.llm.LLMProvider.from_config = orig  # type: ignore[method-assign,assignment]
    return call_with_loop(agent, query, max_steps=max_steps, perm_ctx=perm_ctx)
