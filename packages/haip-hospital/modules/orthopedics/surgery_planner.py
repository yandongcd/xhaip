# @origin: haip-0710/src/agents/domains/haip/orthopedic_surgery/core/surgery_planner.py
# @origin_repo: https://github.com/yandongcd/haip
# @ported_date: 2026-07-12
# @status: ADAPTED (imports rewritten for xhaip engine)
#   Key deps to adapt:
#     agents.domains.haip.core.* -> packages/haip-hospital/modules/shared/
#     agents.harness.* -> packages/haip-core/haip/
#     Rule path resolution -> packages/haip-hospital/knowledge/rules/
"""LLM驱动的个性化手术方案推荐 — 综合骨折类型, 患者状况, 功能需求.

使用方式:
    from orthopedics.surgery_planner import recommend_surgery

    plan = recommend_surgery(patient_dict)
    plan = recommend_surgery(patient_dict, fracture_info={"type": "股骨颈骨折 Garden IV"})
"""

from __future__ import annotations

from typing import Any

from shared.llm_adapter import call_llm_structured

from .prompts.surgery_recommend import (
    OUTPUT_SCHEMA,
    SYSTEM_PROMPT,
    build_prompt,
)

_SURGERY_DATA_CACHE: dict[str, Any] | None = None


def _load_surgery_data() -> dict[str, Any]:
    global _SURGERY_DATA_CACHE
    if _SURGERY_DATA_CACHE is not None:
        return _SURGERY_DATA_CACHE
    from shared.assets_loader import load_surgery_type_rules
    _SURGERY_DATA_CACHE = load_surgery_type_rules() or {}
    return _SURGERY_DATA_CACHE


# ASSET:tool-hip-surgery-plan
def recommend_surgery(
    patient: dict | None = None,
    fracture_info: dict | None = None,
    use_llm: bool = True,
) -> dict:
    """生成个性化手术方案推荐.

    Args:
        patient: 患者信息 dict(含 age, gender, diagnosis, past_history 等)
        fracture_info: 骨折信息 dict(含 type, classification, stability 等)
        use_llm: 是否使用 LLM(True=LLM增强, False=规则模板)

    Returns:
        包含推荐方案的 dict:
        {
            "recommended_surgery": str,
            "alternative_surgery": str,
            "surgical_approach": str,
            "implant_choice": str,
            "anesthesia_recommendation": str,
            "key_considerations": list[str],
            "guideline_ref": str,
            "reasoning": str,
        }
    """
    if patient is None:
        patient = {}

    if fracture_info is None:
        fracture_info = {}

    if use_llm:
        result = _recommend_surgery_llm(patient, fracture_info)
        if "error" not in result:
            return result

    return _recommend_surgery_template(patient, fracture_info)


def _recommend_surgery_llm(patient: dict, fracture_info: dict) -> dict:
    """LLM驱动的个性化手术方案推荐."""
    diagnosis = patient.get("diagnosis", "") or fracture_info.get("type", "")
    fracture_text = _build_fracture_info_text(fracture_info)

    prompt = build_prompt(
        diagnosis=diagnosis,
        fracture_info=fracture_text,
        age=patient.get("age"),
        gender=patient.get("gender"),
        past_history=patient.get("past_history", ""),
        functional_status=patient.get("functional_status", ""),
        bone_quality=fracture_info.get("bone_quality", ""),
        lab_highlights=_extract_lab_highlights(patient.get("lab_tests", [])),
    )

    result = call_llm_structured(
        prompt=prompt,
        agent="orthopedic-surgery",
        system_prompt=SYSTEM_PROMPT,
        output_schema=OUTPUT_SCHEMA,
        temperature=0.2,
    )

    if "data" in result:
        return result["data"]
    return result


def _build_fracture_info_text(fracture_info: dict) -> str:
    parts = []
    if fracture_info.get("type"):
        parts.append(f"类型: {fracture_info['type']}")
    if fracture_info.get("classification_system"):
        parts.append(f"分型系统: {fracture_info['classification_system']}")
    if fracture_info.get("classification_type"):
        parts.append(f"分型: {fracture_info['classification_type']}")
    if fracture_info.get("stability"):
        parts.append(f"稳定性: {fracture_info['stability']}")
    if fracture_info.get("side"):
        parts.append(f"侧别: {fracture_info['side']}")
    return "; ".join(parts)


def _extract_lab_highlights(lab_tests: list[dict] | None) -> str:
    """提取关键异常检验结果."""
    if not lab_tests:
        return ""
    highlights = []
    for t in lab_tests:
        name = t.get("name", "")
        val = t.get("value", "")
        flag = t.get("flag", "")
        unit = t.get("unit", "")
        if flag in ("H", "L", "升高", "降低", "异常"):
            highlights.append(f"{name}: {val} {unit} ({flag})")
    return "; ".join(highlights[:8])


def _match_decision_matrix(sd: dict[str, Any], patient: dict, fracture_info: dict) -> dict | None:
    """Match xhaip surgery_type_rules decision_matrix schema.

    Rule fields: fracture_type (femoral_neck/intertrochanteric/subtrochanteric),
    garden, age_min/age_max, activity, bone_quality, recommended_surgery, ...
    Only non-empty filters are enforced; returns None when nothing matches.
    """
    matrix = sd.get("decision_matrix", [])
    if not matrix:
        return None

    ft = fracture_info.get("type", "") or patient.get("diagnosis", "")
    if "股骨颈" in ft or "femoral neck" in ft.lower():
        fracture_type = "femoral_neck"
    elif "转子间" in ft or "intertrochanteric" in ft.lower():
        fracture_type = "intertrochanteric"
    elif "转子下" in ft or "subtrochanteric" in ft.lower():
        fracture_type = "subtrochanteric"
    else:
        fracture_type = ""

    classification = str(fracture_info.get("classification_type", "") or "")
    import re as _re
    garden_m = _re.search(r"Garden\s*([IViv]+)", classification)
    garden = _roman_to_int(garden_m.group(1)) if garden_m else 0

    age = patient.get("age", 0) or 0
    activity = str(fracture_info.get("activity") or patient.get("functional_status", "") or "")
    bone_quality = str(fracture_info.get("bone_quality", "") or "")

    for opt in matrix:
        if fracture_type and opt.get("fracture_type") and opt.get("fracture_type") != fracture_type:
            continue
        gardens = opt.get("garden") or []
        if gardens and garden:
            if garden not in gardens:
                continue
        age_min = opt.get("age_min")
        age_max = opt.get("age_max")
        if age_min is not None and age < age_min:
            continue
        if age_max is not None and age > age_max:
            continue
        if opt.get("activity") and activity and opt.get("activity") not in activity:
            continue
        if opt.get("bone_quality") and bone_quality and opt.get("bone_quality") not in bone_quality:
            continue
        return {
            "recommended_surgery": opt.get("recommended_surgery", ""),
            "alternative_surgery": opt.get("alternative_surgery", ""),
            "surgical_approach": opt.get("surgical_approach", ""),
            "implant_choice": opt.get("implant_choice", ""),
            "anesthesia_recommendation": opt.get("anesthesia", ""),
            "key_considerations": opt.get("special_notes", "").split(";") if opt.get("special_notes") else [],
            "guideline_ref": opt.get("guideline_ref", ""),
            "reasoning": opt.get("name", ""),
        }
    return None


def _roman_to_int(s: str) -> int:
    """Convert Roman numeral (I/II/III/IV/V) to int; 0 on failure."""
    mapping = {"I": 1, "V": 5}
    total = 0
    prev = 0
    for ch in reversed(s.upper()):
        v = mapping.get(ch, 0)
        if v == 0:
            return 0
        if v < prev:
            total -= v
        else:
            total += v
        prev = v
    return total


def _recommend_surgery_template(patient: dict, fracture_info: dict) -> dict:
    """规则模板版本的手术方案推荐(LLM降级方案) — YAML优先, 硬编码兜底."""
    diagnosis = (patient.get("diagnosis", "") or fracture_info.get("type", "")).lower()
    age = patient.get("age", 0)
    fracture_type = (fracture_info.get("type", "") or "").lower()

    # Try YAML surgery_type_rules first (xhaip decision_matrix schema, then legacy)
    sd = _load_surgery_data()
    dm_result = _match_decision_matrix(sd, patient, fracture_info)
    if dm_result:
        return dm_result

    surgical_options = sd.get("surgery_type_options", [])
    if surgical_options:
        for opt in surgical_options:
            match_keywords = opt.get("match_keywords", [])
            if any(kw in fracture_type or kw in diagnosis for kw in match_keywords):
                age_rule = opt.get("age_rule", {})
                if age_rule:
                    min_age = age_rule.get("min_age", 0)
                    max_age = age_rule.get("max_age", 200)
                    if min_age <= (age or 0) <= max_age:
                        return {
                            "recommended_surgery": opt.get("recommended", ""),
                            "alternative_surgery": opt.get("alternative", ""),
                            "surgical_approach": opt.get("approach", ""),
                            "reasoning": opt.get("reasoning", ""),
                        }

    # 简单决策树
    if "股骨颈" in fracture_type or "股骨颈" in diagnosis:
        if age and age >= 75:
            return {
                "recommended_surgery": "人工全髋关节置换术(THA)",
                "alternative_surgery": "人工股骨头置换术(HA,若预期寿命较短)",
                "surgical_approach": "后外侧入路或直接前入路(DAA)",
                "implant_choice": "生物型假体(骨质量尚可)/骨水泥型假体(骨质疏松严重)",
                "anesthesia_recommendation": "全身麻醉或腰硬联合麻醉",
                "key_considerations": ["高龄患者注意围术期管理", "抗凝药物桥接", "预防DVT"],
                "guideline_ref": "AAOS 2022: 老年移位股骨颈骨折行关节置换",
                "reasoning": f"患者{age}岁,股骨颈骨折,关节置换可早期负重,降低并发症",
            }
        elif age and age < 65:
            return {
                "recommended_surgery": "闭合/切开复位内固定术(空心螺钉/动力髋螺钉)",
                "alternative_surgery": "若复位不满意则考虑THA",
                "surgical_approach": "经皮微创或前外侧入路",
                "implant_choice": "3枚空心螺钉(稳定型)/DHS(不稳定型)",
                "anesthesia_recommendation": "腰麻或全麻",
                "key_considerations": ["尽量保留自身股骨头", "术后避免早期完全负重", "监测股骨头坏死风险"],
                "guideline_ref": "中国成人股骨颈骨折诊治指南(2018)",
                "reasoning": f"患者{age}岁相对年轻,内固定可保留自身关节",
            }

    if "转子间" in fracture_type or "转子间" in diagnosis:
        return {
            "recommended_surgery": "股骨近端防旋髓内钉(PFNA)",
            "alternative_surgery": "InterTAN髓内钉/动力髋螺钉(DHS,稳定型)",
            "surgical_approach": "微创小切口",
            "implant_choice": "PFNA(首选)/InterTAN(反转子间骨折)",
            "anesthesia_recommendation": "全身麻醉或腰硬联合麻醉",
            "key_considerations": ["恢复颈干角和解剖力线", "避免内翻畸形", "尖顶距控制<25mm"],
            "guideline_ref": "老年股骨转子间骨折诊疗指南(2020)",
            "reasoning": "PFNA是转子间骨折金标准,微创, 固定牢固",
        }

    return {
        "recommended_surgery": "需进一步明确骨折类型和患者状况",
        "alternative_surgery": "",
        "surgical_approach": "",
        "implant_choice": "",
        "anesthesia_recommendation": "",
        "key_considerations": ["请完善影像学检查明确骨折分型"],
        "guideline_ref": "",
        "reasoning": "信息不足以做出明确手术推荐",
    }
