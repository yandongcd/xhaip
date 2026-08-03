"""重症医学科 — KnowledgeAgent-powered clinical reasoning.

Focus: 多器官功能支持与危重症管理
GUIDELINES: 中国重症医学临床诊疗指南（2022）, SCCM Surviving Sepsis Campaign Guidelines (2021)
Conditions: 脓毒症休克, ARDS, 多器官功能障碍, 术后危重, 严重感染

Injected clinical scoring systems:
  qSOFA — RR≥22 + SBP≤100 + GCS≤14 → ≥2 = sepsis suspicion
  SOFA — Resp/Coag/Liver/CV/CNS/Renal 0-4 each → daily trend
  APACHE II — 12 physiologic variables + age + chronic health → mortality prediction
  Sepsis 1-hour bundle — lactate + BC + ABx + fluids 30mL/kg + vasopressors
  ARDS Berlin criteria — onset<1wk + bilateral opacities + P/F ratio → severity
  Lung-protective ventilation — Vt 6mL/kg PBW, Pplat≤30, ΔP≤15
  RASS sedation scale — -5 (unarousable) to +4 (combative), target -2 to 0
  CRRT indications — AEIOU (Acidosis/Electrolytes/Intoxication/Overload/Uremia)
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="icu", department="重症医学科")
_GUIDELINES = [
    "中国重症医学临床诊疗指南（2022）",
    "SCCM Surviving Sepsis Campaign Guidelines (2021)",
]

_agent.rule_engine.load_all()


# ── qSOFA ───────────────────────────────────────────────────────────────

def calculate_qsofa(rr: float = 0, sbp: float = 0, gcs: float = 15) -> dict:
    """qSOFA (quick Sequential Organ Failure Assessment).

    Score ≥2 in presence of infection → high risk for poor outcome (sepsis).
    """
    criteria = {
        "rr_ge_22":    (rr >= 22, f"RR={rr}" if rr else "RR unknown"),
        "sbp_le_100":  (sbp <= 100 and sbp > 0, f"SBP={sbp}" if sbp else "SBP unknown"),
        "gcs_le_14":   (gcs <= 14, f"GCS={gcs}" if gcs else "GCS unknown"),
    }
    score = sum(1 for name, (met, _) in criteria.items() if met)
    sepsis = score >= 2
    return {
        "qsofa": score,
        "criteria": criteria,
        "sepsis_suspicion": sepsis,
        "action": "qSOFA ≥2 — treat as sepsis; obtain lactate, blood cultures, start antibiotics within 1h"
        if sepsis else f"qSOFA={score} — continue monitoring, reassess if clinical change",
    }


# ── SOFA ─────────────────────────────────────────────────────────────────

def _sofa_resp(pao2: float, fio2: float = 0.21) -> tuple[int, str]:
    if pao2 <= 0:
        return (0, "PaO2 unknown")
    pf = pao2 / max(fio2, 0.001)
    if pf >= 400:
        return (0, f"P/F={pf:.0f} (normal)")
    if pf >= 300:
        return (1, f"P/F={pf:.0f} (mild)")
    if pf >= 200:
        return (2, f"P/F={pf:.0f} (moderate)")
    if pf >= 100:
        return (3, f"P/F={pf:.0f} (severe)")
    return (4, f"P/F={pf:.0f} (critical)")

def _sofa_coag(plt: float) -> tuple[int, str]:
    if plt <= 0:
        return (0, "PLT unknown")
    if plt >= 150:
        return (0, f"PLT={plt:.0f}")
    if plt >= 100:
        return (1, f"PLT={plt:.0f}")
    if plt >= 50:
        return (2, f"PLT={plt:.0f}")
    if plt >= 20:
        return (3, f"PLT={plt:.0f}")
    return (4, f"PLT={plt:.0f}")

def _sofa_liver(bil: float) -> tuple[int, str]:
    if bil < 0:
        return (0, "bilirubin unknown")
    # bilirubin in umol/L; SOFA uses mg/dL (divide by 17.1)
    bil_mg = bil / 17.1
    if bil_mg < 1.2:
        return (0, f"Bil={bil:.1f}umol/L ({bil_mg:.1f}mg/dL)")
    if bil_mg < 2.0:
        return (1, f"Bil={bil:.1f}umol/L ({bil_mg:.1f}mg/dL)")
    if bil_mg < 6.0:
        return (2, f"Bil={bil:.1f}umol/L ({bil_mg:.1f}mg/dL)")
    if bil_mg < 12.0:
        return (3, f"Bil={bil:.1f}umol/L ({bil_mg:.1f}mg/dL)")
    return (4, f"Bil={bil:.1f}umol/L ({bil_mg:.1f}mg/dL)")

def _sofa_cv(map_val: float, on_vasopressor: str = "", vasopressor_dose: float = 0) -> tuple[int, str]:
    """SOFA CV score. Dose in mcg/kg/min. Agents: DA=dopamine, NE=norepi, EPI=epi, DOB=dobutamine."""
    if map_val <= 0:
        return (0, "MAP unknown")
    if map_val >= 70 and not on_vasopressor:
        return (0, f"MAP={map_val:.0f} (no vasopressor)")
    agent = (on_vasopressor or "").upper().strip()
    if map_val < 70:
        return (1, f"MAP={map_val:.0f} <70 (no vasopressor)")
    # On vasopressor — dose-dependent
    if "DA" in agent and vasopressor_dose <= 5:
        return (2, f"MAP={map_val:.0f} DA≤5mcg/kg/min")
    if ("DA" in agent and vasopressor_dose > 5) or ("NE" in agent and vasopressor_dose <= 0.1) or ("EPI" in agent and vasopressor_dose <= 0.1):
        return (3, f"MAP={map_val:.0f} DA>5 / NE≤0.1 / EPI≤0.1")
    if ("DA" in agent and vasopressor_dose > 15) or ("NE" in agent and vasopressor_dose > 0.1) or ("EPI" in agent and vasopressor_dose > 0.1):
        return (4, f"MAP={map_val:.0f} DA>15 / NE>0.1 / EPI>0.1")
    return (2, f"MAP={map_val:.0f} on vasopressor")

def _sofa_cns(gcs: float) -> tuple[int, str]:
    if gcs <= 0:
        return (0, "GCS unknown")
    if gcs >= 15:
        return (0, f"GCS={gcs:.0f}")
    if gcs >= 13:
        return (1, f"GCS={gcs:.0f}")
    if gcs >= 10:
        return (2, f"GCS={gcs:.0f}")
    if gcs >= 6:
        return (3, f"GCS={gcs:.0f}")
    return (4, f"GCS={gcs:.0f}")

def _sofa_renal(cr: float, urine_ml_day: float = 0) -> tuple[int, str]:
    """Creatinine in umol/L; SOFA uses mg/dL. Urine in mL/day."""
    if cr < 0:
        return (0, "Cr unknown")
    cr_mg = cr / 88.4  # umol/L to mg/dL
    if cr_mg < 1.2 and (urine_ml_day <= 0 or urine_ml_day >= 500):
        return (0, f"Cr={cr:.0f}umol/L ({cr_mg:.2f}mg/dL)")
    if cr_mg < 2.0:
        return (1, f"Cr={cr:.0f}umol/L ({cr_mg:.2f}mg/dL)")
    if cr_mg < 3.5:
        return (2, f"Cr={cr:.0f}umol/L ({cr_mg:.2f}mg/dL)")
    if cr_mg < 5.0 or (urine_ml_day > 0 and urine_ml_day < 500):
        return (3, f"Cr={cr:.0f}umol/L ({cr_mg:.2f}mg/dL) UO={urine_ml_day}mL/d")
    return (4, f"Cr={cr:.0f}umol/L ({cr_mg:.2f}mg/dL) UO<200mL/d (renal failure)")

def calculate_sofa(pao2: float = 0, fio2: float = 0.21, plt: float = 0,
                   bil: float = 0, map_val: float = 0, on_vasopressor: str = "",
                   vasopressor_dose: float = 0, gcs: float = 15,
                   cr: float = 0, urine_ml_day: float = 0) -> dict:
    components = {
        "respiratory": _sofa_resp(pao2, fio2),
        "coagulation": _sofa_coag(plt),
        "liver":       _sofa_liver(bil),
        "cardiovascular": _sofa_cv(map_val, on_vasopressor, vasopressor_dose),
        "cns":         _sofa_cns(gcs),
        "renal":       _sofa_renal(cr, urine_ml_day),
    }
    total = sum(score for score, _ in components.values())
    mortality_estimate = {0: "<10%", 1: "10-15%", 2: "15-20%", 3: "20-25%",
                          4: "25-30%", 5: "30-35%"}.get(total, ">35%")
    return {
        "sofa": total,
        "components": {k: {"score": v[0], "detail": v[1]} for k, v in components.items()},
        "mortality_estimate": mortality_estimate,
        "sepsis_definition": total >= 2,  # SOFA ≥2 + infection = sepsis per Sepsis-3
        "action": "SOFA baseline established; trend daily to assess organ dysfunction trajectory",
    }


# ── APACHE II ────────────────────────────────────────────────────────────

def _apache_age_points(age: int) -> int:
    if age <= 44:
        return 0
    if age <= 54:
        return 2
    if age <= 64:
        return 3
    if age <= 74:
        return 5
    return 6

def _apache_chronic_health(chronic_conditions: list[str]) -> int:
    """Chronic health points: 0 (none), 2 (elective post-op), 5 (non-op/emergency post-op)."""
    if not chronic_conditions:
        return 0
    # Simplified: if any severe chronic condition + non-operative → 5
    severe = [c for c in chronic_conditions if c.lower() in (
        "liver failure", "heart failure n.y.h.a iv", "copd with chronic hypoxia",
        "dialysis dependent", "immunocompromised", "cirrhosis", "hepatic failure",
        "metastatic cancer", "leukemia", "lymphoma", "aids",
    )]
    if severe:
        return 5  # non-operative / emergency post-op
    return 2  # elective post-op with chronic disease

APACHE_PHYS_SCORES = {
    # key: (lower_than_this, points_if_above)  threshold pairs for scoring
    "temp":   [(29.9, 4), (31.9, 3), (33.9, 2), (35.9, 1), (38.4, 0), (38.9, 1), (40.9, 3), (999, 4)],
    "map":    [(49, 4), (69, 2), (109, 0), (129, 2), (159, 3), (999, 4)],
    "hr":     [(39, 4), (54, 3), (69, 2), (109, 0), (139, 2), (154, 3), (999, 4)],
    "rr":     [(5, 4), (9, 2), (11, 1), (24, 0), (34, 1), (49, 3), (999, 4)],
    "pao2":   [(55, 4), (60, 3), (70, 1), (999, 0)],  # if FiO2 <0.5
    "aado2":  [(199, 2), (349, 3), (499, 4), (999, 0)],  # if FiO2 >=0.5, only highest
    "ph":     [(7.15, 4), (7.24, 2), (7.32, 1), (7.49, 0), (7.59, 2), (7.69, 3), (999, 4)],
    "na":     [(110, 4), (119, 3), (129, 2), (149, 0), (154, 1), (159, 2), (169, 3), (179, 4), (999, 4)],
    "k":      [(2.5, 4), (2.9, 2), (3.4, 1), (5.4, 0), (5.9, 1), (6.9, 3), (999, 4)],
    "cr":     [(0.6, 2), (1.4, 0), (1.9, 2), (3.4, 3), (999, 4)],  # mg/dL, double if ARF
    "hct":    [(20, 4), (29.9, 2), (45.9, 0), (49.9, 1), (59.9, 2), (999, 4)],
    "wbc":    [(1, 4), (2.9, 2), (14.9, 0), (19.9, 1), (39.9, 2), (999, 4)],
    "gcs":    [(15, 0), (14, 1), (12, 2), (9, 3), (6, 4), (999, 1)],  # GCS = 15 - actual_GCS
}

def _score_phys(phys: dict) -> int:
    """Score a single physiologic variable from APACHE thresholds."""
    val = phys.get("value", 0)
    if val is None:
        return 0
    for threshold, points in phys.get("thresholds", []):
        if val <= threshold:
            return points
    return 0

def calculate_apache2(age: int = 50, chronic_conditions: list[str] = None,
                      acute_renal_failure: bool = False,
                      temp: float = 37.0, map_val: float = 90, hr: float = 80,
                      rr: float = 18, fio2: float = 0.21, pao2: float = 90,
                      aado2: float = 0, ph: float = 7.40, na: float = 140,
                      k: float = 4.0, cr: float = 1.0, hct: float = 40,
                      wbc: float = 8.0, gcs: float = 15, arf: bool = False) -> dict:
    """APACHE II score with 12 physiologic variables."""
    # Age points
    age_points = _apache_age_points(age)
    # Chronic health points
    chronic_points = _apache_chronic_health(chronic_conditions or [])

    # GCS points: 15 - actual_GCS
    gcs_points = max(0, int(15 - gcs))

    # Cr score (double if ARF)
    cr_points = 0
    for threshold, pts in APACHE_PHYS_SCORES["cr"]:
        if cr <= threshold:
            cr_points = pts
            break
    if arf or acute_renal_failure:
        cr_points *= 2

    # scoring each phys variable
    phys_vars = [
        ("temp",  temp,  APACHE_PHYS_SCORES["temp"]),
        ("map",   map_val, APACHE_PHYS_SCORES["map"]),
        ("hr",    hr,    APACHE_PHYS_SCORES["hr"]),
        ("rr",    rr,    APACHE_PHYS_SCORES["rr"]),
        ("pao2/aado2", pao2 if fio2 < 0.5 else aado2,
         APACHE_PHYS_SCORES["pao2"] if fio2 < 0.5 else APACHE_PHYS_SCORES["aado2"]),
        ("ph",    ph,    APACHE_PHYS_SCORES["ph"]),
        ("na",    na,    APACHE_PHYS_SCORES["na"]),
        ("k",     k,     APACHE_PHYS_SCORES["k"]),
        ("hct",   hct,   APACHE_PHYS_SCORES["hct"]),
        ("wbc",   wbc,   APACHE_PHYS_SCORES["wbc"]),
    ]

    phys_points = 0
    for name, val, thresholds in phys_vars:
        for threshold, pts in thresholds:
            if val <= threshold:
                phys_points += pts
                break

    # Add GCS and Cr separately
    phys_points += gcs_points + cr_points

    total = phys_points + age_points + chronic_points

    # Mortality estimate (approximate)
    if total < 10:
        mortality = "<10%"
    elif total < 15:
        mortality = "10-20%"
    elif total < 20:
        mortality = "20-40%"
    elif total < 25:
        mortality = "40-55%"
    elif total < 30:
        mortality = "55-75%"
    else:
        mortality = ">75%"

    score_range = "low" if total <= 10 else "moderate" if total <= 20 else "high" if total <= 30 else "very high"

    return {
        "apache2": total,
        "breakdown": {
            "physiology_points": phys_points,
            "age_points": age_points,
            "chronic_health_points": chronic_points,
        },
        "age": age,
        "chronic_conditions": chronic_conditions or [],
        "mortality_estimate": mortality,
        "severity": score_range,
        "action": f"APACHE II={total} — {score_range} severity, {mortality} predicted mortality",
    }


# ── Sepsis 1-Hour Bundle ────────────────────────────────────────────────

_SEPSIS_1H_BUNDLE = [
    ("Measure lactate level",          "乳酸测定 — remeasure if initial >2mmol/L"),
    ("Obtain blood cultures",          "血培养 x2 sets before antibiotics — do not delay ABx if difficult"),
    ("Administer broad-spectrum antibiotics",
     "广谱抗生素 — within 1 hour of recognition; each hour delay increases mortality ~7-8%"),
    ("Begin rapid crystalloid",        "晶体液30mL/kg — for hypotension or lactate ≥4mmol/L"),
    ("Apply vasopressors",             "血管活性药物 — if hypotensive during/after fluid resuscitation, target MAP≥65mmHg"),
]


def sepsis_1h_bundle(qsofa_score: int = 0, lactate: float = 0,
                     hypotension: bool = False) -> dict:
    activated = qsofa_score >= 2 or lactate >= 4 or hypotension
    return {
        "bundle_activated": activated,
        "trigger_reason": f"qSOFA={qsofa_score} lactate={lactate} hypotension={hypotension}",
        "steps": [{"step": i + 1, "task": task, "note": note}
                  for i, (task, note) in enumerate(_SEPSIS_1H_BUNDLE)],
        "target_time_elapsed_min": 60,
        "action": "SEPSIS 1-HOUR BUNDLE INITIATED" if activated else "Continue surveillance",
    }


# ── ARDS Berlin Criteria ────────────────────────────────────────────────

def classify_ards(onset_days: float = 0, bilateral_opacities: bool = False,
                  pf_ratio: float = 400, peep: float = 5,
                  heart_failure_excluded: bool = False) -> dict:
    """Berlin Definition of ARDS.

    Staging: mild=200-300, moderate=100-200, severe<100 (with PEEP≥5).
    """
    criteria_met = (
        onset_days <= 7 and
        bilateral_opacities and
        heart_failure_excluded
    )
    if pf_ratio >= 300:
        severity = "none (P/F ≥300)"
        stage = 0
    elif pf_ratio >= 200:
        severity = "mild ARDS (200 < P/F ≤ 300)"
        stage = 1
    elif pf_ratio >= 100:
        severity = "moderate ARDS (100 < P/F ≤ 200)"
        stage = 2
    else:
        severity = "severe ARDS (P/F ≤ 100)"
        stage = 3

    return {
        "ards": criteria_met and stage > 0,
        "stage": stage,
        "severity": severity,
        "pf_ratio": pf_ratio,
        "onset_lt_1_week": onset_days <= 7,
        "bilateral_opacities": bilateral_opacities,
        "heart_failure_excluded": heart_failure_excluded,
        "mortality_estimate": {1: "~27%", 2: "~32%", 3: "~45%"}.get(stage, "N/A"),
        "action": {
            0: "No ARDS — continue monitoring",
            1: "Mild ARDS — lung-protective ventilation, PEEP 5-10",
            2: "Moderate ARDS — lung-protective ventilation, PEEP 10-14, consider prone",
            3: "Severe ARDS — lung-protective ventilation, PEEP≥14, prone, consider ECMO",
        }.get(stage, ""),
    }


# ── Lung-Protective Ventilation ─────────────────────────────────────────

def lung_protective_params(gender: str = "male", height_cm: float = 170,
                           vt_measured: float = 0, pplat: float = 0,
                           peep: float = 5) -> dict:
    """ARDSNet lung-protective ventilation protocol.

    Vt target: 6 mL/kg predicted body weight (PBW).
    Pplat target: ≤30 cmH2O.
    Driving pressure (ΔP): ≤15 cmH2O = Pplat - PEEP.
    """
    # PBW formula
    if gender.lower() in ("female", "f"):
        pbw_kg = 45.5 + 0.91 * (height_cm - 152.4)
    else:
        pbw_kg = 50.0 + 0.91 * (height_cm - 152.4)
    pbw_kg = max(pbw_kg, 30)

    target_vt = 6 * pbw_kg  # mL
    target_vt_range = (4 * pbw_kg, 8 * pbw_kg)

    vt_ok = abs(vt_measured - target_vt) <= (0.5 * pbw_kg) if vt_measured > 0 else None
    pplat_ok = pplat <= 30 if pplat > 0 else None
    driving_pressure = pplat - peep if pplat > 0 else None
    dp_ok = driving_pressure <= 15 if driving_pressure is not None else None

    recommendations = []
    if vt_measured > 0 and not vt_ok:
        recommendations.append(f"Adjust Vt from {vt_measured}mL to {target_vt:.0f}mL (6mL/kg PBW)")
    if pplat > 30:
        recommendations.append(f"Reduce Vt — Pplat={pplat}cmH2O > 30cmH2O")
    if driving_pressure is not None and driving_pressure > 15:
        recommendations.append(f"Driving pressure ΔP={driving_pressure}cmH2O > 15 — optimize PEEP")

    return {
        "pbw_kg": round(pbw_kg, 1),
        "target_vt_ml": round(target_vt),
        "target_vt_range_ml": (round(target_vt_range[0]), round(target_vt_range[1])),
        "vt_measured_ml": vt_measured,
        "vt_ok": vt_ok,
        "pplat_cmh2o": pplat,
        "pplat_ok": pplat_ok,
        "peep_cmh2o": peep,
        "driving_pressure_cmh2o": round(driving_pressure, 1) if driving_pressure else None,
        "driving_pressure_ok": dp_ok,
        "recommendations": recommendations,
        "protocol": "ARDSNet Vt 6mL/kg PBW, Pplat ≤30cmH2O, ΔP ≤15cmH2O",
    }


# ── RASS Sedation Scale ─────────────────────────────────────────────────

RASS_LEVELS: dict[int, str] = {
    4:  "Combative (攻击性) — overtly combative/violent, immediate danger to staff",
    3:  "Very agitated (极度躁动) — pulls/removes tubes or catheters, aggressive",
    2:  "Agitated (躁动) — frequent non-purposeful movement, fights ventilator",
    1:  "Restless (不安) — anxious but movements not aggressive/vigorous",
    0:  "Alert and calm (清醒平静) — calm, attentive",
    -1: "Drowsy (嗜睡) — not fully alert, but sustained awakening (>10s) to voice",
    -2: "Light sedation (轻度镇静) — briefly awakens (<10s) with eye contact to voice",
    -3: "Moderate sedation (中度镇静) — movement or eye opening to voice (no eye contact)",
    -4: "Deep sedation (深度镇静) — no response to voice, but movement/eye opening to physical stimulation",
    -5: "Unarousable (不可唤醒) — no response to voice or physical stimulation",
}

RASS_TARGET_RANGES = {
    "general_icu":      (-2, 0, "General ICU — light sedation, comfortable"),
    "mechanical_ventilation": (-2, 0, "Mechanical ventilation — light sedation target"),
    "ards_severe":      (-4, -3, "Severe ARDS — deep sedation for proning/synchrony"),
    "neuro":            (-2, 0, "Neuro ICU — allow neuro exam"),
    "paralyzed_nmba":   (-5, -4, "NMBA paralysis — deep sedation required"),
}

def assess_rass(rass: int, target: str = "general_icu",
                neuro_exam_needed: bool = False) -> dict:
    target_range = RASS_TARGET_RANGES.get(target, RASS_TARGET_RANGES["general_icu"])
    lo, hi, desc = target_range

    if neuro_exam_needed:
        lo, hi = -2, 0  # override for neuro exam

    in_range = lo <= rass <= hi

    if rass < lo:
        adjustment = f"Reduce sedation — RASS={rass} < target range [{lo},{hi}]"
    elif rass > hi:
        adjustment = f"Increase sedation — RASS={rass} > target range [{lo},{hi}]"
    else:
        adjustment = "At target"

    return {
        "rass": rass,
        "level_description": RASS_LEVELS.get(rass, "Unknown"),
        "target_context": target,
        "target_range": (lo, hi),
        "target_description": desc,
        "in_target_range": in_range,
        "adjustment": adjustment,
        "neuro_exam_adjusted": neuro_exam_needed and target == "neuro",
    }


# ── CRRT Indications (AEIOU) ────────────────────────────────────────────

CRRT_AEIOU = {
    "A_acidosis":     "Acidosis (酸中毒) — severe metabolic acidosis (pH<7.15) refractory to medical therapy",
    "E_electrolytes": "Electrolytes (电解质) — severe hyperkalemia (K+>6.5) or other refractory electrolyte disturbance",
    "I_intoxication": "Intoxication (中毒) — dialyzable toxin (lithium, methanol, ethylene glycol, salicylate, theophylline)",
    "O_overload":     "Overload (容量超负荷) — fluid overload with pulmonary edema refractory to diuretics",
    "U_uremia":       "Uremia (尿毒症) — uremic pericarditis, encephalopathy, or bleeding; BUN>35.7mmol/L",
}

def crrt_indications(pH: float = 7.40, k: float = 4.0, bun: float = 15,
                     has_fluid_overload: bool = False, diuretic_resistant: bool = False,
                     has_uremic_symptoms: bool = False,
                     dialyzable_toxin: str = "") -> dict:
    indications = []
    if pH < 7.15:
        indications.append(("A", CRRT_AEIOU["A_acidosis"], f"pH={pH}"))
    if k > 6.5:
        indications.append(("E", CRRT_AEIOU["E_electrolytes"], f"K+={k}"))
    if dialyzable_toxin:
        indications.append(("I", CRRT_AEIOU["I_intoxication"], dialyzable_toxin))
    if has_fluid_overload and diuretic_resistant:
        indications.append(("O", CRRT_AEIOU["O_overload"], "oliguric + diuretic resistant"))
    if has_uremic_symptoms or bun > 35.7:
        indications.append(("U", CRRT_AEIOU["U_uremia"], f"BUN={bun}"))

    crrt_indicated = len(indications) > 0

    return {
        "crrt_indicated": crrt_indicated,
        "indications": [{"letter": letter, "description": desc, "detail": detail}
                        for letter, desc, detail in indications],
        "count": len(indications),
        "action": "Initiate CRRT" if crrt_indicated else "Continue conservative management",
        "modality": "CVVHDF (continuous veno-venous hemodiafiltration) — default ICU modality",
        "access": "Temporary dialysis catheter — R IJ or L femoral",
        "anticoagulation": "Regional citrate preferred; heparin if contraindicated",
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
        "rr":     _f("rr", _f("RR", _f("respiratory_rate", 0))),
        "temp":   _f("temp", _f("TEMP", _f("temperature", 0))),
        "spo2":   _f("spo2", _f("SpO2", 0)),
        "gcs":    _i("gcs", _i("GCS", 15)),
        "lactate": _f("lactate", _f("Lactate", _f("lac", 0))),
        "cr":     _f("Cr", _f("creatinine", _f("cr", 0))),
        "plt":    _f("PLT", _f("plt", _f("platelet", 0))),
        "bil":    _f("TBIL", _f("bilirubin", _f("tbil", 0))),
        "pao2":   _f("PaO2", _f("pao2", 0)),
        "ph":     _f("pH", _f("ph", 7.40)),
        "k":      _f("K+", _f("k", _f("potassium", 0))),
        "bun":    _f("BUN", _f("bun", 0)),
        "wbc":    _f("WBC", _f("wbc", 0)),
        "hct":    _f("HCT", _f("hct", _f("hematocrit", 0))),
        "na":     _f("Na+", _f("na", _f("sodium", 0))),
    }


def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


# ── Pipeline Handlers (injected with real ICU scoring) ──────────────────

def bp_triage(**kwargs) -> dict:
    """ICU入科评估 — qSOFA + SOFA + APACHE II baseline."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)

    qsofa = calculate_qsofa(v["rr"], v["sbp"], v["gcs"])
    sofa = calculate_sofa(pao2=v["pao2"], plt=v["plt"], bil=v["bil"],
                          map_val=v["sbp"], gcs=v["gcs"], cr=v["cr"])
    apache = calculate_apache2(
        age=50, temp=v["temp"], map_val=v["sbp"], hr=v["pulse"],
        rr=v["rr"], pao2=v["pao2"], gcs=v["gcs"],
        cr=v["cr"] / 88.4 if v["cr"] else 1.0,
        na=v["na"], k=v["k"], hct=v["hct"], wbc=v["wbc"],
    )
    sepsis_bundle = sepsis_1h_bundle(qsofa_score=qsofa["qsofa"], lactate=v["lactate"])


    recommendations = [f"qSOFA={qsofa['qsofa']} → {qsofa['action']}"]
    if sepsis_bundle["bundle_activated"]:
        recommendations.append("SEPSIS 1-HOUR BUNDLE — start immediately")
    recommendations.append(f"Record SOFA={sofa['sofa']} as daily baseline")

    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("重症医学科")
    return _agent.clinical_result(
        summary=f"重症医学科—ICU入科评估 (qSOFA={qsofa['qsofa']} SOFA={sofa['sofa']} APACHE2={apache['apache2']})",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_rescue(**kwargs) -> dict:
    """脏器支持治疗 — ARDS classification + lung-protective vent + CRRT + sepsis bundle."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)

    # ARDS
    pf = v["pao2"] / 0.4 if v["pao2"] > 0 else 400
    ards = classify_ards(pf_ratio=pf)

    # Lung-protective ventilation
    lpv = lung_protective_params(gender=p.get("gender", "male"),
                                  height_cm=float(p.get("height_cm", 170) or 170),
                                  vt_measured=480, pplat=28, peep=8)

    # CRRT indications
    crrt = crrt_indications(pH=v["ph"], k=v["k"], bun=v["bun"])

    # Sepsis bundle
    qsofa = calculate_qsofa(v["rr"], v["sbp"], v["gcs"])
    s1h = sepsis_1h_bundle(qsofa_score=qsofa["qsofa"], lactate=v["lactate"])


    recommendations = []
    if ards["ards"]:
        recommendations.append(ards["action"])
    recommendations.extend(lpv["recommendations"])
    if crrt["crrt_indicated"]:
        recommendations.append(f"CRRT: {crrt['modality']} — {crrt['anticoagulation']}")
    if s1h["bundle_activated"]:
        recommendations.append("SEPSIS 1-HOUR BUNDLE — start immediately")

    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("重症医学科")
    return _agent.clinical_result(
        summary=f"重症医学科—脏器支持 (ARDS={ards['severity']} {'CRRT' if crrt['crrt_indicated'] else ''})",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_icu(**kwargs) -> dict:
    """持续重症监护 — daily SOFA trend + RASS sedation + vent management."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)

    sofa = calculate_sofa(pao2=v["pao2"], plt=v["plt"], bil=v["bil"],
                          map_val=v["sbp"], gcs=v["gcs"], cr=v["cr"])
    # RASS — assume currently at -2 (light sedation target)
    rass = assess_rass(-2, target="general_icu")

    findings = [
        f"SOFA daily: {sofa['sofa']}/24 (mortality ~{sofa['mortality_estimate']})",
        f"RASS sedation: score=-2 (light sedation) — {rass['adjustment']}",
        "镇静镇痛管理 — RASS target [-2, 0]",
        "液体管理 — daily fluid balance goal",
        "营养支持 — enteral nutrition within 24-48h",
        "感染监控 — PCT trend + culture surveillance",
        "DVT prophylaxis + stress ulcer prophylaxis",
    ]
    for organ, detail in sofa["components"].items():
        findings.append(f"  SOFA-{organ}: {detail['score']} ({detail['detail']})")

    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("重症医学科")
    return _agent.clinical_result(
        summary=f"重症医学科—持续ICU监护 (SOFA={sofa['sofa']} RASS={rass['rass']})",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_transfer(**kwargs) -> dict:
    """转出评估 — weaning readiness + organ recovery + transfer risk."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)

    sofa = calculate_sofa(pao2=v["pao2"], plt=v["plt"], bil=v["bil"],
                          map_val=v["sbp"], gcs=v["gcs"], cr=v["cr"])
    qsofa = calculate_qsofa(v["rr"], v["sbp"], v["gcs"])

    # Transfer readiness: SOFA improving, qSOFA <2
    sofa_improving = sofa["sofa"] <= 4
    stable = qsofa["qsofa"] < 2
    ready = sofa_improving and stable


    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("重症医学科")
    return _agent.clinical_result(
        summary=f"重症医学科—转出评估 (SOFA={sofa['sofa']} {'ready' if ready else 'defer'})",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_followup(**kwargs) -> dict:
    """ICU后随访 — PICS assessment + cognitive/functional/quality of life."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)

    # PICS = Post-Intensive Care Syndrome

    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("重症医学科")
    return _agent.clinical_result(
        summary="重症医学科—ICU后随访 (PICS assessment)",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )
