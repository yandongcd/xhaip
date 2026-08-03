"""Timing engine — T2 hierarchical decision for surgical timing.

Port from haip-0705-2 v0.2.0. Pure Python with 8 delay factors + T2 layered arbitration.
"""

from __future__ import annotations

# T2 因子名 → 中文名映射
_T2_FACTOR_NAMES: dict[str, str] = {
    "cardiac": "心脏因素", "pulmonary": "肺部因素", "cerebral": "脑血管因素",
    "anticoagulation": "抗凝因素", "anemia": "贫血因素",
    "renal": "肾功能因素", "infection": "感染因素", "glucose": "血糖因素",
}

# T2 权重分层
_T2_HIGH_WEIGHT = {"cardiac", "pulmonary", "cerebral"}
_T2_MEDIUM_WEIGHT = {"anticoagulation", "anemia", "renal", "infection", "glucose"}

# 默认延迟因素配置
DEFAULT_DELAY_FACTORS = [
    {"id": "cardiac", "name": "心脏因素", "risk_when_triggered": "high",
     "optimization": "心内科会诊", "evaluation_logic": "",
     "threshold_values": {"cTnI": {"high": 0.04}, "cTnT": {"high": 0.1}, "CKMB": {"high": 25}},
     "ecg_high_risk_patterns": ["ST段抬高", "ST段压低", "室性心动过速", "心室颤动", "三度房室传导阻滞"],
     "diagnosis_keywords": ["急性冠脉综合征", "ACS", "心肌梗死", "心梗", "不稳定性心绞痛"]},
    {"id": "pulmonary", "name": "肺部因素", "risk_when_triggered": "high",
     "optimization": "呼吸科会诊+肺功能优化", "evaluation_logic": "",
     "high_risk_keywords": ["急性肺炎", "重症肺炎", "肺栓塞", "肺梗塞", "肺梗死",
                           "哮喘急性发作", "呼吸衰竭", "呼衰", "copd急性加重"],
     "medium_risk_keywords": ["肺炎", "肺部感染", "哮喘", "copd", "慢性阻塞性", "胸腔积液"]},
    {"id": "cerebral", "name": "脑血管因素", "risk_when_triggered": "high",
     "optimization": "神经内科会诊", "evaluation_logic": "",
     "acute_keywords": ["急性脑梗", "脑梗死", "脑梗塞", "脑卒中", "脑出血",
                        "cva", "stroke", "tia", "短暂性脑缺血", "脑梗", "脑血管意外"],
     "history_keywords": ["脑梗病史", "脑梗后", "脑卒中后", "脑梗死后遗症", "脑血管病"]},
    {"id": "anticoagulation", "name": "抗凝因素", "risk_when_triggered": "medium",
     "optimization": "评估停药时间+桥接", "evaluation_logic": "",
     "threshold_values": {"INR": {"high": 1.5}, "PT": {"high": 14}},
     "drug_keywords": ["华法林", "warfarin", "利伐沙班", "达比加群", "阿哌沙班", "NOAC",
                       "氯吡格雷", "替格瑞洛", "阿司匹林"]},
    {"id": "anemia", "name": "贫血因素", "risk_when_triggered": "medium",
     "optimization": "纠正贫血", "evaluation_logic": ""},
    {"id": "renal", "name": "肾功能因素", "risk_when_triggered": "medium",
     "optimization": "肾内科会诊", "evaluation_logic": "",
     "threshold_values": {"eGFR": {"low": 30, "warning": 60}, "creatinine": {"high": 133}}},
    {"id": "infection", "name": "感染因素", "risk_when_triggered": "medium",
     "optimization": "抗感染治疗", "evaluation_logic": "",
     "threshold_values": {"WBC": {"high": 12}, "CRP": {"high": 100}, "NEUT": {"high": 8}},
     "diagnosis_keywords": ["感染", "肺炎", "泌尿系感染", "伤口感染"]},
    {"id": "glucose", "name": "血糖因素", "risk_when_triggered": "medium",
     "optimization": "胰岛素调整", "evaluation_logic": "",
     "threshold_values": {"glucose": {"high": 13.9}, "hba1c": {"high": 9.0}},
     "diagnosis_keywords": ["DKA", "糖尿病酮症酸中毒", "高渗高血糖状态", "HHS"]},
]


def _build_lab_map(patient: dict) -> dict[str, dict]:
    lab_map: dict[str, dict] = {}
    for t in patient.get("lab_tests", []):
        name = t.get("name", "")
        if name:
            lab_map[name] = t
    return lab_map


def _get_lab_value(lab_map: dict[str, dict], names: list[str]) -> float | None:
    for n in names:
        t = lab_map.get(n)
        if t:
            val = t.get("value")
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
    return None


def _has_text_keyword(patient: dict, keywords: list[str], fields: list[str] | None = None) -> bool:
    if fields is None:
        fields = ["diagnosis", "chief_complaint", "present_illness"]
    texts = [(patient.get(f, "") or "") for f in fields]
    combined = " ".join(texts).lower()
    for kw in keywords:
        if kw.lower() in combined:
            return True
    return False


def _has_med_keyword(patient: dict, keywords: list[str]) -> bool:
    texts = [
        patient.get("past_history", "") or "",
        patient.get("medications", "") or "",
    ]
    combined = " ".join(texts).lower()
    for kw in keywords:
        if kw.lower() in combined:
            return True
    return False


def _eval_cardiac(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    evidence_parts: list[str] = []
    triggered = False

    threshold = factor_cfg.get("threshold_values", {})
    ctnI = _get_lab_value(lab_map, ["肌钙蛋白I", "肌钙蛋白", "cTnI", "hs-cTnI"])
    ctnT = _get_lab_value(lab_map, ["肌钙蛋白T", "cTnT", "hs-cTnT"])
    ctnI_thresh = threshold.get("cTnI", {}).get("high", 0.04)
    ctnT_thresh = threshold.get("cTnT", {}).get("high", 0.1)

    if ctnI is not None and ctnI > ctnI_thresh:
        evidence_parts.append(f"cTnI={ctnI}ng/mL (↑)")
        triggered = True
    if ctnT is not None and ctnT > ctnT_thresh:
        evidence_parts.append(f"cTnT={ctnT}ng/mL (↑)")
        triggered = True

    ckmb = _get_lab_value(lab_map, ["心型肌酸激酶", "CK-MB", "CKMB"])
    ckmb_thresh = threshold.get("CKMB", {}).get("high", 25)
    if ckmb is not None and ckmb > ckmb_thresh:
        evidence_parts.append(f"CK-MB={ckmb}U/L (↑)")
        triggered = True

    try:
        from .ecg_analyzer import extract_ecg_keywords_from_exam
        ecg_findings = extract_ecg_keywords_from_exam(patient)
        high_risk_patterns = factor_cfg.get("ecg_high_risk_patterns", [])
        for finding in ecg_findings:
            label = finding.get("label", "")
            if any(p.lower() in label.lower() for p in high_risk_patterns):
                evidence_parts.append(f"ECG: {label}")
                triggered = True
    except ImportError:
        pass

    dx_keywords = factor_cfg.get("diagnosis_keywords", [])
    if _has_text_keyword(patient, dx_keywords):
        evidence_parts.append("诊断包含急性冠脉综合征关键词")
        triggered = True

    risk = "high" if triggered else "none"
    optimization = factor_cfg.get("optimization", "心内科会诊") if triggered else ""
    return {"triggered": triggered, "evidence": "; ".join(evidence_parts), "risk": risk, "optimization": optimization}


def _eval_pulmonary(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    triggered = False
    evidence_parts: list[str] = []

    past = (patient.get("past_history", "") or "").lower()
    diagnosis = (patient.get("diagnosis", "") or "").lower()
    present = (patient.get("present_illness", "") or "").lower()
    combined = f"{past} {diagnosis} {present}"

    high_risk_kw = factor_cfg.get("high_risk_keywords", [])
    medium_kw = factor_cfg.get("medium_risk_keywords", [])

    for kw in high_risk_kw:
        if kw.lower() in combined:
            evidence_parts.append(f"高危: {kw}")
            triggered = True
            break

    if not triggered:
        for kw in medium_kw:
            if kw.lower() in combined:
                evidence_parts.append(f"中危: {kw}")
                triggered = True

    risk = "high" if triggered and evidence_parts and "高危" in evidence_parts[0] else \
           "medium" if triggered else "none"
    optimization = "呼吸科会诊+肺功能优化+抗感染" if triggered else ""
    return {"triggered": triggered, "evidence": "; ".join(evidence_parts), "risk": risk, "optimization": optimization}


def _eval_cerebral(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    triggered = False
    evidence_parts: list[str] = []

    past = (patient.get("past_history", "") or "").lower()
    diagnosis = (patient.get("diagnosis", "") or "").lower()
    present = (patient.get("present_illness", "") or "").lower()
    combined = f"{past} {diagnosis} {present}"

    acute_kw = factor_cfg.get("acute_keywords", [])
    history_kw = factor_cfg.get("history_keywords", [])

    for kw in acute_kw:
        if kw.lower() in combined:
            evidence_parts.append(f"急性脑血管事件: {kw}")
            triggered = True
            break

    if not triggered:
        for kw in history_kw:
            if kw.lower() in combined:
                evidence_parts.append(f"脑血管病史: {kw}")
                triggered = True

    risk = "high" if triggered else "none"
    optimization = "神经内科会诊+头颅CT/MRI+抗血小板评估" if triggered else ""
    return {"triggered": triggered, "evidence": "; ".join(evidence_parts), "risk": risk, "optimization": optimization}


def _eval_anticoagulation(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    evidence_parts: list[str] = []
    triggered = False

    threshold = factor_cfg.get("threshold_values", {})
    drug_keywords = factor_cfg.get("drug_keywords", [])
    inr = _get_lab_value(lab_map, ["凝血酶原时间国际标准化比值", "INR", "PT-INR"])
    pt = _get_lab_value(lab_map, ["凝血酶原时间", "PT"])

    has_anticoag = _has_med_keyword(patient, drug_keywords)

    if has_anticoag:
        if _has_med_keyword(patient, ["华法林", "warfarin"]):
            inr_thresh = threshold.get("INR", {}).get("high", 1.5)
            if inr is not None and inr > inr_thresh:
                evidence_parts.append(f"华法林 + INR={inr} (>{inr_thresh})")
            else:
                evidence_parts.append("使用华法林")
            triggered = True
        elif _has_med_keyword(patient, ["利伐沙班", "达比加群", "阿哌沙班", "NOAC"]):
            evidence_parts.append("使用NOAC，需确认停药时间")
            triggered = True
        elif _has_med_keyword(patient, ["氯吡格雷", "替格瑞洛"]):
            evidence_parts.append("使用抗血小板药物")
            triggered = True
        if pt is not None and not triggered:
            pt_thresh = threshold.get("PT", {}).get("high", 14)
            if pt > pt_thresh:
                evidence_parts.append(f"PT={pt}sec (↑)")
                triggered = True

    risk = "high" if triggered else "none"
    optimization = factor_cfg.get("optimization", "评估停药时间+桥接方案") if triggered else ""
    return {"triggered": triggered, "evidence": "; ".join(evidence_parts), "risk": risk, "optimization": optimization}


def _eval_anemia(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    evidence_parts: list[str] = []
    triggered = False

    hb = _get_lab_value(lab_map, ["血红蛋白测定", "血红蛋白", "Hb", "Hgb"])
    if hb is not None:
        if hb < 80:
            evidence_parts.append(f"Hb={hb}g/L (重度贫血)")
            triggered = True
        elif hb < 100:
            past = (patient.get("past_history", "") or "").lower()
            if any(kw in past for kw in ["冠心病", "心衰", "心力衰竭", "冠状动脉"]):
                evidence_parts.append(f"Hb={hb}g/L (<100, 合并心脏病)")
                triggered = True
            else:
                evidence_parts.append(f"Hb={hb}g/L (轻度贫血)")
        else:
            evidence_parts.append(f"Hb={hb}g/L (正常)")

    risk = "high" if triggered else ("medium" if hb is not None and hb < 100 else "none")
    optimization = factor_cfg.get("optimization", "输注红细胞至Hb≥80g/L") if triggered else ""
    return {"triggered": triggered, "evidence": "; ".join(evidence_parts), "risk": risk, "optimization": optimization}


def _eval_renal(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    evidence_parts: list[str] = []
    triggered = False

    threshold = factor_cfg.get("threshold_values", {})
    egfr = _get_lab_value(lab_map, ["肾小球滤过率", "eGFR", "估算肾小球滤过率"])
    cr = _get_lab_value(lab_map, ["肌酐", "Cr", "血肌酐"])

    if egfr is not None:
        severe_thresh = threshold.get("eGFR", {}).get("low", 30)
        warning_thresh = threshold.get("eGFR", {}).get("warning", 60)
        if egfr < severe_thresh:
            evidence_parts.append(f"eGFR={egfr}mL/min (严重)")
            triggered = True
        elif egfr < warning_thresh:
            evidence_parts.append(f"eGFR={egfr}mL/min (中度减退)")
            triggered = True
        else:
            evidence_parts.append(f"eGFR={egfr}mL/min (正常)")
    elif cr is not None:
        cr_thresh = threshold.get("creatinine", {}).get("high", 133)
        if cr > cr_thresh:
            evidence_parts.append(f"Cr={cr}μmol/L (↑)")
            triggered = True

    risk = "high" if triggered else "none"
    optimization = factor_cfg.get("optimization", "肾内科会诊+避免肾毒性药物") if triggered else ""
    return {"triggered": triggered, "evidence": "; ".join(evidence_parts), "risk": risk, "optimization": optimization}


def _eval_infection(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    evidence_parts: list[str] = []
    triggered = False

    threshold = factor_cfg.get("threshold_values", {})
    wbc = _get_lab_value(lab_map, ["白细胞计数", "WBC", "白细胞"])
    crp = _get_lab_value(lab_map, ["C反应蛋白", "CRP", "超敏C反应蛋白"])
    neut = _get_lab_value(lab_map, ["中性粒细胞计数", "NEUT", "中性粒细胞绝对值"])

    wbc_thresh = threshold.get("WBC", {}).get("high", 12)
    crp_thresh = threshold.get("CRP", {}).get("high", 100)
    neut_thresh = threshold.get("NEUT", {}).get("high", 8)

    if wbc is not None and wbc > wbc_thresh:
        evidence_parts.append(f"WBC={wbc}×10⁹/L (↑)")
        triggered = True
    if crp is not None and crp > crp_thresh:
        evidence_parts.append(f"CRP={crp}mg/L (↑)")
        triggered = True
    if neut is not None and neut > neut_thresh:
        evidence_parts.append(f"NEUT={neut}×10⁹/L (↑)")
        triggered = True

    dx_keywords = factor_cfg.get("diagnosis_keywords", [])
    if _has_text_keyword(patient, dx_keywords):
        evidence_parts.append("诊断含有感染")
        triggered = True

    risk = "high" if (crp is not None and crp > 200) or (wbc is not None and wbc > 20) else \
           "medium" if triggered else "none"
    optimization = factor_cfg.get("optimization", "抗感染治疗+复查炎症指标至正常") if triggered else ""
    return {"triggered": triggered, "evidence": "; ".join(evidence_parts), "risk": risk, "optimization": optimization}


def _eval_glucose(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    evidence_parts: list[str] = []
    triggered = False

    threshold = factor_cfg.get("threshold_values", {})
    glucose = _get_lab_value(lab_map, ["葡萄糖", "血糖", "Glu"])
    hba1c = _get_lab_value(lab_map, ["糖化血红蛋白", "HbA1c", "糖化血红蛋白A1c"])

    glucose_thresh = threshold.get("glucose", {}).get("high", 13.9)

    if glucose is not None:
        if glucose > glucose_thresh:
            evidence_parts.append(f"血糖={glucose}mmol/L (↑)")
            triggered = True
        else:
            evidence_parts.append(f"血糖={glucose}mmol/L (正常)")
    else:
        evidence_parts.append("无血糖数据")

    dx_keywords = factor_cfg.get("diagnosis_keywords", [])
    if _has_text_keyword(patient, dx_keywords):
        evidence_parts.append("诊断含DKA/HHS关键词")
        triggered = True

    if hba1c is not None:
        hba1c_thresh = threshold.get("hba1c", {}).get("high", 9.0)
        if hba1c > hba1c_thresh:
            evidence_parts.append(f"HbA1c={hba1c}% (控制不佳)")
        else:
            evidence_parts.append(f"HbA1c={hba1c}%")

    risk = "high" if triggered and (glucose is not None and glucose > 22.0) else \
           "medium" if triggered else "none"
    optimization = factor_cfg.get("optimization", "胰岛素方案调整+血糖控制") if triggered else ""
    return {"triggered": triggered, "evidence": "; ".join(evidence_parts), "risk": risk, "optimization": optimization}


_EVALUATORS = {
    "cardiac": _eval_cardiac,
    "pulmonary": _eval_pulmonary,
    "cerebral": _eval_cerebral,
    "anticoagulation": _eval_anticoagulation,
    "anemia": _eval_anemia,
    "renal": _eval_renal,
    "infection": _eval_infection,
    "glucose": _eval_glucose,
}


def _apply_t2_hierarchical_decision(results: dict[str, dict]) -> tuple[int, int, str, str, str]:
    high_count = 0
    medium_count = 0
    for fid, r in results.items():
        if not r.get("triggered"):
            continue
        if fid in _T2_HIGH_WEIGHT:
            high_count += 1
        elif fid in _T2_MEDIUM_WEIGHT:
            medium_count += 1

    if high_count >= 1:
        return (high_count, medium_count,
                f"高权重延迟因素 {high_count} 项触发 → 先纠正可逆因素，择期延迟手术",
                "elective", "timing-rule-t2-001")
    if medium_count >= 1:
        return (high_count, medium_count,
                f"无高权重延迟因素，{medium_count} 项中权重因素可控，积极优化后 3-7 天限期手术",
                "urgent", "timing-rule-t2-002")
    return (high_count, medium_count,
            "无延迟因素，48 小时内急诊手术",
            "emergency", "timing-rule-t2-003")


def evaluate_timing(patient: dict, delay_factors: list[dict] | None = None) -> dict:
    """Evaluate surgical timing (v2 fallback) — T2 分层裁决.

    Args:
        patient: Patient data dict with lab_tests, diagnosis, past_history, examinations, medications.
        delay_factors: Optional custom delay factors. Uses DEFAULT_DELAY_FACTORS if not provided.

    Returns:
        {patient_id, delay_factors, delay_factor_count, high_weight_count,
         medium_weight_count, timing_rule_applied, timing_conclusion, urgency,
         action, recommendations, engine_version}
    """
    patient_id = patient.get("patient_id", "") or patient.get("mrn", "")
    factors = delay_factors or DEFAULT_DELAY_FACTORS
    lab_map = _build_lab_map(patient)

    results: dict[str, dict] = {}
    for factor in factors:
        fid = factor["id"]
        evaluator = _EVALUATORS.get(fid)
        if evaluator:
            results[fid] = evaluator(patient, factor, lab_map)
        else:
            results[fid] = {"triggered": False, "evidence": "", "risk": "unknown", "optimization": ""}

    high_count, medium_count, conclusion, urgency, rule_id = _apply_t2_hierarchical_decision(results)
    total_delay = high_count + medium_count

    recs: list[str] = []
    for fid, result in results.items():
        if result.get("triggered") and result.get("optimization"):
            fname = _T2_FACTOR_NAMES.get(fid, fid)
            weight_tag = "高" if fid in _T2_HIGH_WEIGHT else "中"
            recs.append(f"[{weight_tag}] {fname}: {result['optimization']}")
            if result.get("evidence"):
                recs.append(f"  依据: {result['evidence'][:80]}")

    if high_count >= 1:
        recs.append(f">> 高权重 {high_count} 项触发 → 直接 MDT 多学科会诊，延迟手术")
    elif medium_count >= 1:
        recs.append(f">> 中权重 {medium_count} 项可控 → 积极优化后 3-7 天限期手术")
        recs.append(">> 每 24h 重新评估优化进展")
    else:
        recs.append(">> 无延迟因素 → 48 小时内急诊手术")

    return {
        "patient_id": patient_id,
        "delay_factors": results,
        "delay_factor_count": total_delay,
        "high_weight_count": high_count,
        "medium_weight_count": medium_count,
        "timing_rule_applied": rule_id,
        "timing_conclusion": conclusion,
        "urgency": urgency,
        "action": conclusion,
        "recommendations": recs,
        "guideline_refs": [],
        "engine_version": "2.0",
    }
