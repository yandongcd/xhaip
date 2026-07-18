"""血液内科 — KnowledgeAgent-powered clinical reasoning.

Focus: 血液系统疾病诊疗与造血干细胞移植 — anemia, DIC, leukemia, lymphoma, myeloma, coagulation
GUIDELINES: 中国血液病诊疗指南（2022）, ISTH DIC, NCCN Leukemia/Lymphoma/Myeloma, ASH VTE
Conditions: 急性白血病, 淋巴瘤, 多发性骨髓瘤, MDS, ITP, 贫血, DIC, VTE

Real clinical scoring: MCV-based anemia workup, ISTH DIC score, transfusion thresholds,
leukostasis alert, Ann Arbor staging + IPI, CRAB/SLiM, DOAC dosing, Wells DVT/PE.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="hematology", department="血液内科")
_GUIDELINES = [
    "中国血液病诊疗指南（2022）",
    "ISTH DIC 诊断评分标准",
    "NCCN 急性白血病/淋巴瘤/骨髓瘤指南（2025）",
    "ASH VTE 抗凝指南（2020）",
    "中国输血指南",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def _get(patient: dict, *keys, default=0):
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


def _anemia_workup(patient: dict) -> dict:
    hb = float(_get(patient, "hemoglobin", "hb", "Hb", default=13))
    mcv = float(_get(patient, "mcv", "MCV", default=90))
    ferritin = float(_get(patient, "ferritin", default=100))
    tibc = float(_get(patient, "TIBC", "tibc", default=300))
    iron = float(_get(patient, "serum_iron", "iron", "Fe", default=80))
    b12 = float(_get(patient, "b12", "vitamin_b12", "B12", default=400))
    folate = float(_get(patient, "folate", default=10))
    reticulocyte = float(_get(patient, "reticulocyte", "retic", default=1.5))
    ldh = float(_get(patient, "ldh", "LDH", default=200))
    anemia = hb < 13 if _get(patient, "sex", "gender", default="M") == "M" else hb < 12
    tsat = (iron / tibc * 100) if tibc > 0 else 25
    if not anemia:
        return {"anemic": False, "hb": hb, "mcv": mcv, "category": "No anemia"}
    if mcv < 80:
        category = "microcytic"
        if ferritin < 30 or (ferritin < 100 and tsat < 20):
            subtype = "IDA"
            rx = "FeSO4 325mg TID + vitC; GI workup (EGD/colonoscopy)"
        elif ferritin > 100 and tsat > 45:
            subtype = "Thalassemia trait / ACD with overload"
            rx = "Hb electrophoresis; avoid empiric iron"
        else:
            subtype = "ACD with microcytosis"
            rx = "Treat underlying condition; ESA if CKD plus Hb lt 10"
    elif mcv <= 100:
        category = "normocytic"
        if reticulocyte > 2:
            subtype = f"Hemolysis (retic={reticulocyte}%, LDH={ldh})"
            rx = "Coombs DAT, smear, G6PD, Hb electrophoresis"
        elif ferritin < 30:
            subtype = "Early iron deficiency"
            rx = "Iron supplementation + GI workup"
        else:
            subtype = "ACD/CKD/marrow disorder"
            rx = "CBC diff, retic, smear; BMAT if pancytopenia/blasts"
    else:
        category = "macrocytic"
        if b12 < 200:
            subtype = f"B12 deficiency (B12={b12})"
            rx = "IM B12 1000ug daily x1w then weekly"
        elif folate < 4:
            subtype = f"Folate deficiency (folate={folate})"
            rx = "Folic acid 1-5mg PO daily; check B12 first"
        else:
            subtype = f"MDS/alcohol/liver/drug (B12={b12}, folate={folate})"
            rx = "Smear for hypersegmented PMNs; BMAT if pancytopenia/blasts"
    return {"anemic": True, "hb": hb, "mcv": mcv, "category": category,
            "subtype": subtype, "treatment": rx,
            "iron_studies": {"ferritin": ferritin, "TIBC": tibc, "tsat_pct": round(tsat, 1)},
            "vitamin_studies": {"b12": b12, "folate": folate}}


def _calc_isth_dic(patient: dict) -> dict:
    plt = float(_get(patient, "platelets", "plt", "PLT", default=200))
    pt = float(_get(patient, "pt", "PT", default=13))
    pt_control = float(_get(patient, "pt_control", default=12))
    fibrinogen = float(_get(patient, "fibrinogen", default=3.0))
    d_dimer = float(_get(patient, "d_dimer", "D-dimer", "ddimer", default=0.5))
    score = 0
    comp = {}
    if plt > 100:
        comp["plt"] = 0
    elif plt >= 50:
        score += 1
        comp["plt"] = 1
    else:
        score += 2
        comp["plt"] = 2
    pt_ratio = pt / pt_control if pt_control else 1
    if pt_ratio < 1.25:
        comp["pt"] = 0
    elif pt_ratio <= 1.66:
        score += 1
        comp["pt"] = 1
    else:
        score += 2
        comp["pt"] = 2
    if fibrinogen > 1.0:
        comp["fibrinogen"] = 0
    else:
        score += 1
        comp["fibrinogen"] = 1
    if d_dimer < 0.5:
        comp["d_dimer"] = 0
    elif d_dimer <= 5:
        score += 1
        comp["d_dimer"] = 1
    else:
        score += 2
        comp["d_dimer"] = 2
    overt = score >= 5
    return {"score": score, "overt_dic": overt, "components": comp,
            "action": "Treat cause + PLT/FFP/cryo support" if overt else "Monitor, recheck if deteriorates"}


def _transfusion_thresholds(patient: dict) -> dict:
    hb = float(_get(patient, "hemoglobin", "hb", "Hb", default=10))
    plt = float(_get(patient, "platelets", "plt", "PLT", default=150))
    inr = float(_get(patient, "inr", "INR", default=1.2))
    fibrinogen = float(_get(patient, "fibrinogen", default=3.0))
    bleeding = _get(patient, "active_bleeding", "bleeding", default=False)
    cardiac = _get(patient, "cardiac_disease", default=False)
    procedure = _get(patient, "procedure_planned", default=False)
    cvc = _get(patient, "cvc_insertion", default=False)
    recs = []
    if hb < 70 and not cardiac:
        recs.append(f"RBC: Hb={hb}<70 (stable) - transfuse 1 unit, target 70-90")
    elif hb < 80 and cardiac:
        recs.append(f"RBC: Hb={hb}<80 + cardiac - transfuse, target 80-100")
    else:
        recs.append(f"RBC: Hb={hb} - restrictive, no transfusion")
    if plt < 10 and not bleeding:
        recs.append(f"PLT: PLT={plt}<10 - prophylactic transfusion")
    elif plt < 20 and cvc:
        recs.append(f"PLT: PLT={plt}<20 + CVC - transfuse pre-procedure")
    elif plt < 50 and (procedure or bleeding):
        recs.append(f"PLT: PLT={plt}<50 + procedure/bleeding - transfuse")
    if inr > 1.5 and bleeding:
        recs.append(f"FFP: INR={inr}>1.5 + bleeding - 15mL/kg or 4F-PCC")
    if fibrinogen < 1.0:
        recs.append(f"Cryo: fibrinogen={fibrinogen}<1.0 - 1 unit/5-10kg")
    return {"hb": hb, "plt": plt, "inr": inr, "fibrinogen": fibrinogen, "recommendations": recs}


def _leukemia_alert(patient: dict) -> dict:
    wbc = float(_get(patient, "wbc", "WBC", "leukocytes", default=10))
    blasts_pct = float(_get(patient, "blast_percent", "blasts_pct", default=0))
    symptoms = _get(patient, "leukostasis_symptoms", default=False)
    resp = _get(patient, "respiratory_distress", default=False)
    neuro = _get(patient, "neurologic_symptoms", default=False)
    hyper = wbc > 100
    leukostasis = hyper and (symptoms or resp or neuro)
    if leukostasis:
        action = "LEUKOSTASIS EMERGENCY: leukapheresis + hydroxyurea; avoid RBC; TLS prophylaxis"
    elif hyper:
        action = f"Hyperleukocytosis WBC={wbc}K - hydration, allopurinol, hydroxyurea; leukapheresis if symptomatic"
    else:
        action = f"WBC={wbc}K - no leukostasis risk"
    return {"wbc": wbc, "hyperleukocytosis": hyper, "leukostasis": leukostasis,
            "blasts_pct": blasts_pct, "action": action,
            "tls_risk": hyper or blasts_pct > 25}


def _lymphoma_staging(patient: dict) -> dict:
    stage = int(_get(patient, "ann_arbor_stage", default=2))
    b_symptoms = _get(patient, "b_symptoms", default=False)
    ldh = float(_get(patient, "ldh", "LDH", default=200))
    ldh_uln = float(_get(patient, "ldh_uln", default=250))
    age = int(_get(patient, "age", default=55))
    ecog = int(_get(patient, "ecog", default=1))
    extranodal = int(_get(patient, "extranodal_sites", default=0))
    stage_desc = {1: "I - single node region", 2: "II - >=2 regions same side", 3: "III - both sides diaphragm", 4: "IV - disseminated extranodal"}
    ipi = 0
    if age > 60:
        ipi += 1
    if ldh > ldh_uln:
        ipi += 1
    if ecog >= 2:
        ipi += 1
    if stage >= 3:
        ipi += 1
    if extranodal > 1:
        ipi += 1
    risk = {0: "low (0)", 1: "low-intermediate (1)", 2: "low-intermediate (2)", 3: "high-intermediate (3)", 4: "high (4)", 5: "high (5)"}
    return {"stage": stage, "stage_desc": stage_desc.get(stage, "?"), "b_symptoms": b_symptoms,
            "ipi": ipi, "ipi_risk": risk.get(ipi, "?"), "ldh": ldh, "age": age, "ecog": ecog}


def _myeloma_crab(patient: dict) -> dict:
    calcium = float(_get(patient, "calcium", "ca", default=9))
    creatinine = float(_get(patient, "creatinine", "cr", default=1.0))
    hb = float(_get(patient, "hemoglobin", "hb", default=13))
    bone_lesions = _get(patient, "bone_lesions", "lytic_lesions", default=False)
    plasma_pct = float(_get(patient, "plasma_cell_pct", "marrow_plasma", default=10))
    sflc_ratio = float(_get(patient, "sflc_ratio", "free_light_chain_ratio", default=5))
    mri_lesion = _get(patient, "mri_focal_lesion", default=False)
    crab = []
    slim = []
    if calcium > 11:
        crab.append("HyperCalcemia")
    if creatinine > 2 or _get(patient, "renal_insufficiency", default=False):
        crab.append("Renal")
    if hb < 10:
        crab.append("Anemia")
    if bone_lesions:
        crab.append("Bone lesions")
    if plasma_pct >= 60:
        slim.append("SLiM: marrow plasma >=60%")
    if sflc_ratio >= 100:
        slim.append("SLiM: involved/uninvolved FLC ratio >=100")
    if mri_lesion:
        slim.append("SLiM: >1 focal lesion on MRI")
    mm_defining = len(crab) >= 1 or len(slim) >= 1
    return {"mm_defining": mm_defining, "crab": crab, "slim": slim,
            "action": "Treat active MM" if mm_defining else "Smoldering MM - observe or trial"}


def _anticoagulation_guide(patient: dict) -> dict:
    crcl = float(_get(patient, "crcl", "CrCl", "creatinine_clearance", default=80))
    indication = _get(patient, "anticoag_indication", default="AF")
    mechanical_valve = _get(patient, "mechanical_valve", default=False)
    recs = []
    if indication in ("AF", "DVT", "PE") and not mechanical_valve:
        if crcl >= 50:
            recs.append("Apixaban 5mg BID or Rivaroxaban 20mg daily (CrCl>=50)")
        elif crcl >= 30:
            recs.append("Apixaban 5mg BID (CrCl 30-49 OK) or Rivaroxaban 15mg daily")
        elif crcl >= 15:
            recs.append("Apixaban 2.5-5mg BID or Edoxaban 30mg daily (CrCl 15-29)")
            recs.append("Warfarin alternative: target INR 2-3")
        else:
            recs.append("Warfarin only - DOACs not studied with CrCl<15 (apixaban sometimes used)")
    if mechanical_valve:
        recs.append("Warfarin: target INR 2.5-3.5 (mitral/Ao+risk) or 2-3 (bileaflet Ao)")
    recs.append("Reversal: warfarin=4F-PCC+vitK; dabigatran=idarucizumab; Xa inhibitors=andexanet alfa or 4F-PCC")
    return {"crcl": crcl, "indication": indication, "recommendations": recs}


def _vte_wells(patient: dict) -> dict:
    cancer = _get(patient, "active_cancer", default=False)
    immobile = _get(patient, "immobilization", "recent_surgery", default=False)
    prev_vte = _get(patient, "previous_dvt_pe", default=False)
    unilateral = _get(patient, "unilateral_swelling", default=False)
    calf_swelling = _get(patient, "calf_swelling_gt_3cm", default=False)
    pitting = _get(patient, "pitting_edema", default=False)
    collaterals = _get(patient, "collateral_veins", default=False)
    alt_dx = _get(patient, "alternative_diagnosis_likely", default=True)
    score = 0
    if cancer:
        score += 1
    if immobile:
        score += 1
    if prev_vte:
        score += 1
    if unilateral:
        score += 1
    if calf_swelling:
        score += 1
    if pitting:
        score += 1
    if collaterals:
        score += 1
    if not alt_dx:
        score -= 2
    if score <= 0:
        prob = "unlikely"
    elif score <= 2:
        prob = "moderate"
    else:
        prob = "likely"
    return {"score": score, "probability": prob,
            "action": "US if likely; D-dimer if unlikely then US if elevated" if prob == "unlikely" else "Venous US (proximal compression)"}


def bp_reception(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    anemia = _anemia_workup(p)
    findings = ["贫血症状: fatigue, pallor, dyspnea, palpitations", "出血倾向: petechiae, ecchymosis, mucosal bleeding", "发热/淋巴结肿大: B symptoms screen", "骨痛: myeloma/leukemia infiltrative",
                f"贫血筛查: Hb={anemia['hb']}, MCV={anemia['mcv']} - {anemia.get('category','')}"]
    if anemia["anemic"]:
        findings.append(f"贫血分类: {anemia['subtype'][:60]}...")
    recommendations = []
    if any(t in dx for t in ["急性白", "leukemia"]):
        la = _leukemia_alert(p)
        findings.insert(0, f"{'LEUKOSTASIS ALERT' if la['leukostasis'] else 'Leukemia'} WBC={la['wbc']}K blasts={la['blasts_pct']}%")
        if la["leukostasis"]:
            findings.insert(0, la["action"])
            recommendations.append(la["action"])
    if anemia["anemic"] and anemia.get("treatment"):
        recommendations.append(anemia["treatment"])
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血液内科")
    return _agent.clinical_result(patient=p, stage="triage", summary=f"血液内科 - 初诊完成 (Hb={anemia['hb']}, MCV={anemia['mcv']})", findings=findings, guidelines=guides, rules=rules, alerts=vitals.get("alerts",[]), recommendations=recommendations, guideline_refs=_GUIDELINES)


def bp_exam(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    findings = ["CBC + diff + reticulocyte: Hb/PLT/WBC/ANC/AMC/blasts", "外周血涂片: morphology, blasts, schistocytes, spherocytes", "骨髓穿刺+活检: cellularity, blasts%, dysplasia, fibrosis, iron stain", "流式细胞术: immunophenotype - CD markers for lineage", "细胞遗传学+分子: karyotype, FISH, NGS panel (NPM1/FLT3/TP53/IDH)"]
    recommendations = ["Bone marrow: aspirate + biopsy + flow + cyto + molecular (all 5 modalities)"]
    if any(t in dx for t in ["淋巴瘤"]):
        findings.insert(0, "Lymphoma: excisional LN biopsy + IHC + flow + FISH for MYC/BCL2/BCL6")
    if any(t in dx for t in ["骨髓瘤"]):
        findings.insert(0, "Myeloma: SPEP/IFE/sFLC/24h urine + skeletal survey (or PET-CT) + BMAT")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血液内科")
    return _agent.clinical_result(patient=p, stage="exam", summary="血液内科 - 血液学检查完成", findings=findings, guidelines=guides, rules=rules, alerts=vitals.get("alerts",[]), recommendations=recommendations, guideline_refs=_GUIDELINES)


def bp_diagnosis(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    findings = ["WHO分型: 2022 WHO/ICC classification", "危险分层: ELN 2022 (AML), IPSS-R (MDS), R-ISS (myeloma)", "基因突变: NPM1, FLT3-ITD, CEBPA, TP53, IDH1/2, ASXL1, RUNX1", "预后评分: IPI (DLBCL), CLL-IPI, R-ISS (myeloma), IPSS-R (MDS)"]
    recommendations = []
    anemia = _anemia_workup(p)
    findings.append(f"贫血: Hb={anemia['hb']}, MCV={anemia['mcv']} - {anemia.get('category','')}: {anemia.get('subtype','')[:50]}...")
    dic = _calc_isth_dic(p)
    if dic["overt_dic"]:
        findings.insert(0, f"ISTH DIC score={dic['score']}: OVERT DIC - {dic['action']}")
        recommendations.append(dic["action"])

    if any(t in dx for t in ["急性白", "leukemia"]):
        la = _leukemia_alert(p)
        findings.insert(0, f"Leukemia: WBC={la['wbc']}K blasts={la['blasts_pct']}% {'HYPERLEUKOCYTOSIS' if la['hyperleukocytosis'] else ''}")
        if la["tls_risk"]:
            recommendations.append("TLS prophylaxis: allopurinol + IV hydration + rasburicase prn")
    if any(t in dx for t in ["淋巴瘤"]):
        ls = _lymphoma_staging(p)
        findings.insert(0, f"Lymphoma: Ann Arbor {ls['stage_desc']}, {'B sx+' if ls['b_symptoms'] else 'B sx-'}, IPI={ls['ipi']} ({ls['ipi_risk']})")
    if any(t in dx for t in ["骨髓瘤"]):
        mm = _myeloma_crab(p)
        findings.insert(0, f"Myeloma: {'MM-defining' if mm['mm_defining'] else 'Smoldering'} - CRAB: {', '.join(mm['crab']) if mm['crab'] else 'none'}; {'SLiM: '+', '.join(mm['slim']) if mm['slim'] else ''}")
        if mm["mm_defining"]:
            recommendations.append(mm["action"])
    if any(t in dx for t in ["DVT", "PE", "肺栓塞", "深静脉"]):
        vte = _vte_wells(p)
        findings.insert(0, f"VTE: Wells score={vte['score']} ({vte['probability']}) - {vte['action']}")

    tx = _transfusion_thresholds(p)
    recommendations.extend(tx["recommendations"])
    findings.append(f"输血评估: Hb={tx['hb']} PLT={tx['plt']} INR={tx['inr']} Fib={tx['fibrinogen']}")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血液内科")
    return _agent.clinical_result(patient=p, stage="diagnosis", summary=f"血液内科 - 确诊分型完成 ({dx})", findings=findings, guidelines=guides, rules=rules, alerts=vitals.get("alerts",[]), recommendations=recommendations, guideline_refs=_GUIDELINES)


def bp_plan(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    findings = ["化疗方案: induction/consolidation/maintenance per ELN/NCCN", "靶向药物: FLT3/IDH/BCL2/BCR-ABL inhibitors based on mutations", "移植评估: allo-HSCT timing (CR1 for high-risk AML), auto-HSCT (myeloma)", "支持治疗: transfusion, G-CSF, infection prophylaxis, TLS prevention"]
    recommendations = []
    if any(t in dx for t in ["急性白"]):
        findings.insert(0, "AML induction: 7+3 (cytarabine+daunorubicin) or CPX-351 (secondary AML) or Ven+Aza (elderly/unfit)")
        la = _leukemia_alert(p)
        if la["tls_risk"]:
            recommendations.append(la.get("tls_prophylaxis", "Allopurinol + IV fluids"))
    if any(t in dx for t in ["淋巴瘤"]):
        ls = _lymphoma_staging(p)
        findings.insert(0, f"DLBCL: R-CHOP x6 ({'R-miniCHOP if frail' if ls['age']>80 else 'full dose R-CHOP'}), IPI={ls['ipi']}")
    if any(t in dx for t in ["骨髓瘤"]):
        findings.insert(0, "Myeloma: VRd (bortezomib+lenalidomide+dex) or DRd (daratumumab+len+dex) induction x4-6 then auto-HSCT if eligible")
    if any(t in dx for t in ["DVT", "PE"]):
        ac = _anticoagulation_guide(p)
        findings.insert(0, f"Anticoagulation (CrCl={ac['crcl']}): {ac['recommendations'][0]}")
        recommendations.extend(ac["recommendations"])

    tx = _transfusion_thresholds(p)
    findings.append(f"输血支持: {'; '.join(tx['recommendations'][:2])}")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血液内科")
    return _agent.clinical_result(patient=p, stage="plan", summary="血液内科 - 治疗方案完成", findings=findings, guidelines=guides, rules=rules, alerts=vitals.get("alerts",[]), recommendations=recommendations, guideline_refs=_GUIDELINES)


def bp_treatment(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    findings = ["化疗毒副反应: myelosuppression (ANC nadir D7-10), mucositis, nausea/vomiting (CINV prophylaxis), cardiotoxicity (anthracycline echo)", "输血支持: per thresholds - leukoreduced, irradiated if HSCT candidate", "感染防控: neutropenic fever protocol (ANC<500+temp>38.3) - cefepime/pip-tazo/meropenem + vancomycin if indicated", "GVHD 管理: tacrolimus + MTX (CNI+MTX for allo-HSCT); aGVHD grading (Glucksberg); cGVHD (NIH criteria)"]
    recommendations = ["Neutropenic fever: blood cultures + IV antibiotics within 1h, no rectal temps/exams", "G-CSF (filgrastim) 5 mcg/kg/d starting D+5 post-chemo until ANC>1000", "PJP prophylaxis: TMP-SMX DS 3x/week (ALL/lymphoma/T-cell depletion)", "Antifungal prophylaxis: posaconazole or voriconazole (AML induction, GVHD on steroids)"]
    tx = _transfusion_thresholds(p)
    recommendations.extend([r for r in tx["recommendations"] if "transfusion indicated" in r.lower()])
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血液内科")
    return _agent.clinical_result(patient=p, stage="treatment", summary="血液内科 - 治疗执行完成", findings=findings, guidelines=guides, rules=rules, alerts=vitals.get("alerts",[]), recommendations=recommendations, guideline_refs=_GUIDELINES)


def bp_followup(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    findings = ["MRD 监测: flow cytometry (10^-4) or NGS (10^-6) - q3mo for AML/ALL; MRD+ = preemptive intervention", "复发评估: monthly CBC, symptoms (B sx, bone pain, cytopenias)", "远期并发症: t-MDS/AML (alkylators/topoisomerase), cardiotoxicity (anthracyclines >250mg/m^2), infertility (cryopreservation pre-treatment)", "移植后随访: chimerism (STR) q3mo x1yr then q6mo, GVHD evaluation, vaccinations (inactivated only until immune reconstitution)"]
    recommendations = ["CBC q1-3mo (first 2 years) then q6mo", "BMAT at 1mo/3mo/6mo/12mo post-induction (AML); MRD-guided preemptive therapy",
                      "Iron overload (ferritin >1000 or >20 RBC units): cardiac/liver MRI T2*, chelation if indicated", "Survivorship: annual echo, endocrine (thyroid/gonadal), second malignancy screening (skin/breast/colorectal per age)"]
    if any(t in dx for t in ["DVT", "PE"]):
        recommendations.append("Anticoagulation: continue 3-6mo if provoked, indefinite if unprovoked/recurrent/thrombophilia")
        findings.append("Post-thrombotic syndrome prevention: compression stockings 30-40mmHg x2yr")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血液内科")
    return _agent.clinical_result(patient=p, stage="followup", summary="血液内科 - 随访管理完成", findings=findings, guidelines=guides, rules=rules, alerts=vitals.get("alerts",[]), recommendations=recommendations, guideline_refs=_GUIDELINES)
