"""dietitian — Clinical Dietitian Agent for xhaip v1.2.

Covers 6 core nutrition functions:
  1. nrs2002_screen — NRS2002 Nutritional Risk Screening
  2. glim_diagnosis — GLIM Two-Step Malnutrition Diagnosis
  3. route_decision — EN vs PN vs SPN Route Decision
  4. energy_protein_target — Harris-Benedict Energy + Protein Targets
  5. refeeding_risk — Refeeding Syndrome Risk Assessment
  6. nutrition_report — Comprehensive Nutrition Assessment Report

Guidelines referenced:
  - ESPEN Guidelines on Clinical Nutrition (2023)
  - CSPEN Guidelines (2023)
  - GLIM Criteria for Malnutrition (GLIM Core Leadership Committee, 2019)
  - NICE CG32 Nutrition Support for Adults (2006, updated 2017)
  - ASPEN Guidelines for Refeeding Syndrome
"""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════
# 1. NRS2002 营养风险筛查
# ═══════════════════════════════════════════════════════════

NRS2002_RECOMMENDATIONS = {
    "高": [
        "立即启动营养支持 (肠内优先)",
        "24-48h 内建立肠内营养通路",
        "监测再喂养综合征 (K/Mg/P 每日检测)",
        "监测血糖 q6h",
        "每周复查 NRS2002",
    ],
    "中": [
        "48h 内启动营养评估随访",
        "考虑口服营养补充 (ONS) 2-3 次/日",
        "制定个体化营养支持方案",
        "每周复查 NRS2002",
    ],
    "低": [
        "每周复查营养指标",
        "鼓励经口进食",
        "如有病情变化重新评估",
    ],
}


def nrs2002_screen(
    weight_kg: float = 0.0,
    height_cm: float = 0.0,
    age: int = 0,
    disease_severity: int = 0,
    food_intake_pct: int = 100,
    weight_loss_3mo_pct: float = 0.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """NRS2002 营养风险筛查。

    Scoring:
      Disease severity: 0-3 (进入 ICU / 大手术 / 慢性病急性加重)
      Nutritional status: 0-3 (按过去摄入/体重变化/BMI 评分)
      Age bonus: +1 if age ≥ 70
      Total: 0-7, ≥3 = at nutritional risk

    Reference: Kondrup J et al. Clin Nutr 2003;22(4):415-421.
              CSPEN NRS2002 Chinese Consensus.
    """
    # Disease severity (0-3)
    ds_score = max(0, min(disease_severity, 3))
    ds_labels = {
        0: "无显著疾病负担",
        1: "慢性病急性加重 / 髋部骨折 / 肝硬化 / COPD",
        2: "大手术 / 脑卒中 / 严重肺炎 / 血液恶性肿瘤",
        3: "颅脑损伤 / 骨髓移植 / ICU (APACHE II >10)",
    }

    # Nutritional status (0-3)
    bmi = weight_kg / ((height_cm / 100) ** 2) if height_cm > 0 else 0.0
    ns_score = 0
    ns_label = ""
    if bmi < 16:
        ns_score = 3
        ns_label = f"重度营养不良 (BMI={bmi:.1f} <16)"
    elif bmi < 18.5 or weight_loss_3mo_pct > 5:
        ns_score = 2
        ns_label = f"中度营养不良 (BMI={bmi:.1f}, 体重下降{weight_loss_3mo_pct}%)"
    elif food_intake_pct < 50:
        ns_score = 2
        ns_label = f"摄入减少 (过去1周摄入{food_intake_pct}%正常量)"
    elif bmi < 20.5 or weight_loss_3mo_pct > 0:
        ns_score = 1
        ns_label = f"轻度营养不良 (BMI={bmi:.1f}, 体重下降{weight_loss_3mo_pct}%)"
    elif food_intake_pct < 75:
        ns_score = 1
        ns_label = f"摄入轻度减少 (过去1周摄入{food_intake_pct}%正常量)"
    else:
        ns_score = 0
        ns_label = "营养状况正常"

    # Age bonus
    age_bonus = 1 if age >= 70 else 0

    total = ds_score + ns_score + age_bonus

    if total >= 5:
        risk_level = "高"
    elif total >= 3:
        risk_level = "中"
    else:
        risk_level = "低"

    return {
        "status": "ok",
        "risk_level": risk_level,
        "nrs2002_total": total,
        "nrs2002_components": {
            "disease_severity": {"score": ds_score, "label": ds_labels.get(ds_score, "")},
            "nutrition_status": {"score": ns_score, "label": ns_label},
            "age_bonus": {"score": age_bonus, "note": "年龄≥70岁 +1" if age_bonus else "年龄<70岁 无"},
        },
        "bmi": round(bmi, 1) if bmi > 0 else None,
        "at_risk": total >= 3,
        "recommendations": NRS2002_RECOMMENDATIONS[risk_level],
        "reference": "Kondrup J et al. Clin Nutr 2003;22(4):415-421",
    }


# ═══════════════════════════════════════════════════════════
# 2. GLIM 两步营养不良诊断
# ═══════════════════════════════════════════════════════════

def glim_diagnosis(
    weight_loss_6mo_pct: float = 0.0,
    bmi: float = 22.0,
    food_intake_week_pct: int = 100,
    disease_burden: str = "",
    crp: float = 5.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """GLIM 营养不良两步诊断法。

    Step 1: 风险筛查 (假定 NRS2002 ≥3 = 阳性)
    Step 2: 表型标准 (至少1项) + 病因标准 (至少1项) → 确诊营养不良

    Phenotypic criteria (≥1):
      - Non-volitional weight loss: >5% in 6mo or >10% in >6mo
      - Low BMI: <20 (age<70) or <22 (age≥70), <18.5 (Asia)
      - Reduced muscle mass: indirectly assessed

    Etiologic criteria (≥1):
      - Reduced food intake: <50% requirement >1 week
      - Disease burden / inflammation: CRP elevated or acute/chronic disease

    Severity: Stage 1 (moderate) vs Stage 2 (severe)

    Reference: Cederholm T et al. Clin Nutr 2019;38(1):1-9.
    """
    db_lower = disease_burden.lower()

    # ── Step 1: Risk screening (assumed positive if we get here) ──
    step1_positive = True

    # ── Step 2: Phenotypic criteria ──
    pheno_met: list[str] = []
    pheno_score = 0

    asian_bmi_cutoff = 18.5
    if bmi < asian_bmi_cutoff:
        pheno_met.append(f"低BMI ({bmi:.1f} < {asian_bmi_cutoff}, 亚洲标准)")
        pheno_score += 1
    elif bmi < 20.0:
        pheno_met.append(f"低BMI ({bmi:.1f} < 20.0)")
        pheno_score += 1
    elif bmi < 22.0 and kwargs.get("age", 0) >= 70:
        pheno_met.append(f"低BMI ({bmi:.1f} < 22.0, 老年标准)")
        pheno_score += 1

    if weight_loss_6mo_pct > 5:
        pheno_met.append(f"非自主体重下降 >5% ({weight_loss_6mo_pct}%)")
        pheno_score += 1
    elif weight_loss_6mo_pct > 2:
        pheno_met.append(f"体重下降 2-5% ({weight_loss_6mo_pct}%)")
        pheno_score += 0.5

    # ── Etiologic criteria ──
    etio_met: list[str] = []
    etio_score = 0

    if food_intake_week_pct < 50:
        etio_met.append(f"进食减少 >50% (过去1周仅{food_intake_week_pct}%)")
        etio_score += 1
    elif food_intake_week_pct < 75:
        etio_met.append(f"进食减少 25-50% (过去1周仅{food_intake_week_pct}%)")
        etio_score += 0.5

    inflammatory_conditions = [
        "感染", "脓毒症", "sepsis", "创伤", "trauma", "烧伤", "burn",
        "大手术", "major surgery", "胰腺炎", "pancreatitis", "肿瘤", "cancer",
        "炎症", "inflammation",
    ]
    has_inflammation = any(kw in db_lower for kw in inflammatory_conditions)
    if crp > 10 or has_inflammation:
        etio_met.append(f"疾病负担/炎症 (CRP={crp}mg/L)")
        etio_score += 1

    # ── Diagnosis ──
    pheno_positive = pheno_score >= 1
    etio_positive = etio_score >= 1
    malnutrition_confirmed = pheno_positive and etio_positive

    if malnutrition_confirmed:
        if weight_loss_6mo_pct > 10 or bmi < 16.0:
            severity = "重度营养不良 (Stage 2)"
        else:
            severity = "中度营养不良 (Stage 1)"
    else:
        severity = "未达到 GLIM 营养不良诊断标准"

    return {
        "status": "ok",
        "diagnosis": severity,
        "malnutrition_confirmed": malnutrition_confirmed,
        "step1_risk_screening": step1_positive,
        "step2_phenotypic": {
            "criteria_met": pheno_met,
            "positive": pheno_positive,
        },
        "step2_etiologic": {
            "criteria_met": etio_met,
            "positive": etio_positive,
        },
        "reference": "Cederholm T et al. Clin Nutr 2019;38(1):1-9 (GLIM Criteria)",
    }


# ═══════════════════════════════════════════════════════════
# 3. 营养途径决策 (EN vs PN vs SPN)
# ═══════════════════════════════════════════════════════════

def route_decision(
    gi_function: str = "",
    oral_intake_pct: int = 100,
    fasting_days: int = 0,
    bowel_obstruction: bool = False,
    hemodynamic_unstable: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """营养途径决策树 — EN vs PN vs SPN。

    Decision tree:
      1. Hemodynamic unstable? → 暂缓营养支持, 液体复苏优先
      2. Bowel obstruction / GI contraindication? → PN
      3. GI functional + oral intake insufficient? → EN (nasogastric/ONS)
      4. EN intolerance (GRV >200)? → SPN (EN + PN supplement)
      5. Fasting >7d? → PN

    Reference: ESPEN Guidelines (2023); CSPEN (2023).
    """
    route = ""
    route_reason = ""
    recommendations: list[str] = []

    if hemodynamic_unstable:
        route = "暂缓营养"
        route_reason = "血流动力学不稳定，暂缓营养支持，优先液体复苏与血管活性药物管理"
        recommendations = [
            "积极液体复苏，维持 MAP ≥65 mmHg",
            "血流动力学稳定后 24-48h 内启动低剂量肠内营养",
            "避免全量喂养加重肠道缺血",
        ]
    elif bowel_obstruction:
        route = "PN"
        route_reason = "肠梗阻/肠穿孔/严重腹腔感染，肠内营养绝对禁忌"
        recommendations = [
            "全肠外营养 (TPN)，经中心静脉导管输注",
            "尽早解除梗阻后尝试过渡至 EN",
            "监测导管相关感染",
            "每日评估肠道功能恢复",
        ]
    elif gi_function in ("无", "none", "absent") or gi_function.lower() in ("obstructed",):
        route = "PN"
        route_reason = f"肠道功能评估: {gi_function}，无法进行肠内营养"
        recommendations = [
            "全肠外营养 (TPN)",
            "择期评估经口/管饲过渡时机",
        ]
    elif oral_intake_pct < 40 and fasting_days >= 7:
        route = "PN"
        route_reason = f"禁食 {fasting_days} 天 + 经口摄入仅 {oral_intake_pct}%，需肠外营养"
        recommendations = [
            "起始 TPN，稳定后过渡 SPN",
            "每日评估经口/EN 可行性",
        ]
    elif gi_function.lower() in ("正常", "ok", "functional", "normal") or oral_intake_pct >= 60:
        route = "EN"
        route_reason = "肠道功能正常，优先选择肠内营养"
        if oral_intake_pct < 80:
            recommendations.append(f"经口摄入不足 ({oral_intake_pct}%)，补充 ONS 2-3 次/日")
        else:
            recommendations.append(f"经口摄入可 ({oral_intake_pct}%)，鼓励高蛋白饮食")
        recommendations.append("首选鼻胃管喂养 (无法经口者)")
        recommendations.append("若 EN >72h 无法达标，考虑 SPN 补充")
    elif gi_function.lower() in ("部分", "partial", "reduced", "减少") or oral_intake_pct < 60:
        route = "SPN"
        route_reason = f"肠道功能部分 + 摄入仅 {oral_intake_pct}%，EN 不足部分由 PN 补充"
        recommendations = [
            "尝试鼻胃管 / 鼻肠管 EN",
            "EN 耐受后逐步增量 (从 10-20 ml/h 开始)",
            "GRV >200ml 暂停 EN 加量，SPN 补足",
            "每 4h 监测 GRV",
        ]
    else:
        route = "EN"
        route_reason = "默认选择肠内营养 (评估肠道功能)"
        recommendations = [
            "首选鼻胃管喂养",
            "若 EN >72h 无法达标，考虑 SPN",
        ]

    return {
        "status": "ok",
        "recommended_route": route,
        "route_reason": route_reason,
        "recommendations": recommendations,
        "contraindications": {
            "bowel_obstruction": bowel_obstruction,
            "hemodynamic_unstable": hemodynamic_unstable,
        },
        "reference": "ESPEN Guidelines on Clinical Nutrition (2023); CSPEN (2023)",
    }


# ═══════════════════════════════════════════════════════════
# 4. Harris-Benedict 能量 + 蛋白质目标
# ═══════════════════════════════════════════════════════════

PROTEIN_TARGETS = {
    "default": {"min_g_per_kg": 1.0, "max_g_per_kg": 1.2, "label": "维持"},
    "大手术": {"min_g_per_kg": 1.2, "max_g_per_kg": 1.5, "label": "术后恢复"},
    "创伤": {"min_g_per_kg": 1.2, "max_g_per_kg": 2.0, "label": "创伤修复"},
    "烧伤": {"min_g_per_kg": 1.5, "max_g_per_kg": 2.5, "label": "烧伤修复"},
    "感染": {"min_g_per_kg": 1.2, "max_g_per_kg": 1.5, "label": "感染/脓毒症"},
    "脓毒症": {"min_g_per_kg": 1.2, "max_g_per_kg": 1.5, "label": "感染/脓毒症"},
    "sepsis": {"min_g_per_kg": 1.2, "max_g_per_kg": 1.5, "label": "感染/脓毒症"},
    "肿瘤": {"min_g_per_kg": 1.2, "max_g_per_kg": 2.0, "label": "肿瘤恶液质"},
    "cancer": {"min_g_per_kg": 1.2, "max_g_per_kg": 2.0, "label": "肿瘤恶液质"},
    "肥胖": {"min_g_per_kg": 1.5, "max_g_per_kg": 2.0, "label": "肥胖 (标准体重计)"},
    "obese": {"min_g_per_kg": 1.5, "max_g_per_kg": 2.0, "label": "肥胖 (标准体重计)"},
    "肾衰竭": {"min_g_per_kg": 0.6, "max_g_per_kg": 0.8, "label": "肾衰竭 (无透析)"},
    "renal_failure": {"min_g_per_kg": 0.6, "max_g_per_kg": 0.8, "label": "肾衰竭 (无透析)"},
    "透析": {"min_g_per_kg": 1.2, "max_g_per_kg": 1.5, "label": "透析"},
    "dialysis": {"min_g_per_kg": 1.2, "max_g_per_kg": 1.5, "label": "透析"},
    "肝衰竭": {"min_g_per_kg": 0.8, "max_g_per_kg": 1.2, "label": "肝衰竭 (肝性脑病)"},
    "liver_failure": {"min_g_per_kg": 0.8, "max_g_per_kg": 1.2, "label": "肝衰竭 (肝性脑病)"},
}


def energy_protein_target(
    weight_kg: float = 60.0,
    height_cm: float = 170.0,
    age: int = 50,
    gender: str = "M",
    activity_factor: float = 1.2,
    stress_factor: float = 1.0,
    condition: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Harris-Benedict 基础能量消耗 + 活动/应激系数 × 分层蛋白目标。

    BEE (Harris-Benedict):
      Male:   66.5 + 13.75*W + 5.003*H - 6.775*A
      Female: 655.1 + 9.563*W + 1.850*H - 4.676*A

    TEE = BEE × activity_factor × stress_factor

    Activity factors: 1.0 (bed rest), 1.2 (ambulatory), 1.3-1.5 (active)
    Stress factors:   1.0 (no stress), 1.1-1.2 (minor surgery),
                      1.2-1.4 (major surgery/sepsis), 1.5-2.0 (severe burn)

    Reference: Harris JA, Benedict FG. Proc Natl Acad Sci USA 1918;4(12):370-373.
    """
    gender_upper = gender.upper()
    if gender_upper in ("M", "男", "MALE"):
        bee = 66.5 + 13.75 * weight_kg + 5.003 * height_cm - 6.775 * age
    else:
        bee = 655.1 + 9.563 * weight_kg + 1.850 * height_cm - 4.676 * age

    tee = bee * activity_factor * stress_factor

    # Protein target by condition
    condition_lower = condition.lower()
    protein = PROTEIN_TARGETS["default"]
    for key, val in PROTEIN_TARGETS.items():
        if key in condition_lower:
            protein = val
            break

    protein_min_g = round(weight_kg * protein["min_g_per_kg"], 1)
    protein_max_g = round(weight_kg * protein["max_g_per_kg"], 1)

    return {
        "status": "ok",
        "bee_kcal": round(bee, 0),
        "tee_kcal": round(tee, 0),
        "energy_target": f"{round(tee * 0.9)} - {round(tee * 1.1)} kcal/d",
        "factors": {
            "activity_factor": activity_factor,
            "stress_factor": stress_factor,
        },
        "protein_target": {
            "g_per_kg": f"{protein['min_g_per_kg']} - {protein['max_g_per_kg']}",
            "g_per_day": f"{protein_min_g} - {protein_max_g}",
            "category": protein["label"],
        },
        "fluid_target": f"{round(weight_kg * 30)} - {round(weight_kg * 40)} ml/d",
        "reference": "Harris JA, Benedict FG. Proc Natl Acad Sci USA 1918;4(12):370-373",
    }


# ═══════════════════════════════════════════════════════════
# 5. 再喂养综合征风险评估
# ═══════════════════════════════════════════════════════════

def refeeding_risk(
    bmi: float = 22.0,
    weight_loss_3mo_pct: float = 0.0,
    fasting_days: int = 0,
    potassium: float = 4.0,
    phosphorus: float = 1.2,
    magnesium: float = 0.9,
    **kwargs: Any,
) -> dict[str, Any]:
    """再喂养综合征风险评估 — NICE 2006 标准。

    Major criteria (≥1 = high risk):
      BMI < 16
      Unintentional weight loss >15% (3-6mo)
      Little/no nutritional intake >10 days
      Low K+/PO4/Mg before feeding

    Minor criteria (≥2 = high risk):
      BMI < 18.5
      Unintentional weight loss >10% (3-6mo)
      Little/no intake >5 days
      History of: alcohol abuse / drugs (insulin/chemo/antacids/diuretics)

    Reference: NICE CG32 (2006); ASPEN Refeeding Consensus.
    """
    major: list[str] = []
    minor: list[str] = []
    major_count = 0
    minor_count = 0

    if bmi < 16:
        major.append(f"BMI {bmi:.1f} < 16")
        major_count += 1
    elif bmi < 18.5:
        minor.append(f"BMI {bmi:.1f} < 18.5")
        minor_count += 1

    if weight_loss_3mo_pct > 15:
        major.append(f"体重下降 >15% ({weight_loss_3mo_pct}%)")
        major_count += 1
    elif weight_loss_3mo_pct > 10:
        minor.append(f"体重下降 >10% ({weight_loss_3mo_pct}%)")
        minor_count += 1

    if fasting_days > 10:
        major.append(f"禁食/摄入不足 >10天 ({fasting_days}d)")
        major_count += 1
    elif fasting_days > 5:
        minor.append(f"禁食/摄入不足 >5天 ({fasting_days}d)")
        minor_count += 1

    if potassium < 2.5 or phosphorus < 0.5 or magnesium < 0.5:
        major.append("喂养前显著低钾/低磷/低镁")
        major_count += 1
    elif potassium < 3.5 or phosphorus < 0.8 or magnesium < 0.7:
        minor.append("喂养前轻度电解质异常")
        minor_count += 1

    if major_count >= 1 or minor_count >= 2:
        risk_level = "高危"
    elif minor_count >= 1:
        risk_level = "中危"
    else:
        risk_level = "低危"

    if risk_level == "高危":
        start_plan = {
            "energy_start": "从目标量 1/4 开始 (约 5-10 kcal/kg/d)",
            "titration": "每 24-48h 增加 200-300 kcal, 4-7 天达到目标量",
            "thiamine": "启动前 30min: 维生素 B1 200-300mg IV (连续 ≥3 天)",
            "monitoring": {
                "electrolytes": "K/Mg/P 每日检测 × 至少前7天",
                "fluid": "严格出入量记录",
                "glucose": "血糖监测 q6h",
                "ekg": "有电解质异常者每日 EKG",
            },
            "supplementation": {
                "phosphate": "若 PO4 <0.5 mmol/L: 磷酸盐 0.3-0.6 mmol/kg/d IV",
                "potassium": "若 K <3.5 mmol/L: KCl 补入 PN",
                "magnesium": "若 Mg <0.7 mmol/L: MgSO4 补入 PN",
            },
        }
    elif risk_level == "中危":
        start_plan = {
            "energy_start": "从目标量 1/2 开始 (约 15-20 kcal/kg/d)",
            "titration": "每 24h 增加, 3-4 天达到目标量",
            "thiamine": "维生素 B1 100mg/d PO × 3天 (高危IV)",
            "monitoring": {
                "electrolytes": "K/Mg/P 每日检测 × 4天",
                "fluid": "出入量记录",
                "glucose": "血糖监测 q8h",
            },
        }
    else:
        start_plan = {
            "energy_start": "从目标量 2/3 开始",
            "titration": "24-48h 达到目标量",
            "monitoring": {"electrolytes": "K/Mg/P 隔日检测 × 4天"},
        }

    return {
        "status": "ok",
        "risk_level": risk_level,
        "major_criteria": major,
        "major_count": major_count,
        "minor_criteria": minor,
        "minor_count": minor_count,
        "start_plan": start_plan,
        "reference": "NICE CG32 (2006, updated 2017); ASPEN Refeeding Consensus",
    }


# ═══════════════════════════════════════════════════════════
# 6. 综合营养评估报告
# ═══════════════════════════════════════════════════════════

def nutrition_report(
    patient_id: str = "",
    nrs2002: dict | None = None,
    glim: dict | None = None,
    route: dict | None = None,
    energy_protein: dict | None = None,
    refeeding: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """综合营养评估报告 — 汇总五维结果生成结构化报告。

    Aggregates results from nrs2002_screen, glim_diagnosis, route_decision,
    energy_protein_target, and refeeding_risk into a unified Markdown report.
    """
    nrs2002 = nrs2002 or {}
    glim = glim or {}
    route = route or {}
    energy_protein = energy_protein or {}
    refeeding = refeeding or {}

    nrs_total = nrs2002.get("nrs2002_total", 0)
    nrs_risk = nrs2002.get("risk_level", "未知")
    glim_diag = glim.get("diagnosis", "未评估")
    route_sel = route.get("recommended_route", "未评估")
    ep_energy = energy_protein.get("energy_target", "未评估")
    ep_protein = energy_protein.get("protein_target", {}).get("g_per_day", "未评估")
    refeed_risk = refeeding.get("risk_level", "未评估")

    report_text = (
        f"【营养评估报告 — {patient_id}】\n"
        f"\n"
        f"1. NRS2002 营养风险筛查: 总分 {nrs_total}/7, 风险等级 {nrs_risk}\n"
        f"2. GLIM 营养不良诊断: {glim_diag}\n"
        f"3. 营养途径推荐: {route_sel}\n"
        f"4. 能量目标: {ep_energy}, 蛋白质目标: {ep_protein}\n"
        f"5. 再喂养综合征风险: {refeed_risk}\n"
    )

    critical_flags: list[str] = []
    if nrs_total >= 5:
        critical_flags.append(f"NRS2002 高分 ({nrs_total}) — 高营养风险，立即启动营养支持")
    if "重度" in str(glim_diag):
        critical_flags.append("GLIM 诊断为重度营养不良")
    if "暂缓" in str(route_sel):
        critical_flags.append("营养支持暂缓 — 血流动力学不稳定")
    if refeed_risk == "高危":
        critical_flags.append("再喂养综合征高危 — 从 1/4 目标量开始")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "report_text": report_text,
        "report_sections": {
            "nrs2002": {"score": nrs_total, "risk_level": nrs_risk},
            "glim": {"diagnosis": glim_diag},
            "route": {"recommended": route_sel},
            "energy_protein": {"energy": ep_energy, "protein": ep_protein},
            "refeeding": {"risk_level": refeed_risk},
        },
        "critical_flags": critical_flags,
        "critical_count": len(critical_flags),
        "reference": "ESPEN/CSPEN/ASPEN Guidelines (2023); GLIM Criteria (2019)",
    }
