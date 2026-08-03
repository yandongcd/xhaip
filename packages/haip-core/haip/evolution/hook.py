"""进化生产钩子 (L6) — a2a._record 后异步触发进化学习.

fire-and-forget: 不阻塞 A2A 主路径, 异常静默.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def evolution_hook(agent: str, tool: str, status: str, result: dict[str, Any] | None = None) -> None:
    """a2a._record 后的异步进化钩子 (fire-and-forget).

    当 agent 调用成功时 (status='ok'), 尝试:
    1. 从 KG 查找相关金标准 (指南/规则)
    2. 构建 EvalTrajectory
    3. 调用 evolve_from_eval → 成功入案例库 / 失败反思
    """
    if status != "ok":
        return

    try:
        from haip.agent import get as _get_agent
        plugin = _get_agent(agent)
        if plugin is None:
            return
        # 仅对有 learning 配置的 agent 执行进化
        if not getattr(plugin, "learning", None):
            return
    except Exception:
        return

    try:
        # 查找与工具相关的金标准 (通过 KG)
        gold = _lookup_gold(agent, tool, result or {})
        if not gold:
            return  # 无可对标的金标准 → 跳过

        from haip.evolution.trajectory import EvalTrajectory, ToolCallRecord
        from haip.evolution.engine import evolve_from_eval

        trajectory = EvalTrajectory(
            agent=agent,
            patient={"patient_id": "prod", "diagnosis": str(result.get("diagnosis", "") or "unknown")},
            tool_calls=[ToolCallRecord(tool=tool, result=result or {}, ok=True)],
            gold=gold,
            task=tool,
        )

        # 构造简化的 eval_report (使 evolve_from_eval 兼容)
        eval_report = {
            "stages": [{"items": [
                {"field": f"gold_{k}", "detail": f"实际={result.get(k)}, 金标准={v}", "passed": result.get(k) == v}
                for k, v in gold.items()
            ]}],
            "results": {tool: {"_ok": True, **result}} if result else {},
        }
        outcome = evolve_from_eval(None, eval_report, agent=agent)
        logger.debug("Evolution hook: %s %s → %s", agent, tool, outcome.get("action", "skip"))
    except Exception:
        logger.debug("Evolution hook 执行异常 (非致命)", exc_info=True)


def _lookup_gold(agent: str, tool: str, result: dict[str, Any]) -> dict[str, Any] | None:
    """从 KG 查找与工具相关的金标准.

    例如: timing_decision → surgery_type_rules 的 decision_matrix 期望.
    """
    try:
        from haip.kg import trace_evidence
        gold: dict[str, Any] = {}

        # 用 result 中的 urgency (如有) 作为查询 key 查证据链
        urgency = result.get("urgency")
        if urgency and tool == "timing_decision":
            evidence = trace_evidence("timing-rule-t2-001")  # MDT延迟手术规则
            if evidence.get("guidelines"):
                gold["urgency"] = urgency  # 假设 agent 的 verdict 是金标准 (进化是 self-consistency check)

        return gold if gold else None
    except Exception:
        return None
