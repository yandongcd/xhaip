"""进化引擎 — 评测轨迹 → 成功入案例库 / 失败反思+验证 (SEAL MedAgent-Zero 流程).

循环 (每场景):
  1. 评估场景 (haip.eval) → 检查点报告
  2. 有 gold 匹配失败 → 反思生成经验草案 → 验证闸门
  3. 全部关键检查点通过 → 成功案例入库
"""

from __future__ import annotations

import uuid
from typing import Any

from haip.evolution.memory_base import CaseEntry, EvolutionMemory, get_evolution_memory
from haip.evolution.reflect import reflect_failure
from haip.evolution.validate import validate_experience


def _scenario_question(scenario: Any) -> str:
    from haip.eval.scenario import scenario_to_case_text
    return scenario_to_case_text(scenario.patient)


def evolve_from_eval(
    scenario: Any,
    eval_report: dict[str, Any],
    agent: str = "orthopedic-surgery",
    memory: EvolutionMemory | None = None,
) -> dict[str, Any]:
    """单场景进化: 返回 {action: record_case|reflect|skip, case_id?, exp_id?, verdict?}."""
    memory = memory or get_evolution_memory()

    # 关键检查点 (gold 匹配 + 核心决策)
    key_items = []
    for st in eval_report.get("stages", []):
        for item in st.get("items", []):
            if item.get("field") == "urgency" or "金标准" in item.get("detail", ""):
                key_items.append(item)

    failed = [i for i in key_items if not i["passed"]]

    if not failed:
        # 成功: 入案例库
        case_id = f"case_{uuid.uuid4().hex[:8]}"
        memory.add_case(CaseEntry(
            case_id=case_id,
            agent=agent,
            task=scenario.task.get("name", "unknown"),
            question=_scenario_question(scenario),
            answer=eval_report.get("results", {}),
            gold=scenario.gold,
            matched=True,
        ))
        return {"action": "record_case", "case_id": case_id}

    # 失败: 反思 → 经验草案 → 验证
    results = eval_report.get("results", {})
    patient = scenario.patient
    exp = reflect_failure(
        agent=agent,
        task=scenario.task.get("name", "unknown"),
        patient=patient,
        result=results,
        gold=scenario.gold,
        failed_items=failed,
    )
    memory.add_experience(exp)
    verdict = validate_experience(exp.exp_id, memory=memory, mode="sprt")
    return {"action": "reflect", "exp_id": exp.exp_id, "verdict": verdict["verdict"]}


def seed_cases_from_corpus(
    corpus_items: list[dict[str, Any]],
    agent: str = "orthopedic-surgery",
    memory: EvolutionMemory | None = None,
    skip_contaminated: bool = False,
) -> int:
    """把合成语料 (金标签 QA) 作为案例库种子入库.

    skip_contaminated=True 时跳过与知识库同源的条目 (去污染门控).
    """
    memory = memory or get_evolution_memory()
    added = 0
    for i, item in enumerate(corpus_items):
        question = item.get("question", "")
        gold = item.get("gold", {})
        if not question or not gold:
            continue
        case_id = f"seed_{uuid.uuid4().hex[:8]}"
        memory.add_case(CaseEntry(
            case_id=case_id,
            agent=agent,
            task=item.get("type", "synthetic"),
            question=question,
            answer={"answer": item.get("answer", ""), "guideline_ref": item.get("guideline_ref", [])},
            gold=gold,
            matched=True,
        ))
        added += 1
    return added


def run_evolution_cycle(
    scenarios: list[Any],
    traces: list[dict[str, Any]],
    agent: str = "orthopedic-surgery",
    memory: EvolutionMemory | None = None,
) -> dict[str, Any]:
    """批量进化循环: 返回统计."""
    from haip.eval.scenario import evaluate_scenario_stages

    memory = memory or get_evolution_memory()
    stats: dict[str, Any] = {"record_case": 0, "reflect": 0, "skip": 0, "verdicts": {}}
    for scenario, trace in zip(scenarios, traces):
        report = evaluate_scenario_stages(scenario, trace["results"])
        report["results"] = trace["results"]
        outcome = evolve_from_eval(scenario, report, agent=agent, memory=memory)
        stats[outcome.get("action", "skip")] += 1
        verdict = outcome.get("verdict")
        if verdict:
            stats["verdicts"][verdict] = stats["verdicts"].get(verdict, 0) + 1
    stats["cases"] = memory.count_cases(agent)
    stats["experiences"] = len(memory.list_experiences(agent))
    return stats
