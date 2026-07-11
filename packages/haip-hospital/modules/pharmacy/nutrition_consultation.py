"""药剂科 营养途径推荐 — EN vs PN + 配方选择 + 监测计划.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from typing import Any


def route(
    patient_id: str = "", gi_function: str = "",
    weight_kg: float = 0.0, bmi: float = 0.0, age: int = 0,
    nrs2002: int = 0, grv_ml: int = 0, bowel_dysfunction: bool = False,
    alt: float = 0.0, creatinine: float = 0.0, bun: float = 0.0,
    sodium: float = 0.0, potassium: float = 0.0, phosphorus: float = 0.0,
    triglycerides: float = 0.0, glucose: float = 0.0, albumin: float = 0.0,
    fasting_days: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """营养途径推荐 + 配方选择 + 监测计划.

    Backward compatible: minimal inputs (gi_function) still work.
    Enhanced: full clinical inputs yield detailed EN/PN formula + electrolyte advice.
    """
    gi_ok = gi_function.lower() in ("normal", "ok", "functional", "正常", "可")

    # ── Nutrition route decision ──
    reasons: list[str] = []
    recommendations: list[str] = []

    if bowel_dysfunction or not gi_ok:
        recommended_route = "PN"
        reasons.append("肠道功能障碍，无法进行 EN")
        recommendations.append("选择全肠外营养(TPN)")
    elif grv_ml > 200:
        recommended_route = "SPN"
        reasons.append(f"EN 不耐受(GRV>{grv_ml}ml)")
        recommendations.append("先尝试 EN，不足部分由 PN 补充 (SPN)")
    elif gi_ok:
        recommended_route = "EN"
        reasons.append("肠道功能正常，首选 EN")
        if nrs2002 >= 5:
            recommendations.append("高营养风险，建议早期启动 EN(24-48小时内)")
        else:
            recommendations.append("按计划启动 EN")
    else:
        recommended_route = "EN"
        reasons.append("默认选择 EN")

    # ── EN formula recommendations ──
    en_formula: list[str] = []
    if gi_ok and recommended_route in ("EN", "SPN"):
        if bmi >= 30:
            en_formula.append("肥胖患者: 高蛋白低热量配方(瑞代、能全力HP)")
        elif age >= 65:
            en_formula.append("老年患者: 高蛋白配方(瑞能、安素)")
        elif albumin < 30:
            en_formula.append("低蛋白血症: 高蛋白配方(瑞高、百普力)")
        else:
            en_formula.append("标准配方: 整蛋白型(能全力、瑞素)")
        if bun > 14.3:
            en_formula.append("肾功能不全: 低蛋白配方(瑞代)")
        if alt > 80:
            en_formula.append("肝功能不全: BCAA 强化配方(肝安)")
        if glucose > 10:
            en_formula.append("糖尿病: 低糖配方(瑞代、益力佳)")

    # ── PN lipid + amino acid recommendations ──
    lipid_recs: list[str] = []
    if recommended_route in ("PN", "SPN"):
        if alt > 80:
            lipid_recs.append("肝功能异常: 选择 MCT/LCT 或结构脂肪乳")
            lipid_recs.append("推荐: 鱼油脂肪乳 0.2-0.5g/kg/d 改善肝功能")
        elif triglycerides > 5:
            lipid_recs.append(f"TG 偏高({triglycerides}mmol/L): 减少脂肪乳用量")
        else:
            lipid_recs.append("常规选择: MCT/LCT 脂肪乳, 1-2g/kg/d")
        lipid_recs.append("糖脂比: 1:1至2:1(非蛋白热量)")

        if bun > 14.3:
            recommendations.append("肾功能不全: 肾病专用氨基酸 0.6-0.8g/kg/d")
        elif alt > 80:
            recommendations.append("肝功能不全: BCAA 氨基酸 1.0-1.5g/kg/d")
        else:
            recommendations.append("常规: 平衡氨基酸 1.2-1.5g/kg/d")

    # ── Electrolyte recommendations ──
    electrolyte_recs: list[str] = []
    if sodium < 135:
        electrolyte_recs.append(f"低钠({sodium}mmol/L): 补充钠 ≤10-12mmol/L/24h")
    elif sodium > 145:
        electrolyte_recs.append(f"高钠({sodium}mmol/L): 限制钠摄入")
    if potassium < 3.5:
        electrolyte_recs.append(f"低钾({potassium}mmol/L): 补钾 ≤20-40mmol/h")
    elif potassium > 5.5:
        electrolyte_recs.append(f"高钾({potassium}mmol/L): 限制钾摄入")
    if phosphorus < 0.8:
        electrolyte_recs.append(f"低磷({phosphorus}mmol/L): 补磷 0.3-0.6mmol/kg/d")
    electrolyte_recs.append("一价阳离子(Na+K): <150mmol/L")
    electrolyte_recs.append("二价阳离子(Ca+Mg): <10mmol/L")

    # ── Nutrition plan targets ──
    weight = weight_kg if weight_kg > 0 else 60
    if bmi >= 30:
        energy_target = f"{int(weight * 18)}-{int(weight * 22)} kcal/d (低热量)"
    else:
        energy_target = f"{int(weight * 25)}-{int(weight * 30)} kcal/d"
    protein_target = f"{round(weight * 1.2, 1)}-{round(weight * 1.5, 1)} g/d"
    fluid_target = f"{int(weight * 30)}-{int(weight * 40)} ml/d"

    # ── Special situations ──
    special_situations: list[dict] = []
    if bmi < 16:
        special_situations.append({"situation": "再喂养综合征高风险", "risk": "高",
                                    "management": "从目标量1/4开始(3-7天逐步增加)，预防性补充 K/Mg/P"})
    if glucose > 10:
        special_situations.append({"situation": "高血糖", "risk": "高" if glucose > 15 else "中",
                                    "management": "调整胰岛素用量，目标血糖 7.8-10mmol/L"})
    if triglycerides > 5:
        special_situations.append({"situation": "脂肪超载风险", "risk": "高" if triglycerides > 11.4 else "中",
                                    "management": "减少或暂停脂肪乳"})

    # ── Monitoring plan ──
    monitoring = {
        "daily": ["血糖 ≥1次/日", "电解质(Na/K/Ca/Mg/P) 1次/日", "液体平衡 1次/日"],
        "weekly": ["肝功能(ALT/AST/TBIL) 1-2次/周", "肾功能(BUN/Cr) 1-2次/周",
                    "血脂(TG, 使用脂肪乳者) 1次/周", "前白蛋白/CRP 1次/周"],
    }

    return {
        "patient_id": patient_id, "gi_function": gi_function,
        "recommended_route": recommended_route,
        "reason": "; ".join(reasons),
        "route_recommendations": recommendations,
        "en_formula_recommendations": en_formula,
        "lipid_recommendations": lipid_recs,
        "electrolyte_recommendations": electrolyte_recs,
        "energy_target": energy_target,
        "protein_target": protein_target,
        "fluid_target": fluid_target,
        "special_situations": special_situations,
        "monitoring_plan": monitoring,
        "references": [
            "中国成人患者肠外肠内营养临床应用指南（2023版）",
            "成人肠外营养脂肪乳注射液临床应用指南（2023版）",
            "肠外营养中电解质补充中国专家共识（2024版）",
        ],
    }
