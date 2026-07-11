"""呼吸内科 — KnowledgeAgent-powered clinical reasoning.

Focus: 呼吸系统疾病诊疗 — pneumonia, COPD, asthma, PE, TB, lung cancer
GUIDELINES: 中国社区获得性肺炎诊疗指南（2022）, GOLD COPD, GINA Asthma, ESC PE Guidelines
Conditions: 肺炎, COPD, 哮喘, 肺栓塞, 肺结核, 肺癌, 间质性肺病

Real clinical scoring: CURB-65, PSI/PORT, GOLD ABE, GINA Steps, Wells PE, PERC, sPESI, NLST.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="respiratory", department="呼吸内科")
_GUIDELINES = [
    "中国社区获得性肺炎诊疗指南（2022）",
    "GOLD 2024 COPD 全球策略",
    "GINA 2024 哮喘全球防治策略",
    "ESC 2019 肺栓塞诊疗指南",
    "中国肺结核诊疗指南（2020）",
    "NCCN 肺癌筛查指南",
]

_agent.rule_engine.load_all()


# ── Helpers ──────────────────────────────────────────────────────────────

def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def _get_nested(patient: dict, *keys, default=0):
    """Safely traverse nested patient dict; fallback to sibling keys."""
    labs = patient.get("lab_results", patient.get("labs", {}))
    vitals = patient.get("vitals", {})
    combined = {**vitals, **labs, **{k: v for k, v in patient.items() if not isinstance(v, dict)}}
    for key in keys:
        if isinstance(key, (list, tuple)):
            for alt in key:
                val = combined.get(alt)
                if val is not None and val != "":
                    return val
        val = combined.get(key)
        if val is not None and val != "":
            return val
    return default


# ── Clinical Scoring Functions ───────────────────────────────────────────

def _calc_curb65(patient: dict) -> dict:
    """CURB-65 pneumonia severity: Confusion, Urea>7mmol/L, RR≥30, BP<90or≤60, Age≥65."""
    age = _get_nested(patient, "age", default=50)
    confusion = _get_nested(patient, "confusion", "mental_status", default=False)
    urea = _get_nested(patient, "urea", "BUN", default=5)
    rr = _get_nested(patient, "respiratory_rate", "rr", default=18)
    sbp = _get_nested(patient, "sbp", "systolic_bp", "bp_systolic", default=120)
    dbp = _get_nested(patient, "dbp", "diastolic_bp", "bp_diastolic", default=75)
    score = 0
    if confusion:
        score += 1
    if urea > 7:
        score += 1
    if int(rr) >= 30:
        score += 1
    if int(sbp) < 90 or int(dbp) <= 60:
        score += 1
    if int(age) >= 65:
        score += 1
    if score <= 1:
        management = "outpatient (low risk — mortality < 3%)"
    elif score == 2:
        management = "hospital admission (intermediate risk — mortality ~ 9%)"
    else:
        management = "severe — ICU admission (mortality 15-40%)"
    return {"score": score, "management": management, "components": {
        "confusion": bool(confusion), "urea_gt_7": urea > 7, "rr_ge_30": int(rr) >= 30,
        "bp_low": int(sbp) < 90 or int(dbp) <= 60, "age_ge_65": int(age) >= 65,
    }}


def _calc_psi_port(patient: dict) -> dict:
    """PSI/PORT score — 20 factors → class I-V, outpatient(I-II) vs inpatient(III-V)."""
    age_val = int(_get_nested(patient, "age", default=50))
    sex = _get_nested(patient, "sex", "gender", default="M")
    nursing_home = _get_nested(patient, "nursing_home", default=False)
    neoplastic = _get_nested(patient, "neoplastic_disease", "cancer", default=False)
    liver = _get_nested(patient, "liver_disease", default=False)
    chf = _get_nested(patient, "chf", "heart_failure", default=False)
    cvd = _get_nested(patient, "cerebrovascular", "cvd", default=False)
    renal = _get_nested(patient, "renal_disease", "ckd", default=False)
    ams = _get_nested(patient, "altered_mental", "confusion", default=False)
    rr = int(_get_nested(patient, "respiratory_rate", "rr", default=18))
    sbp = int(_get_nested(patient, "sbp", "systolic_bp", default=120))
    temp = float(_get_nested(patient, "temperature", "temp", default=37))
    hr = int(_get_nested(patient, "heart_rate", "hr", "pulse", default=80))
    ph = float(_get_nested(patient, "ph", "arterial_ph", default=7.40))
    bun = float(_get_nested(patient, "bun", "urea", default=5))
    na = float(_get_nested(patient, "sodium", "na", default=140))
    glucose = float(_get_nested(patient, "glucose", "blood_sugar", default=100))
    hct = float(_get_nested(patient, "hematocrit", "hct", default=40))
    pao2 = float(_get_nested(patient, "pao2", default=90))
    pleural_eff = _get_nested(patient, "pleural_effusion", default=False)

    points = age_val if sex == "M" else age_val - 10
    if nursing_home: points += 10
    if neoplastic: points += 30
    if liver: points += 20
    if chf: points += 10
    if cvd: points += 10
    if renal: points += 10
    if ams: points += 20
    if rr >= 30: points += 20
    if sbp < 90: points += 20
    if temp < 35 or temp >= 40: points += 15
    if hr >= 125: points += 10
    if ph < 7.35: points += 30
    if bun > 10.7: points += 20  # ≈ 30 mg/dL
    if na < 130: points += 20
    if glucose > 13.9: points += 10  # ≈ 250 mg/dL
    if hct < 30: points += 10
    if pao2 < 60: points += 10
    if pleural_eff: points += 10

    if points <= 50:
        risk_class = "I"
    elif points <= 70:
        risk_class = "II"
    elif points <= 90:
        risk_class = "III"
    elif points <= 130:
        risk_class = "IV"
    else:
        risk_class = "V"

    mortality = {"I": "0.1%", "II": "0.6%", "III": "0.9%", "IV": "9.3%", "V": "27%"}
    disposition = "outpatient" if risk_class in ("I", "II") else "inpatient" if risk_class in ("III", "IV") else "ICU"

    return {"score": points, "class": risk_class, "mortality": mortality[risk_class],
            "disposition": disposition, "severe": risk_class in ("IV", "V")}


def _classify_copd_gold(patient: dict) -> dict:
    """COPD GOLD ABCD → ABE: spirometry + exacerbation history + symptoms (mMRC/CAT)."""
    fev1_pct = float(_get_nested(patient, "fev1_pct", "fev1_percent", default=65))
    fev1_fvc = float(_get_nested(patient, "fev1_fvc_ratio", "fev1_fvc", default=0.55))
    exacerbations = int(_get_nested(patient, "exacerbations_per_year", "ae_per_year", default=0))
    mmrc = int(_get_nested(patient, "mmrc", default=1))
    cat = int(_get_nested(patient, "cat_score", default=10))
    hospitalized = _get_nested(patient, "exacerbation_hospitalized", "ae_hospitalized", default=False)

    # GOLD spirometry grade
    if fev1_pct >= 80:
        gold_grade = "GOLD 1 (mild)"
    elif fev1_pct >= 50:
        gold_grade = "GOLD 2 (moderate)"
    elif fev1_pct >= 30:
        gold_grade = "GOLD 3 (severe)"
    else:
        gold_grade = "GOLD 4 (very severe)"

    # GOLD ABE classification
    high_exac = exacerbations >= 2 or (hospitalized and exacerbations >= 1)
    high_symptoms = mmrc >= 2 or cat >= 10

    if high_exac:
        group = "E"
        desc = "Group E — high exacerbation risk (regardless of symptoms)"
    elif high_symptoms:
        group = "B"
        desc = "Group B — high symptom burden (mMRC ≥2 or CAT ≥10), low exacerbation risk"
    else:
        group = "A"
        desc = "Group A — low symptom burden, low exacerbation risk"

    treatment = {
        "A": "Bronchodilator (SABA/SAMA prn or LABA/LAMA)",
        "B": "LABA + LAMA combination",
        "E": "LABA + LAMA + ICS (triple therapy) if blood eosinophils ≥ 300 cells/μL; consider roflumilast/azithromycin if chronic bronchitis + frequent exacerbations",
    }

    return {"gold_grade": gold_grade, "group": group, "description": desc,
            "fev1_pct": fev1_pct, "fev1_fvc_ratio": fev1_fvc,
            "exacerbations": exacerbations, "mmrc": mmrc, "cat": cat,
            "treatment": treatment[group]}


def _gina_step(patient: dict) -> dict:
    """GINA asthma step therapy: Steps 1-5."""
    severity = _get_nested(patient, "asthma_severity", "gina_step", default="mild")
    step = int(_get_nested(patient, "gina_step", "current_step", default=2))
    symptoms_freq = _get_nested(patient, "symptom_frequency", default="intermittent")
    exacerbations = int(_get_nested(patient, "exacerbations_per_year", "ae_per_year", default=0))
    fev1_pct = float(_get_nested(patient, "fev1_pct", "fev1_percent", default=80))

    if step < 1 or step > 5:
        if fev1_pct >= 80 and exacerbations == 0:
            step = 1
        elif fev1_pct >= 60 and exacerbations <= 1:
            step = 2
        elif fev1_pct >= 50:
            step = 3
        elif fev1_pct >= 33:
            step = 4
        else:
            step = 5

    regimens = {
        1: "Step 1: As-needed low-dose ICS-formoterol (preferred) OR low-dose ICS whenever SABA taken",
        2: "Step 2: Daily low-dose ICS + as-needed SABA OR as-needed low-dose ICS-formoterol",
        3: "Step 3: Low-dose ICS-LABA maintenance + as-needed SABA OR low-dose ICS-formoterol maintenance + reliever (SMART/MART)",
        4: "Step 4: Medium-dose ICS-LABA + as-needed SABA OR medium-dose ICS-formoterol MART",
        5: "Step 5: High-dose ICS-LABA + LAMA + as-needed SABA; refer for phenotyping ± biologic (anti-IgE/anti-IL5/anti-IL4Rα) ± oral corticosteroids",
    }

    return {"step": step, "regimen": regimens[step], "fev1_pct": fev1_pct,
            "exacerbations": exacerbations, "step_up": step < 5 and exacerbations >= 2,
            "step_up_recommendation": "Consider stepping up if ≥ 2 exacerbations/year or uncontrolled symptoms despite adherence"}


def _calc_wells_pe(patient: dict) -> dict:
    """Wells PE score (two-tier): PE likely (>4) vs unlikely (≤4)."""
    age = int(_get_nested(patient, "age", default=50))
    clinical_dvt = _get_nested(patient, "dvt_signs", "clinical_dvt", default=False)
    pe_likely = _get_nested(patient, "pe_most_likely", default=False)
    hr = int(_get_nested(patient, "heart_rate", "hr", "pulse", default=80))
    immobilization = _get_nested(patient, "immobilization", "surgery_recent", default=False)
    prev_dvt_pe = _get_nested(patient, "previous_dvt_pe", "history_vte", default=False)
    hemoptysis = _get_nested(patient, "hemoptysis", default=False)
    cancer = _get_nested(patient, "active_cancer", "neoplastic", default=False)

    score = 0
    if clinical_dvt: score += 3
    if pe_likely: score += 3
    if hr > 100: score += 1.5
    if immobilization or _get_nested(patient, "recent_surgery", default=False): score += 1.5
    if prev_dvt_pe: score += 1.5
    if hemoptysis: score += 1
    if cancer: score += 1

    pe_likely_flag = score > 4
    if pe_likely_flag:
        action = "PE likely — proceed directly to CTPA (do not use PERC/D-dimer)"
    else:
        action = "PE unlikely — apply PERC rule; if PERC=0, no further testing; if PERC≥1, check age-adjusted D-dimer"

    return {"score": score, "likely": pe_likely_flag, "action": action}


def _apply_perc(patient: dict) -> dict:
    """PERC rule: 8 criteria — all must be 0 to rule out PE without D-dimer."""
    age = int(_get_nested(patient, "age", default=50))
    hr = int(_get_nested(patient, "heart_rate", "hr", "pulse", default=80))
    spo2 = float(_get_nested(patient, "spo2", "o2_saturation", default=97))
    prev_dvt_pe = _get_nested(patient, "previous_dvt_pe", "history_vte", default=False)
    surgery = _get_nested(patient, "recent_surgery", "immobilization", default=False)
    hemoptysis = _get_nested(patient, "hemoptysis", default=False)
    estrogen = _get_nested(patient, "estrogen_use", "ocp", default=False)
    unilateral_swelling = _get_nested(patient, "unilateral_leg_swelling", "clinical_dvt", default=False)

    criteria = 0
    if age >= 50: criteria += 1
    if hr >= 100: criteria += 1
    if spo2 < 95: criteria += 1
    if prev_dvt_pe: criteria += 1
    if surgery: criteria += 1
    if hemoptysis: criteria += 1
    if estrogen: criteria += 1
    if unilateral_swelling: criteria += 1

    rule_out = criteria == 0
    return {"perc_criteria": criteria, "rule_out": rule_out, "total": 8,
            "action": "PE ruled out — no D-dimer needed" if rule_out else f"PERC {criteria}/8: order age-adjusted D-dimer → if positive → CTPA"}


def _calc_spesi(patient: dict) -> dict:
    """sPESI (simplified PESI) for outpatient PE management."""
    age = int(_get_nested(patient, "age", default=50))
    cancer = _get_nested(patient, "active_cancer", "neoplastic", default=False)
    cpf = _get_nested(patient, "chronic_cardiopulmonary", "cpf", default=False)
    hr = int(_get_nested(patient, "heart_rate", "hr", "pulse", default=80))
    sbp = int(_get_nested(patient, "sbp", "systolic_bp", default=120))
    spo2 = float(_get_nested(patient, "spo2", "o2_saturation", default=95))

    points = 0
    if age > 80: points += 1
    if cancer: points += 1
    if cpf: points += 1
    if hr >= 110: points += 1
    if sbp < 100: points += 1
    if spo2 < 90: points += 1

    low_risk = points == 0
    return {"score": points, "low_risk": low_risk,
            "recommendation": "outpatient management / early discharge (30-day mortality < 1%)" if low_risk else "inpatient management (30-day mortality 10.9%)",
            "components": {"age_gt_80": age > 80, "cancer": bool(cancer), "cpf": bool(cpf),
                           "hr_ge_110": hr >= 110, "sbp_lt_100": sbp < 100, "spo2_lt_90": spo2 < 90}}


def _nlst_screen(patient: dict) -> dict:
    """Lung cancer screening — NLST criteria: age 50-80, ≥30 pack-years, quit<15yr → annual LDCT."""
    age = int(_get_nested(patient, "age", default=55))
    pack_years = int(_get_nested(patient, "pack_years", "smoking_pack_years", default=20))
    quit_years = _get_nested(patient, "years_since_quit", "quit_years", default=None)
    current_smoker = _get_nested(patient, "current_smoker", default=False)

    eligible = age >= 50 and age <= 80 and pack_years >= 30
    if not current_smoker and quit_years is not None:
        eligible = eligible and int(quit_years) < 15

    return {"eligible": eligible, "age": age, "pack_years": pack_years,
            "recommendation": "Annual LDCT (low-dose CT) screening indicated" if eligible else "No LDCT screening — does not meet NLST criteria",
            "criteria": "Age 50-80 + ≥ 30 pack-years + currently smoking or quit within 15 years"}


def _tb_algorithm(patient: dict) -> dict:
    """TB diagnostic algorithm: IGRA vs TST, Xpert MTB/RIF, smear/culture, LTBI treatment."""
    tst = float(_get_nested(patient, "tst_mm", "tst_induration", default=0))
    igra = _get_nested(patient, "igra", "quantiferon", default="negative")
    xpert = _get_nested(patient, "xpert_mtb", "genexpert", default="not done")
    smear = _get_nested(patient, "afb_smear", "smear", default="negative")
    culture = _get_nested(patient, "mycobacterium_culture", default="pending")
    symptoms = _get_nested(patient, "cough_weeks", "tb_symptoms", default=0)
    cxr = _get_nested(patient, "cxr_abnormal", "chest_xray_abnormal", default=False)

    active_tb = False
    if xpert == "MTB detected" or smear == "positive" or (cxr and int(symptoms) >= 2):
        active_tb = True

    ltbi = False
    if not active_tb and (igra == "positive" or tst >= 10):
        ltbi = True

    result = {"active_tb": active_tb, "latent_tb": ltbi, "igra": igra, "tst_mm": tst}

    if active_tb:
        rif_resist = "RIF resistance detected" in str(xpert) if xpert else False
        result["regimen"] = "RIPE (2HRZE/4HR) — isoniazid + rifampin + pyrazinamide + ethambutol × 2mo → INH + RIF × 4mo"
        if rif_resist:
            result["regimen"] = "⚠ RIF-resistant: refer for MDR-TB regimen (BPaLM: bedaquiline + pretomanid + linezolid ± moxifloxacin × 6mo)"
        result["action"] = "Initiate airborne isolation (negative pressure), contact investigation, public health notification"
    elif ltbi:
        result["regimen"] = "3HP (isoniazid + rifapentine weekly × 12 weeks — preferred) OR 4R (rifampin daily × 4mo)"
        result["action"] = "Rule out active TB with CXR + symptom screen before starting LTBI treatment"
    else:
        result["regimen"] = "N/A"
        result["action"] = "No TB infection — no treatment needed"

    return result


# ── Business Process Functions ───────────────────────────────────────────

def bp_reception(**kwargs) -> dict:
    """接诊与初步评估 — CURB-65 triage for pneumonia, symptom stratification."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", p.get("labs", {}))
    dx = p.get("diagnosis", "")

    findings = ["呼吸症状: 咳嗽 / 咳痰 / 呼吸困难 / 胸痛 — onset + duration + character",
                f"生命体征: SpO₂={vitals.get('spo2','?')}%, RR={vitals.get('respiratory_rate','?')}/min, HR={vitals.get('heart_rate','?')}/min",
                "危险因素: 吸烟史 / 职业暴露 / TB接触史 / 免疫抑制 / 近期住院"]

    # CURB-65 for pneumonia
    if any(t in dx for t in ["肺炎", "pneumonia"]):
        curb = _calc_curb65(p)
        findings.insert(0, f"CURB-65: {curb['score']}/5 → {curb['management']}")
        if curb["score"] >= 3:
            findings.insert(0, "⚠ SEVERE PNEUMONIA — ICU admission, blood cultures × 2, combination antibiotics within 1h")

    # COPD triage
    if any(t in dx for t in ["COPD", "慢阻肺"]):
        gold = _classify_copd_gold(p)
        findings.append(f"COPD GOLD: {gold['gold_grade']} / Group {gold['group']} — {gold['description']}")

    # PE suspicion
    if any(t in dx for t in ["肺栓塞", "PE", "pulmonary embolism"]):
        wells = _calc_wells_pe(p)
        perc = _apply_perc(p)
        findings.insert(0, f"Wells PE: {wells['score']}/12.5 → {'PE LIKELY — CTPA directly' if wells['likely'] else 'PE unlikely — ' + perc['action']}")

    recommendations = []
    if vitals.get("spo2", 96) < 92:
        recommendations.append("O₂ supplementation to target SpO₂ 92-96% (88-92% if COPD/hypercapnic risk)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("呼吸内科")
    return _agent.clinical_result(
        patient=p, stage="triage",
        summary=f"呼吸内科 — 接诊完成 (CURB-65={_calc_curb65(p)['score'] if any(t in dx for t in ['肺炎']) else 'N/A'})",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """辅助检查 — evidence-based diagnostic testing."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "胸部 X 光 (CXR): PA + lateral — infiltrate / consolidation / effusion / mass",
        "CT chest: high-resolution for ILD; CTPA for PE; contrast-enhanced for malignancy staging",
        "肺功能: spirometry (FEV1/FVC + bronchodilator response), DLCO, lung volumes",
        "动脉血气 (ABG): PaO₂/PaCO₂/pH — assess respiratory failure type",
        "实验室: CBC, CRP, PCT, sputum Gram stain + culture, blood cultures × 2",
    ]

    # Disease-specific exam
    if any(t in dx for t in ["肺栓塞", "PE"]):
        findings.insert(0, "⚠ PE workup: Wells → PERC/D-dimer → CTPA (PIOPED II protocol); bilateral LE ultrasound if DVT suspected")
        wells = _calc_wells_pe(p)
        findings.append(f"Wells PE: {wells['score']} → {wells['action']}")

    if any(t in dx for t in ["肺结核", "TB"]):
        findings.insert(0, "TB workup: CXR (apical infiltrates/cavitation) → sputum AFB × 3 → Xpert MTB/RIF → culture + DST")
        findings.append("IGRA (QuantiFERON-TB Gold) or TST for latent TB screening")

    if any(t in dx for t in ["肺癌", "lung cancer"]):
        nlst = _nlst_screen(p)
        findings.append(f"肺癌筛查: {nlst['recommendation']} ({nlst['age']}yo, {nlst['pack_years']} pack-years)")
        findings.append("Tissue diagnosis: bronchoscopy (EBUS-TBNA) for central; CT-guided biopsy for peripheral; mediastinoscopy for staging")

    recommendations = ["CXR within 4h for suspected pneumonia", "Sputum culture BEFORE antibiotics (if possible)"]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("呼吸内科")
    return _agent.clinical_result(
        patient=p, stage="exam",
        summary="呼吸内科 — 辅助检查完成",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断确诊 — comprehensive scoring: CURB-65, PSI, GOLD, GINA, Wells, sPESI."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", p.get("labs", {}))
    dx = p.get("diagnosis", "")

    findings = []
    recommendations = []

    # Pneumonia
    if any(t in dx for t in ["肺炎", "pneumonia"]):
        curb = _calc_curb65(p)
        psi = _calc_psi_port(p)
        findings.append(f"CURB-65: {curb['score']}/5 — {curb['management']} (mort ~ {curb['score']} pts)")
        findings.append(f"PSI/PORT: Class {psi['class']} (score {psi['score']}) — mortality {psi['mortality']}, disposition: {psi['disposition']}")
        if curb["score"] >= 3 or psi["class"] in ("IV", "V"):
            recommendations.append("Empiric antibiotics: beta-lactam + macrolide OR respiratory fluoroquinolone (CAP)")
            recommendations.append("ICU: blood cultures × 2, Legionella/Pneumococcal urinary Ag, procalcitonin-guided antibiotic duration")
        else:
            recommendations.append("Outpatient antibiotics: amoxicillin 1g TID OR doxycycline 100mg BID × 5-7 days")

    # COPD
    if any(t in dx for t in ["COPD", "慢阻肺"]):
        gold = _classify_copd_gold(p)
        findings.append(f"GOLD 2024: {gold['gold_grade']} / Group {gold['group']}")
        findings.append(f"FEV1: {gold['fev1_pct']}% predicted, FEV1/FVC: {gold['fev1_fvc_ratio']}")
        findings.append(f"Exacerbations: {gold['exacerbations']}/yr, mMRC: {gold['mmrc']}, CAT: {gold['cat']}")
        findings.append(f"Treatment: {gold['treatment']}")
        recommendations.append("Smoking cessation counseling (most effective intervention)")
        recommendations.append("Annual influenza + pneumococcal vaccination")

    # Asthma
    if any(t in dx for t in ["哮喘", "asthma"]):
        gina = _gina_step(p)
        findings.append(f"GINA Step: {gina['step']} — {gina['regimen']}")
        if gina["step_up"]:
            recommendations.append("Consider stepping up: uncontrolled symptoms or ≥ 2 exacerbations/yr despite adherence")

    # PE
    if any(t in dx for t in ["肺栓塞", "PE"]):
        wells = _calc_wells_pe(p)
        spesi = _calc_spesi(p)
        findings.append(f"Wells PE: {wells['score']}/12.5 → {'likely' if wells['likely'] else 'unlikely'}")
        findings.append(f"sPESI: {spesi['score']} — {spesi['recommendation']}")
        if spesi["low_risk"]:
            recommendations.append("Consider outpatient DOAC management (rivaroxaban 15mg BID × 21d → 20mg daily OR apixaban 10mg BID × 7d → 5mg BID)")
            recommendations.append("Early mobilization + compression stockings")
        else:
            recommendations.append("Inpatient: LMWH bridge to warfarin OR DOAC; consider catheter-directed thrombolysis if massive PE with shock")
            recommendations.append("Echocardiogram: assess RV strain (RV/LV ratio ≥ 1.0 = submassive PE → consider thrombolysis)")

    # TB
    if any(t in dx for t in ["肺结核", "TB"]):
        tb = _tb_algorithm(p)
        findings.append(f"TB: {'ACTIVE — ' + tb['regimen'] if tb['active_tb'] else 'LATENT — ' + tb['regimen'] if tb['latent_tb'] else 'No TB infection'}")
        findings.append(tb["action"])

    # Lung cancer screening
    if any(t in dx for t in ["肺癌", "lung cancer"]):
        nlst = _nlst_screen(p)
        findings.append(nlst["recommendation"])

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("呼吸内科")
    return _agent.clinical_result(
        patient=p, stage="diagnosis",
        summary=f"呼吸内科 — 诊断确诊完成 ({dx})",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_plan(**kwargs) -> dict:
    """治疗方案制定 — disease-specific treatment protocols."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = ["抗生素方案 / 支气管扩张剂 / 抗凝方案 分层选择", "剂量: CrCl 调整 (DOAC / beta-lactam / fluoroquinolone)",
                "疗程: CAP 5-7d, COPD AE 5d corticosteroids, PE 3-6mo indefinite if unprovoked",
                "辅助: O₂ 目标 / 胸部理疗 / 肺康复 / 营养支持"]
    recommendations = []

    if any(t in dx for t in ["肺炎"]):
        curb = _calc_curb65(p)
        findings.insert(0, f"CAP empiric Rx: CURB-65={curb['score']} → {'outpatient oral' if curb['score'] <= 1 else 'inpatient IV'} antibiotics")
    if any(t in dx for t in ["COPD"]):
        gold = _classify_copd_gold(p)
        findings.insert(0, f"COPD maintenance: {gold['treatment']}")
    if any(t in dx for t in ["哮喘"]):
        gina = _gina_step(p)
        findings.insert(0, f"Asthma: {gina['regimen'][:60]}...")
    if any(t in dx for t in ["肺栓塞", "PE"]):
        spesi = _calc_spesi(p)
        findings.insert(0, f"PE anticoagulation: {'outpatient DOAC' if spesi['low_risk'] else 'inpatient — LMWH/UFH bridge'}")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("呼吸内科")
    return _agent.clinical_result(
        patient=p, stage="plan",
        summary=f"呼吸内科 — 治疗方案完成",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行与监测 — treatment response, de-escalation, adverse effects."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "抗生素管理: IV→PO switch criteria (afebrile × 48h, stable vitals, tolerating PO, WBC trending down)",
        "PCT 监测: procalcitonin-guided antibiotic cessation (stop if PCT < 0.25 μg/L or decrease > 80% from peak)",
        "不良反应: C. difficile colitis risk (diarrhea), QT prolongation (macrolides/fluoroquinolones), hepatotoxicity (INH/RIF/PZA)",
        "呼吸支持: O₂ weaning protocol, BiPAP/CPAP for hypercapnic respiratory failure, escalation to IMV criteria",
    ]
    recommendations = [
        "Daily spontaneous awakening trial + spontaneous breathing trial (SAT/SBT) if ventilated",
        "Thromboprophylaxis: enoxaparin 40mg SC daily or UFH 5000U TID unless PE (therapeutic dose)",
        "Nutrition: enteral feeding within 24-48h of ICU admission if no contraindication",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("呼吸内科")
    return _agent.clinical_result(
        patient=p, stage="treatment",
        summary="呼吸内科 — 治疗执行监测完成",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """随访与长期管理 — disease monitoring, LTOT, rehab, screening."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    spo2 = vitals.get("spo2", 95)

    findings = [
        "症状监测: cough/sputum/dyspnea diary, exacerbation frequency tracking",
        f"肺功能随访: spirometry q3-12mo (COPD/asthma), DLCO if ILD",
        "影像: CXR at clinical follow-up; CT at 3-6mo for pneumonia resolution / lung nodule surveillance (Fleishner criteria)",
        "康复: 肺康复 program (endurance + strength + education + nutrition) — grade 1A evidence for COPD",
    ]
    recommendations = []

    if spo2 <= 88 and (_get_nested(p, "resting_spo2", default=96) <= 88):
        recommendations.append("LTOT (长期氧疗) evaluation: PaO₂ ≤ 55 mmHg or SpO₂ ≤ 88%; O₂ ≥ 15h/day reduces mortality in COPD (NOTT/MRC trials)")

    if any(t in dx for t in ["肺栓塞", "PE"]):
        spesi = _calc_spesi(p)
        findings.append(f"sPESI at follow-up: {spesi['score']} — {'continue outpatient' if spesi['low_risk'] else 'ongoing monitoring'}")
        recommendations.append("Anticoagulation duration: 3mo if provoked, ≥ 6mo if unprovoked, indefinite if recurrent or persistent risk factors")
        recommendations.append("CTEPH screening: echo at 3-6mo post-PE if persistent dyspnea (chronic thromboembolic pulmonary hypertension)")

    if any(t in dx for t in ["肺癌"]):
        recommendations.append("LDCT surveillance: annual if NLST-eligible (age 50-80, ≥ 30 pack-years)")
        recommendations.append("Nodule follow-up per Fleishner guidelines: <6mm solid → no follow-up; 6-8mm → CT 6-12mo; >8mm → PET/CT ± biopsy")

    if any(t in dx for t in ["肺结核", "TB"]):
        tb = _tb_algorithm(p)
        if tb["active_tb"]:
            findings.append(f"TB treatment monitoring: monthly sputum smear/culture until 2 consecutive negative; LFTs monthly (INH/RIF/PZA hepatotoxicity)")
            recommendations.append("Directly Observed Therapy (DOT) recommended; contact tracing for household + close contacts")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("呼吸内科")
    return _agent.clinical_result(
        patient=p, stage="followup",
        summary="呼吸内科 — 随访管理完成",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )
