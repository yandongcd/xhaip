"""评测 CLI — python -m haip.eval run --task orthopedics_hip_fracture --mode mock|llm.

示例:
    python -m haip.eval run --task orthopedics_hip_fracture --mode mock --limit 5
    python -m haip.eval run --task orthopedics_hip_fracture --mode llm --limit 20
    python -m haip.eval list-tasks
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="haip.eval", description="医学 Agent 评测框架")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="运行评测")
    run.add_argument("--task", default="orthopedics_hip_fracture", help="任务模板名")
    run.add_argument("--mode", choices=["mock", "llm"], default="mock",
                     help="mock=规则评分(CI 可跑); llm=真实 LLM + judge")
    run.add_argument("--limit", type=int, default=0, help="场景数上限 (0=全部)")
    run.add_argument("--agent", default="orthopedic-surgery", help="被测 agent")
    run.add_argument("--judge-against", default="", help="对比基线模型路径 (judge 模式)")
    run.add_argument("--output", default="eval_report.json", help="JSON 输出路径")
    run.add_argument("--markdown", default="", help="Markdown 输出路径")

    sub.add_parser("list-tasks", help="列出可用任务模板")
    return p


def _run_eval(args: argparse.Namespace) -> dict[str, Any]:
    from haip.eval import build_scenarios, list_tasks, run_all
    from haip.eval.report import build_report, save_report
    from haip.eval.scorer import judge_pair, judge_summary, score_scenario_rules

    if args.task not in list_tasks():
        sys.exit(f"未知任务: {args.task}, 可用: {list_tasks()}")

    scenarios = build_scenarios(args.task, limit=args.limit)
    if not scenarios:
        sys.exit("无匹配场景 (检查数字病人库与任务科室)")

    use_llm = args.mode == "llm"
    traces = run_all(scenarios, agent_name=args.agent, use_llm=use_llm)
    scores = []
    for trace, scenario in zip(traces, scenarios):
        scores.append(score_scenario_rules(scenario, trace["results"]))

    judge = None
    if use_llm and len(scores) >= 2:
        # 成对 judge: 当前 agent vs 基线 (或高分 vs 低分场景输出对比)
        pair_results = []
        for trace, scenario, score in zip(traces, scenarios, scores):
            text = json.dumps(trace["results"], ensure_ascii=False)[:3000]
            baseline = f"基线规则引擎输出 (场景 {scenario.scenario_id})"
            provider = _get_provider()
            pair_results.append(judge_pair(
                question=scenario_to_question(scenario),
                ans_a=baseline,
                ans_b=text,
                provider=provider,
            ))
        judge = judge_summary(pair_results)

    report = build_report(args.task, args.mode, scenarios, scores, judge=judge)
    save_report(report, args.output, args.markdown)
    return report


def scenario_to_question(scenario: Any) -> str:
    from haip.eval.scenario import scenario_to_case_text
    return f"{scenario_to_case_text(scenario.patient)} — 请给出诊疗决策。"


def _get_provider():
    from pathlib import Path

    import yaml

    from haip.llm import LLMProvider
    from haip.llm.mock import MockProvider
    cfg_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "llm.yaml"
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = (yaml.safe_load(f) or {}).get("llm", {}) or {}
    except Exception:
        cfg = {}
    if cfg.get("provider", "mock") != "mock" and not cfg.get("api_key"):
        return MockProvider({})
    try:
        return LLMProvider.from_config(cfg)
    except Exception:
        return MockProvider({})


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "list-tasks":
        from haip.eval import list_tasks
        print("\n".join(list_tasks()))
        return 0
    if args.command == "run":
        report = _run_eval(args)
        agg = report["aggregate"]
        print(f"=== {report['task']} ({report['mode']}) ===")
        print(f"场景数: {report['scenarios_count']}")
        print(f"综合: {agg['overall']:.1f} | 疗效: {agg['efficacy']:.1f} | "
              f"流程: {agg['process']:.1f} | 伦理: {agg['ethics']:.1f}")
        if report.get("judge"):
            j = report["judge"]
            print(f"judge: M2 胜率 {j.get('m2_win_rate')}% (CI {j.get('m2_ci')}), "
                  f"净胜率 {j.get('net_win_rate')}%")
        print(f"报告: {args.output}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
