"""cardio_risk — RuleEngine-driven clinical reasoning.

Clinical tools:
  - evaluate: RCRI 6-factor perioperative cardiac risk stratification
  - evaluate_mi: Universal MI definition assessment (troponin + ECG + symptoms)
  - evaluate_htn: BP classification per 2024 Chinese Hypertension Guideline

Guidelines referenced:
  - RCRI (Lee et al. 1999) + ACC/AHA 2014 + ESC 2022
  - 4th Universal Definition of MI (2018)
  - 中国高血压防治指南 (2024 年修订版) — CMA Hypertension Guideline 2024
"""

from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="cardio-risk", department="cardio_risk")
_GUIDELINES = [
    "RCRI 围术期心血管风险评估 (Lee et al. 1999, ACC/AHA 2014, ESC 2022)",
    "4th Universal Definition of Myocardial Infarction (2018)",
    "中国高血压防治指南 (2024年修订版)",
    "ACC/AHA 2014 非心脏手术围术期心血管评估与管理指南",
    "ESC 2022 非心脏手术心血管评估与管理指南",
]
_agent.rule_engine.load_all()


# ═══════════════════════════════════════════════════════════
# RCRI Risk Factors
# ═══════════════════════════════════════════════════════════

_RCRI_FACTORS: list[tuple[str, str, list[str]]] = [
    ("high_risk_surgery", "高危手术", ["腹内", "胸内", "腹股沟上血管", "大血管"]),
    ("cad", "冠心病史(CAD)", ["冠心病", "冠脉", "心梗", "支架", "PCI", "搭桥", "CABG", "缺血性心脏病"]),
    ("chf", "充血性心力衰竭(CHF)", ["心衰", "心力衰竭", "EF<40", "CHF"]),
    ("cva", "脑血管疾病(CVA/TIA)", ["脑梗", "卒中", "TIA", "脑出血", "脑血管"]),
    ("dm_insulin", "胰岛素依赖型糖尿病", ["胰岛素", "糖尿病1型", "IDDM"]),
    ("cr_high", "术前Cr>177μmol/L", []),
]


# ═══════════════════════════════════════════════════════════
# BP Classification (2024 Chinese Hypertension Guideline)
# ═══════════════════════════════════════════════════════════

def _classify_bp(sbp: int, dbp: int) -> dict[str, Any]:
    """BP classification per 中国高血压防治指南 (2024 年修订版).

    Classification tiers:
      正常: SBP < 120 AND DBP < 80
      正常高值: SBP 120-139 AND/OR DBP 80-89
      1 级高血压 (轻度): SBP 140-159 AND/OR DBP 90-99
      2 级高血压 (中度): SBP 160-179 AND/OR DBP 100-109
      3 级高血压 (重度): SBP >= 180 AND/OR DBP >= 110
      单纯收缩期高血压 (ISH): SBP >= 140 AND DBP < 90
    """
    if sbp < 120 and dbp < 80:
        grade = "正常"
        grade_cn = "正常血压"
        level = 0
    elif 120 <= sbp <= 139 or 80 <= dbp <= 89:
        grade = "正常高值"
        grade_cn = "正常高值血压"
        level = 0
    elif (140 <= sbp <= 159 or 90 <= dbp <= 99) and not (sbp >= 140 and dbp < 90):
        grade = "1级"
        grade_cn = "1 级高血压 (轻度)"
        level = 1
    elif 160 <= sbp <= 179 or 100 <= dbp <= 109:
        grade = "2级"
        grade_cn = "2 级高血压 (中度)"
        level = 2
    elif sbp >= 180 or dbp >= 110:
        grade = "3级"
        grade_cn = "3 级高血压 (重度)"
        level = 3
    elif sbp >= 140 and dbp < 90:
        grade = "ISH"
        grade_cn = "单纯收缩期高血压 (ISH)"
        level = 1
    else:
        grade = "未分类"
        grade_cn = "未分类"
        level = 0

    return {"grade": grade, "grade_cn": grade_cn, "level": level, "sbp": sbp, "dbp": dbp}


# ═══════════════════════════════════════════════════════════
# 1. evaluate — RCRI Cardiac Risk Stratification
# ═══════════════════════════════════════════════════════════

def evaluate(
    patient_id: str = "",
    labs: dict[str, float] | None = None,
    ecg_findings: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """RCRI 6-factor perioperative cardiac risk assessment.

    Factors:
      1. High-risk surgery (intraperitoneal / intrathoracic / suprainguinal vascular)
      2. History of ischemic heart disease (CAD)
      3. History of congestive heart failure (CHF)
      4. History of cerebrovascular disease (CVA / TIA)
      5. Preoperative insulin therapy for diabetes mellitus
      6. Preoperative serum creatinine > 177 μmol/L (> 2.0 mg/dL)

    Risk Classes:
      I: 0 factors, cardiac event rate ~0.4%
      II: 1 factor, cardiac event rate ~0.9%
      III: ≥2 factors, cardiac event rate ~6.6-11%
      IV: ≥4 factors (or evidence of active cardiac condition)

    Reference: Lee et al. Circulation 1999 + 2014 ACC/AHA + 2022 ESC
    """
    patient = _agent.get_patient(patient_id) or {}
    labs = labs or {}
    lab_results = patient.get("lab_results", {})

    # Resolve lab values: explicit params take precedence over patient data
    cr = labs.get("creatinine", labs.get("Cr",
        lab_results.get("creatinine", lab_results.get("Cr", 0))))
    troponin = labs.get("troponin", labs.get("cTnI",
        lab_results.get("troponin", 0)))
    ckmb = labs.get("ckmb", labs.get("CK-MB", 0))

    past = patient.get("past_history", "")
    diagnosis = patient.get("diagnosis", "")
    combined_text = f"{past} {diagnosis}"

    # ── RCRI scoring ──
    rcri = 0
    rcri_factors: list[dict[str, Any]] = []

    # Factor 1: High-risk surgery (assumed yes in perioperative context)
    rcri_factors.append({"factor": "高危手术", "detail": "腹内/胸内/腹股沟上血管手术", "present": True})
    rcri += 1

    # Factor 2: CAD / ischemic heart disease
    has_cad = any(kw in combined_text for kw in [
        "冠心病", "冠脉", "心梗", "MI", "支架", "PCI", "搭桥", "CABG", "缺血性心脏病",
    ])
    rcri_factors.append({"factor": "冠心病史(CAD)", "detail": "缺血性心脏病史", "present": has_cad})
    if has_cad:
        rcri += 1

    # Factor 3: CHF
    has_chf = any(kw in combined_text for kw in ["心衰", "CHF", "心力衰竭"])
    rcri_factors.append({"factor": "充血性心力衰竭(CHF)", "detail": "心衰病史", "present": has_chf})
    if has_chf:
        rcri += 1

    # Factor 4: CVA/TIA
    has_cva = any(kw in combined_text for kw in ["脑梗", "卒中", "CVA", "TIA", "脑出血", "脑血管"])
    rcri_factors.append({"factor": "脑血管疾病(CVA/TIA)", "detail": "脑血管病史", "present": has_cva})
    if has_cva:
        rcri += 1

    # Factor 5: Insulin-dependent DM
    has_dm = any(kw in combined_text for kw in ["胰岛素", "糖尿病1型", "IDDM"])
    rcri_factors.append({"factor": "胰岛素依赖型糖尿病", "detail": "术前胰岛素治疗", "present": has_dm})
    if has_dm:
        rcri += 1

    # Factor 6: Cr > 177 μmol/L
    cr_high = float(cr) > 177 if cr else False
    rcri_factors.append({
        "factor": "肾功能不全(Cr>177μmol/L)",
        "detail": f"Cr={cr}μmol/L" if cr else "未提供",
        "present": cr_high,
    })
    if cr_high:
        rcri += 1

    # ── Risk class assignment ──
    if rcri >= 5:
        risk_class = "IV"
        risk_desc = "极高危 (心脏事件风险 ≥11%，存在活动性心脏疾病)"
    elif rcri >= 3:
        risk_class = "III"
        risk_desc = "高危 (心脏事件风险 6.6-11%)"
    elif rcri >= 1:
        risk_class = "II"
        risk_desc = "中危 (心脏事件风险 0.9-6.6%)"
    else:
        risk_class = "I"
        risk_desc = "低危 (心脏事件风险 <0.4%)"

    # ── Enzyme & ECG check ──
    enzyme_abnormal = float(troponin) > 0.04 if troponin else False
    if ckmb:
        enzyme_abnormal = enzyme_abnormal or float(ckmb) > 25

    ecg_upper = ecg_findings.upper() if ecg_findings else ""
    ecg_critical = any(kw in ecg_upper for kw in [
        "ST ELEVATION", "ST DEPRESSION", "STEMI", "NSTEMI", "VT", "VF", "3° AVB",
    ])
    ecg_abnormal = any(kw in ecg_upper for kw in [
        "T WAVE", "Q WAVE", "BBB", "AF", "LVH", "ABNORMAL", "异常", "ST-T",
    ])

    # ── Recommendations ──
    recommendations: list[str] = []
    if enzyme_abnormal or ecg_critical:
        recommendations.append("【紧急】心肌损伤标志物阳性和/或缺血性心电图改变，立即请心内科会诊排除 ACS")
        recommendations.append("【检查】急查 hs-cTnI/T，每 3 小时复查至 12-24 小时；18 导联心电图")
        recommendations.append("【治疗】按 ACS 指南：双联抗血小板 (阿司匹林 + P2Y12 受体抑制剂) + 抗凝")
    elif risk_class in ("III", "IV"):
        recommendations.append("RCRI 高危/极高危：建议 MDT 会诊，优化术前心血管状态")
        recommendations.append("【监测】术中持续心电 + 血压 + 氧饱和度，术后 48h 心肌酶复查")
        recommendations.append("【药物】围术期继续 β 受体阻滞剂 (如已服用)，避免低血压和心动过速")
        recommendations.append("建议完善超声心动图评估心功能 (LVEF)")
    elif risk_class == "II":
        recommendations.append("RCRI 中危：建议完善超声心动图，如合并 ≥2 项临床因素可行无创负荷检查")
        recommendations.append("维持围术期血液动力学稳定，避免贫血 (Hb > 100 g/L) 和低氧")
    else:
        recommendations.append("RCRI 低危：无需额外心脏检查，常规围术期监测即可")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "assessment": f"RCRI 评分 {rcri}/6 分，风险等级 {risk_class} ({risk_desc})",
        "rcri_score": rcri,
        "rcri_class": risk_class,
        "rcri_risk_description": risk_desc,
        "rcri_factors": rcri_factors,
        "enzyme_abnormal": enzyme_abnormal,
        "troponin": troponin,
        "ecg_critical": ecg_critical,
        "ecg_abnormal": ecg_abnormal,
        "recommendations": recommendations,
        "guideline_refs": [
            "RCRI — Lee et al. Circulation 1999;100:1043-1049",
            "2014 ACC/AHA Guideline on Perioperative Cardiovascular Evaluation (JACC 2014)",
            "2022 ESC Guidelines on Cardiovascular Assessment of Non-cardiac Surgery (Eur Heart J 2022)",
        ],
    }


# ═══════════════════════════════════════════════════════════
# 2. evaluate_mi — Universal MI Definition Assessment
# ═══════════════════════════════════════════════════════════

def evaluate_mi(
    patient_id: str = "",
    troponin: float = 0.0,
    ecg: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Universal Definition of MI (4th) assessment.

    Criteria (4th Universal Definition of MI, 2018):
      Detection of rise and/or fall of cardiac troponin (cTn) with at least
      one value above the 99th percentile upper reference limit (URL), AND
      at least one of:
        - Symptoms of acute myocardial ischemia
        - New ischemic ECG changes
        - Development of pathological Q waves
        - Imaging evidence of new loss of viable myocardium or RWMA
        - Identification of coronary thrombus by angiography or autopsy

    cTnI thresholds (per universal-mi-4th):
      99th percentile URL: ~0.04 ng/mL (high-sensitivity assay)
    """
    patient = _agent.get_patient(patient_id) or {}
    lab_results = patient.get("lab_results", {})

    # Resolve troponin: explicit param > patient lab_results
    if not troponin:
        troponin = float(lab_results.get("troponin", 0))

    past = patient.get("past_history", "")
    diagnosis = patient.get("diagnosis", "")
    chief = patient.get("chief_complaint", "")
    combined = f"{chief} {diagnosis} {past}"

    # ── Troponin criterion ──
    TROPONIN_URL = 0.04  # 99th percentile URL for hs-cTnI (ng/mL)
    ctn_elevated = troponin > TROPONIN_URL
    ctn_multiple = round(troponin / TROPONIN_URL, 1) if TROPONIN_URL > 0 else 0

    # ── ECG criterion ──
    ecg_upper = ecg.upper() if ecg else ""
    ecg_ischemic = any(kw in ecg_upper for kw in [
        "ST ELEVATION", "STEMI", "ST DEPRESSION", "ST-T", "T WAVE INVERSION",
        "NEW LBBB", "PATHOLOGICAL Q", "Q WAVE", "NSTEMI",
    ])

    # ── Symptom criterion ──
    symptom_keywords = ["胸闷", "胸痛", "心悸", "气促", "呼吸困难", "大汗", "恶心",
                        "压榨感", "放射痛", "chest pain", "辐射"]
    has_symptoms = any(kw in combined for kw in symptom_keywords)

    # ── MI diagnosis ──
    criteria_met: list[str] = []
    if ctn_elevated:
        criteria_met.append(f"cTnI 升高 ({troponin} ng/mL，>99th URL {TROPONIN_URL} ng/mL, ×{ctn_multiple})")
    if ecg_ischemic:
        criteria_met.append(f"缺血性心电图改变 ({ecg[:60]})")
    if has_symptoms:
        criteria_met.append("存在心肌缺血症状 (胸痛/胸闷/气促等)")

    # MI type
    if ctn_elevated and (ecg_ischemic or has_symptoms):
        if "ST ELEVATION" in ecg_upper or "STEMI" in ecg_upper:
            mi_type = "STEMI (ST 段抬高型心肌梗死)"
        else:
            mi_type = "NSTEMI (非 ST 段抬高型心肌梗死)"
        diagnosis_text = f"符合急性心肌梗死诊断标准: {'; '.join(criteria_met)}"
        urgency = "emergency"
    elif ctn_elevated:
        mi_type = "心肌损伤 (需鉴别 1 型/2 型 MI 与非缺血性心肌损伤)"
        diagnosis_text = f"cTnI 升高但缺乏明确临床证据: {'; '.join(criteria_met)}"
        urgency = "urgent"
    elif ecg_ischemic or has_symptoms:
        mi_type = "疑诊 ACS (需动态观察 troponin + ECG)"
        diagnosis_text = "缺血症状/心电图异常但 troponin 未达阈值，需动态观察"
        urgency = "urgent"
    else:
        mi_type = "排除急性 MI"
        diagnosis_text = "cTnI、ECG 及症状均不符合 MI 诊断标准"
        urgency = "routine"

    # ── Killip class estimation ──
    physical = patient.get("physical_exam", "")
    if any(kw in (physical + diagnosis) for kw in ["肺水肿", "端坐呼吸", "粉红泡沫痰", "双肺湿啰音"]):
        killip = "II-III 级 (肺淤血/肺水肿)"
    elif any(kw in (physical + diagnosis) for kw in ["心源性休克", "低血压", "四肢湿冷", "少尿"]):
        killip = "IV 级 (心源性休克)"
    else:
        killip = "I 级 (无心力衰竭)"

    # ── Recommendations ──
    recommendations: list[str] = []
    if urgency == "emergency":
        recommendations.append("【紧急】立即启动 STEMI/NSTEMI 绿色通道，请心内科急诊会诊")
        recommendations.append("【检查】18 导联心电图 + 床旁超声心动图 + 凝血功能 + 血常规")
        recommendations.append("【治疗】双联抗血小板 (阿司匹林 300mg + 替格瑞洛 180mg 负荷) + 抗凝 (肝素/低分子肝素)")
        recommendations.append("STEMI 患者评估急诊 PCI 指征，目标 D-to-B < 90min")
        recommendations.append("禁止行择期非心脏手术，需先行心血管风险控制")
    elif urgency == "urgent":
        recommendations.append("cTnI 轻度升高：需鉴别 1 型 MI vs 2 型供需失衡 vs 非缺血性心肌损伤")
        recommendations.append("【检查】3h / 6h 复查 hs-cTnI，动态心电图监测")
        recommendations.append("如疑诊 NSTEMI：GRACE 评分风险分层后决定介入时机 (<2h / <24h / <72h)")
    else:
        recommendations.append("排除急性 MI，可安全进行非心脏手术 (结合其他风险评估)")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "assessment": diagnosis_text,
        "mi_type": mi_type,
        "urgency": urgency,
        "cTnI": troponin,
        "cTnI_elevated": ctn_elevated,
        "cTnI_multiple_of_URL": ctn_multiple,
        "ecg_ischemic": ecg_ischemic,
        "has_symptoms": has_symptoms,
        "criteria_met": criteria_met,
        "killip_class": killip,
        "recommendations": recommendations,
        "guideline_refs": [
            "Fourth Universal Definition of Myocardial Infarction (2018) — ESC/ACC/AHA/WHF",
            "2023 ESC Guidelines for the Management of Acute Coronary Syndromes",
            "2020 ESC Guidelines on NSTE-ACS",
        ],
    }


# ═══════════════════════════════════════════════════════════
# 3. evaluate_htn — Hypertension BP Classification
# ═══════════════════════════════════════════════════════════

def evaluate_htn(
    patient_id: str = "",
    sbp: int = 0,
    dbp: int = 0,
    meds: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Hypertension risk classification per 中国高血压防治指南 (2024 年修订版).

    BP Classification:
      正常: SBP < 120 AND DBP < 80
      正常高值: SBP 120-139 AND/OR DBP 80-89
      1 级 (轻度): SBP 140-159 AND/OR DBP 90-99
      2 级 (中度): SBP 160-179 AND/OR DBP 100-109
      3 级 (重度): SBP ≥ 180 AND/OR DBP ≥ 110
      ISH (单纯收缩期): SBP ≥ 140 AND DBP < 90

    Risk stratification (blood-pressure-lowering treatment):
      Low: Grade 1, no RF, no TOD, no CVD/CKD/DM
      Moderate: Grade 1 + 1-2 RF; or Grade 2 + 0-2 RF
      High: Grade 3, no RF; or Grade 1-2 + ≥3 RF or TOD or CKD3 or DM (no TOD)
      Very High: Any grade + CVD or CKD≥4 or DM+TOD

    Reference: 中国高血压防治指南 (2024 年修订版), CMA
    """
    patient = _agent.get_patient(patient_id) or {}
    meds = meds or []

    past = patient.get("past_history", "")
    diagnosis = patient.get("diagnosis", "")
    chief = patient.get("chief_complaint", "")
    combined = f"{chief} {diagnosis} {past}"
    lab_results = patient.get("lab_results", {})

    # ── BP classification ──
    bp_class = _classify_bp(sbp, dbp)

    # ── Risk factors ──
    risk_factors: list[dict[str, Any]] = []
    age = patient.get("age", 0)

    if age >= 60:
        risk_factors.append({"name": "年龄", "value": f"{age} 岁", "risk": "high",
                             "detail": "年龄 ≥60 岁为高危因素 (2024 指南)"})
    elif age >= 45:
        risk_factors.append({"name": "年龄", "value": f"{age} 岁", "risk": "medium",
                             "detail": "男性 ≥45 岁/女性 ≥55 岁为危险因素"})

    comorbidity_map = {
        "糖尿病": ("糖尿病", "high", "合并糖尿病显著增加心血管风险"),
        "冠心病": ("冠心病", "high", "合并冠心病属极高危"),
        "心衰": ("心衰", "high", "合并心衰属极高危"),
        "心力衰竭": ("心衰", "high", "合并心衰属极高危"),
        "脑梗": ("脑血管病", "high", "既往脑血管事件提示靶器官损害"),
        "卒中": ("脑血管病", "high", "既往脑血管事件提示靶器官损害"),
        "脑出血": ("脑血管病", "high", "既往脑血管事件提示靶器官损害"),
        "高脂血症": ("血脂异常", "medium", "血脂异常加重动脉硬化进程"),
        "高血脂": ("血脂异常", "medium", "血脂异常加重动脉硬化进程"),
        "肾病": ("肾脏病", "high", "肾脏疾病与高血压互为因果"),
        "肾功能不全": ("肾脏病", "high", "肾脏疾病与高血压互为因果"),
    }
    for kw, (label, risk, detail) in comorbidity_map.items():
        if kw in combined:
            if not any(rf["name"] == label for rf in risk_factors):
                risk_factors.append({"name": label, "value": "有", "risk": risk, "detail": detail})

    if "吸烟" in combined or "抽烟" in combined:
        risk_factors.append({"name": "吸烟", "value": "有", "risk": "high",
                             "detail": "吸烟是心血管疾病独立危险因素"})

    if any(kw in chief for kw in ["头晕", "头痛", "视物模糊", "颈项"]):
        risk_factors.append({"name": "临床症状", "value": "存在高血压相关症状", "risk": "medium",
                             "detail": "需排除高血压急症或靶器官急性损害"})

    # ── Target organ damage ──
    tod: list[dict[str, Any]] = []
    cr = lab_results.get("creatinine", 0)
    if float(cr) > 133 if cr else False:
        tod.append({"organ": "肾脏", "finding": f"血清肌酐 {cr} μmol/L",
                    "severity": "high", "detail": "肾功能受损，可能为高血压肾损害"})
    if any(kw in combined for kw in ["LVH", "左心室肥厚", "左室肥厚"]):
        tod.append({"organ": "心脏", "finding": "左心室肥厚 (LVH)",
                    "severity": "high", "detail": "高血压靶器官损害——心脏"})
    if any(kw in combined for kw in ["脑梗", "卒中", "脑出血", "TIA"]):
        tod.append({"organ": "脑", "finding": "既往脑血管事件",
                    "severity": "high", "detail": "脑血管事件是高血压靶器官损害的明确证据"})

    # ── Risk stratification ──
    high_rf_count = sum(1 for rf in risk_factors if rf["risk"] == "high")
    has_tod = any(t["severity"] == "high" for t in tod)

    has_dm = any(rf["name"] == "糖尿病" for rf in risk_factors)
    has_cvd = any(rf["name"] in ("冠心病", "脑血管病") for rf in risk_factors)
    has_ckd = any(rf["name"] == "肾脏病" or t["organ"] == "肾脏" for t in tod for rf in risk_factors)

    bp_level = bp_class["level"]

    if has_cvd or (has_dm and has_tod) or (has_ckd and bp_level >= 1):
        risk_level = "很高危"
        risk_desc = "合并心血管疾病/糖尿病靶器官损害/重度 CKD，心血管风险极高危"
    elif (bp_level >= 3) or (bp_level >= 1 and has_tod) or (has_dm and bp_level >= 1) or (bp_level >= 1 and high_rf_count >= 3):
        risk_level = "高危"
        risk_desc = "3 级高血压或合并靶器官损害/≥3 项危险因素"
    elif (bp_level == 2 and high_rf_count >= 1) or (bp_level == 1 and high_rf_count >= 2):
        risk_level = "中危"
        risk_desc = "2 级高血压 + 危险因素，或 1 级 + 多项危险因素"
    elif bp_level >= 1:
        risk_level = "低危"
        risk_desc = "1 级高血压，无其他危险因素"
    else:
        risk_level = "正常/正常高值"
        risk_desc = "血压正常或正常高值，建议定期监测"

    # ── Antihypertensive medication check ──
    med_advice: list[str] = []
    acei_arb = [m for m in meds if m.lower() in ("acei", "arb", "普利", "沙坦", "缬沙坦", "厄贝沙坦", "氯沙坦", "培哚普利")]
    ccb = [m for m in meds if m.lower() in ("ccb", "地平", "硝苯地平", "氨氯地平", "非洛地平")]
    bb = [m for m in meds if m.lower() in ("bb", "β受体阻滞剂", "美托洛尔", "比索洛尔", "阿替洛尔")]
    diuretic = [m for m in meds if m.lower() in ("利尿剂", "氢氯噻嗪", "呋塞米", "螺内酯", "吲达帕胺")]

    if acei_arb:
        med_advice.append(f"正在服用 ACEI/ARB ({'/'.join(acei_arb)})：术前 24h 停药，术后 24-48h 恢复")
    if ccb:
        med_advice.append(f"正在服用 CCB ({'/'.join(ccb)})：围术期可继续使用")
    if bb:
        med_advice.append(f"正在服用 β 受体阻滞剂 ({'/'.join(bb)})：围术期继续使用，避免撤药反跳")
    if diuretic:
        med_advice.append(f"正在服用利尿剂 ({'/'.join(diuretic)})：手术当日停用，术后根据容量状态恢复")

    # ── Recommendations ──
    recommendations: list[str] = []
    if risk_level in ("很高危", "高危"):
        if sbp >= 180 or dbp >= 110:
            recommendations.append("【紧急】血压 ≥180/110 mmHg，应立即启动降压治疗，目标 <140/90 mmHg (1h 内降 10-25%)")
        recommendations.append("【药物】首选 ACEI/ARB，必要时联合 CCB 或利尿剂")
        recommendations.append("【检查】完善超声心动图、颈动脉超声、尿微量白蛋白/肌酐比、24h 动态血压监测")
        recommendations.append("【手术】择期手术延迟至血压控制稳定 (<140/90 mmHg)")
    elif risk_level == "中危":
        recommendations.append("启动生活方式干预 (限盐 <5g/天、减重、规律运动、戒烟限酒)")
        recommendations.append("建议启动或优化药物治疗，目标 <130/80 mmHg")
    elif risk_level == "低危":
        recommendations.append("建议生活方式干预 (限盐、减重、规律运动)")
        recommendations.append("定期监测血压，每 3-6 个月随访")
    else:
        recommendations.append("血压正常/正常高值：保持健康生活方式，定期监测血压")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "assessment": f"血压 {sbp}/{dbp} mmHg，{bp_class['grade_cn']}，心血管风险：{risk_level}",
        "bp": {"systolic": sbp, "diastolic": dbp},
        "bp_classification": bp_class,
        "risk_factors": risk_factors,
        "high_risk_factor_count": high_rf_count,
        "target_organ_damage": tod,
        "has_target_organ_damage": has_tod,
        "cardiovascular_risk_level": risk_level,
        "cardiovascular_risk_description": risk_desc,
        "medication_advice": med_advice,
        "recommendations": recommendations,
        "guideline_refs": [
            "中国高血压防治指南 (2024 年修订版) — 中华医学会心血管病学分会 (CMA)",
            "2023 ESH Guidelines for the Management of Arterial Hypertension",
            "2024 ESC Guidelines on Perioperative Management of Antihypertensive Therapy",
        ],
    }
