"""A2A Dispatcher — Agent 间进程内调度 (统一 dispatch_entry).

与老系统的区别:
  - 老系统: 每个 Agent 手写 dispatch_entry 函数做路由
  - 新系统: 引擎根据 YAML 的 handler 字段自动完成 import → call → format
"""

from __future__ import annotations

import importlib
import time
from typing import Any

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


def call_batch(tasks: list[dict]) -> list[dict]:
    """批量并行调用 (当前为顺序实现, M5 改为 asyncio 并行)。
    
    tasks: [{"agent": ..., "tool": ..., "params": {...}}, ...]
    """
    results = []
    for task in tasks:
        results.append(call(
            agent=task["agent"],
            tool=task["tool"],
            params=task.get("params", {}),
            workflow_id=task.get("workflow_id", ""),
        ))
    return results


def _find_tool(plugin, tool_name: str):
    for t in plugin.tools:
        if t.name == tool_name:
            return t
    return None


def _record(agent: str, tool: str, status: str, error: str,
            elapsed_ms: float, workflow_id: str = "") -> None:
    _call_history.append({
        "agent": agent, "tool": tool, "status": status,
        "error": error, "elapsed_ms": round(elapsed_ms, 2),
        "workflow_id": workflow_id,
    })
    # Prune to prevent unbounded growth
    if len(_call_history) > 1000:
        _call_history[:] = _call_history[-500:]


def get_history(limit: int = 20) -> list[dict[str, Any]]:
    return _call_history[-limit:]


def clear_history() -> None:
    _call_history.clear()
