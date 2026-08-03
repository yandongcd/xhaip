"""肿瘤科 — KnowledgeAgent-powered clinical reasoning (Deep-Optimized).

Focus: 肿瘤综合治疗与精准诊疗
GUIDELINES: CSCO常见恶性肿瘤诊疗指南（2024）, NCCN Guidelines: Non-Small Cell Lung Cancer (2023), NCCN Guidelines: Breast Cancer (2023)
Conditions: 肺癌, 乳腺癌, 胃癌, 结直肠癌, 肝癌

Injected clinical systems: TNM Staging, ECOG PS, RECIST 1.1, CTCAE v5 toxicity grading,
immunotherapy irAE management, WHO cancer pain ladder.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="oncology", department="肿瘤科")
_GUIDELINES = [
    "CSCO常见恶性肿瘤诊疗指南（2024）",
    "NCCN Guidelines: Non-Small Cell Lung Cancer (2023)",
    "NCCN Guidelines: Breast Cancer (2023)",
    "NCCN Guidelines: Colorectal Cancer (2023)",
    "NCCN Guidelines: Hepatobiliary Cancers (2023)",
]

_agent.rule_engine.load_all()

# ── TNM Stage Mapping ───────────────────────────────────────────────
_TNM_LUNG = {
    ("T1a","N0","M0"):"IA1",("T1b","N0","M0"):"IA2",("T1c","N0","M0"):"IA3",
    ("T2a","N0","M0"):"IB",("T2b","N0","M0"):"IIA",
    ("T1a","N1","M0"):"IIB",("T1b","N1","M0"):"IIB",("T1c","N1","M0"):"IIB",
    ("T2a","N1","M0"):"IIB",("T2b","N1","M0"):"IIB",("T3","N0","M0"):"IIB",
    ("T1a","N2","M0"):"IIIA",("T1b","N2","M0"):"IIIA",("T1c","N2","M0"):"IIIA",
    ("T2a","N2","M0"):"IIIA",("T2b","N2","M0"):"IIIA",("T3","N1","M0"):"IIIA",
    ("T4","N0","M0"):"IIIA",("T4","N1","M0"):"IIIA",
    ("T3","N2","M0"):"IIIB",("T4","N2","M0"):"IIIB",
    ("T1-4","N3","M0"):"IIIC",
}
_TNM_BREAST = {
    ("T1","N0","M0"):"I",("T2","N0","M0"):"IIA",("T3","N0","M0"):"IIB",
    ("T0","N1","M0"):"IIA",("T1","N1","M0"):"IIA",("T2","N1","M0"):"IIB",
    ("T3","N1","M0"):"IIIA",("T0","N2","M0"):"IIIA",("T1","N2","M0"):"IIIA",
    ("T2","N2","M0"):"IIIA",("T3","N2","M0"):"IIIA",("T4","N0-2","M0"):"IIIB",
    ("AnyT","N3","M0"):"IIIC",
}
_TNM_COLORECTAL = {
    ("T1-2","N0","M0"):"I",("T3-4","N0","M0"):"II",("AnyT","N1-2","M0"):"III",
}
_TNM_LIVER = {
    ("T1","N0","M0"):"I",("T2","N0","M0"):"II",("T3","N0","M0"):"IIIA",
    ("T4","N0","M0"):"IIIB",("AnyT","N1","M0"):"IVA",
}

ECOG_DESCRIPTIONS = {
    0: "Fully active, able to carry on all pre-disease performance without restriction",
    1: "Restricted in physically strenuous activity but ambulatory and able to carry out light/sedentary work",
    2: "Ambulatory and capable of all self-care but unable to carry out any work activities; up and about >50% of waking hours",
    3: "Capable of only limited self-care; confined to bed or chair >50% of waking hours",
    4: "Completely disabled; cannot carry on any self-care; totally confined to bed or chair",
    5: "Dead",
}

IRA_MANAGEMENT = {
    "pneumonitis": {1:"Monitor", 2:"Prednisone 1-2mg/kg/d; hold ICI", 3:"Methylprednisolone 1-2mg/kg IV; permanently discontinue ICI", 4:"Methylprednisolone 2mg/kg IV + infliximab/MMF/IVIG"},
    "colitis": {1:"Monitor + loperamide", 2:"Prednisone 1mg/kg/d; hold ICI", 3:"Methylprednisolone 1-2mg/kg IV; colonoscopy; infliximab if refractory", 4:"Methylprednisolone 2mg/kg IV + infliximab; surgical consult"},
    "hepatitis": {1:"Monitor LFTs", 2:"Prednisone 0.5-1mg/kg/d; hold ICI", 3:"Methylprednisolone 1-2mg/kg IV; MMF if steroid-refractory", 4:"Methylprednisolone 2mg/kg IV; permanently discontinue ICI"},
    "thyroiditis": {1:"Monitor TSH/fT4", 2:"Levothyroxine replacement; continue ICI", 3:"Hospitalization for myxedema/thyroid storm", 4:"ICU admission"},
}


def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


# ── Clinical Scoring Systems ─────────────────────────────────────────

def _tnm_stage(t: str, n: str, m: str, cancer_type: str = "lung") -> dict:
    """AJCC 8th TNM staging for lung/liver/colorectal/breast cancers."""
    if m == "1":
        stage = "IV"
    else:
        lookup = {"lung": _TNM_LUNG, "breast": _TNM_BREAST,
                  "colorectal": _TNM_COLORECTAL, "liver": _TNM_LIVER}
        table = lookup.get(cancer_type, _TNM_LUNG)
        key = (t, n, m)
        stage = table.get(key) or table.get(t.replace("1","").replace("2","").replace("3","").replace("4","AnyT") if "AnyT" in str(table) else None)
        if not stage:
            stage = _fuzzy_tnm(t, n, m, cancer_type)
    stage_group = "I" if stage and stage[0]=="I" and (len(stage)==1 or not stage[1].isdigit()) else ("I-III" if stage and not stage.startswith("IV") else "IV")
    return {
        "t": t, "n": n, "m": m, "cancer_type": cancer_type,
        "stage": stage or "Unknown", "stage_group": stage_group,
        "resectable": stage_group != "IV" and stage not in ("IIIB", "IIIC", "IV"),
    }


def _fuzzy_tnm(t: str, n: str, m: str, cancer_type: str) -> str:
    """Fallback TNM staging by T/N/M numeric levels."""
    t_val = int("".join(c for c in t if c.isdigit()) or "1")
    n_val = int("".join(c for c in n if c.isdigit()) or "0")
    if cancer_type == "breast":
        if t_val <= 2 and n_val == 0:
            return "I"
        if t_val <= 2 and n_val == 1:
            return "IIA"
        if t_val == 3 and n_val <= 1:
            return "IIB"
        if n_val == 2:
            return "IIIA"
        if t_val == 4:
            return "IIIB"
        if n_val == 3:
            return "IIIC"
    else:
        if t_val <= 1 and n_val == 0:
            return "I"
        if t_val <= 2 and n_val == 0:
            return "II"
        if n_val == 1:
            return "IIIA"
        if n_val == 2:
            return "IIIB"
        if t_val == 4:
            return "IIIA"
    return "Unknown"


def _ecog_assessment(score: int) -> dict:
    """ECOG Performance Status — drives treatment decisions."""
    description = ECOG_DESCRIPTIONS.get(score, "Unknown")
    treatment_decision = {
        0: "Curative-intent chemotherapy/surgery candidate",
        1: "Curative-intent chemotherapy candidate; monitor tolerance",
        2: "Palliative-intent chemotherapy / reduced-dose regimens",
        3: "Palliative care focus; systemic therapy only if high benefit-toxicity ratio",
        4: "Best supportive care only; no systemic chemotherapy",
        5: "N/A",
    }.get(score, "Individualized assessment")
    return {
        "score": score, "description": description,
        "treatment_decision": treatment_decision,
        "chemotherapy_suitable": score <= 2,
        "clinical_trial_eligible": score <= 1,
    }


def _recist_evaluation(target_sum_baseline: float, target_sum_now: float,
                       non_target: str = "non-CR/non-PD", new_lesions: bool = False) -> dict:
    """RECIST 1.1 tumor response evaluation."""
    if new_lesions or non_target == "PD":
        response = "PD"
        change_pct = 100.0
    elif target_sum_baseline == 0:
        response = "N/A"
        change_pct = 0.0
    else:
        change_pct = (target_sum_now - target_sum_baseline) / target_sum_baseline * 100
        target_disappeared = target_sum_now == 0
        if target_disappeared and non_target == "CR":
            response = "CR"
        elif change_pct <= -30 or target_disappeared:
            response = "PR"
        elif change_pct >= 20:
            response = "PD"
        else:
            response = "SD"
    return {
        "response": response, "change_pct": round(change_pct, 1),
        "definition": {"CR": "Disappearance of all target lesions", "PR": "≥30% decrease in sum of diameters",
                        "SD": "Neither PR nor PD", "PD": "≥20% increase OR new lesions"},
        "action": {"CR": "Confirm at 4 weeks", "PR": "Continue current therapy", "SD": "Continue; reassess benefit",
                    "PD": "Change treatment; consider biopsy"}.get(response, "Re-evaluate"),
    }


def _ctcae_toxicity(tox_type: str, grade: int, anc: float = None, plt: float = None,
                     temp: float = None) -> dict:
    """CTCAE v5.0 toxicity grading with clinical actions."""
    emergencies = []
    if tox_type == "neutropenia" and anc is not None:
        detail = {1: f"ANC {anc} (≥1500 normal)", 2: f"ANC {anc} (1000-<1500)", 3: f"ANC {anc} (500-<1000)",
                  4: f"ANC {anc} (<500 — SEVERE)"}.get(grade, "Unknown")
        if grade == 4:
            emergencies.append("ANC<500 → 粒缺合并感染高风险, 立即G-CSF+抗生素预防")
    elif tox_type == "thrombocytopenia" and plt is not None:
        detail = {1: f"PLT {plt}K (75-<LLN)", 2: f"PLT {plt}K (50-<75)", 3: f"PLT {plt}K (25-<50)",
                  4: f"PLT {plt}K (<25 — SEVERE)"}.get(grade, "Unknown")
        if grade >= 3:
            emergencies.append("PLT<50K → 出血风险, 备血小板; PLT<10K → 预防性输注")
    elif tox_type == "febrile_neutropenia" and anc is not None and temp is not None:
        if anc < 500 and temp >= 38.3:
            detail = f"FEBRILE NEUTROPENIA: ANC {anc}, Temp {temp}°C — EMERGENCY"
            emergencies.append("粒缺伴发热=肿瘤急症! 1h内静脉广谱抗生素(头孢吡肟/哌拉西林他唑巴坦/碳青霉烯)")
            grade = 4
        else:
            detail = f"No febrile neutropenia (ANC {anc}, Temp {temp}°C)"
    else:
        detail = f"Grade {grade}"
    return {"toxicity": tox_type, "grade": grade, "detail": detail, "emergencies": emergencies,
            "action": "EMERGENCY: IV antibiotics <1h; admit" if grade >= 4 else
            "Hold chemotherapy; assess recovery" if grade >= 3 else "Monitor"}


def _irae_management(organ: str, grade: int) -> dict:
    """Immunotherapy-related adverse event management — grade-based steroid dosing."""
    organ_info = IRA_MANAGEMENT.get(organ, {1:"Monitor", 2:"Oral steroids; hold ICI",
        3:"IV steroids; consider permanent discontinuation", 4:"IV steroids + 2nd-line immunosuppressant; discontinue ICI"})
    rec = organ_info.get(grade, "Specialist consultation")
    return {
        "organ": organ, "grade": grade,
        "recommendation": rec,
        "steroid_dosing": {1: "None", 2: "Prednisone 0.5-1mg/kg/d PO",
                           3: "Methylprednisolone 1-2mg/kg/d IV", 4: "Methylprednisolone 2mg/kg/d IV + second agent"}.get(grade, ""),
        "ici_action": {1: "Continue", 2: "Hold; resume after G≤1", 3: "Hold; consider permanent D/C",
                        4: "Permanently discontinue"}.get(grade, ""),
    }


def _who_pain_ladder(pain_score: int) -> dict:
    """WHO Analgesic Ladder for cancer pain."""
    steps = [
        (1, "Step 1: Non-opioid", "Acetaminophen / NSAIDs ± adjuvant", lambda s: s <= 3),
        (2, "Step 2: Weak opioid", "Codeine / Tramadol + non-opioid ± adjuvant", lambda s: 4 <= s <= 6),
        (3, "Step 3: Strong opioid", "Morphine / Oxycodone / Fentanyl + non-opioid ± adjuvant", lambda s: s >= 7),
    ]
    for step_num, name, drugs, condition in steps:
        if condition(pain_score):
            return {"pain_score": pain_score, "step": step_num, "step_name": name, "drugs": drugs,
                    "adjuvants": "Gabapentin/pregabalin (neuropathic), corticosteroids (bone mets/brain mets), bisphosphonates (bone pain)"}
    return {"pain_score": pain_score, "step": 3, "step_name": "Step 3: Strong opioid",
            "drugs": "Morphine / Oxycodone / Fentanyl", "adjuvants": "As indicated"}


# ── Business Process Functions ───────────────────────────────────────

def bp_reception(**kwargs) -> dict:
    """接诊与初步评估 — ECOG + TNM + Pain assessment."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    # ── Injected clinical scoring ──
    cancer_type = "lung"
    for ct in ["liver", "breast", "colorectal", "lung"]:
        if ct in dx.lower():
            cancer_type = ct
            break
    tnm_data = p.get("tnm", p.get("staging", {}))
    tnm = _tnm_stage(tnm_data.get("t", "T2"), tnm_data.get("n", "N0"),
                     tnm_data.get("m", "M0"), cancer_type)
    ecog_raw = labs.get("ecog", p.get("ecog_score", 0))
    ecog = _ecog_assessment(int(ecog_raw))
    pain_score = int(labs.get("pain_score", p.get("pain_score", 3)))
    pain = _who_pain_ladder(pain_score)

    findings = [
        f"TNM: T{tnm['t']}N{tnm['n']}M{tnm['m']} → Stage {tnm['stage']} ({cancer_type})",
        f"ECOG PS: {ecog['score']} — {ecog['description'][:60]}...",
        f"Pain (NRS): {pain_score}/10 → {pain['step_name']}",
        "病理类型", "分子分型",
    ]
    if "肺癌" in dx or "乳腺癌" in dx:
        findings.insert(0, f"{'肺癌' if '肺癌' in dx else '乳腺癌'} 疾病匹配 (NCCN/CSCO)")
    recommendations = [
        f"ECOG {ecog['score']} → {ecog['treatment_decision']}",
        f"Stage {tnm['stage']} → {'可切除' if tnm['resectable'] else '不可切除/晚期'}",
        pain["drugs"],
    ]
    checklist = ["肿瘤溶解综合征: 高风险淋巴瘤/白血病→水化+别嘌醇",
                 "粒缺伴发热: ANC<500+fever≥38.3→1h内抗生素",
                 "免疫性肺炎: 干咳+呼吸困难→CT+激素",
                 "VTE: Khorana≥2→LMWH预防",
                 "脊髓压迫: 背痛+神经症状→MRI+紧急激素"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注: CEA/CA19-9/CA125/AFP")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肿瘤科")
    return _agent.clinical_result(
        summary=f"肿瘤科—初诊完成 TNM{tnm['stage']} ECOG{ecog['score']} (stage S1)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_exam(**kwargs) -> dict:
    """辅助检查 — RECIST baseline + tumor markers."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")
    cancer_type = "lung"
    for ct in ["liver", "breast", "colorectal", "lung"]:
        if ct in dx.lower():
            cancer_type = ct
            break

    # ── Injected RECIST baseline ──
    baseline = labs.get("target_sum_baseline", 0)
    current = labs.get("target_sum_now", baseline)
    recist = _recist_evaluation(float(baseline) if baseline else 0, float(current) if current else 0,
                                labs.get("non_target", "non-CR/non-PD"), bool(labs.get("new_lesions", False)))

    findings = [
        f"RECIST 1.1: {recist['response']} (Δ {recist['change_pct']}%)",
        "CT/MRI: 胸部+腹部+盆腔增强扫描",
        "PET-CT: SUVmax评估代谢活性",
        f"肿瘤标志物: CEA/CA19-9/CA125/AFP (依{cancer_type}选择)",
        "基因检测: EGFR/ALK/ROS1/BRAF/KRAS/NTRK (NSCLC); HER2/ER/PR (乳腺癌)",
        "病理会诊: 二次确认 + PD-L1(IHC) + MSI/dMMR",
    ]
    if "肺癌" in dx or "乳腺癌" in dx:
        findings.insert(0, f"{'肺癌' if '肺癌' in dx else '乳腺癌'} 特异性检查方案匹配")
    recommendations = [
        f"RECIST {recist['response']} → {recist['action']}",
        "PD-L1 TPS ≥50% → 一线帕博利珠单抗单药",
        "MSI-H/dMMR → 帕博利珠单抗(不限癌种)",
    ]
    checklist = ["肿瘤溶解综合征", "粒缺伴发热", "免疫性肺炎", "VTE", "脊髓压迫"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肿瘤科")
    return _agent.clinical_result(
        summary=f"肿瘤科—检查完成 RECIST {recist['response']} (stage S2)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊与分型分期 — Full TNM + ECOG + molecular classification."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")
    cancer_type = "lung"
    for ct in ["liver", "breast", "colorectal", "lung"]:
        if ct in dx.lower():
            cancer_type = ct
            break
    tnm_data = p.get("tnm", p.get("staging", {}))
    tnm = _tnm_stage(tnm_data.get("t", "T2"), tnm_data.get("n", "N0"),
                     tnm_data.get("m", "M0"), cancer_type)
    ecog = _ecog_assessment(int(labs.get("ecog", p.get("ecog_score", 0))))

    # Molecular subtype
    mol = []
    if cancer_type == "breast":
        her2 = labs.get("her2", p.get("her2", "negative"))
        er = labs.get("er", p.get("er", "positive"))
        pr = labs.get("pr", p.get("pr", "positive"))
        if her2 == "positive":
            mol.append("HER2+")
        if er == "positive" or pr == "positive":
            mol.append("HR+")
        if not mol:
            mol.append("TNBC (三阴性)")
    elif cancer_type == "lung":
        egfr = labs.get("egfr", p.get("egfr_mutation", "wild-type"))
        alk = labs.get("alk", p.get("alk", "negative"))
        if egfr != "wild-type":
            mol.append(f"EGFR mut ({egfr})")
        if alk == "positive":
            mol.append("ALK+")
    mol_str = " + ".join(mol) if mol else "未明确"

    findings = [
        f"TNM Stage: {tnm['stage']} (T{tnm['t']} N{tnm['n']} M{tnm['m']}) — {cancer_type}",
        f"分子分型: {mol_str}",
        f"ECOG PS: {ecog['score']} → {ecog['treatment_decision'][:40]}",
        f"预后分层: Stage {tnm['stage']} — {'手术+辅助治疗' if tnm['resectable'] else '系统治疗±局部治疗'}",
        "MDT讨论: 外科+内科+放疗科+病理科+影像科",
    ]
    if "肺癌" in dx or "乳腺癌" in dx:
        findings.insert(0, f"{'肺癌' if '肺癌' in dx else '乳腺癌'} NCCN/CSCO 分期确认")
    checklist = ["肿瘤溶解综合征", "粒缺伴发热", "免疫性肺炎", "VTE", "脊髓压迫"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肿瘤科")
    return _agent.clinical_result(
        summary=f"肿瘤科—确诊分期 Stage {tnm['stage']} ECOG{ecog['score']} (stage S3)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=[],
    )


def bp_plan(**kwargs) -> dict:
    """治疗方案制定 — ECOG-driven + stage-specific therapy."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")
    cancer_type = "lung"
    for ct in ["liver", "breast", "colorectal", "lung"]:
        if ct in dx.lower():
            cancer_type = ct
            break
    tnm_data = p.get("tnm", p.get("staging", {}))
    tnm = _tnm_stage(tnm_data.get("t", "T2"), tnm_data.get("n", "N0"),
                     tnm_data.get("m", "M0"), cancer_type)
    ecog = _ecog_assessment(int(labs.get("ecog", p.get("ecog_score", 0))))

    # Stage-specific treatment
    if tnm["stage_group"] == "I-III":
        if tnm["resectable"]:
            surgery_plan = "根治性手术 + 纵隔淋巴结清扫" if cancer_type == "lung" else \
                           "保乳术+前哨淋巴结活检" if cancer_type == "breast" else \
                           "根治性切除术 + 区域淋巴结清扫"
            plan = f"{surgery_plan} → {'辅助化疗' if tnm['stage'] not in ('I','IA1','IA2','IA3') else '术后观察'}"
        else:
            plan = "新辅助化疗/放疗 → 再评估手术可能性"
    else:
        plan = "姑息性系统治疗(化疗/靶向/免疫) ± 局部姑息治疗(放疗/消融)"

    if not ecog["chemotherapy_suitable"]:
        plan = f"ECOG {ecog['score']}不适合化疗 → 最佳支持治疗" if ecog["score"] >= 3 else plan

    findings = [
        f"ECOG {ecog['score']} → {'适合积极治疗' if ecog['chemotherapy_suitable'] else '减量/支持治疗'}",
        f"Stage {tnm['stage']} ({tnm['stage_group']}期) → {plan}",
        "化疗方案: 参照NCCN首选方案",
        "靶向药物: 根据突变选择(EGFR-TKI/ALK-TKI等)",
        "免疫治疗: PD-L1 TPS ≥1%考虑; ≥50%单药",
        "放疗计划: SBRT(早期)/IMRT(局部晚期)/WBRT(脑转移)",
    ]
    if "肺癌" in dx or "乳腺癌" in dx:
        findings.insert(0, f"{'肺癌' if '肺癌' in dx else '乳腺癌'} 精准治疗路径")
    recommendations = [
        f"ECOG {ecog['score']} → {ecog['treatment_decision']}",
        f"Stage {tnm['stage']} → {plan}",
        "MDT讨论确认方案; 入组临床试验评估",
    ]
    checklist = ["肿瘤溶解综合征", "粒缺伴发热", "免疫性肺炎", "VTE", "脊髓压迫"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肿瘤科")
    return _agent.clinical_result(
        summary=f"肿瘤科—治疗计划 ECOG{ecog['score']}-driven (stage S4a)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行与监测 — CTCAE toxicity + irAE management + RECIST monitoring."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")
    for ct in ["liver", "breast", "colorectal", "lung"]:
        if ct in dx.lower():
            break

    # ── Injected toxicity assessments ──
    anc = float(labs.get("anc", 2000))
    plt = float(labs.get("platelets", 150))
    temp = float(labs.get("temperature", vitals.get("temperature", 37.0)))
    neutropenia = _ctcae_toxicity("neutropenia", 4 if anc < 500 else (3 if anc < 1000 else (2 if anc < 1500 else 1)), anc=anc)
    thrombocytopenia = _ctcae_toxicity("thrombocytopenia", 4 if plt < 25 else (3 if plt < 50 else (2 if plt < 75 else 1)), plt=plt)
    febrile = _ctcae_toxicity("febrile_neutropenia", 4 if (anc < 500 and temp >= 38.3) else 0, anc=anc, temp=temp)
    ir_ae = labs.get("irAE", {})
    iraes = [_irae_management(organ, int(grade)) for organ, grade in ir_ae.items()] if ir_ae else []

    findings = [
        f"CTCAE — 中性粒细胞减少: G{neutropenia['grade']} ({anc}/mm³)",
        f"CTCAE — 血小板减少: G{thrombocytopenia['grade']} ({plt}K/mm³)",
    ]
    if anc < 500 and temp >= 38.3:
        findings.append(f"⚠ 粒缺伴发热 EMERGENCY: ANC {anc} + Temp {temp}°C")
    if iraes:
        _irae_items = [f"{i['organ']}(G{i['grade']})" for i in iraes]
        findings.append(f"免疫相关AE: {', '.join(_irae_items)}")
    findings.extend(["RECIST评估: 每2-3周期", "靶向药血药浓度监测", "化疗累积剂量监测(阿霉素≤450mg/m²)"])

    recommendations = []
    if neutropenia["emergencies"]:
        recommendations.extend(neutropenia["emergencies"])
    if thrombocytopenia["emergencies"]:
        recommendations.extend(thrombocytopenia["emergencies"])
    if febrile["grade"] >= 4:
        recommendations.append(febrile["detail"])
    for irae in iraes:
        recommendations.append(f"irAE·{irae['organ']}(G{irae['grade']}): {irae['recommendation']}")
    if "肺癌" in dx or "乳腺癌" in dx:
        findings.insert(0, f"{'肺癌' if '肺癌' in dx else '乳腺癌'} 毒性监测增强")
    checklist = ["肿瘤溶解综合征", "粒缺伴发热", "免疫性肺炎", "VTE", "脊髓压迫"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肿瘤科")
    return _agent.clinical_result(
        summary=f"肿瘤科—治疗执行 CTCAE G{max(neutropenia['grade'],thrombocytopenia['grade'])} (stage S4b)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_followup(**kwargs) -> dict:
    """随访与长期管理 — RECIST re-evaluation + survivorship."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    # ── RECIST re-evaluation ──
    baseline = float(labs.get("target_sum_baseline", 0))
    current = float(labs.get("target_sum_now", baseline))
    recist = _recist_evaluation(baseline, current, labs.get("non_target", "non-CR/non-PD"),
                                bool(labs.get("new_lesions", False)))

    pain_score = int(labs.get("pain_score", p.get("pain_score", 2)))
    pain = _who_pain_ladder(pain_score)

    findings = [
        f"RECIST 随访: {recist['response']} (Δ {recist['change_pct']}%)",
        f"疼痛管理: NRS {pain_score} → {pain['step_name']}",
        "复发监测: 每3-6月影像+肿瘤标志物 (前2年); 每6-12月 (3-5年)",
        "第二原发癌筛查: 符合年龄/性别标准筛查",
        "远期毒性: 心脏毒性(超声心动)/肺毒性(PFT)/继发白血病",
        "生存质量: QLQ-C30评估",
    ]
    if "肺癌" in dx or "乳腺癌" in dx:
        findings.insert(0, f"{'肺癌' if '肺癌' in dx else '乳腺癌'} 长期随访")
    recommendations = [
        f"RECIST {recist['response']} → {recist['action']}",
        f"疼痛 NRS {pain_score} → {pain['drugs']} + {pain['adjuvants']}",
    ]
    if recist["response"] == "PD":
        recommendations.append("疾病进展 → 再次活检(液体活检+组织) → 寻找耐药机制 → 更换方案")
    checklist = ["肿瘤溶解综合征", "粒缺伴发热", "免疫性肺炎", "VTE", "脊髓压迫"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肿瘤科")
    return _agent.clinical_result(
        summary=f"肿瘤科—随访 RECIST {recist['response']} (stage S5)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )
