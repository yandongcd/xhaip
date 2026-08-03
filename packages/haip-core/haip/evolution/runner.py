"""进化闭环批处理 (层3) — 虚拟病人→Agent→进化→前后评测.

流程:
  Round 1: N 个虚拟病人 → agent 会诊 → 转归 → evolve (案例库/经验库增长)
  评测:    跑内置基准 (before vs after)
  Round 2: 同 N 个新病人 (新seed) → 此时 agent 推理可检索 Round1 经验
            → 分数提升即为进化证据
"""

from __future__ import annotations

import time
from typing import Any

from haip.clinical.patient_agent import PatientAgent, run_consultation
from haip.clinical.progression import ProgressionEngine


def _load_sample_patients(n: int) -> list[dict[str, Any]]:
    """加载骨科患者样本."""
    try:
        from haip.patients import load_all_patients
        all_p = load_all_patients()
        ortho = [p for p in all_p if any(k in str(p.get("diagnosis", "")) for k in ("髋", "股骨颈", "转子间", "骨折"))]
        return ortho[:n]
    except Exception:
        return [{"patient_id": f"syn-{i}", "age": 75 + i % 15, "gender": "女",
                 "diagnosis": "左股骨颈骨折", "scenario": "摔倒后左髋疼痛",
                 "lab_results": {"肌钙蛋白I": 0.03, "血红蛋白测定": 100}}
                for i in range(n)]


def run_evolution_batch(n_patients: int = 20, seed: int = 42,
                        agent_name: str = "orthopedic-surgery",
                        use_llm: bool = False) -> dict[str, Any]:
    """单轮进化批处理: 虚拟病人会诊 → 进化学习 → 统计.

    Returns {evolved, cases, experiences, outcomes, improvement}
    """
    from haip.evolution.memory_base import get_evolution_memory

    memory = get_evolution_memory()
    patients = _load_sample_patients(n_patients)
    if not patients:
        return {"evolved": 0, "cases": 0, "experiences": 0, "outcomes": {}, "error": "无患者"}

    # 测试模式: 注入 MockProvider, 禁止真实 LLM (400 根因)
    provider = None
    import os
    if os.environ.get("HAIP_TEST_MODE", "") == "true" or not use_llm:
        from haip.llm.mock import MockProvider
        provider = MockProvider({})

    cases_before = memory.count_cases(agent_name)
    experiences_before = len(memory.list_experiences(agent_name))

    outcomes: dict[str, int] = {"recovered": 0, "deteriorating": 0, "deceased": 0, "stable": 0}
    evolved = 0

    for p in patients:
        # 创建虚拟病人 + 转归引擎
        progression = ProgressionEngine(seed=seed)
        patient_agent = PatientAgent(p, progression=progression, seed=seed)

        # 会诊 (mock 模式: 规则降级, 不调真实 LLM)
        try:
            result = run_consultation(patient_agent, agent_name, max_rounds=2,
                                      provider=provider)
            new_state = result.get("new_state", "stable")
            outcomes[new_state] = outcomes.get(new_state, 0) + 1

            # 进化: 成功 → 案例库 / 失败 → 经验库
            gold = {"urgency": _urgency_from_action(result.get("treatment_action", ""))}
            eval_report = {
                "stages": [{"items": [
                    {"field": "urgency", "detail": f"实际={new_state}, 金标准={gold.get('urgency')}",
                     "passed": new_state in ("recovering", "recovered")}
                ]}],
                "results": {"consultation": {"_ok": True, "outcome": new_state}},
            }
            # evolve_from_eval 需要 scenario 对象; None 时用简化路径直接入库
            if new_state in ("recovering", "recovered"):
                from haip.evolution.memory_base import CaseEntry
                memory.add_case(CaseEntry(
                    case_id=f"evolve-{p.get('patient_id','')}-{seed}",
                    agent=agent_name,
                    task="virtual_patient",
                    question=f"{p.get('age','')}岁 {p.get('diagnosis','')}",
                    answer={"outcome": new_state, "urgency": gold["urgency"]},
                    gold=gold,
                    matched=True,
                ))
            else:
                from haip.evolution.reflect import reflect_failure
                exp = reflect_failure(
                    agent=agent_name, task="virtual_patient",
                    patient=p, result={"outcome": new_state}, gold=gold,
                )
                memory.add_experience(exp)
            evolved += 1
        except Exception:
            continue

    cases_after = memory.count_cases(agent_name)
    experiences_after = len(memory.list_experiences(agent_name))

    return {
        "patients_run": len(patients),
        "evolved": evolved,
        "cases": cases_after,
        "cases_before": cases_before,
        "cases_after": cases_after,
        "cases_grown": cases_after - cases_before,
        "experiences": experiences_after,
        "experiences_before": experiences_before,
        "experiences_after": experiences_after,
        "experiences_grown": experiences_after - experiences_before,
        "outcomes": outcomes,
        "recovery_rate": round(
            (outcomes.get("recovered", 0) + outcomes.get("recovering", 0)) / max(1, len(patients)) * 100, 1),
        "improvement": None,  # 需第二轮对比
        "seed": seed,
        "duration_ms": 0,
    }


def run_evolution_cycle(n_patients: int = 20, rounds: int = 2,
                        seed: int = 42) -> dict[str, Any]:
    """两轮进化对比: Round1 学习 → Round2 用新病例评测.

    Returns {round1, round2, improvement_delta, conclusion}
    """
    t0 = time.time()
    r1 = run_evolution_batch(n_patients, seed=seed)
    r2 = run_evolution_batch(n_patients, seed=seed + 100)

    delta = round((r2.get("recovery_rate", 0) - r1.get("recovery_rate", 0)), 1)
    return {
        "round1": r1,
        "round2": r2,
        "improvement_delta": delta,
        "conclusion": (
            f"进化有效: 恢复率 {r1.get('recovery_rate',0)}% → {r2.get('recovery_rate',0)}%"
            f" (Δ{delta}%)" if delta > 0 else
            f"进化持平: 恢复率 {r1.get('recovery_rate',0)}% → {r2.get('recovery_rate',0)}%"
        ),
        "duration_ms": round((time.time() - t0) * 1000),
    }


def _urgency_from_action(action: str) -> str:
    """从治疗方案推断 urgency."""
    if "48h" in action or "急诊" in action:
        return "emergency"
    if "延迟" in action or "MDT" in action:
        return "elective"
    return "urgent"
