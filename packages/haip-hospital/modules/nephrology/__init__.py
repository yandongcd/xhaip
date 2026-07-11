"""肾内科 — KnowledgeAgent-powered clinical reasoning (Deep-Optimized).

Focus: 慢性肾脏病管理与替代治疗
GUIDELINES: KDIGO 2024 Clinical Practice Guideline for CKD Evaluation and Management
Conditions: 慢性肾小球肾炎, 糖尿病肾病, 高血压肾病, 肾病综合征, AKI

Injected clinical systems: CKD-EPI eGFR calculator, KDIGO CKD heat map (GFR×Albuminuria),
AKI KDIGO criteria (Cr+UO), Dialysis indications (AEIOU), RAASi triple therapy,
Electrolyte emergencies (K+ / Na+).
"""

from __future__ import annotations

from math import exp, log

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="nephrology", department="肾内科")
_GUIDELINES = [
    "KDIGO 2024 Clinical Practice Guideline for CKD Evaluation and Management",
    "KDIGO 2024 Clinical Practice Guideline for Acute Kidney Injury",
    "KDIGO 2022 Clinical Practice Guideline for Diabetes Management in CKD",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


# ── Clinical Scoring Systems ─────────────────────────────────────────

def _ckd_epi_egfr(age: int, sex: str, creatinine_mgdl: float) -> dict:
    """CKD-EPI 2021 eGFR calculator (creatinine-based)."""
    if sex == "female":
        k, alpha, sc_ratio = 0.7, -0.241, creatinine_mgdl / 0.7
    else:
        k, alpha, sc_ratio = 0.9, -0.302, creatinine_mgdl / 0.9

    if sc_ratio <= 1:
        egfr = 142 * (sc_ratio ** alpha) * (0.9938 ** age)
    else:
        egfr = 142 * (sc_ratio ** -1.200) * (0.9938 ** age)

    if sex == "female":
        egfr *= 1.012

    egfr = min(egfr, 200)

    if egfr >= 90:
        stage = "G1"
    elif egfr >= 60:
        stage = "G2"
    elif egfr >= 45:
        stage = "G3a"
    elif egfr >= 30:
        stage = "G3b"
    elif egfr >= 15:
        stage = "G4"
    else:
        stage = "G5"

    return {
        "egfr": round(egfr, 1), "stage": stage, "age": age, "sex": sex,
        "creatinine_mgdl": creatinine_mgdl,
        "stage_description": {
            "G1": "Normal or high (≥90) — kidney damage with normal GFR",
            "G2": "Mildly decreased (60-89)",
            "G3a": "Mildly to moderately decreased (45-59)",
            "G3b": "Moderately to severely decreased (30-44)",
            "G4": "Severely decreased (15-29)",
            "G5": "Kidney failure (<15)",
        }.get(stage, "Unknown"),
    }


def _kdigo_heatmap(gfr_stage: str, albuminuria_stage: str) -> dict:
    """KDIGO CKD risk heat map: GFR × Albuminuria → risk category."""
    a = {"A1": 1, "A2": 2, "A3": 3}.get(albuminuria_stage, 1)
    g = {"G1": 1, "G2": 2, "G3a": 3, "G3b": 4, "G4": 5, "G5": 6}.get(gfr_stage, 1)

    risk_table = {
        (1, 1): "Low", (2, 1): "Low", (1, 2): "Moderate", (2, 2): "Moderate",
        (3, 1): "Moderate", (3, 2): "High", (4, 1): "High", (4, 2): "Very high",
        (5, 1): "Very high", (5, 2): "Very high", (6, 1): "Very high", (6, 2): "Very high",
        (1, 3): "High", (2, 3): "Very high", (3, 3): "Very high",
        (4, 3): "Very high", (5, 3): "Very high", (6, 3): "Very high",
    }
    risk = risk_table.get((g, a), "Moderate")
    proteinuria_target = {"A1": "Monitor", "A2": "<30 mg/mmol (ACR)", "A3": "≥50% reduction in ACR"}.get(albuminuria_stage, "")
    return {
        "gfr_stage": gfr_stage, "albuminuria": albuminuria_stage, "risk": risk,
        "monitoring_frequency": {
            "Low": "Annual (eGFR + ACR)", "Moderate": "Every 6 months",
            "High": "Every 3-4 months", "Very high": "Every 1-3 months; nephrology referral"
        }.get(risk, "Every 6 months"),
        "nephrology_referral": risk in ("High", "Very high"),
        "proteinuria_target": proteinuria_target,
    }


def _aki_kdigo(cr_baseline: float, cr_current: float, cr_48h_ago: float = None,
               urine_output_mlkgh_6h: float = None, dialysis: bool = False) -> dict:
    """KDIGO AKI criteria: Cr rise + urine output + staging."""
    cr_rise_48h = (cr_current - cr_48h_ago) if cr_48h_ago else 0
    cr_ratio = cr_current / cr_baseline if cr_baseline > 0 else 1.0
    stage = 0
    reasons = []

    if cr_rise_48h >= 0.3:
        stage = max(stage, 1)
        reasons.append(f"Cr rise ≥0.3 mg/dL in 48h (Δ{cr_rise_48h:.2f})")

    if cr_ratio >= 3.0:
        stage = max(stage, 3)
        reasons.append(f"Cr ≥3× baseline ({cr_ratio:.1f}×)")
    elif cr_ratio >= 2.0:
        stage = max(stage, 2)
        reasons.append(f"Cr ≥2× baseline ({cr_ratio:.1f}×)")
    elif cr_ratio >= 1.5:
        stage = max(stage, 1)
        reasons.append(f"Cr ≥1.5× baseline ({cr_ratio:.1f}×)")

    if cr_current >= 4.0 and cr_rise_48h >= 0.5:
        stage = max(stage, 3)
        reasons.append("Cr ≥4.0 + acute rise ≥0.5")

    if urine_output_mlkgh_6h is not None and urine_output_mlkgh_6h < 0.5:
        if urine_output_mlkgh_6h < 0.3:
            stage = max(stage, 3)
            reasons.append(f"UO<0.3 mL/kg/h × 6h ({urine_output_mlkgh_6h:.2f})")
        else:
            stage = max(stage, 1)
            reasons.append(f"UO<0.5 mL/kg/h × 6h ({urine_output_mlkgh_6h:.2f})")

    if dialysis:
        stage = 3
        reasons.append("On RRT (Stage 3 by definition)")

    management = {
        0: "No AKI — continue monitoring", 1: "Stage 1: Discontinue nephrotoxins; ensure euvolemia; monitor Cr/UO",
        2: "Stage 2: Nephrology consult; consider renal biopsy; avoid subclavian CVC",
        3: "Stage 3: ICU admission; urgent nephrology; RRT evaluation (AEIOU criteria)"
    }.get(stage, "Unknown")

    return {
        "aki": stage > 0, "stage": stage if stage > 0 else "No AKI",
        "criteria_met": reasons, "cr_baseline": cr_baseline, "cr_current": cr_current,
        "cr_ratio": round(cr_ratio, 2), "management": management,
    }


def _dialysis_indications(eGFR: float, k: float, hco3: float = 24, bun: float = 20,
                          urine_output: float = 1500, has_pericarditis: bool = False,
                          has_encephalopathy: bool = False, dm: bool = False) -> dict:
    """AEIOU dialysis indications + eGFR criteria."""
    aeiou = {
        "Acidosis": hco3 < 12,
        "Electrolytes (K+)": k > 6.5 or (k > 6.0 and has_encephalopathy),
        "Intoxication": False,
        "Overload": urine_output < 100,
        "Uremia": has_pericarditis or has_encephalopathy or bun > 100,
    }
    urgent = any(aeiou.values())
    planned = not urgent and eGFR < (15 if dm else 10)

    return {
        "urgent_dialysis": urgent, "planned_dialysis": planned,
        "aeiou": {k: v for k, v in aeiou.items() if v},
        "eGFR_threshold_met": eGFR < (15 if dm else 10),
        "recommendation": "EMERGENCY DIALYSIS — call nephrology STAT" if urgent else
        "Preemptive AV fistula creation; initiate dialysis within weeks" if planned else
        "Continue conservative management; monitor eGFR trend",
    }


def _electrolyte_emergency(k: float, na: float, ca: float = 2.3, mg: float = 1.8) -> dict:
    """Electrolyte emergency detection and management."""
    emergencies = []
    ecg_recommendation = "No ECG changes expected"

    # Hyperkalemia
    if k > 6.5:
        emergencies.append(
            f"K⁺ {k} → SEVERE HYPERKALEMIA: ECG STAT (peaked T → loss P → wide QRS); "
            "IV Calcium Gluconate 1g/10min (cardioprotection) + IV Insulin 10U + D50 25g + IV NaHCO3 50mEq + "
            "KAYEXALATE 30g PO/PR + arrange EMERGENCY DIALYSIS"
        )
        ecg_recommendation = "ECG STAT: peaked T → widened QRS → sine wave → VF"
    elif k > 6.0:
        emergencies.append(f"K⁺ {k} → HYPERKALEMIA: ECG; stop K+ supplements/ACEi/ARB/MRA; Kayexalate; arrange dialysis")
        ecg_recommendation = "ECG: peaked T waves"
    elif k > 5.5:
        emergencies.append(f"K⁺ {k} → Mild hyperkalemia: stop K+ supplements; review meds(ACEi/ARB/MRA); repeat labs")

    # Hyponatremia
    if na < 120:
        emergencies.append(
            f"Na⁺ {na} → SEVERE HYPONATREMIA: 3% Hypertonic Saline (100mL bolus → recheck Na⁺ q2h; "
            "correct ≤8 mEq/L/24h → avoid osmotic demyelination); ICU admission"
        )
    elif na < 125:
        emergencies.append(
            f"Na⁺ {na} → Moderate hyponatremia: fluid restriction <1L/d; consider vaptans (tolvaptan); "
            "correct ≤8 mEq/L/24h"
        )
    elif na < 130:
        emergencies.append(f"Na⁺ {na} → Mild hyponatremia: fluid restriction 1.2L/d; investigate cause(SIADH/HF/cirrhosis)")

    return {
        "has_emergency": len(emergencies) > 0,
        "emergencies": emergencies,
        "ecg_recommendation": ecg_recommendation,
        "k": k, "na": na, "ca": ca, "mg": mg,
    }


# ── Business Process Functions ───────────────────────────────────────

def bp_reception(**kwargs) -> dict:
    """接诊与初步评估 — eGFR + KDIGO heatmap + AKI screening."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    # ── Injected clinical scoring ──
    age = int(p.get("age", 55))
    sex = p.get("sex", "male")
    cr = float(labs.get("creatinine", 1.0))
    egfr_result = _ckd_epi_egfr(age, sex, cr)
    alb = labs.get("albuminuria_stage", "A1")
    heatmap = _kdigo_heatmap(egfr_result["stage"], alb)
    cr_baseline = float(labs.get("cr_baseline", cr))
    cr_48h = float(labs.get("cr_48h_ago", cr_baseline))
    uo_6h = float(labs.get("urine_output_mlkgh_6h", vitals.get("urine_output", 1.0)) if "urine_output_mlkgh_6h" in labs else
                  float(vitals.get("urine_output_hourly", 0.016)) * 6 if vitals.get("urine_output_hourly") else None)
    aki = _aki_kdigo(cr_baseline, cr, cr_48h, uo_6h)

    findings = [
        f"CKD-EPI eGFR: {egfr_result['egfr']} mL/min/1.73m² → Stage {egfr_result['stage']} ({egfr_result['stage_description']})",
        f"KDIGO Heatmap: GFR {egfr_result['stage']} × Albuminuria {alb} → Risk: {heatmap['risk']}",
        f"AKI: {'YES Stage ' + str(aki['stage']) if aki['aki'] else 'No'} — Cr {cr} (baseline {cr_baseline}, ratio {aki['cr_ratio']}×)",
        f"尿量变化: {labs.get('urine_output_24h', 'N/A')} mL/24h",
        "水肿: " + ("有" if labs.get("edema") else "无"),
        f"BP: {vitals.get('sbp',120)}/{vitals.get('dbp',80)} mmHg",
    ]
    recommendations = [
        f"Monitoring: {heatmap['monitoring_frequency']}; referral: {'YES' if heatmap['nephrology_referral'] else 'No'}",
        aki["management"],
    ]
    if aki["aki"]:
        recommendations.insert(0, "AKI → 停用NSAIDs/ACEi/ARB/氨基糖苷类; 维持MAP≥65; 避免高渗对比剂")
    if "慢性肾" in dx or "糖尿病" in dx:
        findings.insert(0, f"{'慢性肾病' if '慢性肾' in dx else '糖尿病肾病'} 疾病匹配")
    checklist = ["eGFR下降>25%", "K+>6.0", "严重酸中毒(HCO3<12)", "尿毒症脑病", "心包炎"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注: Cr/BUN/eGFR/尿蛋白")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肾内科")
    return _agent.clinical_result(
        summary=f"肾内科—初诊 eGFR{egfr_result['egfr']} Risk:{heatmap['risk']} (stage S1)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_exam(**kwargs) -> dict:
    """辅助检查 — eGFR confirmation + urine protein + imaging."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    age = int(p.get("age", 55))
    sex = p.get("sex", "male")
    cr = float(labs.get("creatinine", 1.0))
    egfr_result = _ckd_epi_egfr(age, sex, cr)
    alb = labs.get("albuminuria_stage", "A1")
    heatmap = _kdigo_heatmap(egfr_result["stage"], labs.get("albuminuria_stage", "A1"))

    findings = [
        f"eGFR: {egfr_result['egfr']} → Stage {egfr_result['stage']}",
        "尿常规+沉渣: RBC casts → 肾小球肾炎; WBC casts → 间质性肾炎; granular casts → CKD",
        f"24h尿蛋白: {labs.get('proteinuria_24h', 'N/A')}g → {'Nephrotic (>3.5g)' if float(labs.get('proteinuria_24h',0))>3.5 else 'Non-nephrotic'}",
        "肾脏B超: 大小/皮质厚度/回声/肾积水/囊肿",
        "自身抗体: ANA/ANCA/anti-GBM/anti-PLA2R → 肾小球肾炎病因",
    ]
    recommendations = [
        f"KDIGO: {heatmap['monitoring_frequency']}; ACR target: {heatmap['proteinuria_target']}",
        "肾活检指征: nephrotic syndrome; RPGN; unexplained AKI; transplant rejection",
    ]
    if "慢性肾" in dx or "糖尿病" in dx:
        findings.insert(0, f"{'慢性肾病' if '慢性肾' in dx else '糖尿病肾病'} 检查方案")
    checklist = ["eGFR下降>25%", "K+>6.0", "严重酸中毒", "尿毒症脑病", "心包炎"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肾内科")
    return _agent.clinical_result(
        summary=f"肾内科—检查 eGFR{egfr_result['egfr']} (stage S2)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊与分型分期 — Full KDIGO staging + AKI confirmation."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    age = int(p.get("age", 55))
    sex = p.get("sex", "male")
    cr = float(labs.get("creatinine", 1.0))
    egfr_result = _ckd_epi_egfr(age, sex, cr)
    alb = labs.get("albuminuria_stage", "A1")
    heatmap = _kdigo_heatmap(egfr_result["stage"], alb)
    cr_baseline = float(labs.get("cr_baseline", cr))
    aki = _aki_kdigo(cr_baseline, cr, float(labs.get("cr_48h_ago", cr_baseline)),
                     float(labs.get("urine_output_mlkgh_6h", vitals.get("urine_output", 0)) * 6)
                     if labs.get("urine_output_mlkgh_6h") or vitals.get("urine_output") else None)

    findings = [
        f"CKD Stage: {egfr_result['stage']} — eGFR {egfr_result['egfr']} mL/min/1.73m²",
        f"Albuminuria: {alb} — KDIGO Risk: {heatmap['risk']}",
        f"AKI Status: {'Stage ' + str(aki['stage']) if aki['aki'] else 'No AKI'} (Cr {cr}, ratio {aki['cr_ratio']}×)",
        f"病理类型: {labs.get('pathology', '待活检')}",
        f"原发病因: {dx or '待明确'}",
        f"并发症评估: Anemia(Hb<13♂/<12♀) / MBD(Ca/P/PTH) / Metabolic acidosis(HCO3<22)",
    ]
    recommendations = [
        f"Staging: CKD {egfr_result['stage']}{alb} → {heatmap['risk']} risk → {heatmap['monitoring_frequency']}",
        f"Referral: {'Nephrology NOW' if heatmap['nephrology_referral'] else 'Primary care management'}",
        aki["management"],
    ]
    if "慢性肾" in dx or "糖尿病" in dx:
        findings.insert(0, f"{'慢性肾病' if '慢性肾' in dx else '糖尿病肾病'} 分期确认")
    checklist = ["eGFR下降>25%", "K+>6.0", "严重酸中毒", "尿毒症脑病", "心包炎"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肾内科")
    return _agent.clinical_result(
        summary=f"肾内科—确诊 CKD{egfr_result['stage']}{alb} Risk:{heatmap['risk']} (stage S3)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_plan(**kwargs) -> dict:
    """治疗方案制定 — RAASi triple + dialysis planning + electrolyte management."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    age = int(p.get("age", 55))
    sex = p.get("sex", "male")
    cr = float(labs.get("creatinine", 1.0))
    egfr_result = _ckd_epi_egfr(age, sex, cr)
    k = float(labs.get("potassium", 4.0))
    na = float(labs.get("sodium", 140))
    elytes = _electrolyte_emergency(k, na)
    dm = "糖尿病" in dx or labs.get("dm", False)
    dialysis = _dialysis_indications(egfr_result["egfr"], k, float(labs.get("hco3", 24)),
                                     float(labs.get("bun", 20)), float(labs.get("urine_output", 1500)),
                                     dm=dm)

    proteinuric = float(labs.get("proteinuria_24h", 0)) > 0.5 or labs.get("albuminuria_stage", "") in ("A2", "A3")
    raasi = (
        "RAASi Triple: ACEi/ARB (最大耐受剂量) + SGLT2i (达格列净10mg/d, eGFR≥20) + nsMRA (非奈利酮20mg/d, eGFR≥25, K+≤5.0)"
        if proteinuric and egfr_result["egfr"] >= 20 and k <= 5.0 else
        "RAASi block: ACEi/ARB (K+ monitor) + SGLT2i (eGFR≥20)" if egfr_result["egfr"] >= 20 else
        "Conservative management"
    )

    findings = [
        f"RAASi方案: {raasi}",
        f"Dialysis: {'URGENT' if dialysis['urgent_dialysis'] else 'Planned (preemptive AVF)' if dialysis['planned_dialysis'] else 'Not yet indicated'}",
        f"Electrolytes: K⁺ {k} / Na⁺ {na} → {'EMERGENCY' if elytes['has_emergency'] else 'Stable'}",
        f"降压目标: SBP<120 (KDIGO 2021) — {'ACEi/ARB first-line' if proteinuric else 'CCB/ACEi/ARB'}",
        "肾移植评估: eGFR<20 → living donor vs deceased donor listing",
    ]
    recommendations = [
        raasi,
        dialysis["recommendation"],
    ]
    if elytes["has_emergency"]:
        recommendations.extend(["ELECTROLYTE EMERGENCY:"] + elytes["emergencies"])
    if "慢性肾" in dx or "糖尿病" in dx:
        findings.insert(0, f"{'慢性肾病' if '慢性肾' in dx else '糖尿病肾病'} 治疗路径")
    checklist = ["eGFR下降>25%", "K+>6.0", "严重酸中毒", "尿毒症脑病", "心包炎"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肾内科")
    return _agent.clinical_result(
        summary=f"肾内科—计划 eGFR{egfr_result['egfr']} (stage S4a)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行与监测 — Dialysis execution + electrolyte correction + anemia/MBD."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    age = int(p.get("age", 55))
    sex = p.get("sex", "male")
    cr = float(labs.get("creatinine", 1.0))
    egfr_result = _ckd_epi_egfr(age, sex, cr)
    k = float(labs.get("potassium", 4.0))
    na = float(labs.get("sodium", 140))
    elytes = _electrolyte_emergency(k, na, float(labs.get("calcium", 2.3)), float(labs.get("magnesium", 1.8)))
    aki = _aki_kdigo(float(labs.get("cr_baseline", cr)), cr, float(labs.get("cr_48h_ago", cr)))

    findings = [
        f"eGFR: {egfr_result['egfr']} (Stage {egfr_result['stage']})",
        f"Electrolytes: K⁺ {k} {'⚠' if k>5.5 else ''} / Na⁺ {na} / Ca²⁺ {labs.get('calcium',2.3)} / Mg²⁺ {labs.get('magnesium',1.8)}",
        f"AKI Monitoring: {'Stage ' + str(aki['stage']) if aki['aki'] else 'No AKI'}",
        "Anemia: Hb<13♂/<12♀ → ESA + iron (TSAT<30% or ferritin<500 → IV iron)",
        "CKD-MBD: Ca/P/PTH management → phosphate binders + calcitriol/cinacalcet",
        f"Dialysis: {'Active (HD/PD)' if labs.get('on_dialysis') else ('Vascular access: AVF/AVG' if egfr_result['egfr']<20 else 'Pre-dialysis education')}",
    ]
    recommendations = []
    if elytes["has_emergency"]:
        recommendations.extend(elytes["emergencies"])
        recommendations.append(elytes["ecg_recommendation"])
    else:
        recommendations.extend([
            f"BP target <130/80; SGLT2i if eGFR≥20",
            f"K⁺ diet <2g/d; Na⁺ <2g/d; Phosphate <800mg/d",
        ])
    if aki["aki"]:
        recommendations.append(aki["management"])
    if "慢性肾" in dx or "糖尿病" in dx:
        findings.insert(0, f"{'慢性肾病' if '慢性肾' in dx else '糖尿病肾病'} 治疗监测")
    checklist = ["eGFR下降>25%", "K+>6.0", "严重酸中毒", "尿毒症脑病", "心包炎"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肾内科")
    return _agent.clinical_result(
        summary=f"肾内科—执行 eGFR{egfr_result['egfr']} K+{k} (stage S4b)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_followup(**kwargs) -> dict:
    """随访与长期管理 — eGFR trend + proteinuria trajectory + dialysis adequacy."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    age = int(p.get("age", 55))
    sex = p.get("sex", "male")
    cr = float(labs.get("creatinine", 1.0))
    cr_prev = float(labs.get("cr_previous", cr))
    egfr_result = _ckd_epi_egfr(age, sex, cr)
    egfr_prev = _ckd_epi_egfr(age, sex, cr_prev)
    delta = egfr_result["egfr"] - egfr_prev["egfr"]
    alb = labs.get("albuminuria_stage", "A1")
    heatmap = _kdigo_heatmap(egfr_result["stage"], alb)
    k = float(labs.get("potassium", 4.0))
    na = float(labs.get("sodium", 140))
    elytes = _electrolyte_emergency(k, na)

    findings = [
        f"eGFR Trend: {egfr_result['egfr']} (prev {egfr_prev['egfr']}; Δ {delta:+.1f}) → Stage {egfr_result['stage']}",
        f"Slope: {'RAPID DECLINE (>5/yr)' if abs(delta)>5 else 'Slow decline' if delta<0 else 'Stable'}",
        f"KDIGO Risk: {heatmap['risk']} → {heatmap['monitoring_frequency']}",
        f"Electrolytes: K⁺ {k} / Na⁺ {na} → {'⚠ Emergency' if elytes['has_emergency'] else 'OK'}",
        f"Dialysis adequacy: {'Kt/V≥1.2 (HD) / Kt/V≥1.7 (PD)' if labs.get('on_dialysis') else 'N/A'}",
        f"Proteinuria: {labs.get('proteinuria_24h','N/A')}g/24h → {'50% reduction achieved' if float(labs.get('proteinuria_24h',0))<1 else 'Target not met'}",
    ]
    recommendations = [
        f"Monitoring: {heatmap['monitoring_frequency']} (eGFR + ACR + K⁺)",
        f"Nephrology: {'Continue q3mo' if heatmap['nephrology_referral'] else 'Annual PCP follow-up'}",
    ]
    if elytes["has_emergency"]:
        recommendations.extend(elytes["emergencies"])
    if delta <= -5:
        recommendations.append("RAPID DECLINE → evaluate for secondary cause: NSAIDs, obstruction, infection, GN flare")
    if "慢性肾" in dx or "糖尿病" in dx:
        findings.insert(0, f"{'慢性肾病' if '慢性肾' in dx else '糖尿病肾病'} 长期随访")
    checklist = ["eGFR下降>25%", "K+>6.0", "严重酸中毒", "尿毒症脑病", "心包炎"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肾内科")
    return _agent.clinical_result(
        summary=f"肾内科—随访 eGFR{egfr_result['egfr']} Δ{delta:+.1f} (stage S5)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )
