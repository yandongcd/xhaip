"""心血管内科 — KnowledgeAgent-powered clinical reasoning.

GUIDELINES: 中国心衰指南2024, 中国高血压指南2024, AHA/ACC, ESC Guidelines

Injected clinical scoring systems:
  CHA₂DS₂-VASc — CHF(1) + HTN(1) + Age≥75(2) + DM(1) + Stroke(2) + Vascular(1) + Age65-74(1) + Sex(F=1) → anticoagulation
  HAS-BLED — HTN(1) + Renal(1) + Liver(1) + Stroke(1) + Bleeding(1) + LabileINR(1) + Elderly(1) + Drugs/Alcohol(1-2) → bleeding risk
  Killip class — I(noHF) / II(rales<50%) / III(edema) / IV(shock) — post-MI prognosis
  NYHA functional class — I(no limit) / II(mild) / III(marked) / IV(at rest)
  TIMI risk score — 0-2=low / 3-4=intermediate / 5-7=high for UA/NSTEMI
  Heart Failure GDMT — HFrEF(EF≤40%) ARNI→BB→MRA→SGLT2i 四联疗法 with target doses
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="cardiology", department="心血管内科")
_GUIDELINES = [
    "中国心力衰竭诊断和治疗指南 (2024)",
    "中国高血压防治指南 (2024)",
    "AHA/ACC/HFSA 2022 Heart Failure Guideline",
    "ESC 2021 Heart Failure Guidelines",
]

_agent.rule_engine.load_all()


# ── CHA₂DS₂-VASc ───────────────────────────────────────────────────────

def calculate_chads2_vasc(chf: bool = False, htn: bool = False,
                           age: int = 60, dm: bool = False,
                           prior_stroke_tia_te: bool = False,
                           vascular_disease: bool = False,
                           sex_female: bool = False) -> dict:
    """CHA₂DS₂-VASc score for atrial fibrillation stroke risk.

    Score: 0=low (no anticoagulation needed)
           1=male → consider OAC; female=1 → consider OAC (if only female sex, may not need OAC per ESC)
           ≥2 → OAC recommended (Class I)

    Ref: ESC 2020 AF Guidelines, AHA/ACC/HRS 2023.
    """
    items = {
        "CHF/LVEF≤40%":     (1 if chf else 0, chf),
        "Hypertension":      (1 if htn else 0, htn),
        "Age ≥75":            (2 if age >= 75 else 0, age >= 75),
        "Diabetes Mellitus":  (1 if dm else 0, dm),
        "Stroke/TIA/TE":      (2 if prior_stroke_tia_te else 0, prior_stroke_tia_te),
        "Vascular disease":   (1 if vascular_disease else 0, vascular_disease),
        "Age 65-74":          (1 if 65 <= age < 75 else 0, 65 <= age < 75),
        "Female sex":         (1 if sex_female else 0, sex_female),
    }
    total = sum(v[0] for v in items.values())

    # ESC 2020 guidelines: class IIa for male=1, IIb for female=1 (if only sex factor)
    only_sex_factor = total == 1 and sex_female
    if total == 0:
        recommendation = "No antithrombotic therapy (unless other indications)"
        class_rec = "—"
    elif only_sex_factor:
        recommendation = "Consider no OAC — only risk factor is female sex (ESC IIb)"
        class_rec = "IIb"
    elif total == 1:
        recommendation = "Consider OAC (ESC IIa — NOAC preferred over VKA)"
        class_rec = "IIa"
    else:
        recommendation = "OAC recommended (ESC Class I — NOAC preferred over VKA)"
        class_rec = "I"

    return {
        "chads2_vasc": total,
        "items": {k: v[0] for k, v in items.items()},
        "anticoagulation_recommended": total >= 2 or (total == 1 and not only_sex_factor),
        "recommendation": recommendation,
        "class_of_recommendation": class_rec,
        "stroke_risk_annual": {
            0: "0%", 1: "~1.3%", 2: "~2.2%", 3: "~3.2%",
            4: "~4.0%", 5: "~6.7%", 6: "~9.8%", 7: "~9.6%",
            8: "~6.7%", 9: "~15.2%",
        }.get(total, ">15%"),
    }


# ── HAS-BLED ────────────────────────────────────────────────────────────

def calculate_has_bled(htn_uncontrolled: bool = False,
                        renal_disease: bool = False,
                        liver_disease: bool = False,
                        prior_stroke: bool = False,
                        prior_bleeding: bool = False,
                        labile_inr: bool = False,
                        age_gt_65: bool = False,
                        antiplatelet_nsaid: bool = False,
                        alcohol_excess: bool = False,
                        cr_dialysis: bool = False,
                        lft_abnormal: bool = False) -> dict:
    """HAS-BLED score for bleeding risk on OAC.

    ≥3 = high bleeding risk → caution with OAC; address modifiable risk factors.
    Maximum = 9.

    Note: HAS-BLED ≥3 does NOT contraindicate OAC — it identifies patients needing
    closer monitoring and modifiable risk factor correction.
    """
    items = {
        "Hypertension (uncontrolled, SBP>160)":     (1 if htn_uncontrolled else 0),
        "Renal disease (Cr>200/CKD/dialysis)":       (1 if (renal_disease or cr_dialysis) else 0),
        "Liver disease (cirrhosis/bil>2x + ALT>3x)": (1 if (liver_disease or lft_abnormal) else 0),
        "Stroke history":                             (1 if prior_stroke else 0),
        "Bleeding history/predisposition":            (1 if prior_bleeding else 0),
        "Labile INR (TTR<60%)":                       (1 if labile_inr else 0),
        "Elderly (age>65)":                           (1 if age_gt_65 else 0),
        "Drugs (antiplatelet/NSAID)":                 (1 if antiplatelet_nsaid else 0),
        "Alcohol (≥8 drinks/week)":                   (1 if alcohol_excess else 0),
    }
    total = sum(items.values())
    high_risk = total >= 3

    return {
        "has_bled": total,
        "items": items,
        "high_bleeding_risk": high_risk,
        "bleeding_risk_annual": {
            0: "~0.9%", 1: "~1.0%", 2: "~1.9%",
            3: "~3.7%", 4: "~5.9%", 5: "~8.7%",
        }.get(total, ">10%"),
        "recommendation": (
            "HAS-BLED ≥3 — high bleeding risk. "
            "Address modifiable factors: BP control, reduce NSAID, limit alcohol, "
            "optimize INR control. DOES NOT contraindicate OAC — continue with close monitoring."
        ) if high_risk else (
            "HAS-BLED <3 — acceptable bleeding risk for OAC"
        ),
        "modifiable_factors": [k for k, v in items.items() if v == 1 and k in (
            "Hypertension (uncontrolled, SBP>160)",
            "Labile INR (TTR<60%)",
            "Drugs (antiplatelet/NSAID)",
            "Alcohol (≥8 drinks/week)",
        )],
    }


# ── Killip Classification ───────────────────────────────────────────────

KILLIP_CLASSES = {
    1: ("Killip I", "No signs of heart failure", "~6%"),
    2: ("Killip II", "Rales/jugular venous distension (<50% lung fields), S3 gallop", "~17%"),
    3: ("Killip III", "Acute pulmonary edema (rales ≥50% lung fields)", "~38%"),
    4: ("Killip IV", "Cardiogenic shock (SBP<90, oliguria, cyanosis, cold/clammy)", "~81%"),
}

def classify_killip(has_rales: bool = False,
                     rales_extent_pct: float = 0,
                     has_pulmonary_edema: bool = False,
                     sbp: float = 120,
                     has_shock_signs: bool = False) -> dict:
    """Killip classification for acute MI prognosis."""
    if has_shock_signs and sbp < 90:
        klass = 4
    elif has_pulmonary_edema or has_rales and rales_extent_pct >= 50:
        klass = 3
    elif has_rales and rales_extent_pct < 50:
        klass = 2
    else:
        klass = 1

    name, desc, mortality = KILLIP_CLASSES[klass]
    return {
        "killip_class": klass,
        "name": name,
        "description": desc,
        "in_hospital_mortality": mortality,
        "findings": {
            "rales": has_rales,
            "rales_extent_lt_50pct": has_rales and rales_extent_pct < 50,
            "rales_extent_ge_50pct": has_rales and rales_extent_pct >= 50,
            "pulmonary_edema": has_pulmonary_edema,
            "sbp": sbp,
            "shock_signs": has_shock_signs,
        },
        "action": {
            1: "Standard post-MI care, monitor for progression",
            2: "Diuretics + afterload reduction, monitor SpO2, consider NIV if needed",
            3: "Aggressive diuresis + vasodilators, NIV/ventilation, consider Swan-Ganz",
            4: "Urgent revascularization, IABP/Impella, inotropes/vasopressors",
        }.get(klass, ""),
    }


# ── NYHA Functional Classification ─────────────────────────────────────

NYHA_CLASSES = {
    1: ("NYHA I", "No limitation — ordinary physical activity does not cause undue fatigue, palpitation, or dyspnea",
        "GC (良好)"),
    2: ("NYHA II", "Slight limitation — comfortable at rest; ordinary activity causes fatigue, palpitation, dyspnea",
        "GC (良好)"),
    3: ("NYHA III", "Marked limitation — comfortable at rest; less than ordinary activity causes symptoms",
        "GC (中等)"),
    4: ("NYHA IV", "Unable to carry on any physical activity without discomfort; symptoms at rest",
        "GC (差)"),
}

def classify_nyha(nyha: int) -> dict:
    """NYHA functional classification for heart failure."""
    if nyha not in NYHA_CLASSES:
        nyha = 2
    name, desc, prognosis = NYHA_CLASSES[nyha]
    return {
        "nyha_class": nyha,
        "name": name,
        "description": desc,
        "prognosis": prognosis,
        "gdmt_indication": "GDMT 四联疗法适用" if nyha >= 2 else "Risk factor management + surveillance",
    }


# ── TIMI Risk Score (UA/NSTEMI) ────────────────────────────────────────

def calculate_timi_ua_nstemi(age_ge_65: bool = False,
                              cad_risk_factors_ge_3: bool = False,
                              known_cad_stenosis_ge_50: bool = False,
                              asa_use_7d: bool = False,
                              severe_angina_ge_2_24h: bool = False,
                              st_deviation_ge_0_5mm: bool = False,
                              elevated_cardiac_markers: bool = False) -> dict:
    """TIMI risk score for UA/NSTEMI.

    Each risk factor = 1 point. Range 0-7.
    0-2 = low risk, 3-4 = intermediate, 5-7 = high risk.
    """
    items = {
        "Age ≥65":                         (1 if age_ge_65 else 0),
        "≥3 CAD risk factors":             (1 if cad_risk_factors_ge_3 else 0),
        "Known CAD (stenosis ≥50%)":       (1 if known_cad_stenosis_ge_50 else 0),
        "ASA use in past 7 days":          (1 if asa_use_7d else 0),
        "≥2 angina episodes in 24h":       (1 if severe_angina_ge_2_24h else 0),
        "ST deviation ≥0.5mm":             (1 if st_deviation_ge_0_5mm else 0),
        "Elevated cardiac markers (TnI/TnT/CK-MB)": (1 if elevated_cardiac_markers else 0),
    }
    total = sum(items.values())

    if total <= 2:
        risk, dapt, invasive = "low", "consider", "not routinely"
        event_rate = "<8.3%"
    elif total <= 4:
        risk, dapt, invasive = "intermediate", "recommended", "within 72h"
        event_rate = "~12.8-19.9%"
    else:
        risk, dapt, invasive = "high", "strongly recommended", "within 24h"
        event_rate = ">26.2%"

    return {
        "timi_score": total,
        "items": items,
        "risk_stratum": risk,
        "dapt_recommendation": dapt,
        "invasive_strategy": invasive,
        "event_rate_14d": event_rate,
        "action": (
            f"TIMI={total} ({risk} risk) — {dapt} DAPT, invasive strategy {invasive}, "
            f"14-day event rate {event_rate}"
        ),
    }


# ── Heart Failure GDMT ─────────────────────────────────────────────────

HFREF_GDMT = [
    {
        "class": "ARNI/ACEi/ARB",
        "drugs": ["Sacubitril/Valsartan (沙库巴曲缬沙坦)", "Enalapril", "Ramipril", "Candesartan"],
        "target_dose": "Sac/Val 97/103mg BID  or  Enalapril 20mg BID",
        "evidence": "PARADIGM-HF (ARNI vs Enalapril — 20% RRR in CV death/HF hosp)",
        "indication": "ARNI preferred as first-line over ACEi/ARB (ACC 2022 Class I)",
        "sequence": 1,
    },
    {
        "class": "Beta-Blocker",
        "drugs": ["Bisoprolol", "Carvedilol", "Metoprolol succinate"],
        "target_dose": "Bisoprolol 10mg QD / Carvedilol 50mg BID / Metoprolol succinate 200mg QD",
        "evidence": "CIBIS-II (34% RRR mortality), MERIT-HF, COPERNICUS",
        "indication": "Start with low dose, uptitrate every 2 weeks",
        "sequence": 2,
    },
    {
        "class": "MRA (Mineralocorticoid Receptor Antagonist)",
        "drugs": ["Spironolactone", "Eplerenone"],
        "target_dose": "Spironolactone 25-50mg QD / Eplerenone 50mg QD",
        "evidence": "RALES (30% RRR mortality), EMPHASIS-HF",
        "indication": "Contraindicated if eGFR<30 or K+>5.0",
        "sequence": 3,
    },
    {
        "class": "SGLT2i",
        "drugs": ["Dapagliflozin (达格列净)", "Empagliflozin (恩格列净)"],
        "target_dose": "Dapagliflozin 10mg QD / Empagliflozin 10mg QD",
        "evidence": "DAPA-HF (26% RRR CV death/HF hosp), EMPEROR-Reduced",
        "indication": "Class I regardless of DM status (ACC/AHA 2022)",
        "sequence": 4,
    },
]

def hfref_gdmt_recommendation(ef_pct: float = 25, systolic_bp: float = 120,
                                egfr: float = 60, k: float = 4.0,
                                nyha: int = 2) -> dict:
    """Heart Failure with reduced EF (HFrEF, EF≤40%) GDMT recommendation.

    Four pillars: ARNI → BB → MRA → SGLT2i.
    """
    is_hfref = ef_pct <= 40
    if not is_hfref:
        return {
            "gdmt_applicable": False,
            "ef": ef_pct,
            "type": f"HFpEF (EF>{40}%)" if ef_pct > 50 else "HFmrEF (EF 41-49%)",
            "recommendation": "SGLT2i (EMPEROR-Preserved, DELIVER) + diuretics, treat underlying cause",
        }

    # Check contraindications
    contraindications = {}
    if systolic_bp < 90:
        contraindications["ARNI/ACEi/ARB"] = "SBP<90 — relative contraindication for RASi"
    if egfr < 30:
        contraindications["MRA"] = f"eGFR={egfr} <30 — contraindicated for MRA"
    if k > 5.0:
        contraindications["MRA"] = f"K+={k} >5.0 — contraindicated for MRA"

    applicable_pillars = []
    for pillar in HFREF_GDMT:
        if pillar["class"] not in contraindications:
            applicable_pillars.append({
                **pillar,
                "contraindicated": False,
            })

    return {
        "gdmt_applicable": True,
        "ef": ef_pct,
        "type": "HFrEF (EF≤40%)",
        "nyha": nyha,
        "pillars": applicable_pillars,
        "contraindications": [f"{drug}: {reason}" for drug, reason in contraindications.items()],
        "total_pillars": len(applicable_pillars),
        "sequence": "ARNI/ACEi/ARB → Beta-Blocker → MRA → SGLT2i",
        "recommendation": (
            f"HFrEF GDMT: start {len(applicable_pillars)}/4 pillars, "
            f"titrate to target doses over 4-8 weeks. "
            f"Reassess EF at 3 months."
        ),
        "target_doses": [f"{p['class']}: {p['target_dose']}" for p in applicable_pillars],
        "evidence": [f"{p['class']}: {p['evidence'][:60]}" for p in applicable_pillars],
        "additional": [
            "Loop diuretics for congestion (furosemide/torsemide)",
            "Ivabradine if sinus rhythm + HR≥70 on max tolerated BB",
            "Hydralazine + ISDN if African-American (A-HeFT)",
            "Digoxin if persistent symptoms despite GDMT",
            "CRT-D if LBBB + QRS≥150ms + EF≤35%",
            "ICD if EF≤35% after ≥3 months GDMT (primary prevention)",
        ],
    }


# ── Utility ─────────────────────────────────────────────────────────────

def extract_vitals(patient: dict) -> dict:
    labs = patient.get("lab_results", {}) if patient else {}
    def _f(key, default=0):
        try:
            return float(labs.get(key, default) or default)
        except (ValueError, TypeError):
            return default
    def _i(key, default=0):
        try:
            return int(_f(key, default))
        except Exception:
            return default
    return {
        "pulse":  _f("pulse", _f("HR", 0)),
        "sbp":    _f("sbp", _f("sBP", _f("SBP", 0))),
        "rr":     _f("rr", _f("RR", 0)),
        "temp":   _f("temp", _f("TEMP", 0)),
        "spo2":   _f("spo2", _f("SpO2", 0)),
        "troponin": _f("Troponin", _f("troponin", 0)),
        "bnp":    _f("BNP", _f("NT-proBNP", _f("bnp", 0))),
        "cr":     _f("Cr", _f("creatinine", 0)),
        "k":      _f("K+", _f("k", 0)),
        "egfr":   _f("eGFR", _f("egfr", 60)),
        "ef":     _f("EF", _f("ef", _f("LVEF", 55))),
    }


# ── Pipeline Handlers (injected with cardiology scoring systems) ───────

def bp_reception(**kwargs) -> dict:
    """接诊评估 — CHADS-VASc + HAS-BLED + NYHA + GDMT screening."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None, guidelines=_GUIDELINES)

    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)
    dx = p.get("diagnosis", "")
    age = int(p.get("age", 60) or 60)
    gender = p.get("gender", "male") or "male"
    ef = v["ef"] or 55

    # CHADS-VASc
    chads = calculate_chads2_vasc(
        chf=("心衰" in dx or "HF" in dx.upper()),
        htn=("高血压" in dx or "HTN" in dx.upper()),
        age=age,
        dm=("糖尿病" in dx or "DM" in dx.upper()),
        prior_stroke_tia_te=("卒中" in dx or "脑梗" in dx or "TIA" in dx.upper()),
        sex_female=(gender.lower() in ("female", "f", "女")),
    )
    # HAS-BLED
    has_bled = calculate_has_bled(
        htn_uncontrolled=v["sbp"] > 160,
        age_gt_65=age > 65,
    )
    # NYHA
    nyha = classify_nyha(2)  # default NYHA II
    # GDMT
    gdmt = hfref_gdmt_recommendation(
        ef_pct=ef, systolic_bp=v["sbp"], egfr=v["egfr"], k=v["k"], nyha=nyha["nyha_class"],
    )

    recommendations = [
        f"CHA₂DS₂-VASc={chads['chads2_vasc']}: {chads['recommendation']}",
        f"HAS-BLED={has_bled['has_bled']}: monitor modifiable factors",
    ]
    if gdmt["gdmt_applicable"]:
        recommendations.append(gdmt["recommendation"])

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("心血管内科")
    return _agent.clinical_result(
        summary=f"接诊评估 — CHA₂DS₂-VASc={chads['chads2_vasc']} HAS-BLED={has_bled['has_bled']} EF={ef}%",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_exam(**kwargs) -> dict:
    """心脏辅助检查 — CHADS-VASc/HAS-BLED based risk stratification for exam planning."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    dx = p.get("diagnosis", "")
    age = int(p.get("age", 60) or 60)

    chads = calculate_chads2_vasc(
        chf=("心衰" in dx), age=age,
        prior_stroke_tia_te=("卒中" in dx or "脑梗" in dx),
    )

    exams = ["12-lead ECG", "心脏超声 (TTE) — EF, chamber size, valves, diastology"]
    if chads["chads2_vasc"] >= 2 or "AF" in dx.upper() or "房颤" in dx:
        exams.append("Holter 24-48h monitoring — AF burden assessment")
    if "心衰" in dx or "CAD" in dx.upper() or "胸痛" in dx:
        exams.extend(["心肌酶谱 (Troponin I/T, CK-MB)", "BNP / NT-proBNP"])
    if "CAD" in dx.upper() or "CHD" in dx.upper() or "ACS" in dx.upper():
        exams.extend(["动态心电图 (Holter)", "负荷试验 (stress echo/SPECT) as indicated"])
        if chads["chads2_vasc"] >= 3:
            exams.append("冠脉CTA — non-invasive anatomical assessment")
    if "高血压" in dx:
        exams.extend(["24h ABPM (动态血压)", "肾功能 (eGFR, 尿ACR)", "眼底检查"])

    exams.extend(["血脂全套 (LDL-C, HDL-C, TG, Lp(a))", "糖化血红蛋白 (HbA1c)", "甲状腺功能 (TSH) if atrial fibrillation"])

    return _agent.clinical_result(
        summary=f"心脏辅助检查 ({len(exams)} items — CHA₂DS₂-VASc={chads['chads2_vasc']})",
        patient=p, guidelines=_agent.search_guidelines(dx) or _GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断确认 — Killip + TIMI + NYHA staging."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)
    dx = p.get("diagnosis", "")
    age = int(p.get("age", 60) or 60)

    # Killip
    killip = classify_killip(
        has_rales=("心衰" in dx),
        sbp=v["sbp"],
        has_shock_signs=(v["sbp"] < 90 and "心衰" in dx),
    )
    # TIMI
    trop_positive = v["troponin"] > 0.04
    timi = calculate_timi_ua_nstemi(
        age_ge_65=age >= 65,
        elevated_cardiac_markers=trop_positive,
        st_deviation_ge_0_5mm=("STEMI" in dx.upper() or "ST段" in dx),
    )
    # NYHA
    nyha = classify_nyha(3 if ("心衰" in dx and v["sbp"] < 100) else 2)


    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("心血管内科")
    return _agent.clinical_result(
        summary=f"确诊 — Killip={killip['name']} TIMI={timi['timi_score']} NYHA={nyha['name']}",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_plan(**kwargs) -> dict:
    """治疗方案 — GDMT 四联疗法 + anticoagulation + risk-adjusted plan."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    v = extract_vitals(p)
    age = int(p.get("age", 60) or 60)
    gender = p.get("gender", "male") or "male"

    # Scoring
    gdmt = hfref_gdmt_recommendation(
        ef_pct=v["ef"] or 55, systolic_bp=v["sbp"],
        egfr=v["egfr"], k=v["k"],
    )
    chads = calculate_chads2_vasc(
        chf=("心衰" in dx), htn=("高血压" in dx),
        age=age, sex_female=(gender.lower() in ("female", "f", "女")),
    )
    has_bled = calculate_has_bled(age_gt_65=age > 65, htn_uncontrolled=v["sbp"] > 160)
    timi = calculate_timi_ua_nstemi(
        age_ge_65=age >= 65,
        elevated_cardiac_markers=v["troponin"] > 0.04,
    )

    plan_items = []

    # Anticoagulation
    if chads["anticoagulation_recommended"]:
        plan_items.append(f"OAC — NOAC (Class {chads['class_of_recommendation']}): "
                          f"CHA₂DS₂-VASc={chads['chads2_vasc']}, stroke risk {chads['stroke_risk_annual']}")
        if has_bled["high_bleeding_risk"]:
            plan_items.append(f"HAS-BLED={has_bled['has_bled']} — address modifiable: "
                              f"{', '.join(has_bled['modifiable_factors'][:3])}")

    # GDMT
    if gdmt.get("gdmt_applicable"):
        plan_items.append(f"HFrEF GDMT {gdmt.get('total_pillars', 0)}/4 pillars:")
        for p in gdmt["pillars"]:
            plan_items.append(f"  {p['sequence']}. {p['class']} → {p['target_dose']}")
    else:
        plan_items.append(gdmt["recommendation"])

    # Antiplatelet
    if timi["timi_score"] >= 3:
        plan_items.append(f"DAPT: Aspirin 100mg + Ticagrelor 90mg BID (TIMI={timi['timi_score']}, {timi['risk_stratum']})")
    else:
        plan_items.append("Aspirin 100mg QD (primary prevention)")

    # Statin
    plan_items.append("High-intensity statin: Atorvastatin 40-80mg / Rosuvastatin 20mg (LDL-C target <1.4mmol/L)")

    # Lifestyle
    plan_items.extend(["限盐 <5g/d", "运动处方: 150min/wk moderate aerobic",
                        "戒烟 + 限酒", "体重管理 (BMI<24)"])

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("心血管内科")
    return _agent.clinical_result(
        summary=f"治疗方案 — GDMT {gdmt.get('total_pillars', 0)}/4 pillars + {'OAC' if chads.get('anticoagulation_recommended') else 'no OAC'}",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行与监测 — dose titration + monitoring for GDMT."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    v = extract_vitals(p)
    dx = p.get("diagnosis", "")
    age = int(p.get("age", 60) or 60)

    gdmt = hfref_gdmt_recommendation(
        ef_pct=v["ef"] or 55, systolic_bp=v["sbp"], egfr=v["egfr"], k=v["k"],
    )
    chads = calculate_chads2_vasc(
        chf=("心衰" in dx), age=age, prior_stroke_tia_te=("卒中" in dx),
    )
    has_bled = calculate_has_bled(age_gt_65=age > 65)

    monitoring = [
        "BP + HR q15min during dose titration",
        "K+ + Cr at baseline, 1-2w after each dose change, then q3mo",
        "BNP/NT-proBNP 1-3 months after GDMT initiation",
        "Echocardiogram at 3-6 months to reassess EF",
        f"INR weekly if on VKA (target 2.0-3.0, TTR≥65%) — {'not required for NOAC' if chads['chads2_vasc'] >= 2 else ''}",
    ]
    if has_bled["high_bleeding_risk"]:
        monitoring.append(f"HAS-BLED={has_bled['has_bled']} — monitor for bleeding signs q1mo")

    return _agent.clinical_result(
        summary=f"治疗执行与监测 — {'HFrEF GDMT titration' if gdmt['gdmt_applicable'] else 'CV risk management'}",
        patient=p, guidelines=_agent.search_guidelines(dx) or _GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """慢病随访 — 1/3/6/12月 plan with scoring re-assessment."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    v = extract_vitals(p)
    age = int(p.get("age", 60) or 60)
    gender = p.get("gender", "male") or "male"

    chads = calculate_chads2_vasc(
        chf=("心衰" in dx), htn=("高血压" in dx),
        age=age, sex_female=(gender.lower() in ("female", "f", "女")),
    )
    has_bled = calculate_has_bled(age_gt_65=age > 65)
    gdmt = hfref_gdmt_recommendation(
        ef_pct=v["ef"] or 55, systolic_bp=v["sbp"], egfr=v["egfr"], k=v["k"],
    )

    followup_schedule = [
        {"month": 1,  "items": ["Clinical assessment + BP + HR", "K+ + Cr (post BB/ARNI titration)",
                                 "NYHA re-classification", "Medication adherence audit"]},
        {"month": 3,  "items": ["Echocardiogram — EF re-assessment", "BNP/NT-proBNP trend",
                                 f"Re-score CHA₂DS₂-VASc (baseline={chads['chads2_vasc']})",
                                 f"Re-score HAS-BLED (baseline={has_bled['has_bled']})"]},
        {"month": 6,  "items": ["GDMT target dose achievement check", "ICD/CRT eligibility if EF≤35%",
                                 "6-min walk test", "ECG — QRS duration for CRT candidacy"]},
        {"month": 12, "items": ["Annual comprehensive CV risk re-assessment",
                                 "Echo + BNP + K+ panel + eGFR", "Lifestyle goal review",
                                 "Cancer screening age-appropriate"]},
    ]


    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("心血管内科")
    return _agent.clinical_result(
        summary=(
            f"慢病随访 — {len(followup_schedule)} visits (1/3/6/12mo) "
            f"CHA₂DS₂-VASc={chads['chads2_vasc']} "
            f"({'HFrEF GDMT titration' if gdmt['gdmt_applicable'] else 'CV risk management'})"
        ),
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )
