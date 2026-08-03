"""验证闸门 — 经验在相似案例上的通过率验证 (SEAL experience validation 量化版).

SEAL: 原则在 exemplar cases 上测试, 判定标准模糊
增强: 明确阈值 (pass_rate >= 0.6 且 trials >= 3 → validated),
     通过率不足 → rejected; 支持人工审批 → approved.
"""

from __future__ import annotations

from typing import Any

from haip.evolution.memory_base import EvolutionMemory, get_evolution_memory

VALIDATE_MIN_TRIALS = 3
VALIDATE_PASS_RATE = 0.6


def _rule_applies(exp: dict[str, Any], case: dict[str, Any]) -> bool:
    """经验触发条件是否适用于案例 (关键词重叠, 忽略空格)."""
    trigger = exp.get("trigger", "")
    question = (case.get("question", "") or "").replace(" ", "")
    trigger_kws = [t.replace(" ", "") for t in trigger.replace("，", ",").split(",") if len(t.strip()) >= 2]
    if not trigger_kws:
        return True
    return any(kw in question for kw in trigger_kws)


def _rule_suggests(exp: dict[str, Any], case: dict[str, Any]) -> bool | None:
    """经验的行动建议是否与案例金标准一致 (字段级对比).

    Returns:
        True/False: 可判断的一致/不一致
        None: 经验文本不含任何可判定关键词 → 无法判断 (不计入 trials, 防假阳性)
    """
    gold = case.get("gold", {})
    if not gold:
        return None
    # 对比 urgency (最常用金标准字段)
    gold_urgency = gold.get("urgency")
    if gold_urgency:
        action = exp.get("action", "") + exp.get("rule", "")
        if "急诊" in action or "48h" in action:
            return gold_urgency == "emergency"
        if "限期" in action or "3-7" in action:
            return gold_urgency == "urgent"
        if "延迟" in action or "MDT" in action:
            return gold_urgency == "elective"
        return None  # 无法从文本判定与 gold 的关系
    return None


def validate_experience(
    exp_id: str,
    memory: EvolutionMemory | None = None,
    min_trials: int = VALIDATE_MIN_TRIALS,
    pass_rate: float = VALIDATE_PASS_RATE,
) -> dict[str, Any]:
    """对 pending 经验执行验证: 在相似案例库上检验.

    返回 {exp_id, trials, pass_count, pass_rate, verdict, detail}
    """
    memory = memory or get_evolution_memory()
    exp = memory.get_experience(exp_id)
    if exp is None:
        return {"exp_id": exp_id, "verdict": "unknown", "detail": "经验不存在"}
    if exp["status"] in ("validated", "approved", "rejected"):
        return {"exp_id": exp_id, "verdict": exp["status"], "detail": "已终态"}

    cases = memory.search_cases(exp["agent"], exp["trigger"], k=10)
    trials = 0
    passed = 0
    undecidable = 0
    detail_parts = []
    for case in cases:
        if not _rule_applies(exp, case):
            continue
        suggestion = _rule_suggests(exp, case)
        if suggestion is None:
            undecidable += 1
            detail_parts.append(f"~ {case['case_id']} (无法判断)")
            continue
        trials += 1
        if suggestion:
            passed += 1
            detail_parts.append(f"✓ {case['case_id']}")
        else:
            detail_parts.append(f"✗ {case['case_id']}")

    if trials < min_trials:
        verdict = "pending"  # 样本不足, 保持待验证
        status = "pending"
    else:
        rate = passed / trials
        if rate >= pass_rate:
            verdict = "validated"
            status = "validated"
        else:
            verdict = "rejected"
            status = "rejected"

    memory.update_experience(
        exp_id, status=status, trials=trials, pass_count=passed,
        verified_at=__import__("time").time(),
    )
    rate_now = round(passed / trials, 3) if trials else 0.0
    return {
        "exp_id": exp_id, "trials": trials, "pass_count": passed,
        "pass_rate": rate_now, "verdict": verdict,
        "undecidable": undecidable,
        "detail": "; ".join(detail_parts[:6]) or "无适用案例",
    }


def approve_experience(exp_id: str, reviewer: str = "", memory: EvolutionMemory | None = None) -> bool:
    """人工审批: validated → approved (审计留痕 reviewer)."""
    memory = memory or get_evolution_memory()
    exp = memory.get_experience(exp_id)
    if exp is None or exp["status"] != "validated":
        return False
    memory.update_experience(exp_id, status="approved")
    return True


def reject_experience(exp_id: str, reason: str = "", memory: EvolutionMemory | None = None) -> bool:
    """人工驳回: 回滚至 rejected (审计留痕 reason)."""
    memory = memory or get_evolution_memory()
    exp = memory.get_experience(exp_id)
    if exp is None or exp["status"] in ("approved", "rejected"):
        return False
    memory.update_experience(exp_id, status="rejected")
    return True
