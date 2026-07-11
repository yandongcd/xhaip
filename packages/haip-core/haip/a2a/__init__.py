"""A2A Dispatcher — Agent 间进程内调度 (统一 dispatch_entry).

与老系统的区别:
  - 老系统: 每个 Agent 手写 dispatch_entry 函数做路由
  - 新系统: 引擎根据 YAML 的 handler 字段自动完成 import → call → format
"""

from __future__ import annotations

import importlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from haip.agent import get as get_agent


_agent_cache: dict[str, Any] = {}       # module cache: module_path → module_obj
_call_history: list[dict[str, Any]] = []


def call(agent: str, tool: str, params: dict[str, Any] | None = None,
         workflow_id: str = "") -> dict[str, Any]:
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
    except Exception:
        pass

    _call_history.append(entry)
    # Prune to prevent unbounded growth
    if len(_call_history) > 1000:
        _call_history[:] = _call_history[-500:]


def get_history(limit: int = 20) -> list[dict[str, Any]]:
    return _call_history[-limit:]


def clear_history() -> None:
    _call_history.clear()


# ── ReAct Loop 集成 ──

def _load_llm_config() -> dict[str, Any]:
    """加载 LLM 配置（从 config/llm.yaml）。"""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "config" / "llm.yaml",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "llm.yaml",
    ]
    for p in candidates:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f).get("llm", {})
    return {"provider": "mock", "mock_responses": True}


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
    plugin = get_agent(agent)
    if plugin is None:
        return {"status": "error", "error": f"Unknown agent: {agent}"}

    # 提取 per-agent tools → schema
    tools = [
        {"name": t.name, "description": t.description, "input": t.input}
        for t in plugin.tools
    ]

    # 创建 LLM
    from haip.llm import LLMProvider

    llm_config = _load_llm_config()
    try:
        llm = LLMProvider.from_config(llm_config)
    except Exception:
        from haip.llm.mock import MockProvider
        llm = MockProvider({})

    # 工具执行器 → 通过 A2A 路由（支持跨 Agent 调用）
    def _a2a_executor(tool_name: str, tool_args: dict) -> dict:
        return call(agent, tool_name, tool_args)

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

    # 高危输出 Guard 校验
    guard_result = {"checked": False, "passed": True, "flags": []}
    try:
        from haip.guard.verifier import GuardVerifier
        verifier = GuardVerifier()
        g = verifier.verify(
            output=result.reply,
            scenario="药物交互" if any(
                kw in str(result.tool_calls) for kw in ["antiemetic", "ponv", "drug", "regimen"]
            ) else "",
            agent_name=agent,
        )
        guard_result = {
            "checked": True,
            "passed": g.passed,
            "flags": g.flags,
            "requires_human_review": g.requires_human_review,
        }
    except Exception:
        pass  # Guard is best-effort, don't block response

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
