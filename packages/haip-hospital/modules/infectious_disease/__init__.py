"""感染内科 — KnowledgeAgent-powered clinical reasoning.

Focus: 感染性疾病诊疗与抗生素管理 — SIRS/Sepsis, FUO, HBV, HIV, TB, COVID-19
GUIDELINES: 中国感染性疾病诊疗指南（2022）, Surviving Sepsis Campaign, WHO TB, CDC STI
Conditions: 肺炎, 泌尿系感染, 腹腔感染, 中枢神经系统感染, 结核病, 病毒性肝炎, HIV

Real clinical scoring: SIRS criteria, Antibiotic timeouts, FUO algorithm, Hepatitis B serology,
HIV OI prophylaxis, TB RIPE/MDR regimens, COVID-19 severity.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="infectious_disease", department="感染内科")
_GUIDELINES = [
    "中国感染性疾病诊疗指南（2022）",
    "Surviving Sepsis Campaign Guidelines（2021）",
    "WHO 结核病治疗指南（2022）",
    "中国慢性乙型肝炎防治指南（2022）",
    "DHHS HIV 诊疗指南（2023）",
    "WHO COVID-19 临床管理指南",
]

_agent.rule_engine.load_all()


# ── Helpers ──────────────────────────────────────────────────────────────

def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def _vn(patient: dict, *keys, default=0):
    """Get value from patient vitals/labs with fallback."""
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

def _calc_sirs(patient: dict) -> dict:
    """SIRS criteria: ≥ 2 of — Temp>38 or<36 + HR>90 + RR>20 or PaCO2<32 + WBC>12 or<4 or bands>10%."""
    temp = float(_vn(patient, "temperature", "temp", default=37))
    hr = int(_vn(patient, "heart_rate", "hr", "pulse", default=80))
    rr = int(_vn(patient, "respiratory_rate", "rr", default=16))
    paco2 = float(_vn(patient, "paco2", default=40))
    wbc = float(_vn(patient, "wbc", "white_blood_cell", "leukocytes", default=7))
    bands = float(_vn(patient, "bands_pct", "immature_neutrophils", default=5))

    criteria = 0
    components = {}
    if temp > 38 or temp < 36:
        criteria += 1
        components["temp"] = True
    else:
        components["temp"] = False
    if hr > 90:
        criteria += 1
        components["hr"] = True
    else:
        components["hr"] = False
    if rr > 20 or paco2 < 32:
        criteria += 1
        components["rr_paco2"] = True
    else:
        components["rr_paco2"] = False
    if wbc > 12 or wbc < 4 or bands > 10:
        criteria += 1
        components["wbc_bands"] = True
    else:
        components["wbc_bands"] = False

    sirs = criteria >= 2
    return {"sirs": sirs, "criteria_met": criteria, "total": 4, "components": components,
            "sepsis_suspected": sirs and _vn(patient, "infection_suspected", "suspected_infection", default=False),
            "action": "SIRS+ criteria met — screen for sepsis (lactate, blood cultures, SOFA score)" if sirs else "No SIRS"}


def _antibiotic_timeout(patient: dict) -> dict:
    """Antibiotic timeout: 48-72h reassessment, de-escalation, stop rules."""
    abx_day = int(_vn(patient, "antibiotic_day", "abx_day", default=1))
    cultures = _vn(patient, "culture_results", "cultures", default="pending")
    pct = float(_vn(patient, "procalcitonin", "pct", default=2))
    afebrile_hours = float(_vn(patient, "afebrile_hours", default=24))

    timeout_due = abx_day >= 3
    action = ""
    if timeout_due:
        if cultures and "no growth" in str(cultures).lower():
            action = "Cultures negative — STOP antibiotics if clinically improved and PCT < 0.5"
        elif cultures and any(b in str(cultures).lower() for b in ["e. coli", "staph", "pseudomonas", "klebsiella"]):
            action = "Pathogen identified — de-escalate to narrowest-spectrum agent based on sensitivities"
        elif pct < 0.25 and afebrile_hours >= 48:
            action = "PCT < 0.25 + afebrile ≥ 48h — stop antibiotics per PCT-guided algorithm"
        else:
            action = "Continue current regimen; re-evaluate in 24h with repeat PCT + cultures"
    else:
        action = f"Continue empiric antibiotics (day {abx_day}/3); reassess at 48-72h"

    return {"timeout_due": timeout_due, "abx_day": abx_day, "action": action,
            "de_escalation_rules": ["Narrow spectrum as soon as culture sensitivities available",
                                    "Stop vancomycin at 48h if no MRSA in cultures",
                                    "Stop anaerobic coverage if intra-abdominal source controlled"]}


def _fuo_workup(patient: dict) -> dict:
    """Fever of Unknown Origin (FUO): >38.3 × 3 weeks + 3 outpatient visits or 1 week inpatient workup.
       Categories: infectious (30-40%), neoplastic (20-30%), autoimmune (10-20%), miscellaneous, undiagnosed."""
    temp_max = float(_vn(patient, "temperature_max", "temp_max", default=38.5))
    fever_days = int(_vn(patient, "fever_days", "fever_duration_days", default=14))
    workup_inpatient_days = int(_vn(patient, "inpatient_workup_days", default=0))
    outpatient_visits = int(_vn(patient, "outpatient_visits", default=2))

    meets_criteria = (fever_days >= 21 and outpatient_visits >= 3) or (workup_inpatient_days >= 7 and fever_days >= 7)
    if not meets_criteria and temp_max < 38.3:
        meets_criteria = False

    algorithm = [
        "Phase 1: CBC + diff, CMP, ESR, CRP, ferritin, LDH, blood cultures × 3, CXR, UA + culture",
        "Phase 2: CT chest/abdomen/pelvis with contrast; HIV, EBV, CMV serologies; ANA, RF; TTE (vegetations)",
        "Phase 3: PET-CT (if available), temporal artery biopsy (age > 50), bone marrow biopsy, liver biopsy",
        "Phase 4: Therapeutic trial — NSAID (Still's), steroids (PMR/GCA), anti-TB trial",
    ]

    return {"fuo": meets_criteria, "temp_max": temp_max, "fever_days": fever_days,
            "workup_algorithm": algorithm,
            "differential_top": ["Infection: TB, endocarditis, abscess, EBV/CMV, brucellosis",
                                 "Neoplasm: lymphoma, renal cell carcinoma, leukemia, HCC",
                                 "Autoimmune: Still's disease, SLE, giant cell arteritis, polyarteritis nodosa"],
            "action": "Proceed with FUO workup algorithm" if meets_criteria else "Does not meet FUO criteria — continue standard fever workup"}


def _interpret_hbv_serology(patient: dict) -> dict:
    """Hepatitis B serology interpretation."""
    hbsag = _vn(patient, "hbsag", "HBsAg", default="negative")
    hbsab = _vn(patient, "hbsab", "anti-HBs", "HBsAb", default="negative")
    hbeag = _vn(patient, "hbeag", "HBeAg", default="negative")
    hbeab = _vn(patient, "hbeab", "anti-HBe", "HBeAb", default="negative")
    hbcab = _vn(patient, "hbcab", "anti-HBc", "HBcAb", "anti-HBc_total", default="negative")
    hbv_dna = float(_vn(patient, "hbv_dna", "HBV-DNA", "viral_load", default=0))
    alt = float(_vn(patient, "alt", "ALT", "alanine_transferase", default=30))

    def pos(s):
        return s in ("positive", "reactive", "+", True, 1)

    if pos(hbsag) and pos(hbeag) and pos(hbcab) and not pos(hbsab):
        interpretation = "HBeAg-positive chronic HBV (immune-active) — high viral load, active hepatitis"
        phase = "Immune-active HBeAg(+)"
    elif pos(hbsag) and not pos(hbeag) and pos(hbeab) and pos(hbcab):
        interpretation = "HBeAg-negative chronic HBV — precore/core mutant, variable activity"
        phase = "Immune-active HBeAg(-)"
    elif pos(hbsag) and pos(hbeag) and pos(hbcab) and hbv_dna > 20000 and alt < 40:
        interpretation = "HBeAg-positive chronic HBV (immune-tolerant) — high DNA, normal ALT, minimal inflammation"
        phase = "Immune-tolerant"
    elif pos(hbsag) and not pos(hbeag) and pos(hbeab) and pos(hbcab) and hbv_dna < 2000 and alt < 35:
        interpretation = "Inactive HBsAg carrier — low DNA, normal ALT, resolved inflammation"
        phase = "Inactive carrier"
    elif not pos(hbsag) and pos(hbsab) and pos(hbcab):
        interpretation = "Resolved HBV infection (immune) — anti-HBs+ / anti-HBc+"
        phase = "Resolved"
    elif not pos(hbsag) and pos(hbsab) and not pos(hbcab):
        interpretation = "Vaccinated — anti-HBs+ / anti-HBc−"
        phase = "Vaccinated"
    elif not pos(hbsag) and not pos(hbsab) and pos(hbcab):
        interpretation = "Isolated anti-HBc+ — could be resolved, occult HBV, or false positive"
        phase = "Isolated anti-HBc"
    else:
        interpretation = "No HBV infection, not immune — vaccinate"
        phase = "Susceptible"

    treat = (alt > 80 or (alt > 40 and hbv_dna > 2000) or phase in ("Immune-active HBeAg(+)", "Immune-active HBeAg(-)"))
    antivirals = "TDF (tenofovir disoproxil) 300mg daily OR TAF (tenofovir alafenamide) 25mg daily OR ETV (entecavir) 0.5mg daily"

    return {"phase": phase, "interpretation": interpretation, "hbv_dna": hbv_dna, "alt": alt,
            "treatment_indicated": treat, "antivirals": antivirals if treat else "Monitor every 6-12 months",
            "surveillance": "US + AFP q6mo if cirrhosis or family history of HCC; FibroScan/Fib-4 annually" if pos(hbsag) else "N/A"}


def _hiv_oi_prophylaxis(patient: dict) -> dict:
    """HIV: CD4 thresholds for OI prophylaxis, ART initiation."""
    cd4 = int(_vn(patient, "cd4", "CD4", "cd4_count", default=350))
    on_art = _vn(patient, "on_art", "ART_status", default=False)
    viral_load = float(_vn(patient, "hiv_viral_load", "HIV_RNA", default=0))

    recs = []
    if cd4 < 200:
        recs.append("PCP prophylaxis: TMP-SMX DS (800/160mg) daily or 3×/week (stop when CD4 > 200 × 3mo on ART)")
    if cd4 < 100:
        recs.append("Toxoplasma prophylaxis: TMP-SMX DS daily (same as PCP) or dapsone + pyrimethamine (stop when CD4 > 200 × 3mo)")
    if cd4 < 50:
        recs.append("MAC prophylaxis: azithromycin 1200mg weekly or clarithromycin 500mg BID (stop when CD4 > 100 × 3mo)")
    if not recs:
        recs.append(f"CD4 {cd4} > 200 — no OI prophylaxis needed; continue ART monitoring")

    art_rec = "Start ART immediately (all patients regardless of CD4) — preferred: BIC/FTC/TAF (Biktarvy) or DTG/3TC (Dovato)"
    if not on_art:
        recs.insert(0, f"ART initiation: {art_rec}")

    return {"cd4": cd4, "viral_load": viral_load, "on_art": on_art,
            "recommendations": recs, "art_immediate": not on_art}


def _tb_regimen(patient: dict) -> dict:
    """TB treatment: active vs latent, RIPE, MDR-TB."""
    active = _vn(patient, "active_tb", default=False)
    latent = _vn(patient, "latent_tb", "ltbi", default=False)
    mdr = _vn(patient, "mdr_tb", "drug_resistant", default=False)
    rif_resist = _vn(patient, "rif_resistance", "rr_tb", default=False)
    site = _vn(patient, "tb_site", "site", default="pulmonary")

    if active:
        if mdr or rif_resist:
            regimen = "MDR/RR-TB: BPaLM (bedaquiline + pretomanid + linezolid ± moxifloxacin) × 6mo (WHO 2022 all-oral regimen)"
            duration = "6 months"
        else:
            regimen = "RIPE: 2HRZE/4HR (isoniazid + rifampin + pyrazinamide + ethambutol × 2mo → isoniazid + rifampin × 4mo)"
            duration = "6 months (9mo if cavitary + culture+ at 2mo)"
        if site in ("meningitis", "cns"):
            regimen += "; extend to 9-12mo + dexamethasone (CNS TB)"
            duration = "9-12 months"
        action = "Airborne isolation until 3 negative AFB smears + effective treatment ≥ 2 weeks"
    elif latent:
        regimen = "3HP (isoniazid + rifapentine weekly × 12 weeks) — preferred; alt: 4R (rifampin daily × 4mo)"
        duration = "3-4 months"
        action = "Rule out active TB with CXR + symptom screen before starting LTBI Rx"
    else:
        regimen = "N/A"
        duration = "N/A"
        action = "No TB infection"

    return {"active": active, "latent": latent, "regimen": regimen, "duration": duration, "action": action,
            "monitoring": "Monthly LFTs (INH/RIF/PZA hepatotoxicity); monthly sputum smear + culture × 2; baseline + monthly visual acuity (EMB toxicity)" if active else "LFTs at baseline + monthly if LTBI Rx"}


def _covid_severity(patient: dict) -> dict:
    """COVID-19 severity classification and treatment."""
    spo2 = float(_vn(patient, "spo2", "o2_saturation", default=95))
    rr = int(_vn(patient, "respiratory_rate", "rr", default=18))
    _vn(patient, "cxr_infiltrate", "cxr", default="normal")
    d_dimer = float(_vn(patient, "d_dimer", default=0.5))

    if spo2 >= 94 and rr < 24:
        severity = "mild"
        rx = "Symptomatic treatment; isolate × 10 days from symptom onset"
    elif spo2 >= 90 and rr < 30:
        severity = "moderate"
        rx = "Consider Remdesivir (3 days) if high risk; monitor SpO₂; dexamethasone NOT indicated (RECOVERY: harm in non-hypoxic)"
    elif spo2 < 90 and rr >= 30:
        severity = "severe"
        rx = "Dexamethasone 6mg PO/IV daily × 10 days + Remdesivir 200mg IV D1 → 100mg D2-5 + O₂ support"
    else:
        severity = "critical"
        rx = "Dexamethasone 6mg daily + Remdesivir + consider baricitinib (JAK inhibitor) or tocilizumab (IL-6) if CRP > 75 + rapid deterioration"

    anticoag = "Prophylactic LMWH/enoxaparin" if d_dimer < 3 else "Therapeutic anticoagulation if D-dimer > 3×ULN + clinical PE/DVT suspected"

    return {"severity": severity, "spo2": spo2, "rr": rr, "treatment": rx,
            "anticoagulation": anticoag, "isolation": "Airborne + contact + droplet — N95 + eye protection",
            "paxlovid": "Paxlovid (nirmatrelvir/ritonavir) within 5 days of symptom onset if age ≥ 65 or high-risk (NOT needed if already on dexamethasone for severe disease)" if severity in ("mild", "moderate") else "Not indicated (hospitalized severe/critical — use Remdesivir)"}


# ── Business Process Functions ───────────────────────────────────────────

def bp_reception(**kwargs) -> dict:
    """接诊与初步评估 — SIRS screening, FUO identification, triage."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    sirs = _calc_sirs(p)
    findings = [
        "发热热型: onset, duration, pattern (intermittent/remittent/continuous), maximum temperature",
        "感染灶定位: respiratory / urinary / abdominal / CNS / skin / line-associated",
        "流行病学史: travel (malaria/dengue/typhoid), animal contact (brucellosis/leptospirosis), TB exposure, sick contacts",
        "免疫状态: HIV risk, immunosuppression (steroids/biologics/chemo), splenectomy, neutropenia",
    ]

    if sirs["sirs"]:
        findings.insert(0, f"⚠ SIRS: {sirs['criteria_met']}/4 criteria met — {'SEPSIS SCREENING REQUIRED' if sirs['sepsis_suspected'] else 'monitor for infection progression'}")
        if sirs["sepsis_suspected"]:
            findings.insert(0, "⚠ SEPSIS ALERT: lactate STAT, blood cultures × 2 (before antibiotics), IVF 30mL/kg, broad-spectrum antibiotics within 1h (Surviving Sepsis Bundle)")

    fuo = _fuo_workup(p)
    if fuo["fuo"]:
        findings.append(f"FUO criteria met: temp {fuo['temp_max']}°C × {fuo['fever_days']}d — initiate FUO workup")

    if any(t in dx for t in ["肝炎", "hepatitis", "HBV", "HCV"]):
        hbv = _interpret_hbv_serology(p)
        findings.insert(0, f"HBV: {hbv['phase']} — {'treatment indicated' if hbv['treatment_indicated'] else 'monitor'} (ALT={hbv['alt']}, DNA={hbv['hbv_dna']})")

    if any(t in dx for t in ["艾滋", "HIV"]):
        hiv = _hiv_oi_prophylaxis(p)
        findings.insert(0, f"HIV: CD4={hiv['cd4']}, {'on ART' if hiv['on_art'] else 'ART-naive — START IMMEDIATELY'}")

    recommendations = []
    if sirs["sirs"]:
        recommendations.append("STAT: lactate, blood cultures × 2, CBC, CMP, coagulation panel, urinalysis, CXR")
        recommendations.append("Time-to-antibiotics goal: ≤ 1 hour from recognition of sepsis")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("感染内科")
    return _agent.clinical_result(
        patient=p, stage="triage",
        summary=f"感染内科 — 感染科初诊完成 (SIRS={'+' if sirs['sirs'] else '−'}, FUO={fuo['fuo']})",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """辅助检查 — targeted microbiology and serology."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "血培养 × 2-3 sets (aerobic + anaerobic) from separate venipuncture sites — before antibiotics",
        "PCT (procalcitonin) + CRP — differentiate bacterial vs viral; PCT-guided antibiotic cessation",
        "病原学: Gram stain + culture (sputum/urine/CSF/fluid), GeneXpert MTB/RIF, BioFire FilmArray multiplex PCR",
        "影像: CXR, CT chest/abdomen ± contrast, US for abscess/fluid collection",
        "药敏试验 (AST): MIC determination — ESBL/MRSA/VRE/CRE screening",
    ]

    if any(t in dx for t in ["肝炎", "HBV"]):
        findings.insert(1, "HBV panel: HBsAg, anti-HBs, HBeAg, anti-HBe, anti-HBc (total + IgM), HBV DNA (quantitative)")
    if any(t in dx for t in ["HIV"]):
        findings.insert(1, "HIV: 4th-gen Ag/Ab test + HIV RNA; CD4 count, HIV genotype (resistance testing)")
    if any(t in dx for t in ["结核", "TB"]):
        findings.insert(1, "TB: IGRA (QuantiFERON-TB Gold Plus), sputum Xpert MTB/RIF × 1-3, AFB smear, mycobacterial culture + DST")
    if any(t in dx for t in ["新冠", "COVID"]):
        findings.insert(1, "COVID-19: SARS-CoV-2 RT-PCR (NP swab); inflammatory markers: CRP, ferritin, LDH, D-dimer")

    recommendations = ["Blood cultures BEFORE antibiotics (if clinical stability allows)", "PCT at admission + q48h for antibiotic de-escalation guidance"]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("感染内科")
    return _agent.clinical_result(
        patient=p, stage="exam",
        summary="感染内科 — 感染相关检查完成",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊与分型分期 — pathogen identification + disease-specific scoring."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = ["病原体鉴定: culture/PCR/antigen results → targeted pathogen", "感染部位: anatomical localization confirmed",
                "严重程度: SIRS/sepsis/septic shock stratification", "耐药评估: AST panel → ESBL/MRSA/VRE/CRE/ESKAPE pathogens"]
    recommendations = []

    sirs = _calc_sirs(p)
    if sirs["sirs"]:
        findings.append(f"严重程度: SIRS {sirs['criteria_met']}/4 — {'worsening to sepsis' if sirs['sepsis_suspected'] else 'systemic inflammatory response'}")

    if any(t in dx for t in ["肝炎", "HBV"]):
        hbv = _interpret_hbv_serology(p)
        findings.insert(0, f"HBV: {hbv['phase']} — {hbv['interpretation']}")
        if hbv["treatment_indicated"]:
            recommendations.append(f"Treat: {hbv['antivirals']}")
            recommendations.append("Monitoring: ALT + HBV DNA q3-6mo; FibroScan annually; US + AFP q6mo if cirrhosis/F3+")
        else:
            recommendations.append("No treatment indicated; monitor ALT + HBV DNA q6-12mo")

    if any(t in dx for t in ["HIV"]):
        hiv = _hiv_oi_prophylaxis(p)
        findings.insert(0, f"HIV: CD4={hiv['cd4']} cells/μL, VL={hiv['viral_load']} copies/mL")
        recommendations = hiv["recommendations"] + recommendations

    if any(t in dx for t in ["结核", "TB"]):
        tb = _tb_regimen(p)
        findings.insert(0, f"TB: {'ACTIVE — ' + tb['regimen'] if tb['active'] else 'LATENT — ' + tb['regimen'] if tb['latent'] else 'No TB'}")
        findings.append(tb["action"])
        recommendations.append(tb["monitoring"])

    if any(t in dx for t in ["新冠", "COVID"]):
        covid = _covid_severity(p)
        findings.insert(0, f"COVID-19: {covid['severity']} (SpO₂={covid['spo2']}%, RR={covid['rr']}/min)")
        recommendations.append(covid["treatment"] if covid["severity"] in ("severe", "critical") else "Symptomatic care + isolation")

    timeout = _antibiotic_timeout(p)
    if timeout["timeout_due"]:
        findings.append(f"Antibiotic timeout (day {timeout['abx_day']}): {timeout['action']}")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("感染内科")
    return _agent.clinical_result(
        patient=p, stage="diagnosis",
        summary=f"感染内科 — 病原诊断完成 ({dx})",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_plan(**kwargs) -> dict:
    """治疗方案制定 — empiric → targeted antibiotics, disease-specific protocols."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "经验性抗生素: broad-spectrum based on infection site + local antibiogram + risk for MDR",
        "目标性治疗: de-escalate to narrowest-spectrum agent when culture sensitivities available (usually at 48-72h)",
        "疗程确定: CAP 5-7d, HAP/VAP 7d, UTI 3-7d (F), pyelonephritis 7-14d, bacteremia 7-14d (uncomplicated), endocarditis 4-6w, osteomyelitis 4-6w",
        "感染源控制: abscess drainage, debridement, device removal (CVC/urinary catheter), surgical source control (perforation/anastomotic leak)",
    ]
    recommendations = []

    abx = _antibiotic_timeout(p)
    if abx["timeout_due"]:
        recommendations.append(f"TIME OUT (day {abx['abx_day']}): {abx['action']}")
        recommendations.extend(abx["de_escalation_rules"])

    if any(t in dx for t in ["肝炎", "HBV"]):
        hbv = _interpret_hbv_serology(p)
        if hbv["treatment_indicated"]:
            recommendations.append(f"Start: {hbv['antivirals']}")
            recommendations.append("Renal monitoring: TDF — Cr + phosphate q3mo (nephrotoxicity/Fanconi); TAF — Cr q6mo")
            recommendations.append("Pregnancy: TDF preferred; avoid ETV in pregnancy")

    if any(t in dx for t in ["HIV"]):
        hiv = _hiv_oi_prophylaxis(p)
        findings.insert(0, f"HIV ART + OI prophylaxis plan (CD4={hiv['cd4']})")
        recommendations = hiv["recommendations"] + recommendations

    if any(t in dx for t in ["结核", "TB"]):
        tb = _tb_regimen(p)
        recommendations.append(f"Regimen: {tb['regimen']} (duration: {tb['duration']})")
        recommendations.append("Pyridoxine (vitamin B6) 25-50mg daily to prevent INH neuropathy")
        recommendations.append("Baseline visual acuity + monthly Ishihara (ethambutol optic neuropathy)")

    if any(t in dx for t in ["新冠", "COVID"]):
        covid = _covid_severity(p)
        recommendations.append(covid["treatment"])

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("感染内科")
    return _agent.clinical_result(
        patient=p, stage="plan",
        summary="感染内科 — 抗感染方案完成",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行与监测 — antibiotic stewardship, drug monitoring, adverse effects."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "抗菌药物管理: daily review of indication + dose (CrCl-adjusted) + route (IV→PO switch when afebrile + tolerating PO + clinically improving)",
        "药物浓度监测: vancomycin trough 10-20 mg/L (severe MRSA), aminoglycoside peak/trough, voriconazole trough 1-5.5 mg/L",
        "不良反应: nephrotoxicity (vancomycin + pip/tazo, aminoglycosides, amphotericin B), hepatotoxicity (INH/RIF/PZA, azoles, echinocandins), QT prolongation (macrolides, fluoroquinolones, azoles)",
        "耐药监测: repeat cultures at 48-72h and EOT; CRE/MRSA/VRE colonization surveillance (rectal/nasal swabs)",
    ]
    recommendations = [
        "C. difficile screening: diarrhea + ≥ 3 loose stools/24h → C. diff PCR (GDH + toxin EIA)",
        "Fever curve: daily Tmax + defervescence pattern; if persistent fever at day 5 → drug fever, abscess, or resistant pathogen",
        "Line removal: CVC removal + tip culture if CLABSI suspected (timing: within 24h of positive blood culture)",
        "PCT q48h: stop antibiotics when PCT < 0.25 μg/L OR decrease ≥ 80% from peak + clinically improved",
    ]

    abx = _antibiotic_timeout(p)
    if abx["timeout_due"]:
        recommendations.insert(0, f"ANTIBIOTIC TIMEOUT day {abx['abx_day']}: {abx['action']}")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("感染内科")
    return _agent.clinical_result(
        patient=p, stage="treatment",
        summary="感染内科 — 治疗执行完成",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """随访与长期管理 — infection clearance, chronic disease management (HBV/HIV/TB)."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "感染清除确认: clinical resolution (afebrile ≥ 48h, WBC normalized, PCT < 0.25), microbiological clearance (repeat cultures negative)",
        "复发监测: follow-up at 1mo + 3mo post treatment completion; repeat cultures if symptoms recur",
        "耐药监测: if recurrent infection → repeat AST, consider biofilm/undrained focus",
        "免疫重建: HIV — CD4 trend + OI prophylaxis discontinuation criteria; post-splenectomy vaccination compliance",
    ]
    recommendations = ["Follow-up cultures at 4-6 weeks post treatment (endocarditis/osteomyelitis/prosthetic joint infection)"]

    if any(t in dx for t in ["肝炎", "HBV"]):
        hbv = _interpret_hbv_serology(p)
        findings.append(f"HBV long-term: {hbv['phase']} — {'on antivirals — ALT + HBV DNA q6mo + FibroScan annually' if hbv['treatment_indicated'] else 'monitor q6-12mo for reactivation'}")
        findings.append(f"HCC surveillance: {hbv['surveillance']}")
        recommendations.append("HBV vaccination for household + sexual contacts if anti-HBs negative")

    if any(t in dx for t in ["HIV"]):
        hiv = _hiv_oi_prophylaxis(p)
        findings.append(f"HIV follow-up: CD4={hiv['cd4']}, {'on ART' if hiv['on_art'] else 'NEED ART'}, VL={hiv['viral_load']}")
        recommendations.append("CD4 + HIV RNA every 3-4mo (first 2 years on ART) → q6mo if stable + suppressed")
        recommendations.append("STI screening q6-12mo: syphilis (RPR), gonorrhea/chlamydia (NAAT), HCV Ab (annual)")

    if any(t in dx for t in ["结核", "TB"]):
        recommendations.append("TB: monthly sputum smear + culture until 2 consecutive negative; CXR at 2mo + EOT; DOT adherence tracking")
        recommendations.append("Contact investigation: TST/IGRA for household contacts; LTBI treatment for positives (3HP preferred)")

    if any(t in dx for t in ["新冠", "COVID"]):
        recommendations.append("Post-COVID follow-up: symptom diary (fatigue/dyspnea/brain fog), PFT at 3mo if persistent dyspnea, CXR at 3mo if severe pneumonia")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("感染内科")
    return _agent.clinical_result(
        patient=p, stage="followup",
        summary="感染内科 — 随访管理完成",
        findings=findings, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []), recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )
