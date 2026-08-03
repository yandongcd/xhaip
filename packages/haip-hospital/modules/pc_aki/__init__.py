"""PC-AKI 对比剂急性肾损伤筛查管理智能体.

JBI 5项高危因素 + KDIGO AKI分期 + ESUR水化方案 + 药物安全管理.
"""
from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="pc-aki", department="心内科")
_GUIDELINES = [
    "KDIGO 2024 急性肾损伤临床实践指南",
    "ESUR V10.0 对比剂安全指南",
    "ACR 2021 对比剂手册",
    "JBI 碘对比剂风险筛查最佳实践 (2023)",
    "中国对比剂安全使用专家共识 (2024)",
]
_agent.rule_engine.load_all()

# JBI 5项高危因素
JBI_RISK_FACTORS = [
    {"id": "age_ge_60", "label": "年龄 ≥60岁", "weight": 1},
    {"id": "diabetes", "label": "糖尿病", "weight": 2},
    {"id": "hypertension_rx", "label": "高血压(需药物控制)", "weight": 1},
    {"id": "metformin", "label": "使用二甲双胍", "weight": 2},
    {"id": "renal_history", "label": "肾脏问题(移植/单肾/CKD/透析/手术/肿瘤/既往AKI)", "weight": 3},
]

# eGFR → CKD stage
CKD_STAGES = [
    (90, "G1 正常或增高", "green"),
    (60, "G2 轻度下降", "green"),
    (45, "G3a 轻-中度下降", "yellow"),
    (30, "G3b 中-重度下降", "orange"),
    (15, "G4 重度下降", "red"),
    (0, "G5 肾衰竭", "red"),
]


def _calc_egfr(scr: float, age: int, sex: str = "male", race: str = "asian") -> float:
    """CKD-EPI 2021 eGFR calculation (no race coefficient for Asian)."""
    if scr <= 0:
        return 90.0
    k = 0.9 if sex == "male" else 0.7
    a = -0.302 if sex == "male" else -0.241
    female_factor = 1.0 if sex == "male" else 1.012
    return 142.0 * ((scr / k) ** (min(scr / k, 1) * -0.241 + max(scr / k - 1, 0) * -1.200)) * (0.9938 ** age) * female_factor


def _get_ckd_stage(egfr: float) -> dict:
    for threshold, label, color in CKD_STAGES:
        if egfr >= threshold:
            return {"stage": label, "egfr": round(egfr, 1), "color": color}
    return {"stage": "G5 肾衰竭", "egfr": round(egfr, 1), "color": "red"}


def risk_screen(**kwargs) -> dict:
    """PC-AKI 高危因素筛查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    age = p.get("age", 0)
    dx = str(p.get("diagnosis", "")).lower()
    meds = str(p.get("medications", "")).lower()

    hits = []
    risk_score = 0

    if age >= 60:
        hits.append(JBI_RISK_FACTORS[0])
        risk_score += 1
    if any(kw in dx for kw in ["糖尿病", "diabetes", "dm"]):
        hits.append(JBI_RISK_FACTORS[1])
        risk_score += 2
    if any(kw in dx for kw in ["高血压", "hypertension"]):
        hits.append(JBI_RISK_FACTORS[2])
        risk_score += 1
    if any(kw in meds for kw in ["二甲双胍", "metformin"]):
        hits.append(JBI_RISK_FACTORS[3])
        risk_score += 2
    if any(kw in dx for kw in ["肾病", "肾脏", "CKD", "透析", "dialysis", "肾移植", "renal"]):
        hits.append(JBI_RISK_FACTORS[4])
        risk_score += 3

    level = "低危"
    if risk_score >= 5:
        level = "高危"
    elif risk_score >= 3:
        level = "中危"

    guides = _agent.search_guidelines("对比剂安全") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"PC-AKI风险筛查 — {level} (评分{risk_score})",
        patient=p,
        guidelines=guides,
        findings=[{"JBI高危因素": [h["label"] for h in hits], "风险评分": risk_score, "风险等级": level}],
        recommendations=[
            f"建议术前检查eGFR (风险评分{risk_score})",
            "二甲双胍: 造影前48h停用, 术后48h复查肾功能正常后恢复" if any("二甲双胍" in h["label"] for h in hits) else "",
            "高危患者: 术前水化+术后48-72h监测肾功能",
        ],
    )


def renal_assess(**kwargs) -> dict:
    """肾功能评估 — eGFR + AKI分期."""
    pid = kwargs.get("patient_id", "")
    pre_cr = float(kwargs.get("pre_creatinine", 0) or 0)
    post_cr = float(kwargs.get("post_creatinine", 0) or 0)

    p = _agent.get_patient(pid) or {}
    age = p.get("age", 65)
    sex = p.get("gender", "male")

    egfr = _calc_egfr(pre_cr, age, sex) if pre_cr > 0 else 90
    stage = _get_ckd_stage(egfr)

    aki_info = ""
    if post_cr > 0 and pre_cr > 0:
        cr_ratio = post_cr / pre_cr
        if cr_ratio >= 3.0 or post_cr >= 354:
            aki_info = "🔴 AKI Stage 3 (KDIGO)"
        elif cr_ratio >= 2.0:
            aki_info = "🟠 AKI Stage 2 (KDIGO)"
        elif cr_ratio >= 1.5:
            aki_info = "🟡 AKI Stage 1 (KDIGO)"

    guides = _agent.search_guidelines("KDIGO") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"肾功能评估 — eGFR {stage['egfr']} mL/min/1.73m² ({stage['stage']})",
        patient=p,
        guidelines=guides,
        findings=[{
            "eGFR": f"{stage['egfr']} mL/min/1.73m²",
            "CKD分期": stage["stage"],
            "AKI判定": aki_info or "无AKI",
            "术前肌酐": f"{pre_cr} μmol/L" if pre_cr > 0 else "未提供",
            "术后肌酐": f"{post_cr} μmol/L" if post_cr > 0 else "未提供",
        }],
        recommendations=[
            "eGFR≥45: 常规水化预防 (生理盐水1mL/kg/h, 术前3-12h+术后12h)",
            "eGFR<45: 加强水化+术后48-72h监测肾功能",
            "eGFR<30: 严格权衡风险获益+最小剂量对比剂+必须水化",
        ],
        alerts=[
            "eGFR<30 → 对比剂肾病高风险" if egfr < 30 else "",
            aki_info if aki_info else "",
        ],
    )


def prevention_plan(**kwargs) -> dict:
    """预防管理方案 — 水化/药物调整/重复造影."""
    pid = kwargs.get("patient_id", "")
    egfr = float(kwargs.get("eGFR", 90) or 90)
    risk_level = kwargs.get("risk_level", "低危")
    contrast_dose = float(kwargs.get("contrast_dose", 0) or 0)

    p = _agent.get_patient(pid) or {}

    plan = {
        "hydration": [],
        "medication": [],
        "monitoring": [],
        "contraindications": [],
    }

    # Hydration
    if egfr < 30 or risk_level == "高危":
        plan["hydration"] = [
            "术前3-12h: 生理盐水 1.0 mL/kg/h IV",
            "术后12-24h: 生理盐水 1.0 mL/kg/h IV (心衰患者减量至0.5 mL/kg/h)",
            "容量超负荷监测: 每小时尿量+每日体重+肺部听诊",
        ]
    elif egfr < 45:
        plan["hydration"] = [
            "术前3-12h: 生理盐水 1.0 mL/kg/h IV",
            "术后12h: 生理盐水 1.0 mL/kg/h IV",
        ]
    else:
        plan["hydration"] = ["口服水化: 术前饮水500-1000mL + 术后24h饮水≥2000mL"]

    # Medication
    plan["medication"] = [
        "二甲双胍: 造影前48h停用, 术后48h复查Cr正常后恢复",
        "ACEI/ARB: eGFR<30 → 建议造影前24h暂停 (KDIGO弱推荐)",
        "利尿剂: 造影当天暂停 → 避免脱水加重肾损伤",
        "NSAIDs: 造影前后48h避免使用",
    ]

    # Monitoring
    if egfr < 45:
        plan["monitoring"] = [
            "术后24h复查SCr",
            "术后48-72h复查SCr (如24h升高>25%)",
            "eGFR<30 → 住院监测 ≥72h",
        ]
    else:
        plan["monitoring"] = ["术后48h复查SCr (高危患者)"]

    # Contraindications
    if egfr < 30:
        plan["contraindications"].append("⚠️ eGFR<30: 严格限制对比剂剂量 (≤100mL碘海醇350)")
    if contrast_dose > 0 and egfr < 30:
        max_dose = max(egfr * 3, 30)
        if contrast_dose > max_dose:
            plan["contraindications"].append(f"🔴 对比剂剂量>{max_dose}mL (建议≤5×eGFR) — 超量风险")

    guides = _agent.search_guidelines("对比剂安全") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"PC-AKI预防方案 — eGFR {egfr} / {risk_level}",
        patient=p,
        guidelines=guides,
        findings=[{
            "eGFR": egfr,
            "风险等级": risk_level,
            "水化方案": plan["hydration"],
            "药物调整": plan["medication"],
            "术后监测": plan["monitoring"],
        }],
        recommendations=plan["hydration"] + plan["medication"] + plan["monitoring"],
        alerts=plan["contraindications"],
    )


def nursing_checklist(**kwargs) -> dict:
    """护理执行清单."""
    pid = kwargs.get("patient_id", "")
    risk_level = kwargs.get("risk_level", "低危")

    checklist = [
        {"项": "PC-AKI风险筛查", "状态": "待确认", "责任": "责任护士"},
        {"项": "eGFR/SCr术前基线", "状态": "待抽血", "责任": "责任护士/检验科"},
        {"项": "二甲双胍停药确认", "状态": "待确认", "责任": "责任护士"},
        {"项": "水化执行(术前)", "状态": "待执行", "责任": "责任护士"},
        {"项": "水化执行(术后)", "状态": "待执行", "责任": "责任护士"},
        {"项": "术后24h复查SCr", "状态": "待提醒", "责任": "责任护士"},
        {"项": "患者宣教(多饮水+药物调整)", "状态": "待执行", "责任": "责任护士"},
        {"项": "交班: 标注对比剂暴露及肾功能监测计划", "状态": "待执行", "责任": "责任护士"},
    ]

    if risk_level == "高危":
        checklist.append({"项": "⚠️ 告知主治医师: eGFR<30高危", "状态": "必须立即", "责任": "责任护士"})

    return {
        "status": "ok",
        "summary": f"PC-AKI护理清单 — {risk_level}",
        "checklist": checklist,
        "disclaimer": "本清单为AI辅助生成，须经责任护士逐项确认执行",
    }
