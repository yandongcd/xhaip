"""haip/eval 评测框架测试 — mock 模式 (CI 可跑)."""

from __future__ import annotations

import json

import pytest


@pytest.fixture(scope="module")
def ortho_scenarios():
    from haip.eval import build_scenarios
    scs = build_scenarios("orthopedics_hip_fracture", limit=3)
    if not scs:
        pytest.skip("无骨科患者数据")
    return scs


def test_list_tasks():
    from haip.eval import list_tasks
    tasks = list_tasks()
    assert "orthopedics_hip_fracture" in tasks


def test_load_task():
    from haip.eval import load_task
    task = load_task("orthopedics_hip_fracture")
    assert task["department"] == "orthopedic_surgery"
    assert len(task["stages"]) == 7
    assert set(task["dimensions"]) == {"efficacy", "process", "ethics"}


def test_scenario_gold_urgency(ortho_scenarios):
    s = ortho_scenarios[0]
    assert s.expected_urgency in ("emergency", "urgent", "elective")
    assert s.gold.get("urgency") == s.expected_urgency


def test_checkpoint_operators():
    from haip.eval.checkpoints import evaluate_checkpoint
    assert evaluate_checkpoint(
        {"id": "t", "type": "rule", "field": "x", "op": ">=", "value": 5},
        {"x": 7})["passed"] is True
    assert evaluate_checkpoint(
        {"id": "t", "type": "rule", "field": "x", "op": "in", "value": [1, 2]},
        {"x": 3})["passed"] is False
    assert evaluate_checkpoint(
        {"id": "t", "type": "rule", "field": "y", "op": "nonempty"},
        {"y": []})["passed"] is False
    # gold 对比
    assert evaluate_checkpoint(
        {"id": "g", "type": "gold", "field": "urgency"},
        {"urgency": "emergency"}, {"urgency": "emergency"})["passed"] is True
    assert evaluate_checkpoint(
        {"id": "g", "type": "gold", "field": "urgency"},
        {"urgency": "urgent"}, {"urgency": "emergency"})["passed"] is False


def test_runner_executes_toolchain(ortho_scenarios):
    from haip.eval.runner import EvalRunner
    runner = EvalRunner()
    results = runner.run_scenario(ortho_scenarios[0])
    assert set(results.keys()) == {"triage", "timing", "classify", "surgery_plan",
                                   "complications", "nursing", "followup"}
    for r in results.values():
        assert r["_ok"] is True, f"工具失败: {r.get('_error')}"


def test_score_scenario_rules_bounds(ortho_scenarios):
    from haip.eval.runner import EvalRunner
    from haip.eval.scorer import score_scenario_rules
    runner = EvalRunner()
    results = runner.run_scenario(ortho_scenarios[0])
    score = score_scenario_rules(ortho_scenarios[0], results)
    assert 0 <= score.efficacy <= 100
    assert 0 <= score.process <= 100
    assert 0 <= score.ethics <= 100
    assert 0 <= score.overall <= 100


def test_full_mock_run_reports():
    """CLI 路径: mock 全流程产出报告."""
    import os
    import tempfile

    from haip.eval.cli import main
    out = os.path.join(tempfile.gettempdir(), "eval_test_report.json")
    rc = main(["run", "--task", "orthopedics_hip_fracture", "--mode", "mock",
               "--limit", "2", "--output", out])
    assert rc == 0
    with open(out, encoding="utf-8") as f:
        report = json.load(f)
    assert report["mode"] == "mock"
    assert report["scenarios_count"] == 2
    assert "aggregate" in report and "overall" in report["aggregate"]
    assert "per_scenario" in report


def test_judge_pair_swap_unswap():
    """Auto-MOOVE 位置偏差: swap 后 unswap 还原."""
    from haip.eval.scorer import _unswap, build_judge_messages
    data = {"winner": "Model 2", "scores": {"Model 1": {"clarity": 4}, "Model 2": {"clarity": 3}}}
    swapped = _unswap(data, swap=True)
    assert swapped["winner"] == "Model 1"
    assert swapped["scores"]["Model 1"]["clarity"] == 3  # 还原后 M1=原M2 的 3 分


def test_judge_pair_with_mock_provider():
    """MockProvider 模式: judge 返回解析失败时安全降级为 Tie."""
    from haip.eval.scorer import judge_pair
    from haip.llm.mock import MockProvider
    provider = MockProvider({})
    result = judge_pair("临床问题", "答案A", "答案B", provider=provider)
    assert result["winner"] in ("Model 1", "Model 2", "Tie")
    assert "parse_failure" in result  # mock 非 JSON → 解析失败降级


def test_judge_summary_ci():
    from haip.eval.scorer import compute_ci, judge_summary
    pt, (lo, hi) = compute_ci([1.0] * 10)
    assert pt == 1.0 and lo == 1.0 and hi == 1.0
    summary = judge_summary([
        {"winner": "Model 1"}, {"winner": "Model 2"}, {"winner": "Tie"},
        {"winner": "Model 2"}, {"winner": "Model 1"},
    ])
    assert summary["total"] == 5
    assert summary["m1_win_rate"] == 40.0
    assert summary["m2_win_rate"] == 40.0
    assert summary["tie_rate"] == 20.0
    assert 0 <= summary["net_win_rate"] <= 100


def test_report_markdown():
    from haip.eval.report import build_report, to_markdown
    report = build_report("t", "mock", [], [], judge=None)
    md = to_markdown(report)
    assert "评测报告" in md
    assert "三维度" in md
