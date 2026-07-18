# @origin: haip-0710/src/agents/domains/haip/orthopedic_surgery/core/timing_engine.py
# @origin_repo: https://github.com/yandongcd/haip
# @ported_date: 2026-07-12
# @status: REFERENCE — requires import adaptation for xhaip engine
#   Key deps to adapt:
#     agents.domains.haip.core.* -> packages/haip-hospital/modules/shared/
#     agents.harness.* -> packages/haip-core/haip/
#     Rule path resolution -> packages/haip-hospital/knowledge/rules/
"""可执行手术时机规则引擎 — T2 分层裁决 (创伤骨科).

核心入口:
    evaluate_timing(patient_dict) -> dict (TimingDecision 结构)

T2 分层裁决（创伤骨科临床经验）:
    高权重 >= 1 → 直接 MDT 延迟
    高 = 0 且 中 >= 1 → 限期 (3-7天)
    高 = 0 且 中 = 0 → 48h 内急诊
"""

from __future__ import annotations

from pathlib import Path

from agents.domains.haip.core.ecg_analyzer import extract_ecg_keywords_from_exam

# ─── 规则文件路径（旧格式兼容）───
_RULES_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent / "assets" / "rules" / "timing_rules.yaml"

# ─── 缓存 ───
_RULES_CACHE: dict | None = None
_RULE_SERVICE_AVAILABLE: bool | None = None

# T2_OVERRIDE: 创伤骨科 T2 分层权重 | T1来源: NICE NG37/NHC 2022 | 场景: 手术时机评估
# 高权重因子：任一触发 → 直接 MDT 延迟手术
_T2_HIGH_WEIGHT = {"cardiac", "pulmonary", "cerebral"}
# 中权重因子：仅在高权重全为 0 时纳入计数
_T2_MEDIUM_WEIGHT = {"anticoagulation", "anemia", "renal", "infection", "glucose"}

# T2 因子名→中文名映射
_T2_FACTOR_NAMES: dict[str, str] = {
    "cardiac": "心脏因素", "pulmonary": "肺部因素", "cerebral": "脑血管因素",
    "anticoagulation": "抗凝因素", "anemia": "贫血因素",
    "renal": "肾功能因素", "infection": "感染因素", "glucose": "血糖因素",
}


def _build_evaluation_context(patient: dict) -> dict:
    """从患者数据构建规则引擎评估上下文."""
    lab_map: dict[str, dict] = {}
    for t in patient.get("lab_tests", []):
        name = t.get("name", "")
        if name:
            lab_map[name] = t

    def lv(names: list[str]) -> float | None:
        for n in names:
            t = lab_map.get(n)
            if t:
                v = t.get("value")
                if v is not None:
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        pass
        return None

    exams = patient.get("examinations", [])
    ecg_text = " ".join([e.get("description", "") for e in exams if "心电" in e.get("name", "")])

    ctx = {
        "troponin_I": lv(["肌钙蛋白I", "肌钙蛋白", "cTnI", "hs-cTnI"]) or 0,
        "troponin_T": lv(["肌钙蛋白T", "cTnT", "hs-cTnT"]) or 0,
        "ckmb": lv(["心型肌酸激酶", "CK-MB", "CKMB"]) or 0,
        "INR": lv(["凝血酶原时间国际标准化比值", "INR", "PT-INR"]) or 0,
        "hemoglobin": lv(["血红蛋白测定", "血红蛋白", "Hb", "Hgb"]) or 0,
        "eGFR": lv(["肾小球滤过率", "eGFR", "估算肾小球滤过率"]) or 0,
        "creatinine": lv(["肌酐", "Cr", "血肌酐"]) or 0,
        "WBC": lv(["白细胞计数", "WBC", "白细胞"]) or 0,
        "CRP": lv(["C反应蛋白", "CRP", "超敏C反应蛋白"]) or 0,
        "glucose": lv(["葡萄糖", "血糖", "Glu"]) or 0,
        "ecg_text": ecg_text,
        "diagnosis": patient.get("diagnosis", ""),
        "past_history": patient.get("past_history", ""),
        "medications": patient.get("medications", ""),
        "present_illness": patient.get("present_illness", ""),
        "chief_complaint": patient.get("chief_complaint", ""),
    }
    return ctx


def _rule_service_available() -> bool:
    try:
        from importlib.util import find_spec
        return (
            find_spec("agents.rules.models") is not None
        )
    except ImportError:
        return False


# ═══════════════════════════════════════════════════
# 1. 规则加载（旧格式兼容）
# ═══════════════════════════════════════════════════

def load_timing_rules(path: str | Path | None = None) -> dict:
    """从 YAML 文件加载手术时机判定规则.

    Args:
        path: YAML 文件路径，默认使用 assets/rules/timing_rules.yaml

    Returns:
        解析后的规则字典，包含 delay_factors, rules, engine_config
    """
    global _RULES_CACHE
    if path is None:
        path = _RULES_PATH

    if _RULES_CACHE is not None:
        return _RULES_CACHE

    import yaml
    path = Path(path)
    if not path.exists():
        _RULES_CACHE = _default_rules()
        return _RULES_CACHE

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    _RULES_CACHE = raw
    return raw


def reload_timing_rules(path: str | Path | None = None) -> dict:
    """强制重新加载规则（用于热更新场景）."""
    global _RULES_CACHE
    _RULES_CACHE = None
    return load_timing_rules(path)


def _default_rules() -> dict:
    """YAML 文件不存在时的默认规则（降级方案）."""
    return {
        "delay_factors": [
            {"id": "cardiac", "name": "心脏因素", "risk_when_triggered": "high",
             "optimization": "心内科会诊", "evaluation_logic": ""},
            {"id": "pulmonary", "name": "肺部因素(T2)", "risk_when_triggered": "high",
             "optimization": "呼吸科会诊+肺功能优化", "evaluation_logic": ""},
            {"id": "cerebral", "name": "脑血管因素(T2)", "risk_when_triggered": "high",
             "optimization": "神经内科会诊", "evaluation_logic": ""},
            {"id": "anticoagulation", "name": "抗凝因素", "risk_when_triggered": "medium",
             "optimization": "评估停药时间+桥接", "evaluation_logic": ""},
            {"id": "anemia", "name": "贫血因素", "risk_when_triggered": "medium",
             "optimization": "纠正贫血", "evaluation_logic": ""},
            {"id": "renal", "name": "肾功能因素", "risk_when_triggered": "medium",
             "optimization": "肾内科会诊", "evaluation_logic": ""},
            {"id": "infection", "name": "感染因素", "risk_when_triggered": "medium",
             "optimization": "抗感染治疗", "evaluation_logic": ""},
            {"id": "glucose", "name": "血糖因素", "risk_when_triggered": "medium",
             "optimization": "胰岛素调整", "evaluation_logic": ""},
        ],
        "rules": [
            {"id": "timing-rule-t2-001", "name": "MDT延迟手术",
             "condition": "high_weight_triggered",
             "conclusion": "高权重延迟因素≥1，需MDT会诊延迟手术", "urgency": "elective"},
            {"id": "timing-rule-t2-002", "name": "限期手术",
             "condition": "medium_weight_only",
             "conclusion": "无高权重延迟因素，中权重可控，积极优化后3-7天限期手术", "urgency": "urgent"},
            {"id": "timing-rule-t2-003", "name": "急诊手术",
             "condition": "no_delay",
             "conclusion": "无延迟因素，48小时内急诊手术", "urgency": "emergency"},
        ],
    }


# ═══════════════════════════════════════════════════
# 2. 六维延迟因素评估器
# ═══════════════════════════════════════════════════

def _build_lab_map(patient: dict) -> dict[str, dict]:
    """将 lab_tests 转为 name→dict 映射."""
    lab_map: dict[str, dict] = {}
    for t in patient.get("lab_tests", []):
        name = t.get("name", "")
        if name:
            lab_map[name] = t
    return lab_map


def _get_lab_value(lab_map: dict[str, dict], names: list[str]) -> float | None:
    """从 lab_map 中获取第一个匹配的检验数值."""
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


def _has_diagnosis_keyword(patient: dict, keywords: list[str]) -> bool:
    """检查诊断/主诉/现病史是否含有关键词."""
    texts = [
        patient.get("diagnosis", "") or "",
        patient.get("chief_complaint", "") or "",
        patient.get("present_illness", "") or "",
    ]
    combined = " ".join(texts).lower()
    for kw in keywords:
        if kw.lower() in combined:
            return True
    return False


def _has_medication_keyword(patient: dict, keywords: list[str]) -> bool:
    """检查用药史/既往史是否含有关键词."""
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
    """评估心脏延迟因素."""
    evidence_parts: list[str] = []
    triggered = False

    # 1. 肌钙蛋白
    ctnI = _get_lab_value(lab_map, ["肌钙蛋白I", "肌钙蛋白", "cTnI", "hs-cTnI"])
    ctnT = _get_lab_value(lab_map, ["肌钙蛋白T", "cTnT", "hs-cTnT"])
    threshold = factor_cfg.get("threshold_values", {})
    ctnI_thresh = threshold.get("cTnI", {}).get("high", 0.04)
    ctnT_thresh = threshold.get("cTnT", {}).get("high", 0.1)

    if ctnI is not None and ctnI > ctnI_thresh:
        evidence_parts.append(f"cTnI={ctnI}ng/mL (↑, 阈值>{ctnI_thresh})")
        triggered = True
    if ctnT is not None and ctnT > ctnT_thresh:
        evidence_parts.append(f"cTnT={ctnT}ng/mL (↑, 阈值>{ctnT_thresh})")
        triggered = True

    # 2. CK-MB
    ckmb = _get_lab_value(lab_map, ["心型肌酸激酶", "CK-MB", "CKMB"])
    ckmb_thresh = threshold.get("CKMB", {}).get("high", 25)
    if ckmb is not None and ckmb > ckmb_thresh:
        evidence_parts.append(f"CK-MB={ckmb}U/L (↑, 阈值>{ckmb_thresh})")
        triggered = True

    # 3. ECG 高危模式
    ecg_findings = extract_ecg_keywords_from_exam(patient)
    high_risk_patterns = factor_cfg.get("ecg_high_risk_patterns", [])
    for finding in ecg_findings:
        label = finding.get("label", "")
        if any(p.lower() in label.lower() for p in high_risk_patterns):
            evidence_parts.append(f"ECG: {label}")
            triggered = True

    # 4. 诊断关键词
    dx_keywords = factor_cfg.get("diagnosis_keywords", [])
    if _has_diagnosis_keyword(patient, dx_keywords):
        evidence_parts.append("诊断包含急性冠脉综合征关键词")
        triggered = True

    risk = "high" if triggered else "none"
    optimization = factor_cfg.get("optimization", "心内科会诊") if triggered else ""
    return {
        "triggered": triggered,
        "evidence": "; ".join(evidence_parts) if evidence_parts else "",
        "risk": risk,
        "optimization": optimization,
    }


def _eval_anticoagulation(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    """评估抗凝延迟因素."""
    evidence_parts: list[str] = []
    triggered = False

    threshold = factor_cfg.get("threshold_values", {})
    drug_keywords = factor_cfg.get("drug_keywords", [])
    inr = _get_lab_value(lab_map, ["凝血酶原时间国际标准化比值", "INR", "PT-INR"])
    pt = _get_lab_value(lab_map, ["凝血酶原时间", "PT"])

    # 检查用药史
    has_anticoag = _has_medication_keyword(patient, drug_keywords)

    if has_anticoag:
        # 华法林 + INR>1.5
        if _has_medication_keyword(patient, ["华法林", "warfarin"]):
            inr_thresh = threshold.get("INR", {}).get("high", 1.5)
            if inr is not None and inr > inr_thresh:
                evidence_parts.append(f"华法林 + INR={inr} (>阈值{inr_thresh})")
                triggered = True
            else:
                evidence_parts.append("使用华法林（INR未测或在安全范围）")
                triggered = True
        # NOAC
        elif _has_medication_keyword(patient, ["利伐沙班", "达比加群", "阿哌沙班", "NOAC"]):
            evidence_parts.append("使用NOAC，需确认停药时间")
            triggered = True
        # 抗血小板
        elif _has_medication_keyword(patient, ["氯吡格雷", "替格瑞洛"]):
            evidence_parts.append("使用抗血小板药物（氯吡格雷/替格瑞洛）")
            triggered = True
        # PT 延长(非特异性)
        if pt is not None and not triggered:
            pt_thresh = threshold.get("PT", {}).get("high", 14)
            if pt > pt_thresh:
                evidence_parts.append(f"PT={pt}sec (↑)")
                triggered = True

    risk = "high" if triggered else "none"
    optimization = factor_cfg.get("optimization", "评估停药时间+桥接方案") if triggered else ""
    return {
        "triggered": triggered,
        "evidence": "; ".join(evidence_parts) if evidence_parts else "",
        "risk": risk,
        "optimization": optimization,
    }


def _eval_anemia(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    """评估贫血延迟因素."""
    evidence_parts: list[str] = []
    triggered = False

    hb = _get_lab_value(lab_map, ["血红蛋白测定", "血红蛋白", "Hb", "Hgb"])
    if hb is not None:
        if hb < 80:
            evidence_parts.append(f"Hb={hb}g/L (重度贫血, <80)")
            triggered = True
        elif hb < 100:
            # 合并心脏病才触发
            past = (patient.get("past_history", "") or "").lower()
            if any(kw in past for kw in ["冠心病", "心衰", "心力衰竭", "冠状动脉"]):
                evidence_parts.append(f"Hb={hb}g/L (<100, 合并心脏病)")
                triggered = True
            else:
                evidence_parts.append(f"Hb={hb}g/L (轻度贫血, 不强制延迟)")
        else:
            evidence_parts.append(f"Hb={hb}g/L (正常范围)")

    risk = "high" if triggered else ("medium" if hb is not None and hb < 100 else "none")
    optimization = factor_cfg.get("optimization", "输注红细胞至Hb≥80g/L") if triggered else ""
    return {
        "triggered": triggered,
        "evidence": "; ".join(evidence_parts) if evidence_parts else "",
        "risk": risk,
        "optimization": optimization,
    }


def _eval_renal(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    """评估肾功能延迟因素."""
    evidence_parts: list[str] = []
    triggered = False

    threshold = factor_cfg.get("threshold_values", {})
    egfr = _get_lab_value(lab_map, ["肾小球滤过率", "eGFR", "估算肾小球滤过率"])
    cr = _get_lab_value(lab_map, ["肌酐", "Cr", "血肌酐"])

    if egfr is not None:
        severe_thresh = threshold.get("eGFR", {}).get("low", 30)
        warning_thresh = threshold.get("eGFR", {}).get("warning", 60)
        if egfr < severe_thresh:
            evidence_parts.append(f"eGFR={egfr}mL/min (严重, <{severe_thresh})")
            triggered = True
        elif egfr < warning_thresh:
            evidence_parts.append(f"eGFR={egfr}mL/min (中度减退, 需关注)")
            # 仅在需造影时触发，保守触发
            triggered = True
        else:
            evidence_parts.append(f"eGFR={egfr}mL/min (正常范围)")
    elif cr is not None:
        cr_thresh = threshold.get("creatinine", {}).get("high", 133)
        if cr > cr_thresh:
            evidence_parts.append(f"Cr={cr}μmol/L (↑, 阈值>{cr_thresh})")
            triggered = True

    risk = "high" if triggered else "none"
    optimization = factor_cfg.get("optimization", "肾内科会诊+避免肾毒性药物") if triggered else ""
    return {
        "triggered": triggered,
        "evidence": "; ".join(evidence_parts) if evidence_parts else "",
        "risk": risk,
        "optimization": optimization,
    }


def _eval_infection(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    """评估感染延迟因素."""
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
        evidence_parts.append(f"WBC={wbc}×10⁹/L (↑, 阈值>{wbc_thresh})")
        triggered = True
    if crp is not None and crp > crp_thresh:
        evidence_parts.append(f"CRP={crp}mg/L (↑, 阈值>{crp_thresh})")
        triggered = True
    if neut is not None and neut > neut_thresh:
        evidence_parts.append(f"NEUT={neut}×10⁹/L (↑, 阈值>{neut_thresh})")
        triggered = True

    dx_keywords = factor_cfg.get("diagnosis_keywords", [])
    if _has_diagnosis_keyword(patient, dx_keywords):
        dx = patient.get("diagnosis", "")
        evidence_parts.append(f"诊断含有感染: {dx[:40]}")
        triggered = True

    risk = "high" if (crp is not None and crp > 200) or (wbc is not None and wbc > 20) else \
           "medium" if triggered else "none"
    optimization = factor_cfg.get("optimization", "抗感染治疗+复查炎症指标至正常") if triggered else ""
    return {
        "triggered": triggered,
        "evidence": "; ".join(evidence_parts) if evidence_parts else "",
        "risk": risk,
        "optimization": optimization,
    }


def _eval_glucose(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    """评估血糖延迟因素."""
    evidence_parts: list[str] = []
    triggered = False

    threshold = factor_cfg.get("threshold_values", {})
    glucose = _get_lab_value(lab_map, ["葡萄糖", "血糖", "Glu"])
    hba1c = _get_lab_value(lab_map, ["糖化血红蛋白", "HbA1c", "糖化血红蛋白A1c"])

    glucose_thresh = threshold.get("glucose", {}).get("high", 13.9)

    if glucose is not None:
        if glucose > glucose_thresh:
            evidence_parts.append(f"血糖={glucose}mmol/L (↑, 阈值>{glucose_thresh})")
            triggered = True
        else:
            evidence_parts.append(f"血糖={glucose}mmol/L (正常)")
    else:
        evidence_parts.append("无血糖数据")

    dx_keywords = factor_cfg.get("diagnosis_keywords", ["DKA", "糖尿病酮症酸中毒", "高渗高血糖状态", "HHS"])
    if _has_diagnosis_keyword(patient, dx_keywords):
        evidence_parts.append("诊断含DKA/HHS关键词")
        triggered = True

    if hba1c is not None:
        hba1c_thresh = threshold.get("hba1c", {}).get("high", 9.0)
        if hba1c > hba1c_thresh:
            evidence_parts.append(f"HbA1c={hba1c}% (长期控制不佳, >{hba1c_thresh}%)")
        else:
            evidence_parts.append(f"HbA1c={hba1c}%")

    risk = "high" if triggered and (glucose is not None and glucose > 22.0) else \
           "medium" if triggered else "none"
    optimization = factor_cfg.get("optimization", "胰岛素方案调整+血糖控制至空腹<10mmol/L") if triggered else ""
    return {
        "triggered": triggered,
        "evidence": "; ".join(evidence_parts) if evidence_parts else "",
        "risk": risk,
        "optimization": optimization,
    }


def _eval_pulmonary(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    """评估肺部延迟因素 — T2 独立高权重维度.

    # T2_OVERRIDE: 肺部因素 | T1来源: NICE NG37 | 场景: 手术时机评估
    创伤骨科经验：急性肺炎(1周内)/哮喘/肺梗塞 直接触发 MDT.
    """
    triggered = False
    evidence_parts: list[str] = []

    past = (patient.get("past_history", "") or "").lower()
    diagnosis = (patient.get("diagnosis", "") or "").lower()
    present = (patient.get("present_illness", "") or "").lower()
    combined = f"{past} {diagnosis} {present}"

    high_risk_kw = ["急性肺炎", "重症肺炎", "肺栓塞", "肺梗塞", "肺梗死",
                    "哮喘急性发作", "呼吸衰竭", "呼衰", "copd急性加重"]
    medium_kw = ["肺炎", "肺部感染", "哮喘", "copd", "慢性阻塞性", "胸腔积液"]

    for kw in high_risk_kw:
        if kw in combined:
            evidence_parts.append(f"高危: {kw}")
            triggered = True
            break

    if not triggered:
        for kw in medium_kw:
            if kw in combined:
                evidence_parts.append(f"中危: {kw}")
                triggered = True

    risk = "high" if triggered and evidence_parts and "高危" in evidence_parts[0] else \
           "medium" if triggered else "none"
    optimization = "呼吸科会诊+肺功能优化+抗感染" if triggered else ""

    return {
        "triggered": triggered,
        "evidence": "; ".join(evidence_parts) if evidence_parts else "",
        "risk": risk,
        "optimization": optimization,
    }


def _eval_cerebral(patient: dict, factor_cfg: dict, lab_map: dict[str, dict]) -> dict:
    """评估脑血管延迟因素 — T2 新增高权重维度.

    # T2_OVERRIDE: 脑血管因素 | T1来源: NICE NG37 | 场景: 手术时机评估
    创伤骨科经验：一月内脑梗直接触发神经内科会诊.
    """
    triggered = False
    evidence_parts: list[str] = []

    past = (patient.get("past_history", "") or "").lower()
    diagnosis = (patient.get("diagnosis", "") or "").lower()
    present = (patient.get("present_illness", "") or "").lower()
    combined = f"{past} {diagnosis} {present}"

    acute_kw = ["急性脑梗", "脑梗死", "脑梗塞", "脑卒中", "脑出血",
                "cva", "stroke", "tia", "短暂性脑缺血", "脑梗", "脑血管意外"]
    history_kw = ["脑梗病史", "脑梗后", "脑卒中后", "脑梗死后遗症", "脑血管病"]

    for kw in acute_kw:
        if kw in combined:
            evidence_parts.append(f"急性脑血管事件: {kw}")
            triggered = True
            break

    if not triggered:
        for kw in history_kw:
            if kw in combined:
                evidence_parts.append(f"脑血管病史: {kw}")
                triggered = True

    risk = "high" if triggered else "none"
    optimization = "神经内科会诊+头颅CT/MRI+抗血小板评估" if triggered else ""

    return {
        "triggered": triggered,
        "evidence": "; ".join(evidence_parts) if evidence_parts else "",
        "risk": risk,
        "optimization": optimization,
    }


# ─── 评估器映射 ───
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


# ═══════════════════════════════════════════════════
# 3a. T2 分层裁决引擎
# ═══════════════════════════════════════════════════

def _apply_t2_hierarchical_decision(
    results: dict[str, dict],
) -> tuple[int, int, str, str, str]:
    """应用 T2 分层裁决逻辑.

    Returns:
        (high_count, medium_count, timing_conclusion, urgency, rule_id)
    """
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
        return (
            high_count, medium_count,
            f"高权重延迟因素 {high_count} 项触发 → 先纠正可逆因素（详见 Stage 4），择期延迟手术",
            "elective",
            "timing-rule-t2-001",
        )
    if medium_count >= 1:
        return (
            high_count, medium_count,
            f"无高权重延迟因素，{medium_count} 项中权重因素可控，积极优化后 3-7 天限期手术",
            "urgent",
            "timing-rule-t2-002",
        )
    return (
        high_count, medium_count,
        "无延迟因素，48 小时内急诊手术",
        "emergency",
        "timing-rule-t2-003",
    )


# ═══════════════════════════════════════════════════
# 3. 规则引擎 — 核心入口
# ═══════════════════════════════════════════════════

# ASSET:rule-hip-timing
def evaluate_timing(
    patient: dict,
    rules_path: str | Path | None = None,
) -> dict:
    """评估患者手术时机 — 主入口.

    优先通过 agents.rules 规则服务平台评估（v3.0），
    回退到 v2.0 内联评估器。

    Args:
        patient: 患者数据字典
        rules_path: (废弃) 旧YAML路径，兼容参数

    Returns:
        TimingDecision 字典
    """
    patient_id = patient.get("patient_id", "") or patient.get("mrn", "")

    # ── 尝试 v3.0 规则服务平台 ──
    if _rule_service_available():
        try:
            return _evaluate_timing_v3(patient, patient_id)
        except Exception:
            pass

    # ── 回退 v2.0 内联评估器 ──
    return _evaluate_timing_v2(patient, patient_id)


def _evaluate_timing_v3(patient: dict, patient_id: str) -> dict:
    """v3.0: 通过 agents.rules 规则服务平台 + T2 分层裁决."""
    from agents.rules.models import EvaluationContext
    from agents.rules.rule_registry import find_rules
    from agents.rules.arbitration_engine import evaluate_rules as engine_evaluate

    ctx_values = _build_evaluation_context(patient)
    ctx = EvaluationContext(values=ctx_values)

    delay_points = [
        "cardiac_delay", "pulmonary_delay", "cerebral_delay",
        "anticoagulation_delay", "anemia_delay",
        "renal_delay", "infection_delay", "glucose_delay",
    ]
    delay_id_to_t2: dict[str, str] = {
        "cardiac_delay": "cardiac", "pulmonary_delay": "pulmonary",
        "cerebral_delay": "cerebral", "anticoagulation_delay": "anticoagulation",
        "anemia_delay": "anemia", "renal_delay": "renal",
        "infection_delay": "infection", "glucose_delay": "glucose",
    }
    results: dict[str, dict] = {}

    for dp in delay_points:
        rules = find_rules(dp, "hip_fracture_timing")
        t2_id = delay_id_to_t2.get(dp, dp)
        if not rules:
            results[t2_id] = {"triggered": False, "evidence": "", "risk": "unknown", "optimization": ""}
            continue
        ar = engine_evaluate(rules, ctx)
        triggered = ar.winner_rule_id != "" and "触发" in ar.conclusion
        risk = "high" if "升高" in ar.conclusion or "高危" in ar.conclusion else \
               "medium" if "可能" in ar.conclusion else "none"
        results[t2_id] = {
            "triggered": triggered,
            "evidence": f"{ar.conclusion}; 来源: {'; '.join(ar.chain[:3])}" if ar.chain else ar.conclusion,
            "risk": risk,
            "optimization": _T2_FACTOR_NAMES.get(t2_id, t2_id) if triggered else "",
        }

    high_count, medium_count, conclusion, urgency, rule_id = _apply_t2_hierarchical_decision(results)
    total_delay = high_count + medium_count

    recs = _build_t2_recommendations(results, high_count, medium_count)

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
        "engine_version": "4.0",
    }


def _evaluate_timing_v2(patient: dict, patient_id: str) -> dict:
    """v2.0: 内联评估器 + T2 分层裁决（回退方案）."""
    rules = load_timing_rules()
    delay_factor_cfgs = rules.get("delay_factors", [])
    lab_map = _build_lab_map(patient)

    results: dict[str, dict] = {}
    for factor in delay_factor_cfgs:
        fid = factor["id"]
        evaluator = _EVALUATORS.get(fid)
        if evaluator:
            results[fid] = evaluator(patient, factor, lab_map)
        else:
            results[fid] = {"triggered": False, "evidence": f"无评估器（{fid}）", "risk": "unknown", "optimization": ""}

    high_count, medium_count, conclusion, urgency, rule_id = _apply_t2_hierarchical_decision(results)
    total_delay = high_count + medium_count

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
        "recommendations": _build_t2_recommendations(results, high_count, medium_count),
        "guideline_refs": _build_guideline_refs(results, rules),
        "engine_version": "4.0",
    }


def _build_t2_recommendations(
    results: dict[str, dict], high_count: int, medium_count: int,
) -> list[str]:
    """基于 T2 分层评估生成建议列表."""
    recs: list[str] = []

    for fid, result in results.items():
        if result.get("triggered") and result.get("optimization"):
            fname = _T2_FACTOR_NAMES.get(fid, fid)
            weight_tag = "🔴高" if fid in _T2_HIGH_WEIGHT else "🟡中"
            recs.append(f"{weight_tag} {fname}: {result['optimization']}")
            if result.get("evidence"):
                recs.append(f"    依据: {result['evidence'][:80]}")

    if high_count >= 1:
        recs.append(f">> 高权重 {high_count} 项触发 → 直接 MDT 多学科会诊，延迟手术")
    elif medium_count >= 1:
        recs.append(f">> 中权重 {medium_count} 项可控 → 积极优化后 3-7 天限期手术")
        recs.append(">> 每 24h 重新评估优化进展")
    else:
        recs.append(">> 无延迟因素 → 48 小时内急诊手术")

    return recs


def _build_guideline_refs(results: dict[str, dict], rules: dict) -> list[str]:
    """聚合所有触发因素的指南引用."""
    refs_set: set[str] = set()

    # 规则级引用
    for rule in rules.get("rules", []):
        gr = rule.get("guideline_ref", "")
        if gr:
            refs_set.add(gr)

    # 全局引用
    for gr in rules.get("guideline_ref", []):
        refs_set.add(gr)

    return sorted(refs_set)


# ═══════════════════════════════════════════════════
# 4. 辅助输出
# ═══════════════════════════════════════════════════

def print_timing_decision(decision: dict) -> None:
    """友好打印 TimingDecision."""
    print("===== 手术时机评估报告 — Timing Engine v4.0 (T2 分层裁决) =====")
    pid = decision.get("patient_id", "")
    if pid:
        print(f"患者: {pid}")
    print()

    print(f"手术时机建议: {decision.get('timing_conclusion', '')}")
    print(f"紧急度: {decision.get('urgency', '')}")
    print(f"高权重触发: {decision.get('high_weight_count', 0)}  中权重触发: {decision.get('medium_weight_count', 0)}")
    print()

    print("--- 八维延迟因素评估 (T2 分层) ---")
    for fid, result in decision.get("delay_factors", {}).items():
        icon = "🔴" if result["triggered"] else "🟢"
        weight_label = "高权重" if fid in _T2_HIGH_WEIGHT else "中权重" if fid in _T2_MEDIUM_WEIGHT else "未知"
        print(f"  {icon} [{weight_label}] {fid}: risk={result.get('risk', '').upper()}")
        if result.get("evidence"):
            print(f"     证据: {result['evidence']}")
        if result.get("optimization"):
            print(f"     优化: {result['optimization']}")
    print()

    recs = decision.get("recommendations", [])
    if recs:
        print("--- 建议 ---")
        for r in recs:
            print(f"  - {r}")
    print()

    refs = decision.get("guideline_refs", [])
    if refs:
        print("--- 指南引用 ---")
        for ref in refs:
            print(f"  - {ref}")
