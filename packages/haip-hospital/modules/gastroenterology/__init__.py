"""消化内科 — KnowledgeAgent-powered clinical reasoning (Deep-Optimized).

Focus: 消化系统疾病内镜诊疗
GUIDELINES: 中国慢性胃炎共识意见 (2022, 上海), Rome IV (2016),
ACG Clinical Guideline: Upper GI and Ulcer Bleeding (2021), AASLD NAFLD Guidance (2023)
Conditions: 消化性溃疡, IBD, 肝硬化, 胰腺炎, GERD

Injected clinical systems: Rome IV (IBS/FD), H.pylori eradication protocols,
Glasgow-Blatchford UGIB score, Endoscopy urgency triage, NAFLD/NASH (FLI->Fib-4->FibroScan),
IBD differentiation (Crohn's vs UC + Montreal classification),
Liver cirrhosis (Child-Pugh + MELD).
"""

from __future__ import annotations

from math import exp, log

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="gastroenterology", department="消化内科")
_GUIDELINES = [
    "中国慢性胃炎共识意见 (2022, 上海)",
    "Rome IV Diagnostic Criteria for Functional GI Disorders (2016)",
    "ACG Clinical Guideline: Upper GI and Ulcer Bleeding (2021)",
    "AASLD Guidance on NAFLD/NASH (2023)",
    "ACG Clinical Guideline: Crohn's Disease / Ulcerative Colitis (2019)",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


# ── Clinical Scoring Systems ─────────────────────────────────────────

def _rome_iv_ibs(abdominal_pain_days_month: int, months_duration: int,
                 stool_form: str = "mixed", pain_related_to_defecation: bool = True,
                 onset_with_stool_freq_change: bool = True) -> dict:
    """Rome IV criteria for Irritable Bowel Syndrome."""
    criteria_met = (
        abdominal_pain_days_month >= 4 and months_duration >= 3
        and pain_related_to_defecation and onset_with_stool_freq_change
    )
    subtypes = {
        "constipation": "IBS-C: >25% hard/lumpy stools (BSFS 1-2)",
        "diarrhea": "IBS-D: >25% loose/watery stools (BSFS 6-7)",
        "mixed": "IBS-M: >25% hard/lumpy AND >25% loose/watery",
        "unspecified": "IBS-U: Does not meet C/D/M criteria",
    }
    subtype = subtypes.get(stool_form, subtypes["unspecified"])
    return {
        "ibs": criteria_met,
        "criteria": "Pain >=1d/wk for >=3mo + >=2 of: defecation / stool freq change / stool form change",
        "subtype": subtype,
        "management": "Low-FODMAP diet + antispasmodics + gut-brain neuromodulators (TCA/SSRI)" if criteria_met else
        "Rome IV not met; consider IBD/celiac/microscopic colitis",
    }


def _rome_iv_fd(postprandial_fullness: bool, early_satiety: bool,
                epigastric_pain: bool, epigastric_burning: bool,
                months_duration: int = 3) -> dict:
    """Rome IV criteria for Functional Dyspepsia."""
    eps = epigastric_pain or epigastric_burning
    pds = postprandial_fullness or early_satiety
    fd = months_duration >= 3 and (eps or pds)
    subtype_str = []
    if eps:
        subtype_str.append("EPS (Epigastric Pain Syndrome)")
    if pds:
        subtype_str.append("PDS (Postprandial Distress Syndrome)")
    return {
        "functional_dyspepsia": fd, "eps": eps, "pds": pds,
        "subtype": " + ".join(subtype_str) if subtype_str else "None",
        "management": "HP test-and-treat; PPI trial 4-8w; prokinetics; TCA (amitriptyline)" if fd else
        "Rome IV FD not met; consider GERD/peptic ulcer/gastroparesis",
    }


def _hp_eradication(regimen: str = "bismuth_quadruple") -> dict:
    """H.pylori eradication regimens per ACG/Maastricht VI consensus."""
    regimens = {
        "bismuth_quadruple": {
            "name": "Bismuth Quadruple Therapy",
            "drugs": "PPI BID + Bismuth 220mg BID + Amoxicillin 1g BID + Clarithromycin 500mg BID (or Metronidazole 400mg QID if clarithromycin resistance >15%)",
            "duration": "14 days", "efficacy": "85-90%",
        },
        "concomitant": {
            "name": "Concomitant Therapy",
            "drugs": "PPI BID + Amoxicillin 1g BID + Clarithromycin 500mg BID + Metronidazole 500mg BID",
            "duration": "14 days", "efficacy": "90%",
        },
        "levofloxacin_triple": {
            "name": "Levofloxacin Triple (2nd-line)",
            "drugs": "PPI BID + Amoxicillin 1g BID + Levofloxacin 500mg QD",
            "duration": "14 days", "efficacy": "75-80%",
        },
    }
    reg = regimens.get(regimen, regimens["bismuth_quadruple"])
    return {
        "regimen": reg["name"], "drugs": reg["drugs"], "duration": reg["duration"],
        "efficacy": reg["efficacy"],
        "post_treatment": "C13/C14 urea breath test >=4 weeks after completion; PPI held 2 weeks prior",
        "confirmation_required": True,
    }


def _glasgow_blatchford(hb: float, bun: float, sbp: int = 120, pulse: int = 80,
                         melena: bool = False, syncope: bool = False,
                         liver_disease: bool = False, cardiac_failure: bool = False) -> dict:
    """Glasgow-Blatchford score for UGIB — predicts need for intervention."""
    score = 0
    if hb < 10:
        score += 6
    elif 10 <= hb < 12:
        score += 3
    elif 12 <= hb < 13:
        score += 1
    if bun >= 25:
        score += 6
    elif bun >= 22.4:
        score += 5
    elif bun >= 18.2:
        score += 4
    elif bun >= 14:
        score += 3
    elif bun >= 10:
        score += 2
    elif bun >= 8:
        score += 1
    if sbp < 90:
        score += 3
    elif sbp < 100:
        score += 2
    elif sbp < 110:
        score += 1
    if pulse >= 100:
        score += 1
    if melena:
        score += 1
    if syncope:
        score += 2
    if liver_disease:
        score += 2
    if cardiac_failure:
        score += 2

    risk = "Low" if score <= 1 else "High"
    recommendation = (
        "Outpatient safe; discharge with PPI + outpatient endoscopy" if score <= 1
        else "Admit for urgent endoscopy <24h; IV PPI 80mg bolus + 8mg/h infusion"
    )
    return {
        "gb_score": score, "risk": risk, "recommendation": recommendation,
        "components": {"Hb": hb, "BUN": bun, "SBP": sbp, "Pulse": pulse,
                       "Melena": melena, "Syncope": syncope,
                       "Liver disease": liver_disease, "Cardiac failure": cardiac_failure},
    }


def _endoscopy_urgency(indication: str) -> dict:
    """Endoscopy urgency triage — timing recommendations."""
    triage = {
        "variceal_bleed": ("Emergency", "<12 hours", "Active variceal hemorrhage; airway + octreotide + EVL"),
        "ugib_active": ("Emergency", "<24 hours", "Active UGIB with hemodynamic instability"),
        "ugib_stable": ("Urgent", "<24 hours", "GB score >=2; IV PPI + EGD with hemostasis"),
        "food_impaction": ("Urgent", "<24 hours", "Esophageal food bolus; risk of perforation"),
        "cholangitis": ("Urgent", "<24-48 hours", "ERCP for biliary decompression"),
        "dysphagia": ("Semi-urgent", "<2 weeks", "Progressive dysphagia + weight loss -> r/o malignancy"),
        "ibd_flare": ("Semi-urgent", "<1 week", "Severe UC/Crohn flare; colonoscopy for CMV exclusion"),
        "screening": ("Elective", "Routine", "Colorectal cancer screening (age 45-75)"),
        "surveillance": ("Elective", "Scheduled", "Post-polypectomy / IBD dysplasia surveillance"),
    }
    urgency, timing, details = triage.get(indication, ("Elective", "Routine", "Scheduled outpatient endoscopy"))
    return {"indication": indication, "urgency": urgency, "timing": timing, "details": details}


def _nafld_fli(bmi: float, waist_cm: float, ggt: float, tg_mgdl: float) -> dict:
    """Fatty Liver Index (FLI) — screening tool for NAFLD."""
    if tg_mgdl <= 0 or ggt <= 0:
        return {"fli": 0, "nafld_risk": "Unknown", "error": "TG/GGT must be >0"}
    y = 0.953 * log(tg_mgdl) + 0.139 * bmi + 0.718 * log(ggt) + 0.053 * waist_cm - 15.745
    fli = round((exp(y) / (1 + exp(y))) * 100, 1)
    risk = "Low (rule-out)" if fli < 30 else ("High (rule-in)" if fli >= 60 else "Indeterminate")
    return {
        "fli": fli, "risk": risk, "bmi": bmi, "waist_cm": waist_cm, "ggt": ggt, "tg_mgdl": tg_mgdl,
        "next_step": "No further workup; lifestyle modification" if fli < 30 else
        "Calculate Fib-4 -> if >=1.30 -> FibroScan -> if >=8 kPa -> liver biopsy",
    }


def _fib4_score(age: int, ast: float, alt: float, plt: float) -> dict:
    """Fibrosis-4 (Fib-4) index for liver fibrosis."""
    if alt <= 0 or plt <= 0:
        return {"fib4": 0, "risk": "Unknown", "error": "ALT/PLT must be >0"}
    fib4 = (age * ast) / (plt * (alt ** 0.5))
    fib4 = round(fib4, 2)
    if fib4 < 1.30:
        risk = "Low — exclude advanced fibrosis"
    elif fib4 <= 2.67:
        risk = "Indeterminate — FibroScan recommended"
    else:
        risk = "High — advanced fibrosis likely; GI/hepatology referral"
    return {"fib4": fib4, "risk": risk, "age": age, "ast": ast, "alt": alt, "plt": plt}


def _ibd_classification(diarrhea_type: str = "bloody", endoscopic_pattern: str = "continuous",
                        histology: str = "crypt_abscess", skip_lesions: bool = False,
                        transmural: bool = False, granulomas: bool = False) -> dict:
    """IBD differentiation: Crohn's Disease vs Ulcerative Colitis."""
    uc_features = 0
    cd_features = 0
    if diarrhea_type == "bloody":
        uc_features += 1
    if endoscopic_pattern == "continuous":
        uc_features += 1
    else:
        cd_features += 1
    if histology == "crypt_abscess":
        uc_features += 1
    if skip_lesions:
        cd_features += 2
    if transmural:
        cd_features += 2
    if granulomas:
        cd_features += 3

    diagnosis = ("Crohn's Disease" if cd_features > uc_features
                 else ("Ulcerative Colitis" if uc_features > cd_features
                       else "IBD Unclassified (IBDU)"))

    montreal = {}
    if "Crohn's" in diagnosis:
        montreal = {
            "age_at_dx": "A1 (<16y) / A2 (17-40y) / A3 (>40y)",
            "location": "L1 (ileal) / L2 (colonic) / L3 (ileocolonic) / L4 (upper GI)",
            "behavior": "B1 (non-stricturing/non-penetrating) / B2 (stricturing) / B3 (penetrating) + p (perianal)",
        }
    else:
        montreal = {
            "extent": "E1 (proctitis) / E2 (left-sided) / E3 (extensive/pancolitis)",
            "severity": "S0 (remission) / S1 (mild) / S2 (moderate) / S3 (severe)",
        }

    return {
        "diagnosis": diagnosis, "cd_score": cd_features, "uc_score": uc_features,
        "montreal_classification": montreal,
        "biologic_indications": "Anti-TNF (infliximab/adalimumab) 1st-line; vedolizumab/ustekinumab if anti-TNF failure",
        "surgery_considerations": ("CD: strictureplasty/resection; UC: IPAA (J-pouch)" if "Crohn's" in diagnosis
                                   else "Refractory/severe UC -> colectomy + IPAA after 2nd-line biologic failure"),
    }


def _child_pugh(bilirubin: float, albumin: float, inr: float, ascites: str = "none",
                encephalopathy: str = "none") -> dict:
    """Child-Pugh classification for liver cirrhosis severity."""
    score = 0
    if bilirubin < 2:
        score += 1
    elif bilirubin <= 3:
        score += 2
    else:
        score += 3
    if albumin > 3.5:
        score += 1
    elif albumin >= 2.8:
        score += 2
    else:
        score += 3
    if inr < 1.7:
        score += 1
    elif inr <= 2.3:
        score += 2
    else:
        score += 3
    if ascites == "none":
        score += 1
    elif ascites == "mild":
        score += 2
    else:
        score += 3
    if encephalopathy == "none":
        score += 1
    elif "grade 1" in encephalopathy.lower() or "grade 2" in encephalopathy.lower():
        score += 2
    else:
        score += 3

    if score <= 6:
        child_class = "A"
    elif score <= 9:
        child_class = "B"
    else:
        child_class = "C"

    prognosis = {
        "A": "Compensated; 1-year survival ~100%; elective surgery safe",
        "B": "Significant functional compromise; 1-year survival ~80%",
        "C": "Decompensated; 1-year survival ~45%; transplant evaluation",
    }.get(child_class, "")

    return {
        "child_pugh_score": score, "class": child_class, "prognosis": prognosis,
        "components": {"Bilirubin": bilirubin, "Albumin": albumin, "INR": inr,
                       "Ascites": ascites, "Encephalopathy": encephalopathy},
        "hcc_screening": "US + AFP q6mo" if child_class in ("A", "B")
        else "Individualize; transplant evaluation priority",
    }


def _meld_score(bilirubin: float, creatinine: float, inr: float, dialysis: bool = False,
                sodium: float = 140) -> dict:
    """MELD score for liver transplant priority (MELD-Na)."""
    def safe_log(x): return log(x) if x > 0 else 0
    bili_cap = min(max(bilirubin, 1.0) if bilirubin > 0 else 1.0, 4.0)
    cr_cap = 4.0 if dialysis else min(max(creatinine, 1.0) if creatinine > 0 else 1.0, 4.0)
    inr_cap = min(max(inr, 1.0) if inr > 0 else 1.0, 3.0)

    meld = round(3.78 * safe_log(bili_cap) + 11.2 * safe_log(cr_cap) + 9.57 * safe_log(inr_cap) + 6.43)
    meld = max(meld, 6)

    meld_na = meld + 1.32 * (137 - sodium) - 0.033 * meld * (137 - sodium)
    meld_na = round(meld_na)

    mortality = {range(0, 10): "~2%", range(10, 20): "~6%", range(20, 30): "~20%",
                 range(30, 40): "~53%", range(40, 100): "~71%"}
    mort = "Unknown"
    for r, m in mortality.items():
        if meld in r:
            mort = m
            break
    if mort == "Unknown":
        if meld <= 9:
            mort = "~2%"
        elif meld <= 19:
            mort = "~6%"
        elif meld <= 29:
            mort = "~20%"
        elif meld <= 39:
            mort = "~53%"
        else:
            mort = "~71%"

    return {
        "meld": meld, "meld_na": meld_na,
        "transplant_priority": f"MELD-Na {meld_na}; listed at MELD >=15",
        "mortality_90d": mort,
        "components": {"Bilirubin": bilirubin, "Creatinine": creatinine, "INR": inr,
                       "Dialysis": dialysis, "Sodium": sodium},
    }


# ── Business Process Functions ───────────────────────────────────────

def bp_reception(**kwargs) -> dict:
    """接诊与初步评估 — Rome IV + Glasgow-Blatchford + Child-Pugh screening."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    rome_ibs = _rome_iv_ibs(int(labs.get("pain_days_month", 2)), int(labs.get("months_duration", 1)),
                            labs.get("stool_form", "mixed"), bool(labs.get("pain_defecation", True)),
                            bool(labs.get("stool_freq_change", True)))
    rome_fd = _rome_iv_fd(bool(labs.get("postprandial_fullness", False)),
                          bool(labs.get("early_satiety", False)),
                          bool(labs.get("epigastric_pain", False)),
                          bool(labs.get("epigastric_burning", False)),
                          int(labs.get("months_duration", 1)))
    hb = float(labs.get("hemoglobin", 14))
    bun = float(labs.get("bun", 15))
    gb = _glasgow_blatchford(hb, bun, int(vitals.get("sbp", 120)), int(vitals.get("heart_rate", 80)),
                             bool(labs.get("melena", False)), bool(labs.get("syncope", False)),
                             bool(labs.get("liver_disease", "肝硬化" in dx)),
                             bool(labs.get("cardiac_failure", False)))
    child = _child_pugh(float(labs.get("bilirubin", 1.0)), float(labs.get("albumin", 4.0)),
                        float(labs.get("inr", 1.1)), labs.get("ascites", "none"),
                        labs.get("encephalopathy", "none")) if "肝硬化" in dx else None

    findings = [
        f"Rome IV IBS: {'Positive — ' + rome_ibs['subtype'] if rome_ibs['ibs'] else 'Criteria not met'}",
        f"Rome IV FD: {'Positive — ' + rome_fd['subtype'] if rome_fd['functional_dyspepsia'] else 'Criteria not met'}",
    ]
    if "出血" in dx or labs.get("melena"):
        findings.append(f"GB Score: {gb['gb_score']} -> {gb['risk']}")
    else:
        findings.append("No UGIB signs")
    findings.extend([
        "腹痛性质: " + labs.get("pain_character", "待评估"),
        "大便性状: " + labs.get("stool_form", "mixed") + (" + melena" if labs.get("melena") else ""),
    ])
    if child:
        findings.append(f"Child-Pugh: {child['child_pugh_score']} -> Class {child['class']} ({child['prognosis']})")

    recommendations = []
    if gb["gb_score"] > 0:
        recommendations.append(gb["recommendation"])
    if rome_ibs["ibs"]:
        recommendations.append(rome_ibs["management"])
    if rome_fd["functional_dyspepsia"]:
        recommendations.append(rome_fd["management"])
    if child and child["class"] == "C":
        recommendations.append("Child-Pugh C -> Transplant evaluation; HCC screening q6mo")
    if "消化性" in dx or "IBD" in dx:
        findings.insert(0, f"{'消化性溃疡' if '消化性' in dx else 'IBD'} 疾病匹配")
    checklist = ["呕血/黑便", "急性腹痛", "黄疸加重", "腹水增加", "肝性脑病"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注: ALT/AST/TBIL/ALB")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("消化内科")
    return _agent.clinical_result(
        summary=f"消化内科—初诊 GB{gb['gb_score']} {'Child'+child['class'] if child else ''} (stage S1)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_exam(**kwargs) -> dict:
    """辅助检查 — Endoscopy urgency + FLI + Fib-4."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    egd_urgency = _endoscopy_urgency(labs.get("endoscopy_indication",
        labs.get("indication", "ugib_active" if labs.get("ugib") else "screening")))
    fli = _nafld_fli(float(labs.get("bmi", 24)), float(labs.get("waist_cm", 85)),
                     float(labs.get("ggt", 30)), float(labs.get("triglycerides", 150)))
    fib4 = _fib4_score(int(p.get("age", 45)), float(labs.get("ast", 25)),
                       float(labs.get("alt", 25)), float(labs.get("platelets", 200)))

    findings = [
        f"Endoscopy: {egd_urgency['urgency']} — {egd_urgency['indication']} ({egd_urgency['timing']})",
        f"FLI: {fli['fli']} -> NAFLD risk: {fli['risk']}",
        f"Fib-4: {fib4['fib4']} -> {fib4['risk']}",
        "胃镜: LA classification (GERD); Forrest classification (ulcer bleed)",
        "肠镜: Mayo score (UC); SES-CD (Crohn); Paris classification (polyps)",
        "HP检测: C13/C14 UBT OR stool antigen OR gastric biopsy (RUT/histology)",
        "腹部CT: 肝脏/脾脏/胰腺/肠道壁增厚/淋巴结",
    ]
    recommendations = [
        f"Endoscopy: {egd_urgency['details']}",
        fli["next_step"],
    ]
    if egd_urgency["urgency"] in ("Emergency", "Urgent"):
        recommendations.insert(0, f"URGENT endoscopy: {egd_urgency['timing']}")
    if "消化性" in dx or "IBD" in dx:
        findings.insert(0, f"{'消化性溃疡' if '消化性' in dx else 'IBD'} 检查方案")
    checklist = ["呕血/黑便", "急性腹痛", "黄疸加重", "腹水增加", "肝性脑病"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("消化内科")
    return _agent.clinical_result(
        summary=f"消化内科—检查 {egd_urgency['urgency']} FLI{fli['fli']} Fib4{fib4['fib4']} (stage S2)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊与分型分期 — IBD classification + Child-Pugh + MELD."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    ibd = _ibd_classification(labs.get("diarrhea_type", "bloody"),
                              labs.get("endoscopic_pattern", "continuous"),
                              labs.get("histology", "crypt_abscess"),
                              bool(labs.get("skip_lesions", False)),
                              bool(labs.get("transmural", False)),
                              bool(labs.get("granulomas", False)))
    child = _child_pugh(float(labs.get("bilirubin", 1.0)), float(labs.get("albumin", 4.0)),
                        float(labs.get("inr", 1.1)), labs.get("ascites", "none"),
                        labs.get("encephalopathy", "none")) if "肝硬化" in dx else None
    meld = _meld_score(float(labs.get("bilirubin", 1.0)), float(labs.get("creatinine", 0.8)),
                       float(labs.get("inr", 1.1)), bool(labs.get("dialysis", False)),
                       float(labs.get("sodium", 140))) if "肝硬化" in dx else None

    findings = [
        f"IBD: {ibd['diagnosis']} (CD:{ibd['cd_score']} UC:{ibd['uc_score']})",
        f"内镜分级: Montreal {list(ibd['montreal_classification'].keys()) if ibd['montreal_classification'] else 'N/A'}",
    ]
    if child:
        findings.append(f"Child-Pugh: {child['child_pugh_score']} -> Class {child['class']} — {child['prognosis']}")
    if meld:
        findings.append(f"MELD-Na: {meld['meld_na']} — 90d mortality {meld['mortality_90d']}")
    findings.append(f"病理诊断: {labs.get('pathology', '待病理')}")
    findings.append(f"肝功能: {'Child-Pugh ' + child['class'] if child else 'Normal LFTs'}")

    recommendations = [
        f"IBD: {ibd['biologic_indications']}",
        ibd["surgery_considerations"],
    ]
    if child and child["class"] == "C":
        recommendations.append("Child-Pugh C -> Liver transplant evaluation; HCC surveillance")
    if meld and meld["meld_na"] >= 15:
        recommendations.append(f"MELD-Na {meld['meld_na']} >= 15 -> liver transplant listing")
    if "消化性" in dx or "IBD" in dx:
        findings.insert(0, f"{'消化性溃疡' if '消化性' in dx else 'IBD'} 确诊")
    checklist = ["呕血/黑便", "急性腹痛", "黄疸加重", "腹水增加", "肝性脑病"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("消化内科")
    return _agent.clinical_result(
        summary=f"消化内科—确诊 {ibd['diagnosis']}{' Child'+child['class'] if child else ''} MELD{meld['meld_na'] if meld else ''} (stage S3)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_plan(**kwargs) -> dict:
    """治疗方案制定 — HP eradication + IBD biologics + cirrhosis management."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    hp = _hp_eradication(labs.get("hp_regimen", "bismuth_quadruple"))
    child = _child_pugh(float(labs.get("bilirubin", 1.0)), float(labs.get("albumin", 4.0)),
                        float(labs.get("inr", 1.1)), labs.get("ascites", "none"),
                        labs.get("encephalopathy", "none")) if "肝硬化" in dx else None
    meld = _meld_score(float(labs.get("bilirubin", 1.0)), float(labs.get("creatinine", 0.8)),
                       float(labs.get("inr", 1.1)), bool(labs.get("dialysis", False)),
                       float(labs.get("sodium", 140))) if "肝硬化" in dx else None

    findings = [
        f"HP Eradication: {hp['regimen']} ({hp['duration']}); efficacy {hp['efficacy']}",
        "IBD Biologics: Anti-TNF (inflix/adalim) 1st-line; vedo/ustekinumab 2nd-line; JAKi (tofacitinib) for UC",
        "PPI: Omeprazole 20mg BID / Esomeprazole 40mg QD for GERD/PUD",
    ]
    if child:
        findings.extend([
            f"Cirrhosis: Child-Pugh {child['class']} ({child['child_pugh_score']}pts) -> {child['prognosis']}",
            f"MELD-Na: {meld['meld_na']} -> 90d mortality {meld['mortality_90d']}" if meld else "",
        ])
        findings.extend([
            "Ascites: Na restriction <2g/d + spironolactone 100mg/d (+ furosemide 40mg/d)",
            "Varices: NSBB (propranolol/carvedilol) for primary prophylaxis; EVL for high-risk varices",
            "HE: Lactulose 30mL BID titrated to 2-3 BM/d + rifaximin 550mg BID",
        ])
    findings.append("内镜治疗: EMR/ESD (early GI cancer); EVL (varices); APC (GAVE)")

    recommendations = [
        f"HP: {hp['drugs']} x {hp['duration']} -> {hp['post_treatment']}",
    ]
    if child and child["class"] == "C":
        recommendations.append("Child-Pugh C -> urgent transplant evaluation")
    if meld and meld["meld_na"] >= 15:
        recommendations.append(f"MELD {meld['meld_na']} -> list for OLT")
    if "消化性" in dx or "IBD" in dx:
        findings.insert(0, f"{'消化性溃疡' if '消化性' in dx else 'IBD'} 治疗路径")
    checklist = ["呕血/黑便", "急性腹痛", "黄疸加重", "腹水增加", "肝性脑病"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("消化内科")
    return _agent.clinical_result(
        summary=f"消化内科—治疗计划 {'Child'+child['class'] if child else ''} (stage S4a)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行与监测 — Endoscopic therapy + bleeding management + decompensation."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    gb = _glasgow_blatchford(float(labs.get("hemoglobin", 14)), float(labs.get("bun", 15)),
                             int(vitals.get("sbp", 120)), int(vitals.get("heart_rate", 80)),
                             bool(labs.get("melena", False)), bool(labs.get("syncope", False)),
                             bool(labs.get("liver_disease", "肝硬化" in dx)),
                             bool(labs.get("cardiac_failure", False)))
    egd = _endoscopy_urgency(labs.get("endoscopy_indication", "screening"))

    findings = [
        f"GB Score: {gb['gb_score']} -> {gb['risk']} risk",
        f"Endoscopy: {egd['urgency']} ({egd['timing']}) — {egd['indication']}",
        "出血止血: IV PPI 80mg bolus + 8mg/h x72h; EGD <24h (GB >=2) -> thermal/hemoclip",
        "息肉切除: EMR (10-20mm) / ESD (>20mm); clipping for perforation prophylaxis",
        "ERCP: CBD stone extraction + sphincterotomy + stent for cholangitis",
    ]
    if "肝硬化" in dx:
        findings.extend([
            "肝病综合治疗: Lactulose + rifaximin (HE); spironolactone + furosemide (ascites); NSBB (varices)",
            "SBP prophylaxis: Norfloxacin 400mg/d or TMP/SMX DS if ascites protein <1.5g/dL + Child B/C",
        ])
    recommendations = [
        gb["recommendation"] if gb["gb_score"] > 0 else "No acute bleeding; continue maintenance therapy",
        f"Endoscopy plan: {egd['details']}",
    ]
    if "消化性" in dx or "IBD" in dx:
        findings.insert(0, f"{'消化性溃疡' if '消化性' in dx else 'IBD'} 治疗执行")
    checklist = ["呕血/黑便", "急性腹痛", "黄疸加重", "腹水增加", "肝性脑病"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("消化内科")
    return _agent.clinical_result(
        summary=f"消化内科—治疗执行 GB{gb['gb_score']} {egd['urgency']} (stage S4b)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_followup(**kwargs) -> dict:
    """随访与长期管理 — Endoscopic surveillance + HP confirmation + HCC screening."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    child = _child_pugh(float(labs.get("bilirubin", 1.0)), float(labs.get("albumin", 4.0)),
                        float(labs.get("inr", 1.1)), labs.get("ascites", "none"),
                        labs.get("encephalopathy", "none")) if "肝硬化" in dx else None

    findings = [
        "内镜复查: Post-polypectomy (3-5yr); Barrett esophagus q3-5yr; IBD q1-3yr",
        "HP根除确认: C13/C14 UBT >=4wk post-treatment; stool antigen if UBT unavailable",
        "IBD缓解评估: Fecal calprotectin <250 + endoscopic Mayo 0-1 = deep remission",
    ]
    if child:
        findings.extend([
            f"Child-Pugh {child['class']} ({child['child_pugh_score']}pts)",
            f"HCC screening: {child['hcc_screening']}",
            "Varices surveillance: EGD q2-3yr (no varices); q1-2yr (small varices)",
        ])
    else:
        findings.append("肝癌筛查: N/A (no cirrhosis)")

    recommendations = [
        "HP test-of-cure at 4 weeks post-eradication",
        "IBD: Fecal calprotectin q3-6mo + colonoscopy q1-3yr",
    ]
    if child:
        recommendations.append(child["hcc_screening"])
    if "消化性" in dx or "IBD" in dx:
        findings.insert(0, f"{'消化性溃疡' if '消化性' in dx else 'IBD'} 长期随访")
    checklist = ["呕血/黑便", "急性腹痛", "黄疸加重", "腹水增加", "肝性脑病"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("消化内科")
    return _agent.clinical_result(
        summary=f"消化内科—随访 {'Child'+child['class'] if child else ''} (stage S5)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )
