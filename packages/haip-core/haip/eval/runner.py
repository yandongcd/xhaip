"""评测执行器 — 按任务模板驱动 agent 工具链, 收集轨迹.

经 haip.a2a.call 调用 Agent YAML 定义的工具 (与生产路径一致),
逐阶段收集 {tool, params, result, elapsed_ms, ok}.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from haip.eval.scenario import EvalScenario, build_stage_inputs

_REGISTRY_ENSURED = False


def _ensure_agent_registry(agent_name: str = "orthopedic-surgery") -> None:
    """确保目标 agent 已注册 (幂等; 注册表可能被其他测试清空, 按需重载)."""
    global _REGISTRY_ENSURED
    try:
        from haip.agent import get as get_agent
        from haip.agent import load_from_dir
        if get_agent(agent_name) is not None:
            _REGISTRY_ENSURED = True
            return
        root = Path(__file__).resolve().parents[4]
        definitions = root / "packages" / "haip-hospital" / "agents" / "definitions"
        if definitions.exists():
            load_from_dir(str(definitions))
    except Exception:
        pass
    _REGISTRY_ENSURED = True


class EvalRunner:
    """按任务模板执行工具链并收集轨迹."""

    def __init__(self, agent_name: str = "orthopedic-surgery", use_llm: bool = False):
        self.agent_name = agent_name
        self.use_llm = use_llm  # llm 模式: 工具内 LLM 增强开启 (fracture/surgery)
        _ensure_agent_registry()

    def _call_tool(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """通过 A2A 调用 agent 工具 (与生产一致), 失败返回 error 结构."""
        from haip.a2a import call as a2a_call

        _ensure_agent_registry(self.agent_name)

        if self.use_llm and tool in ("classify_fracture", "surgical_plan"):
            params = dict(params)
            params["use_llm"] = True
        t0 = time.time()
        try:
            resp = a2a_call(self.agent_name, tool, params)
            elapsed = (time.time() - t0) * 1000
            if isinstance(resp, dict) and resp.get("status") == "error":
                return {"_ok": False, "_elapsed_ms": round(elapsed, 1),
                        "_error": resp.get("error", "a2a error")}
            return {"_ok": True, "_elapsed_ms": round(elapsed, 1), **resp}
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            return {"_ok": False, "_elapsed_ms": round(elapsed, 1), "_error": str(e)[:200]}

    def run_scenario(self, scenario: EvalScenario) -> dict[str, Any]:
        """执行单个场景的完整工具链, 返回 stage_id → 结果轨迹."""
        results: dict[str, dict[str, Any]] = {}
        for stage in scenario.task.get("stages", []):
            tool = stage.get("tool", "")
            inputs = build_stage_inputs(stage, scenario)
            result = self._call_tool(tool, inputs)
            results[stage.get("id", tool)] = result
        return results


def run_all(
    scenarios: list[EvalScenario],
    agent_name: str = "orthopedic-surgery",
    use_llm: bool = False,
) -> list[dict[str, Any]]:
    """批量执行场景, 返回每场景 {scenario_id, results}."""
    runner = EvalRunner(agent_name=agent_name, use_llm=use_llm)
    out = []
    for s in scenarios:
        out.append({"scenario_id": s.scenario_id, "results": runner.run_scenario(s)})
    return out
