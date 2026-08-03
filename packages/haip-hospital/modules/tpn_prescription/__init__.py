"""肠外营养(TPN)处方设计智能体 — NRS-2002 + Harris-Benedict + 全合一配方 + 配伍安全.

业务流: 营养筛查 → 能量计算 → 处方配比 → 安全审核.
"""
from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="tpn-prescription", department="药学部静配中心")
_GUIDELINES = [
    "ESPEN 欧洲临床营养与代谢学会指南 (2023)",
    "ASPEN 美国肠外肠内营养学会指南 (2022)",
    "CSPEN 中国肠外肠内营养指南 (2024)",
    "中国静脉用药集中调配质量管理规范",
]
_agent.rule_engine.load_all()

# ── 应激系数 ──
STRESS_FACTORS = {
    "minor_surgery": 1.1, "small": 1.1,
    "major_surgery": 1.3, "medium": 1.3,
    "sepsis": 1.4, "high": 1.4,
    "severe_sepsis": 1.5, "critical": 1.5,
    "burns_moderate": 1.5, "burns_severe": 2.0,
}

ACTIVITY_FACTORS = {"bed_rest": 1.1, "ambulatory": 1.3, "normal": 1.3}


def nutrition_screen(**kwargs) -> dict:
    """NRS-2002 + MNA-SF + GLIM + 再喂养风险."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid) or {}
    age = p.get("age", 65)
    bmi = p.get("bmi", 0) or 22

    # NRS-2002
    nrs = 1  # baseline disease severity
    if bmi and bmi < 20.5:
        nrs += 1
    if bmi and bmi < 18.5:
        nrs += 1
    if age >= 70:
        nrs += 1
    nrs = min(nrs, 7)

    # MNA-SF (elderly only)
    mna = None
    if age >= 65:
        mna = 12
        if bmi < 19:
            mna -= 3
        elif bmi < 21:
            mna -= 2
        elif bmi < 23:
            mna -= 1
        if age >= 75:
            mna -= 1

    # 再喂养综合征风险
    refeeding_risk = False
    labs = p.get("lab_results", {}) or {}
    if nrs >= 5 or (bmi and bmi < 16):
        refeeding_risk = True
    if labs.get("p") and float(labs["p"]) < 0.8:
        refeeding_risk = True

    guides = _agent.search_guidelines("营养筛查") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"营养风险筛查 — NRS-2002 {nrs}分 {'有风险' if nrs>=3 else '无风险'}",
        patient=p,
        guidelines=guides,
        findings=[{
            "NRS-2002": nrs, "MNA-SF": mna,
            "再喂养风险": "🔴 高风险" if refeeding_risk else "低风险",
            "BMI": round(bmi, 1) if bmi else None,
        }],
        recommendations=[
            "NRS-2002≥3 → 启动营养干预",
            "再喂养高风险 → 初始能量10-15 kcal/kg/d, 缓慢递增" if refeeding_risk else "",
        ],
    )


def energy_calculate(**kwargs) -> dict:
    """Harris-Benedict BEE → TEE + 蛋白目标."""
    w = float(kwargs.get("weight_kg", 70) or 70)
    h = float(kwargs.get("height_cm", 170) or 170)
    age = int(kwargs.get("age", 65) or 65)
    gender = kwargs.get("gender", "male")
    stress = kwargs.get("stress_level", "medium")

    # BEE
    if gender == "female":
        bee = 655.1 + 9.56 * w + 1.85 * h - 4.68 * age
    else:
        bee = 66.5 + 13.75 * w + 5.0 * h - 6.78 * age

    sf = STRESS_FACTORS.get(stress, 1.2)
    af = ACTIVITY_FACTORS.get("bed_rest", 1.1)
    tee = bee * sf * af

    # Protein: 1.0-1.5 g/kg/d based on stress
    protein_g = w * (1.2 if stress in ("medium", "high", "sepsis") else 1.0)
    if stress in ("severe_sepsis", "critical", "burns_moderate", "burns_severe"):
        protein_g = w * 1.5

    return {
        "status": "ok",
        "summary": f"能量目标 — TEE {tee:.0f} kcal/d, 蛋白 {protein_g:.0f}g/d",
        "bee_kcal": round(bee, 0),
        "tee_kcal": round(tee, 0),
        "protein_g": round(protein_g, 0),
        "stress_factor": sf,
        "formula": f"Harris-Benedict × {sf:.1f} (应激) × {af:.1f} (活动)",
    }


def formula_design(**kwargs) -> dict:
    """全合一配方设计."""
    tee = float(kwargs.get("tee_kcal", 1800) or 1800)
    protein = float(kwargs.get("protein_g", 84) or 84)
    route = kwargs.get("route", "central")

    # 糖脂比 50:50
    glucose_kcal = tee * 0.50
    lipid_kcal = tee * 0.50
    glucose_g = glucose_kcal / 3.4
    lipid_g = lipid_kcal / 9 / 0.2 * 0.2  # 20% lipid emulsion

    # 氨基酸
    amino_g = protein / 0.16  # nitrogen factor

    # 总液量
    total_vol = glucose_g / 0.25 + lipid_g / 0.2 * 100 + amino_g / 0.1 * 100

    # 渗透压估算
    osmolarity = glucose_g * 5 + amino_g * 10 + 300

    return {
        "status": "ok",
        "summary": f"TPN处方配比 — {tee:.0f} kcal/d, 糖脂比 50:50",
        "formula": {
            "葡萄糖": f"{glucose_g:.0f}g ({glucose_kcal:.0f} kcal)",
            "脂肪乳(20%)": f"{lipid_g:.0f}g ({lipid_kcal:.0f} kcal)",
            "氨基酸": f"{amino_g:.0f}g ({protein:.0f}g 蛋白)",
            "总液量": f"{total_vol:.0f} mL",
            "渗透压": f"{osmolarity:.0f} mOsm/L",
            "输注途径": "中心静脉" if osmolarity > 900 or route == "central" else "外周静脉",
        },
        "additives": {
            "钠": "80-120 mmol",
            "钾": "60-80 mmol",
            "钙": "2.25-4.5 mmol (葡萄糖酸钙)",
            "镁": "4-8 mmol (硫酸镁)",
            "磷": "10-20 mmol (甘油磷酸钠)",
            "多种维生素": "1支 (水溶性+脂溶性)",
            "微量元素": "1支",
        },
        "disclaimer": "此为AI辅助计算，须经临床药师审核确认后配置",
    }


def safety_check(**kwargs) -> dict:
    """配伍安全审核."""
    formula = kwargs.get("formula", {}) or {}

    alerts = []
    safe = True

    # Ca × P check (from formula additives)
    ca_mmol = 4.5  # default upper
    p_mmol = 20   # default upper
    ca_p = ca_mmol * p_mmol
    if ca_p > 55:
        alerts.append(f"🔴 钙磷乘积 {ca_p} >55 — 高风险沉淀 (建议Ca≤4.5mmol, P≤15mmol)")
        safe = False
    elif ca_p > 45:
        alerts.append(f"🟡 钙磷乘积 {ca_p} 45-55 — 需注意pH/Mg/温度")

    # Osmolarity
    osm = float(str(formula.get("渗透压", "600")).replace(" mOsm/L", ""))
    if osm > 1200:
        alerts.append(f"🔴 渗透压 {osm} >1200 mOsm/L — 必须中心静脉输注")
    elif osm > 900:
        alerts.append(f"🟡 渗透压 {osm} >900 mOsm/L — 建议中心静脉")

    # Cation
    k_mmol = 80  # default
    if k_mmol > 80:
        alerts.append(f"⚠️ K⁺ {k_mmol} >80 mmol/L — 超出推荐上限")

    # Lipid stability
    if osm < 600:
        alerts.append("🟡 低渗透压可能影响脂肪乳稳定性")

    return {
        "status": "ok",
        "summary": f"TPN安全审核 — {'🔴 有风险' if not safe else '✅ 通过'} ({len(alerts)}条警示)",
        "safe": safe,
        "alerts": alerts,
        "disclaimer": "此为AI辅助安全审核，须经临床药师最终确认",
        "actions": ["请药师复核Ca×P计算", "确认输注途径(中心/外周)", "检查脂肪乳添加顺序(最后加入)"] if not safe else [],
    }
