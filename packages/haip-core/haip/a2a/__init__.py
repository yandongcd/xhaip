"""A2A Dispatcher — Agent 间进程内调度 (统一 dispatch_entry).

与老系统的区别:
  - 老系统: 每个 Agent 手写 dispatch_entry 函数做路由
  - 新系统: 引擎根据 YAML 的 handler 字段自动完成 import → call → format
"""

from __future__ import annotations

import importlib
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from haip.agent import get as get_agent

logger = logging.getLogger(__name__)


_agent_cache: dict[str, Any] = {}       # module cache: module_path → module_obj
_call_history: list[dict[str, Any]] = []


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

    # Permission enforcement (A2A)
    if perm_ctx is not None:
        try:
            from haip.permission import PermissionContext, get_permission_manager
            if isinstance(perm_ctx, dict):
                pc = PermissionContext(**{k: perm_ctx.get(k, "") for k in
                    ("user_id", "role", "agent_id", "department", "is_emergency")})
            else:
                pc = perm_ctx
            pm = get_permission_manager()  # D2: 进程级单例, 审计落盘
            if not pm.can_call_agent(pc, agent, tool):
                pm.log_access(pc, "A2A_call", f"{agent}.{tool}", "deny", "no policy/role grant")
                err = {"status": "error", "error": "Permission denied",
                       "code": "PERMISSION_DENIED",
                       "detail": f"Cannot call {agent}.{tool}"}
                _record(agent, tool, "error", "Permission denied", 0, workflow_id)
                return err
            pm.log_access(pc, "A2A_call", f"{agent}.{tool}", "allow")
        except ImportError:
            logger.debug("Permission module not available — allow all (dev mode)")

    tool_def = _find_tool(plugin, tool)
    if tool_def is None:
        err = {"status": "error", "error": f"Agent '{agent}' has no tool: {tool}"}
        _record(agent, tool, "error", str(err), 0, workflow_id)
        return err

    handler = tool_def.handler  # e.g. "pharmacy.assessment.nutrition_risk"
    module_name, func_name = handler.rsplit(".", 1)

    try:
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
    _record(agent, tool, result.get("status", "ok"), "", elapsed, workflow_id)
    return result


def call_batch(tasks: list[dict], max_workers: int = 8) -> list[dict]:
    """批量并行调用。

    tasks: [{"agent": ..., "tool": ..., "params": {...}}, ...]
    max_workers: 线程池最大工作线程数 (默认 8)。
    """
    results: list[dict | None] = [None] * len(tasks)

    def _run(idx: int, task: dict) -> tuple[int, dict]:
        return idx, call(
            agent=task["agent"],
            tool=task["tool"],
            params=task.get("params", {}),
            workflow_id=task.get("workflow_id", ""),
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
            elapsed_ms: float, workflow_id: str = "") -> None:
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

    _call_history.append(entry)
    # Prune to prevent unbounded growth
    if len(_call_history) > 1000:
        _call_history[:] = _call_history[-500:]

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


def get_history(limit: int = 20) -> list[dict[str, Any]]:
    return _call_history[-limit:]


def clear_history() -> None:
    _call_history.clear()


# ── ReAct Loop 集成 ──

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z0-9_]+)\}")


def _interpolate_env(value: Any) -> Any:
    """把配置值中的 ${ENV_NAME} 替换为环境变量值 (缺失 → 空串)。"""
    if isinstance(value, str):
        return _ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
    return value


def _load_llm_config() -> dict[str, Any]:
    """加载     LLM 配置（从 config/llm.yaml, 含环境变量插值）。"""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "config" / "llm.yaml",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "llm.yaml",
    ]
    for p in candidates:
        if p.exists():
            try:
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
            return cfg
    return {"provider": "mock", "mock_responses": True}


def _build_loop_components(agent: str):
    """构建 AgentLoop 所需组件 (共享逻辑)."""
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
        return call(agent, tool_name, tool_args)

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
        logger.debug("Guard 验证异常, 降级通过: %s", e)

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
    **kwargs,
) -> dict[str, Any]:
    """ReAct AgentLoop — LLM 自主规划调用工具，多步推理。

    Agent 的 tools 通过 A2A call() 执行，而非全局 tool registry。
    每次请求创建新的 AgentLoop 实例，无状态共享，无竞态风险。
    """
    try:
        plugin, tools, llm, _a2a_executor = _build_loop_components(agent)
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
) -> dict[str, Any]:
    """异步 ReAct AgentLoop — 支持 state_delta + session 持久化."""
    try:
        plugin, tools, llm, _a2a_executor = _build_loop_components(agent)
    except ValueError as e:
        return {"status": "error", "error": str(e)}

    from haip.loop import AsyncAgentLoop
    from haip.session.store import InMemorySessionService, SessionService
    from haip.loop.context import InvocationContext

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

    return {
        "status": "ok",
        "reply": final_reply,
        "steps": steps,
        "duration_ms": elapsed,
        "events": events,
        "session_id": session_id,
        "invocation_id": invocation_id,
        "error": final_error or None,
        "guard": guard_result,
    }


async def stream_events(
    agent: str, query: str, max_steps: int = 5,
    session_id: str = "default", user_id: str = "default",
):
    """SSE 事件流生成器 — 每步实时推送 Event (state_delta + content)."""
    import json as _json

    try:
        plugin, tools, llm, _a2a_executor = _build_loop_components(agent)
    except ValueError as e:
        yield f"data: {_json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        return

    from haip.loop import AsyncAgentLoop
    from haip.session.store import InMemorySessionService
    from haip.loop.context import InvocationContext

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

    async for evt in loop.run(query):
        yield f"data: {_json.dumps(evt.to_dict(), ensure_ascii=False)}\n\n"

    session_svc.end_invocation(session)
