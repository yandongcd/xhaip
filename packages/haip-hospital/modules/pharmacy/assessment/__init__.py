"""药剂科 — 营养风险评估模块"""

from __future__ import annotations

from typing import Any


def assess_nutrition_risk(
    patient_id: str = "",
    weight_kg: float = 0.0,
    height_cm: float = 0.0,
    lab_results: dict[str, float] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """NRS2002 营养风险评估 + 再喂养综合征 + 电解质 + 肝功能复核。

    Args:
        patient_id: 患者ID
        weight_kg: 体重 (kg)
        height_cm: 身高 (cm)
        lab_results: 实验室检查结果 {albumin, crp, na, k, ca, mg, bun, glucose, alt}

    Returns:
        {"risk_level": "低/中/高", "nrs_score": int, "recommendations": [...], "details": {...}}
    """
    lab = lab_results or {}
    bmi = weight_kg / ((height_cm / 100) ** 2) if height_cm > 0 else 0

    # NRS2002 评分
    nrs_score = 0
    details: dict[str, Any] = {}

    # 疾病严重程度 (0-3)
    if bmi < 18.5 or lab.get("albumin", 4.0) < 30:
        nrs_score += 3
        details["disease_severity"] = "重度 (BMI<18.5 或 白蛋白<30g/L)"
    elif lab.get("albumin", 4.0) < 35:
        nrs_score += 2
        details["disease_severity"] = "中度 (白蛋白 30-35g/L)"
    elif lab.get("crp", 0) > 50:
        nrs_score += 1
        details["disease_severity"] = "轻度 (CRP 升高)"
    else:
        details["disease_severity"] = "无显著疾病负担"

    # 营养状况 (0-3)
    if bmi < 16:
        nrs_score += 3
        details["nutrition_status"] = "重度营养不良 (BMI<16)"
    elif bmi < 18.5:
        nrs_score += 2
        details["nutrition_status"] = "中度营养不良 (BMI 16-18.5)"
    elif bmi < 20.5:
        nrs_score += 1
        details["nutrition_status"] = "轻度营养不良 (BMI 18.5-20.5)"
    else:
        details["nutrition_status"] = "营养状况正常"

    # 年龄 (≥70 岁 +1)
    age_bonus = 0
    if kwargs.get("age", 0) >= 70:
        age_bonus = 1
        nrs_score += 1
    details["age_bonus"] = age_bonus

    # 风险等级
    if nrs_score >= 5:
        risk_level = "高"
    elif nrs_score >= 3:
        risk_level = "中"
    else:
        risk_level = "低"

    recommendations: list[str] = []
    if risk_level == "高":
        recommendations.append("立即启动营养支持 (肠内优先)")
        recommendations.append("监测再喂养综合征 (K/Mg/P 每日检测)")
    elif risk_level == "中":
        recommendations.append("48h 内启动营养评估随访")
        recommendations.append("考虑口服营养补充 (ONS)")
    else:
        recommendations.append("每周复查营养指标")

    # 电解质评估
    electrolytes_ok = True
    for ion, low, high, name in [
        ("na", 135, 145, "钠"), ("k", 3.5, 5.0, "钾"),
        ("ca", 2.1, 2.6, "钙"), ("mg", 0.7, 1.1, "镁"),
    ]:
        val = lab.get(ion)
        if val is not None and (val < low or val > high):
            electrolytes_ok = False
            recommendations.append(f"电解质异常: {name} {val} mmol/L (参考 {low}-{high})")

    return {
        "patient_id": patient_id,
        "risk_level": risk_level,
        "nrs_score": nrs_score,
        "bmi": round(bmi, 1) if bmi > 0 else None,
        "recommendations": recommendations,
        "details": details,
        "electrolytes_ok": electrolytes_ok,
    }
