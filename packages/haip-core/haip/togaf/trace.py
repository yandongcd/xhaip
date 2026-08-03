"""TOGAF-AI 决策溯源 (B3) — 每步决策带完整 provenance.

可解释-原生架构: 不是事后解释, 而是 Agent 执行路径的自动记录.
每条输出携带: 查询KG → 匹配规则 → LLM推理 → Guard审问 → HITL确认 的完整链条.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DecisionStep:
    """单步决策溯源."""
    step: str                            # KG查询 / 规则执行 / LLM推理 / Guard审问 / HITL
    source: str                          # 证据来源 (guideline YAML / rule ID / agent name)
    trust_level: str = ""               # T1/T2
    input_summary: str = ""              # 输入摘要
    output_summary: str = ""             # 输出摘要
    elapsed_ms: float = 0.0
    status: str = "ok"                  # ok / warning / blocked


@dataclass
class DecisionTrace:
    """完整决策溯源链."""
    agent: str
    patient_id: str
    steps: list[DecisionStep] = field(default_factory=list)
    final_output: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "patient_id": self.patient_id,
            "timestamp": self.timestamp,
            "steps": [
                {"step": s.step, "source": s.source, "trust_level": s.trust_level,
                 "input": s.input_summary[:100], "output": s.output_summary[:200],
                 "status": s.status, "elapsed_ms": s.elapsed_ms}
                for s in self.steps
            ],
            "final_output": self.final_output[:500],
            "chain_summary": " → ".join(f"{s.step}[{s.source[:30]}]" for s in self.steps),
        }

    def has_guideline_evidence(self) -> bool:
        return any(s.step == "KG查询" and s.trust_level for s in self.steps)

    def has_rule_execution(self) -> bool:
        return any(s.step == "规则执行" for s in self.steps)

    def has_guard_interrogation(self) -> bool:
        return any(s.step == "Guard审问" for s in self.steps)


class TraceRecorder:
    """决策溯源记录器 — 挂在 AgentLoop / a2a.call 后自动收集."""

    def __init__(self, agent: str, patient_id: str = ""):
        self.trace = DecisionTrace(agent=agent, patient_id=patient_id)

    def record_kg_query(self, query: str, results: list[dict[str, Any]],
                        trust_level: str = "") -> None:
        self.trace.steps.append(DecisionStep(
            step="KG查询",
            source=f"by_diagnosis({query[:30]})",
            trust_level=trust_level,
            input_summary=query[:80],
            output_summary=f"{len(results)} results (trust {trust_level})",
        ))

    def record_rule_execution(self, rule_id: str, condition: str,
                              verdict: str, source: str = "") -> None:
        self.trace.steps.append(DecisionStep(
            step="规则执行",
            source=source or rule_id,
            input_summary=condition[:80],
            output_summary=verdict[:200],
        ))

    def record_llm_reasoning(self, agent: str, input_len: int,
                             output: str, elapsed_ms: float) -> None:
        self.trace.steps.append(DecisionStep(
            step="LLM推理",
            source=agent,
            input_summary=f"prompt {input_len} chars",
            output_summary=output[:200],
            elapsed_ms=elapsed_ms,
        ))

    def record_guard_interrogation(self, passed: bool, score: int,
                                   core_passed: int) -> None:
        self.trace.steps.append(DecisionStep(
            step="Guard审问",
            source="guard/interrogate.py",
            output_summary=f"{score}/9 passed, core {core_passed}/3",
            status="ok" if passed else "warning",
        ))

    def record_hitl(self, reviewer: str, action: str) -> None:
        self.trace.steps.append(DecisionStep(
            step="HITL",
            source=reviewer or "human",
            output_summary=action,
            status="ok",
        ))

    def finalize(self, output: str) -> DecisionTrace:
        self.trace.final_output = output
        return self.trace

    def to_json(self) -> str:
        return json.dumps(self.trace.to_dict(), ensure_ascii=False, indent=2)


def build_trace_from_call(agent: str, patient_id: str,
                          tool_results: dict[str, Any],
                          guard_result: dict[str, Any] | None = None,
                          kg_queries: list[dict[str, Any]] | None = None,
                          ) -> dict[str, Any]:
    """从 A2A 调用结果构建决策溯源."""
    recorder = TraceRecorder(agent, patient_id)

    # KG 查询
    if kg_queries:
        for q in kg_queries:
            recorder.record_kg_query(
                q.get("query", ""),
                q.get("results", []),
                q.get("trust_level", ""),
            )

    # 工具执行 (每个 tool 对应一条规则/函数)
    for tool_name, result in tool_results.items():
        if result.get("_ok"):
            recorder.record_rule_execution(
                rule_id=tool_name,
                input_summary=json.dumps({k: v for k, v in result.items() if not k.startswith("_")})[:80],
                verdict=str(result.get("urgency", result.get("recommended_surgery", "")))[:80],
            )

    # Guard 审问
    if guard_result:
        ir = guard_result.get("interrogation")
        if ir:
            # ir may be InterrogationReport or dict
            passed = ir.is_clean() if hasattr(ir, "is_clean") else ir.get("passed", False)
            score = ir.passed_dimensions if hasattr(ir, "passed_dimensions") else ir.get("passed_dimensions", 0)
            core = ir.core_passed if hasattr(ir, "core_passed") else ir.get("core_passed", 0)
            recorder.record_guard_interrogation(passed, score, core)

    output = tool_results.get("_final_reply", "Agent 推理完成")
    recorder.finalize(str(output))
    return recorder.trace.to_dict()
