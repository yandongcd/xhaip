# @origin: haip-0710/src/agents/domains/haip/orthopedic_surgery/core/complication_predictor.py
# @origin_repo: https://github.com/yandongcd/haip
# @ported_date: 2026-07-12
# @status: REFERENCE — requires import adaptation for xhaip engine
#   Key deps to adapt:
#     agents.domains.haip.core.* -> packages/haip-hospital/modules/shared/
#     agents.harness.* -> packages/haip-core/haip/
#     Rule path resolution -> packages/haip-hospital/knowledge/rules/
"""并发症预测模块 — 基于患者数据预测围术期主要并发症风险.

预测维度:
  1. DVT/PE 风险 (Caprini评分 + D-dimer)
  2. 术后感染风险 (ASA + 营养状态 + 血糖)
  3. 心血管事件风险 (RCRI + 高龄 + 合并症)
  4. 跌倒/二次骨折风险 (骨密度 + 肌力 + 认知)
"""

from __future__ import annotations

import re
from typing import Any

from .assets_loader import load_complication_rules


_LAB_ALIASES: dict[str, list[str]] = {
    "d_dimer": ["d-二聚体", "d二聚体", "ddimer"],
    "albumin": ["白蛋白", "albumin"],
    "creatinine": ["肌酐", "creatinine"],
}


def _get_field(field_name: str, patient: dict) -> Any:
    if field_name.startswith("lab."):
        lab_key = field_name[4:]
        aliases = _LAB_ALIASES.get(lab_key, [lab_key])
        for t in patient.get("lab_tests", []):
            tname = (t.get("name", "") or "").lower()
            for alias in aliases:
                if alias.lower() in tname:
                    try:
                        return float(t.get("value", 0))
                    except (ValueError, TypeError):
                        return None
        return None

    if field_name == "bmi":
        bmi = patient.get("bmi")
        if bmi is None:
            for v in patient.get("vitals", []):
                if "bmi" in (v.get("name", "") or "").lower():
                    try:
                        return float(v.get("value", 0))
                    except (ValueError, TypeError):
                        pass
        return bmi

    return patient.get(field_name, "")


def _check_string_field(field_name: str, keywords: list[str], patient: dict) -> bool:
    val = _get_field(field_name, patient)
    if not isinstance(val, str):
        return False
    val_lower = val.lower()
    for kw in keywords:
        if kw.lower() in val_lower:
            return True
    return False


def _eval_condition(condition: str, patient: dict) -> bool:
    """Evaluate a YAML condition string against patient data."""
    cond = condition.strip()

    if " and " in cond:
        parts = cond.split(" and ")
        return all(_eval_condition(p.strip(), patient) for p in parts)

    contains_match = re.match(r"^(\w+(?:\.\w+)?)\s+contains\s+(.+)", cond)
    if contains_match:
        field = contains_match.group(1)
        rest = contains_match.group(2)
        values = re.findall(r"'([^']*)'", rest)
        return _check_string_field(field, values, patient)

    range_match = re.match(
        r"^(-?\d+\.?\d*)\s*<=\s*(\w+(?:\.\w+)?)\s*<=\s*(-?\d+\.?\d*)$", cond
    )
    if range_match:
        low = float(range_match.group(1))
        field = range_match.group(2)
        high = float(range_match.group(3))
        val = _get_field(field, patient)
        if val is None:
            return False
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return False
        return low <= fval <= high

    none_match = re.match(r"^(\w+(?:\.\w+)?)\s+is\s+not\s+None$", cond)
    if none_match:
        field = none_match.group(1)
        return _get_field(field, patient) is not None

    simple_match = re.match(
        r"^(\w+(?:\.\w+)?)\s*(>=|<=|>|<|==)\s*(-?\d+\.?\d*)$", cond
    )
    if simple_match:
        field = simple_match.group(1)
        op = simple_match.group(2)
        threshold = float(simple_match.group(3))
        val = _get_field(field, patient)
        if val is None:
            return False
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return False
        if op == ">=":
            return fval >= threshold
        elif op == "<=":
            return fval <= threshold
        elif op == ">":
            return fval > threshold
        elif op == "<":
            return fval < threshold
        elif op == "==":
            return fval == threshold

    return False


def _risk_level_from_yaml(score: int, risk_levels: list[dict]) -> str:
    for rl in risk_levels:
        if score >= rl.get("min_score", 0):
            return rl.get("level", "低危")
    return risk_levels[-1].get("level", "低危") if risk_levels else "低危"


def _get_action(level: str, risk_levels: list[dict]) -> list[str]:
    for rl in risk_levels:
        if rl.get("level") == level:
            action = rl.get("action", "")
            if not action:
                return []
            return [a.strip() for a in action.split("，") if a.strip()]
    return []


def _get_mace_rate(level: str, risk_levels: list[dict]) -> str:
    for rl in risk_levels:
        if rl.get("level") == level:
            return rl.get("mace_rate", "未知")
    return "未知"


def _assess_dimension(patient: dict, dim: dict, dim_id: str) -> dict:
    score = 0
    factors: list[str] = []
    triggered_ids: list[str] = []

    for item in dim.get("score_items", []):
        condition = item.get("condition", "")
        if _eval_condition(condition, patient):
            pts = item.get("score", 0)
            score += pts
            item_id = item.get("id", "?")
            triggered_ids.append(item_id)
            factors.append(f"{item_id} (+{pts})")

    risk_levels = dim.get("risk_levels", [])
    level = _risk_level_from_yaml(score, risk_levels)

    result: dict[str, Any] = {
        "score": score,
        "risk_level": level,
        "factors": factors,
        "recommendations": _get_action(level, risk_levels),
    }

    if dim_id == "dvt":
        result["d_dimer_elevated"] = "d_dimer_elevated" in triggered_ids

    if dim_id == "cardiac":
        result["mace_risk"] = _get_mace_rate(level, risk_levels)

    return result


def _get_dim(dim_id: str) -> dict:
    rules = load_complication_rules()
    for d in rules.get("complication_dimensions", []):
        if d["id"] == dim_id:
            return d
    return {}


def _compute_overall_risk(patient: dict) -> dict:
    dvt = _assess_dimension(patient, _get_dim("dvt"), "dvt")
    inf = _assess_dimension(patient, _get_dim("infection"), "infection")
    card = _assess_dimension(patient, _get_dim("cardiac"), "cardiac")
    fall = _assess_dimension(patient, _get_dim("fall"), "fall")

    levels = [dvt["risk_level"], inf["risk_level"], card["risk_level"], fall["risk_level"]]
    priority = ["极高危", "高危", "中危", "低危"]
    overall = "低危"
    for lvl in levels:
        if lvl in priority and priority.index(lvl) < priority.index(overall):
            overall = lvl

    return {
        "overall_risk_level": overall,
        "dimensions": {"dvt": dvt["risk_level"], "infection": inf["risk_level"], "cardiac": card["risk_level"], "fall": fall["risk_level"]},
    }


# ASSET:rule-hip-fracture-complication
def predict_complications(patient: dict | None = None) -> dict:
    """评估患者围术期并发症风险.

    Args:
        patient: 患者信息 dict(含 age, past_history, lab_tests 等)

    Returns:
        各并发症维度的风险评估结果
    """
    if patient is None:
        patient = {}

    rules = load_complication_rules()
    dims = rules.get("complication_dimensions", [])
    dim_map = {d["id"]: d for d in dims}

    return {
        "dvt_risk": _assess_dimension(patient, dim_map.get("dvt", {}), "dvt"),
        "infection_risk": _assess_dimension(patient, dim_map.get("infection", {}), "infection"),
        "cardiac_risk": _assess_dimension(patient, dim_map.get("cardiac", {}), "cardiac"),
        "fall_risk": _assess_dimension(patient, dim_map.get("fall", {}), "fall"),
        "overall_risk_level": _compute_overall_risk(patient),
    }


def print_complication_report(result: dict) -> None:
    """打印并发症风险评估报告."""
    print("===== 围术期并发症风险评估 =====")
    overall = result.get("overall_risk_level", {})
    if isinstance(overall, dict):
        print(f"综合风险等级: {overall.get('overall_risk_level', '未知')}")
        dims = overall.get("dimensions", {})
        print(f"  DVT风险: {dims.get('dvt', '-')}")
        print(f"  感染风险: {dims.get('infection', '-')}")
        print(f"  心脏风险: {dims.get('cardiac', '-')}")
        print(f"  跌倒风险: {dims.get('fall', '-')}")

    for key, label in [("dvt_risk", "DVT/PE"), ("infection_risk", "感染"), ("cardiac_risk", "心脏"), ("fall_risk", "跌倒")]:
        dim = result.get(key, {})
        print(f"\n--- {label} ---")
        print(f"  评分: {dim.get('score', '-')} | 风险等级: {dim.get('risk_level', '-')}")
        for f in dim.get("factors", []):
            print(f"  • {f}")
        if dim.get("recommendations"):
            print("  建议:")
            for r in dim["recommendations"]:
                print(f"    - {r}")
