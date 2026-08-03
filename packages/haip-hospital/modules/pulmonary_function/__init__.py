"""PFT v2.0 — 肺功能智能评估: ATS/ERS 6模式判读 + GOLD ABE + 术前风险 + Z-score.

Guidelines: ATS/ERS 2022, GOLD 2025, 中国肺功能检查指南(2022), ACCP 围术期指南
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="pulmonary-function", department="呼吸科")
_GUIDELINES = [
    "GOLD 2025 COPD 全球策略",
    "ATS/ERS 2022 肺功能判读技术标准 (Z-score推荐)",
    "中国肺功能检查指南 (2022)",
    "ACCP 围术期肺功能评估指南",
    "ATS/ERS 2005 肺功能测定标准化 (LLN参考值)",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ Reference Value Calculations ═══════

def _predicted_fev1(age: int, height_cm: float, gender: str) -> float:
    """GLI-2012 参考值 (亚洲人群) — 简化版 FEV1 预测值."""
    if gender.upper() == "M":
        return round(0.0576 * height_cm - 0.026 * age - 4.34, 2)
    return round(0.0395 * height_cm - 0.025 * age - 2.60, 2)


def _predicted_fvc(age: int, height_cm: float, gender: str) -> float:
    """GLI-2012 FVC 预测值."""
    if gender.upper() == "M":
        return round(0.0756 * height_cm - 0.028 * age - 5.76, 2)
    return round(0.0498 * height_cm - 0.021 * age - 3.34, 2)


def _lln_fev1_fvc(age: int) -> float:
    """FEV1/FVC 正常值下限 (LLN, Lower Limit of Normal)."""
    if age < 25:
        return 0.80
    elif age < 40:
        return 0.78
    elif age < 55:
        return 0.75
    elif age < 70:
        return 0.72
    return 0.70


def _zscore_fev1(measured: float, predicted: float) -> float:
    """Z-score = (measured - predicted) / SD."""
    sd = predicted * 0.15  # 近似 SD ≈ 15% predicted
    return round((measured - predicted) / sd, 2) if sd > 0 else 0


def _lung_age(fev1_measured: float, height_cm: float, gender: str) -> int:
    """估算肺年龄 — 基于FEV1实测值与预测值反推."""
    if gender.upper() == "M":
        predicted_25yo = _predicted_fev1(25, height_cm, "M")
        decline_per_year = 0.028  # ~28mL/yr FEV1 decline
        if fev1_measured >= predicted_25yo:
            return 25
        age = int(25 + (predicted_25yo - fev1_measured) / decline_per_year)
        return min(age, 120)
    predicted_25yo = _predicted_fev1(25, height_cm, "F")
    decline_per_year = 0.021
    if fev1_measured >= predicted_25yo:
        return 25
    age = int(25 + (predicted_25yo - fev1_measured) / decline_per_year)
    return min(age, 120)


# ═══════ ATS/ERS 6 Pattern Classification ═══════

def _classify_ventilation(fev1: float, fvc: float, fev1_pred: float, fvc_pred: float,
                          dlco: float, tlc: float, tlc_pred: float, age: int) -> dict:
    """ATS/ERS 2022 通气功能障碍 6 种模式分类."""

    ratio = fev1 / fvc if fvc > 0 else 0
    fev1_pct = fev1 / fev1_pred * 100 if fev1_pred > 0 else 0
    fvc_pct = fvc / fvc_pred * 100 if fvc_pred > 0 else 0
    tlc_pct = tlc / tlc_pred * 100 if tlc_pred > 0 else 100
    lln = _lln_fev1_fvc(age)
    z_fev1 = _zscore_fev1(fev1, fev1_pred)
    z_fvc = _zscore_fev1(fvc, fvc_pred)

    pattern = ""
    severity = ""
    subtype = ""
    details = []

    # Pattern 1: Normal
    if ratio >= lln and fev1_pct >= 80 and fvc_pct >= 80:
        pattern = "正常通气功能"
        severity = "正常"
        details = ["FEV1/FVC在正常范围", "FEV1和FVC均在参考值≥80%"]

    # Pattern 2: Obstructive
    elif ratio < lln:
        pattern = "阻塞性通气功能障碍"
        if fev1_pct >= 80: severity = "轻度"
        elif fev1_pct >= 50: severity = "中度"
        elif fev1_pct >= 30: severity = "重度"
        else: severity = "极重度"

        # Subtype
        if dlco < 60 and dlco > 0:
            subtype = "伴弥散功能下降 (提示肺气肿/肺实质破坏)"
        elif fvc_pct < 80:
            subtype = "伴肺过度充气 (TLC↑/RV↑)"

        details = [
            f"FEV1/FVC={ratio:.2f} < LLN({lln:.2f})",
            f"FEV1={fev1_pct:.0f}%pred (Z-score={z_fev1})",
            f"FVC={fvc_pct:.0f}%pred (Z-score={z_fvc})",
            f"严重度: {severity} (以FEV1%pred分级)",
        ]

    # Pattern 3: Restrictive
    elif ratio >= lln and tlc_pct < 80:
        pattern = "限制性通气功能障碍"
        if tlc_pct >= 70: severity = "轻度"
        elif tlc_pct >= 60: severity = "中度"
        else: severity = "重度"

        details = [
            f"TLC={tlc_pct:.0f}%pred (限制性核心指标)",
            f"FEV1/FVC={ratio:.2f} (正常或增高)",
            f"FVC={fvc_pct:.0f}%pred (降低)",
        ]
        if dlco > 0 and dlco < 60:
            subtype = "伴弥散功能下降 (提示间质性肺病/ILD)"
        elif dlco > 0 and dlco >= 80:
            subtype = "弥散正常 (提示胸廓/神经肌肉/肥胖限制)"

    # Pattern 4: Mixed
    elif ratio < lln and tlc_pct < 80:
        pattern = "混合性通气功能障碍"
        severity = "中重度" if fev1_pct < 50 else "轻中度"
        details = [
            f"FEV1/FVC={ratio:.2f} + TLC={tlc_pct:.0f}%pred (双项异常)",
            "同时具有阻塞性+限制性特征",
        ]

    # Pattern 5: Small airway dysfunction (early disease)
    elif ratio >= lln and fev1_pct >= 80 and (fvc_pct < 80 or z_fvc < -1.64):
        pattern = "小气道功能障碍 (FEF25-75%↓)"
        severity = "早期病变"
        subtype = "FVC正常低值/轻度下降, 提示早期小气道病变"
        details = [
            "FEV1/FVC在正常范围 (≥LLN)",
            "FVC轻度下降 (可能为早期指标)",
            "建议FEF25-75%或Impulse Oscillometry (IOS) 进一步评估",
        ]

    # Pattern 6: Nonspecific pattern
    else:
        pattern = "非特异性通气功能异常"
        severity = "轻度"
        subtype = "单项指标轻度异常, 不符合阻塞/限制标准"
        details = ["建议复查肺功能 + 临床综合判断"]

    # DLCO interpretation (independent of ventilation pattern)
    dlco_interp = ""
    if dlco > 0:
        if dlco >= 80:
            dlco_interp = "弥散功能正常 (DLCO≥80%pred)"
        elif dlco >= 60:
            dlco_interp = "弥散功能轻度下降 (DLCO 60-79%pred)"
        elif dlco >= 40:
            dlco_interp = "弥散功能中度下降 (DLCO 40-59%pred)"
        else:
            dlco_interp = "弥散功能重度下降 (DLCO<40%pred)"

    return {
        "pattern": pattern, "severity": severity, "subtype": subtype,
        "fev1_fvc_ratio": round(ratio * 100, 1), "lln": round(lln * 100, 1),
        "fev1_pct": round(fev1_pct, 1), "fvc_pct": round(fvc_pct, 1),
        "tlc_pct": round(tlc_pct, 1) if tlc > 0 else None,
        "zscore_fev1": z_fev1, "zscore_fvc": z_fvc,
        "dlco_interpretation": dlco_interp, "details": details,
    }


# ═══════ Pre-operative Risk ═══════

def _preop_risk(fev1_pct: float, dlco_pct: float, vo2max: float | None,
                surgery_type: str) -> dict:
    """胸科手术前肺功能风险评估 (ACCP/BTS指南)."""
    risk = "低危"
    recommendations = []

    # Pneumonectomy threshold
    if "全肺切除" in surgery_type or "pneumonectomy" in surgery_type.lower():
        if fev1_pct < 80 or (dlco_pct > 0 and dlco_pct < 80):
            risk = "需进一步评估 (ppo-FEV1/ppo-DLCO)"
            recommendations.append("计算预计术后肺功能: ppo-FEV1 = FEV1 × (1 - 切除肺段/19)")
            if fev1_pct < 40:
                risk = "高危 — 全肺切除高风险"
                recommendations.append("建议CPET (心肺运动试验) + 多学科讨论")

    # Lobectomy threshold
    elif "肺叶切除" in surgery_type or "lobectomy" in surgery_type.lower():
        if fev1_pct < 60 or (dlco_pct > 0 and dlco_pct < 60):
            risk = "中危 — 需ppo-FEV1/ppo-DLCO评估"
            recommendations.append("ppo-FEV1>40%且ppo-DLCO>40% → 可耐受肺叶切除")
        if fev1_pct < 30:
            risk = "高危"
            recommendations.append("建议CPET + 6MWT + 多学科讨论")

    # General thoracic
    else:
        if fev1_pct < 40 or (dlco_pct > 0 and dlco_pct < 40):
            risk = "高危 — 围术期肺部并发症高风险"
            recommendations.append("术前肺康复训练 (I/E 呼吸锻炼) 2-4周")
            recommendations.append("术后: 早期下床 + 深呼吸/诱发性肺量计 + 镇痛优化")

    if vo2max is not None:
        if vo2max < 10:
            risk = "极高危 — VO2max<10 mL/kg/min (围术期死亡率极高)"
            recommendations.append("强烈建议非手术/微创替代方案")
        elif vo2max < 15:
            risk = "高危" if risk == "低危" else risk
            recommendations.append(f"VO2max={vo2max:.1f} — 心肺储备严重不足")

    return {"risk": risk, "recommendations": recommendations}


# ═══════ Handler Functions ═══════


def pft_interpret(patient_id: str = "",
                  FEV1: float = 0.0, FVC: float = 0.0,
                  FEV1_pred: float = 0.0, FVC_pred: float = 0.0,
                  DLCO: float = 0.0, TLC: float = 0.0,
                  TLC_pred: float = 0.0, age: int = 50,
                  height_cm: float = 170.0, gender: str = "M",
                  **kwargs: Any) -> dict:
    """肺功能综合判读 — ATS/ERS 6模式 + Z-score + 肺年龄."""
    p, err = _get_patient({"patient_id": patient_id})

    # Use patient data if available, else use explicit params
    if p:
        age = int(p.get("age", age) or age)
        height_cm = float(p.get("height_cm", height_cm) or height_cm)
        gender = str(p.get("gender", gender) or gender)
        labs = p.get("lab_results", {}) or {}
        if FEV1 <= 0:
            FEV1 = float(labs.get("FEV1", 0) or 0)
        if FVC <= 0:
            FVC = float(labs.get("FVC", 0) or 0)

    # Auto-calculate predictions if not provided
    if FEV1_pred <= 0:
        FEV1_pred = _predicted_fev1(age, height_cm, gender)
    if FVC_pred <= 0:
        FVC_pred = _predicted_fvc(age, height_cm, gender)
    if TLC_pred <= 0 and TLC > 0:
        TLC_pred = FVC_pred / 0.75

    # Classification
    result = _classify_ventilation(FEV1, FVC, FEV1_pred, FVC_pred, DLCO, TLC, TLC_pred, age)

    # Lung age
    lung_age = _lung_age(FEV1, height_cm, gender)

    # Bronchial challenge placeholder
    challenge_advice = ""
    if result["fev1_pct"] >= 80 and result["fev1_fvc_ratio"] >= result["lln"]:
        if kwargs.get("symptoms", ""):
            challenge_advice = "肺功能正常但有呼吸道症状 → 建议支气管激发试验(乙酰甲胆碱/组胺)排除哮喘"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "ventilation_pattern": result["pattern"],
        "severity": result["severity"],
        "subtype": result.get("subtype", ""),
        "fev1_fvc_ratio_pct": result["fev1_fvc_ratio"],
        "lln_pct": result["lln"],
        "fev1_pct": result["fev1_pct"],
        "fvc_pct": result["fvc_pct"],
        "tlc_pct": result["tlc_pct"],
        "dlco_interpretation": result["dlco_interpretation"],
        "zscore_fev1": result["zscore_fev1"],
        "zscore_fvc": result["zscore_fvc"],
        "lung_age": lung_age,
        "lung_age_gap": lung_age - age,
        "details": result["details"],
        "bronchial_challenge_advice": challenge_advice,
        "summary": f"肺功能 — {result['pattern']} ({result['severity']}) | 肺年龄={lung_age}岁",
        "guideline_ref": "ATS/ERS 2022 (Z-score推荐) + GLI-2012 参考值",
    }


def gold_staging(patient_id: str = "", fev1_percent: float = 80.0,
                 exacerbations: int = 0, CAT_score: int = 10,
                 mMRC: int = 1, eosinophil_count: float = 0.0,
                 **kwargs: Any) -> dict:
    """GOLD 2025 COPD 综合评估 — 分级+ABE分组+个体化治疗."""
    p, err = _get_patient({"patient_id": patient_id})

    # GOLD stage (1-4) by FEV1%pred
    if fev1_percent >= 80:
        stage = "GOLD 1 (轻度)"
        stage_num = 1
    elif fev1_percent >= 50:
        stage = "GOLD 2 (中度)"
        stage_num = 2
    elif fev1_percent >= 30:
        stage = "GOLD 3 (重度)"
        stage_num = 3
    else:
        stage = "GOLD 4 (极重度)"
        stage_num = 4

    # GOLD 2025 ABE grouping
    if exacerbations >= 2 or (exacerbations >= 1 and "住院" in str(kwargs.get("exac_severity", ""))):
        group = "E"
        group_desc = "频繁急性加重 (≥2次/年 或 ≥1次住院)"
    elif mMRC <= 1 and CAT_score < 10 and exacerbations <= 1:
        group = "A"
        group_desc = "少症状 + 低急性加重风险"
    else:
        group = "B"
        group_desc = "多症状 (mMRC≥2 或 CAT≥10) + 低急性加重风险"

    # Treatment recommendation (GOLD 2025)
    treatment = []
    if group == "A":
        treatment = ["SABA 或 SAMA 按需 (短效支气管舒张剂)", "若持续症状 → LAMA 或 LABA"]
    elif group == "B":
        treatment = ["LAMA + LABA (双支气管舒张剂)"]
        if eosinophil_count >= 300:
            treatment.append("考虑 LABA+LAMA+ICS (血EOS≥300/μL)")
    elif group == "E":
        treatment = ["LABA+LAMA (双支气管舒张剂)"]
        if eosinophil_count >= 300:
            treatment.append("强烈考虑 LABA+LAMA+ICS 三联疗法 (血EOS≥300/μL)")
        if eosinophil_count >= 100:
            treatment.append("可考虑 LABA+LAMA+ICS (血EOS≥100/μL)")
        treatment.append("肺康复训练 + 戒烟 + 疫苗接种(流感/肺炎)")

    # Non-pharmacological
    non_pharm = [
        "戒烟 (最重要干预!)",
        "年度流感疫苗 + 肺炎球菌疫苗",
        "规律运动/肺康复训练 (每周≥3次, 30-60min)",
        "长程氧疗 (LTOT) — 若PaO2≤55mmHg 或 SpO2≤88%",
    ]
    if stage_num >= 3:
        non_pharm.append("无创通气(NIV)评估 — 若PaCO2≥52mmHg")
    if stage_num >= 4:
        non_pharm.insert(0, "肺减容术(LVRS)/肺移植评估 — 终末期COPD")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "gold_stage": stage,
        "gold_stage_num": stage_num,
        "abg_group": group,
        "group_description": group_desc,
        "fev1_percent": fev1_percent,
        "exacerbations_per_year": exacerbations,
        "cat_score": CAT_score,
        "mMRC": mMRC,
        "eosinophil_count": eosinophil_count,
        "pharmacological_treatment": treatment,
        "non_pharmacological": non_pharm,
        "summary": f"{stage}, Group {group} | {group_desc}",
        "guideline_ref": "GOLD 2025 — Global Strategy for COPD",
    }


def bronchodilator_test(patient_id: str = "", pre_FEV1: float = 0.0,
                        post_FEV1: float = 0.0, pre_FVC: float = 0.0,
                        post_FVC: float = 0.0, bronchodilator: str = "沙丁胺醇 400μg",
                        **kwargs: Any) -> dict:
    """支气管舒张试验判读 + 支气管激发试验解读."""
    p, err = _get_patient({"patient_id": patient_id})

    # Bronchodilator reversibility (BDR)
    delta_fev1 = post_FEV1 - pre_FEV1
    delta_fev1_pct = delta_fev1 / pre_FEV1 * 100 if pre_FEV1 > 0 else 0
    delta_fev1_ml = delta_fev1 * 1000
    bdr_positive = delta_fev1_pct >= 12 and delta_fev1_ml >= 200

    # FVC reversibility
    delta_fvc = post_FVC - pre_FVC if pre_FVC > 0 else 0
    delta_fvc_pct = delta_fvc / pre_FVC * 100 if pre_FVC > 0 else 0
    delta_fvc_ml = delta_fvc * 1000

    # Interpretation
    if bdr_positive:
        if delta_fev1_pct >= 20:
            interp = "显著阳性 — 高度提示哮喘 (可逆性气流受限)"
        else:
            interp = "阳性 — 存在可逆性气流受限 (哮喘/ACO)"
    elif delta_fvc_ml >= 200 and delta_fvc_pct >= 12:
        interp = "FVC改善阳性 (FEV1不满足) — 提示肺容积改善, 可能为COPD"
    else:
        interp = "阴性 — 无明显可逆性气流受限 (不排除哮喘: 炎症控制后/间歇期可阴性)"

    # Bronchial challenge interpretation (if provided)
    challenge_info = {}
    if "pc20" in kwargs:
        pc20 = float(kwargs.get("pc20", 16) or 16)
        if pc20 < 1:
            challenge_info = {"pc20": pc20, "result": "重度气道高反应性 (PC20<1 mg/mL)"}
        elif pc20 < 4:
            challenge_info = {"pc20": pc20, "result": "中度气道高反应性 (PC20 1-4 mg/mL)"}
        elif pc20 < 16:
            challenge_info = {"pc20": pc20, "result": "轻度气道高反应性 (PC20 4-16 mg/mL)"}
        else:
            challenge_info = {"pc20": pc20, "result": "正常 — 基本排除哮喘 (PC20≥16 mg/mL)"}

    return {
        "status": "ok",
        "patient_id": patient_id,
        "bronchodilator": bronchodilator,
        "bdr_positive": bdr_positive,
        "fev1_change_ml": round(delta_fev1_ml, 0),
        "fev1_change_pct": round(delta_fev1_pct, 1),
        "fvc_change_ml": round(delta_fvc_ml, 0) if pre_FVC > 0 else None,
        "fvc_change_pct": round(delta_fvc_pct, 1) if pre_FVC > 0 else None,
        "interpretation": interp,
        "challenge_test": challenge_info,
        "summary": f"舒张试验 {'阳性' if bdr_positive else '阴性'} (ΔFEV1={delta_fev1_ml:.0f}mL, {delta_fev1_pct:.0f}%) | {interp}",
        "guideline_ref": "ATS/ERS 2005 BDR标准 (FEV1改善≥12%+≥200mL)",
    }


def preop_assessment(patient_id: str = "", surgery_type: str = "",
                     FEV1: float = 0.0, FEV1_pred: float = 0.0,
                     DLCO: float = 0.0, VO2max: float | None = None,
                     walk_distance_6mwt: float = 0.0,
                     **kwargs: Any) -> dict:
    """术前肺功能风险评估 — ACCP/BTS 胸科手术分层."""
    p, err = _get_patient({"patient_id": patient_id})

    if FEV1_pred <= 0:
        FEV1_pred = _predicted_fev1(50, 170, "M")  # default
    fev1_pct = FEV1 / FEV1_pred * 100 if FEV1_pred > 0 else 0
    dlco_pct = DLCO  # Assume DLCO is already %pred

    risk = _preop_risk(fev1_pct, dlco_pct, VO2max, surgery_type)

    # 6MWT assessment
    walk_assessment = ""
    if walk_distance_6mwt > 0:
        if walk_distance_6mwt < 300:
            walk_assessment = f"6MWT={walk_distance_6mwt:.0f}m — 严重受限 (<300m, 高风险)"
        elif walk_distance_6mwt < 400:
            walk_assessment = f"6MWT={walk_distance_6mwt:.0f}m — 中度受限"
        else:
            walk_assessment = f"6MWT={walk_distance_6mwt:.0f}m — 正常 (>400m)"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "surgery_type": surgery_type,
        "preop_fev1_pct": round(fev1_pct, 1),
        "preop_dlco_pct": round(dlco_pct, 1) if dlco_pct > 0 else None,
        "vo2max": VO2max,
        "walk_6mwt": walk_assessment if walk_distance_6mwt > 0 else None,
        "risk_level": risk["risk"],
        "recommendations": risk["recommendations"],
        "summary": f"术前评估 — {surgery_type} | {risk['risk']}",
        "guideline_ref": "ACCP 围术期肺功能评估指南 + BTS 胸科手术指南",
    }
