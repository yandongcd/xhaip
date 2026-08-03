"""评测报告 — JSON + Markdown 导出."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def build_report(
    task_name: str,
    mode: str,
    scenarios: list[Any],
    scores: list[Any],
    judge: dict[str, Any] | None = None,
    durations: dict[str, float] | None = None,
) -> dict[str, Any]:
    """聚合完整评测报告."""
    n = len(scores)
    agg = {"efficacy": 0.0, "process": 0.0, "ethics": 0.0, "overall": 0.0}
    if n:
        for s in scores:
            agg["efficacy"] += s.efficacy
            agg["process"] += s.process
            agg["ethics"] += s.ethics
            agg["overall"] += s.overall
        for k in agg:
            agg[k] = round(agg[k] / n, 1)

    failures = [
        {"scenario_id": s.scenario_id, "score": s.overall,
         "details": s.details}
        for s in scores if s.overall < 60
    ]
    return {
        "task": task_name,
        "mode": mode,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "scenarios_count": n,
        "aggregate": agg,
        "dimensions": {"efficacy": 0.40, "process": 0.35, "ethics": 0.25},
        "judge": judge,
        "failures": failures[:20],
        "per_scenario": [
            {"scenario_id": s.scenario_id, "overall": s.overall,
             "efficacy": s.efficacy, "process": s.process, "ethics": s.ethics}
            for s in scores
        ],
    }


def to_markdown(report: dict[str, Any]) -> str:
    agg = report["aggregate"]
    lines = [
        f"# 医学 Agent 评测报告 — {report['task']}",
        "",
        f"- 模式: `{report['mode']}` | 场景数: {report['scenarios_count']} | 时间: {report['timestamp']}",
        "",
        "## 三维度总分 (0-100)",
        "",
        "| 临床疗效 | 流程能力 | 专业伦理 | **综合** |",
        "|--------:|--------:|--------:|--------:|",
        f"| {agg['efficacy']:.1f} | {agg['process']:.1f} | {agg['ethics']:.1f} | **{agg['overall']:.1f}** |",
        "",
    ]
    if report.get("judge"):
        j = report["judge"]
        lines += [
            "## LLM-as-judge 对比 (Auto-MOOVE 协议)",
            "",
            f"- 总对数: {j.get('total', 0)}",
            (
                f"- 胜率: M1 {j.get('m1_win_rate', '-')}% (CI {j.get('m1_ci', '-')}), "
                f"M2 {j.get('m2_win_rate', '-')}% (CI {j.get('m2_ci', '-')})"
            ),
            (
                f"- 平局: {j.get('tie_rate', '-')}% | 净胜率: {j.get('net_win_rate', '-')}% "
                f"(CI {j.get('net_ci', '-')})"
            ),
            "",
        ]
    if report.get("failures"):
        lines += ["## 低分场景 (<60)", ""]
        for f_ in report["failures"]:
            lines.append(f"- `{f_['scenario_id']}`: {f_['score']:.1f} — {f_.get('details', {})}")
        lines.append("")
    return "\n".join(lines)


def save_report(report: dict[str, Any], path: str, markdown_path: str = "") -> None:
    import pathlib
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if markdown_path:
        mp = pathlib.Path(markdown_path)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(to_markdown(report), encoding="utf-8")
