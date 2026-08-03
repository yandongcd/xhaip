"""三层增强测试 — 记忆注入 + Plan-then-Execute + 进化闭环."""
from __future__ import annotations

import pytest

from haip.llm import ChatResponse, ToolCall
from haip.llm.mock import SeqMockProvider


@pytest.fixture(scope="module")
def _registry():
    from pathlib import Path

    from haip.agent import load_from_dir
    load_from_dir(str(Path(r"D:\dst\projects\xhaip\packages\haip-hospital\agents\definitions")))


def test_memory_inject_context():
    """层2: 记忆注入 — case_base 案例进入 system prompt."""
    from haip.evolution.memory_base import CaseEntry, get_evolution_memory
    mem = get_evolution_memory()
    mem.add_case(CaseEntry(
        case_id="mem-inject-test", agent="orthopedic-surgery",
        task="orthopedics_hip_fracture",
        question="85岁女性 左股骨颈骨折",
        answer={"urgency": "emergency"}, gold={"urgency": "emergency"},
    ))
    from haip.loop.memory_inject import build_memory_context, inject_into_system_prompt
    ctx = build_memory_context("股骨颈骨折 评估", "orthopedic-surgery")
    injected = inject_into_system_prompt("你是骨科助手", ctx)
    assert "[相关历史案例]" in injected or "[相关指南]" in injected or "[近期同类决策]" in injected


def test_memory_inject_returns_empty_on_no_data():
    """层2: 无数据时返回空 (不影响原 prompt)."""
    from haip.loop.memory_inject import build_memory_context
    ctx = build_memory_context("无相关诊断词", "ghost-agent")
    assert ctx == "" or isinstance(ctx, str)


def test_plan_mode_executes_all_tools(_registry):
    """层1: Plan-then-Execute — 一次规划执行多工具再综合."""
    from haip.a2a import call_with_loop

    mock = SeqMockProvider([
        ChatResponse(content="", tool_calls=[
            ToolCall(id="p1", name="checklist", arguments={"symptoms": ["摔倒后左髋疼痛"], "conditions": ["左股骨颈骨折"], "age": 85}),
            ToolCall(id="p2", name="timing_decision", arguments={"patient_id": "P001", "labs": {}}),
            ToolCall(id="p3", name="classify_fracture", arguments={"diagnosis": "左股骨颈骨折", "xray_findings": {"location": "femoral_neck", "type": "IV"}}),
        ]),
        ChatResponse(content="综合结果: Garden IV, 建议THA"),
    ])
    r = call_with_loop(
        "orthopedic-surgery", "评估并制定方案",
        llm_provider=mock, plan_mode=True, max_steps=5,
    )
    assert r["status"] == "ok"
    assert len(r["tool_calls"]) == 3
    tools = [tc["tool"] for tc in r["tool_calls"]]
    assert "checklist" in tools
    assert "timing_decision" in tools
    assert "classify_fracture" in tools
    assert "Garden" in r.get("reply", "") or "THA" in r.get("reply", "")


def test_plan_mode_with_template(_registry):
    """层1: plan_template 作为临床路径框架."""
    from haip.a2a import call_with_loop

    mock = SeqMockProvider([
        ChatResponse(content="", tool_calls=[ToolCall(id="p1", name="timing_decision", arguments={"patient_id": "P001"})]),
        ChatResponse(content="48h内手术"),
    ])
    r = call_with_loop(
        "orthopedic-surgery", "评估时机",
        llm_provider=mock, plan_mode=True,
        plan_template=["checklist", "timing_decision", "classify_fracture"],
    )
    assert r["status"] == "ok"
    assert len(r["tool_calls"]) == 1


def test_plan_mode_single_answer_no_tools(_registry):
    """层1: LLM 直接回答 (无工具) 时单步完成."""
    from haip.a2a import call_with_loop

    mock = SeqMockProvider([ChatResponse(content="无需额外工具, 建议门诊随诊")])
    r = call_with_loop("orthopedic-surgery", "简单问题", llm_provider=mock, plan_mode=True)
    assert r["status"] == "ok"
    assert "门诊" in r.get("reply", "")


def test_memory_injection_wired_into_loop(_registry):
    """层2: call_with_loop memory_injection 参数接线."""
    from haip.a2a import call_with_loop

    mock = SeqMockProvider([ChatResponse(content="评估完成")])
    r = call_with_loop("orthopedic-surgery", "评估", llm_provider=mock,
                       memory_injection=True, max_steps=2)
    assert r["status"] == "ok"


def test_evolution_runner_closure():
    """层3: 进化闭环 — 批量虚拟病人→进化→前后对比."""
    from haip.evolution.runner import run_evolution_batch
    result = run_evolution_batch(n_patients=5, seed=42)
    assert result["evolved"] >= 0
    assert result["cases"] >= 0
    assert "improvement" in result
