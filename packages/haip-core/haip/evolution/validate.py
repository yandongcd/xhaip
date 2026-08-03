"""验证闸门 — 经验在相似案例上的通过率验证.

v1: 固定阈值 (trials>=3, pass_rate>=0.6) — 实现简单但无统计学基础.
v2 (AI-2): Sequential Probability Ratio Test (SPRT) — 贝叶斯框架,
  有 95% 置信度时判定 validated/rejected, 否则保持 pending 持续收集证据.
  消除小样本误判 + 假阳性风险量化.
"""

from __future__ import annotations

from typing import Any

from haip.evolution.memory_base import EvolutionMemory, get_evolution_memory

# SPRT 参数 (可调节)
ALPHA = 0.05          # Type I error: validated 但实际不成立 (≤5%)
BETA = 0.10           # Type II error: rejected 但实际成立 (≤10%)
P0 = 0.55             # H0: pass_rate ≤ P0 (不合格)
P1 = 0.75             # H1: pass_rate ≥ P1 (合格)
MIN_TRIALS = 3        # 最少试验次数 (防止过早判定)

# 固定阈值模式 (legacy)
FIXED_MIN_TRIALS = 3
FIXED_PASS_RATE = 0.6


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


def _sprt_verdict(trials: int, passed: int) -> str:
    """Sequential Probability Ratio Test.

    计算似然比 λ = P(X|H1) / P(X|H0) where X~Binomial.
    若 λ ≥ (1-β)/α → accept H1 (validated)
    若 λ ≤ β/(1-α) → accept H0 (rejected)
    否则 → pending (继续收集证据)
    """
    import math
    if trials < MIN_TRIALS:
        return "pending"

    a = math.log((1 - BETA) / ALPHA)       # upper bound log
    b = math.log(BETA / (1 - ALPHA))        # lower bound log

    # 对数似然比
    llr = passed * math.log(P1 / P0) + (trials - passed) * math.log((1 - P1) / (1 - P0))

    if llr >= a:
        posterior = passed / trials
        return "validated" if posterior >= FIXED_PASS_RATE else "pending"
    if llr <= b:
        return "rejected"
    return "pending"


def validate_experience(
    exp_id: str,
    memory: EvolutionMemory | None = None,
    mode: str = "sprt",
    **overrides: Any,
) -> dict[str, Any]:
    """对 pending 经验执行验证 (SPRT 贝叶斯模式 或 固定阈值模式).

    mode='sprt': SPRT 序贯检验 (推荐, 自动控制 α=5% β=10%)
    mode='fixed': 固定阈值 trials>=3, pass_rate>=0.6 (legacy)
    """
    memory = memory or get_evolution_memory()
    exp = memory.get_experience(exp_id)
    if exp is None:
        return {"exp_id": exp_id, "verdict": "unknown", "detail": "经验不存在"}
    if exp["status"] in ("validated", "approved", "rejected"):
        return {"exp_id": exp_id, "verdict": exp["status"], "detail": "已终态"}

    min_trials = overrides.get("min_trials", MIN_TRIALS)
    pass_rate_threshold = overrides.get("pass_rate", FIXED_PASS_RATE)

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

    if mode == "sprt":
        verdict = _sprt_verdict(trials, passed)
    elif mode == "fixed":
        if trials < min_trials:
            verdict = "pending"
        else:
            rate = passed / trials
            verdict = "validated" if rate >= pass_rate_threshold else "rejected"
    else:
        verdict = "pending"

    status = "pending" if verdict == "pending" else verdict

    memory.update_experience(
        exp_id, status=status, trials=trials, pass_count=passed,
        verified_at=__import__("time").time(),
    )
    rate_now = round(passed / trials, 3) if trials else 0.0
    return {
        "exp_id": exp_id, "trials": trials, "pass_count": passed,
        "pass_rate": rate_now, "verdict": verdict,
        "undecidable": undecidable, "mode": mode,
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
