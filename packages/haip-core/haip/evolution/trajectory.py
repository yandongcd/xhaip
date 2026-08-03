"""EvalTrajectory 协议 — evolution 与 eval 的解耦接口.

evolution 引擎只消费此协议 (不再依赖 eval 的内部数据结构).
eval / 虚拟病人 / 外部评测 各自负责生成轨迹.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCallRecord:
    """单次工具调用记录."""
    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    elapsed_ms: float = 0.0


@dataclass
class EvalTrajectory:
    """评测轨迹: agent + 患者 + 工具调用链 + 金标准.

    与 evolution 引擎的标准接口.
    """

    agent: str
    patient: dict[str, Any]
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    gold: dict[str, Any] = field(default_factory=dict)
    task: str = ""

    def question_text(self) -> str:
        """从患者数据生成可检索文本 (用于案例库检索)."""
        p = self.patient
        parts = []
        if p.get("age"):
            parts.append(f"{p['age']}岁")
        if p.get("gender"):
            parts.append(str(p.get("gender", "")))
        if p.get("diagnosis"):
            parts.append(str(p.get("diagnosis", "")))
        if p.get("chief_complaint"):
            parts.append(str(p.get("chief_complaint", "")))
        return "，".join(parts) or "未知患者"

    def has_failed(self) -> bool:
        return any(not tc.ok for tc in self.tool_calls)

    def passed_count(self) -> int:
        return sum(1 for tc in self.tool_calls if tc.ok)


def from_eval_scenario(scenario: Any, eval_report: dict[str, Any]) -> EvalTrajectory:
    """从 haip/eval 场景 + 报告 → EvalTrajectory."""
    patient = scenario.patient
    results = eval_report.get("results", {})
    tool_calls = []
    for stage_id, result in results.items():
        tool_calls.append(ToolCallRecord(
            tool=stage_id,
            params={},
            result={k: v for k, v in result.items() if not k.startswith("_")},
            ok=result.get("_ok", False),
            elapsed_ms=result.get("_elapsed_ms", 0.0),
        ))
    return EvalTrajectory(
        agent="orthopedic-surgery",
        patient=patient,
        tool_calls=tool_calls,
        gold=scenario.gold,
        task=scenario.task.get("name", ""),
    )


def from_a2a_session(agent: str, patient: dict, results: list[dict], gold: dict | None = None) -> EvalTrajectory:
    """从 A2A 会话结果 → EvalTrajectory."""
    return EvalTrajectory(
        agent=agent,
        patient=patient,
        tool_calls=[ToolCallRecord(
            tool=r.get("tool", ""),
            params={},
            result=r.get("result", {}),
            ok=r.get("status") == "ok",
            elapsed_ms=r.get("elapsed_ms", 0.0),
        ) for r in results],
        gold=gold or {},
    )
