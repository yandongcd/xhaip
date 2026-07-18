"""神经外科 — KnowledgeAgent-powered clinical reasoning.

Focus: 颅脑与脊柱神经外科手术
GUIDELINES: 中国神经外科临床诊疗指南（2021）, WFNS SAH Guidelines, AANS/STN TBI Guidelines
Conditions: 颅脑损伤, 脑出血, 蛛网膜下腔出血, 脑肿瘤, 脊柱损伤, 脑血管疾病

Real clinical scoring: GCS, Hunt-Hess, Fisher, WFNS, ASIA, Cushing's Triad, ICP management.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="neurosurgery", department="神经外科")
_GUIDELINES = [
    "中国神经外科临床诊疗指南（2021）",
    "WFNS 蛛网膜下腔出血诊疗指南",
    "AANS/STN 颅脑创伤诊疗指南（第四版）",
    "AOSpine 脊柱损伤分级指南",
]

_agent.rule_engine.load_all()


# ── Helpers ──────────────────────────────────────────────────────────────

def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


# ── Clinical Scoring Functions ───────────────────────────────────────────

def _calc_gcs(patient: dict) -> dict:
    """Glasgow Coma Scale: Eye(1-4) + Verbal(1-5) + Motor(1-6) → total 3-15"""
    neuro = patient.get("neuro_exam", patient.get("neurological_exam", {}))
    eye = int(neuro.get("eye_opening", neuro.get("gcs_eye", 4)))
    verbal = int(neuro.get("verbal_response", neuro.get("gcs_verbal", 5)))
    motor = int(neuro.get("motor_response", neuro.get("gcs_motor", 6)))
    eye = max(1, min(4, eye))
    verbal = max(1, min(5, verbal))
    motor = max(1, min(6, motor))
    total = eye + verbal + motor
    if total <= 8:
        severity = "severe (intubate)"
    elif total <= 12:
        severity = "moderate"
    else:
        severity = "mild"
    return {
        "eye": eye, "verbal": verbal, "motor": motor,
        "total": total, "severity": severity,
        "range": "3-15",
        "eye_labels": {1: "no opening", 2: "to pain", 3: "to speech", 4: "spontaneous"},
        "verbal_labels": {1: "none", 2: "sounds", 3: "words", 4: "confused", 5: "oriented"},
        "motor_labels": {1: "none", 2: "extension", 3: "flexion", 4: "withdraws", 5: "localizes", 6: "obeys"},
    }


def _calc_hunt_hess(patient: dict) -> dict:
    """Hunt-Hess grade for SAH: I (minimal) → V (deep coma, moribund)."""
    neuro = patient.get("neuro_exam", patient.get("neurological_exam", {}))
    grade = int(neuro.get("hunt_hess", patient.get("hunt_hess_grade", 2)))
    grade = max(1, min(5, grade))
    descriptions = {
        1: "I - Asymptomatic or mild headache / slight nuchal rigidity",
        2: "II - Moderate-severe headache / nuchal rigidity / CN palsy (no focal deficit)",
        3: "III - Drowsy / confused / mild focal neurological deficit",
        4: "IV - Stupor / moderate-severe hemiparesis / early decerebrate rigidity",
        5: "V - Deep coma / decerebrate rigidity / moribund appearance",
    }
    surgical_mortality = {1: "0-5%", 2: "2-10%", 3: "10-15%", 4: "60-70%", 5: "70-100%"}
    return {
        "grade": grade,
        "description": descriptions[grade],
        "surgical_mortality": surgical_mortality[grade],
        "high_grade": grade >= 4,
    }


def _calc_fisher_grade(patient: dict) -> dict:
    """Fisher grade (SAH on CT): 1 (no blood) → 4 (intraventricular or parenchymal)."""
    imaging = patient.get("imaging", patient.get("ct_findings", {}))
    grade = int(imaging.get("fisher_grade", patient.get("fisher_grade", 2)))
    grade = max(1, min(4, grade))
    descriptions = {
        1: "1 - No subarachnoid blood detected on CT",
        2: "2 - Diffuse thin layer of SAH (<1mm)",
        3: "3 - Localized clot or thick layer of SAH (≥1mm)",
        4: "4 - Intracerebral or intraventricular hemorrhage with diffuse or no SAH",
    }
    vasospasm_risk = {1: "low (~0%)", 2: "moderate (~20%)", 3: "high (~40%)", 4: "variable"}
    return {
        "grade": grade,
        "description": descriptions[grade],
        "vasospasm_risk": vasospasm_risk[grade],
        "nimodipine_indicated": grade >= 2,
    }


def _calc_wfns(patient: dict) -> dict:
    """WFNS grade (SAH): GCS + motor deficit → I-V."""
    gcs = _calc_gcs(patient)
    gcs_total = gcs["total"]
    motor = gcs["motor"]
    has_motor_deficit = motor < 6
    if gcs_total == 15 and not has_motor_deficit:
        grade = 1
    elif 14 <= gcs_total <= 15 and has_motor_deficit:
        grade = 2
    elif 13 <= gcs_total <= 14:
        grade = 3
    elif 7 <= gcs_total <= 12:
        grade = 4
    else:
        grade = 5
    labels = {1: "I - GCS 15, no motor deficit", 2: "II - GCS 13-14, no motor deficit",
              3: "III - GCS 13-14, motor deficit present", 4: "IV - GCS 7-12",
              5: "V - GCS 3-6"}
    return {"grade": grade, "label": labels[grade], "gcs": gcs_total, "motor_deficit": has_motor_deficit}


def _check_cushing_triad(vitals: dict) -> dict:
    """Cushing's triad: bradycardia + hypertension + irregular breathing → ↑ICP emergency."""
    hr = vitals.get("heart_rate", vitals.get("hr", vitals.get("pulse", 75)))
    sbp = vitals.get("sbp", vitals.get("systolic_bp", vitals.get("bp_systolic", 120)))
    rr = vitals.get("respiratory_rate", vitals.get("rr", 16))
    rr_irregular = vitals.get("rr_irregular", vitals.get("breathing_irregular", False))
    bradycardia = hr < 60
    hypertension = sbp > 140
    widened_pulse = vitals.get("dbp", 80) and (sbp - vitals.get("dbp", 80)) > 50
    irregular_breathing = rr < 10 or rr > 24 or rr_irregular
    triad_present = bradycardia and hypertension and irregular_breathing
    return {
        "present": triad_present,
        "bradycardia": bradycardia,
        "hypertension": hypertension,
        "irregular_breathing": irregular_breathing,
        "widened_pulse_pressure": widened_pulse,
        "emergency": triad_present,
        "action": "IMMEDIATE neurosurgical consult — suspect ↑ICP with brainstem herniation" if triad_present else "monitor",
    }


def _icp_management(gcs: dict, patient: dict) -> dict:
    """ICP management protocol: head elevation, mannitol, hypertonic saline, decompressive craniectomy."""
    recommendations = []
    recommendations.append("Head elevation 30° (ensure neutral neck alignment, no cervical collar constriction)")
    recommendations.append("Maintain euvolemia: target MAP ≥ 80 mmHg, CPP ≥ 60 mmHg")
    if gcs["total"] <= 12:
        recommendations.append("Mannitol 0.25-1.0 g/kg IV bolus (serum osmolality ≤ 320 mOsm/L)")
        recommendations.append("Consider hypertonic saline 3% (250 mL over 30 min) if hyponatremic")
    if gcs["total"] <= 8:
        recommendations.append("Prophylactic hyperventilation to PaCO₂ 30-35 mmHg (short-term bridge)")
        recommendations.append("Sedation + analgesia protocol (propofol/midazolam + fentanyl)")
        recommendations.append("Ventriculostomy / EVD for ICP monitoring + CSF drainage")
    if patient.get("icp", patient.get("intracranial_pressure", 15)) > 25:
        recommendations.append(
            "⚠ DECOMPRESSIVE CRANIECTOMY THRESHOLD — ICP > 25 mmHg refractory to tier-2 therapies")
    recommendations.append("Defer elective neurosurgery if ICP uncontrolled")
    return {"recommendations": recommendations, "gcs_trigger": gcs["total"] <= 8,
            "refractory_icp": patient.get("icp", patient.get("intracranial_pressure", 0)) > 25}


def _assess_asia(patient: dict) -> dict:
    """ASIA Impairment Scale: A (complete) / B (sensory incomplete) / C-D (motor incomplete) / E (normal)."""
    spine = patient.get("spine_exam", patient.get("asia_exam", {}))
    grade = spine.get("asia_grade", patient.get("asia", "E")).upper()
    motor_level = spine.get("motor_level", patient.get("neurologic_level", "N/A"))
    descriptions = {
        "A": "Complete — no motor or sensory function preserved in sacral segments S4-S5",
        "B": "Sensory Incomplete — sensory but no motor function preserved below neurological level (includes S4-S5)",
        "C": "Motor Incomplete — motor function preserved below neurological level, >½ key muscles < grade 3",
        "D": "Motor Incomplete — motor function preserved below neurological level, ≥½ key muscles ≥ grade 3",
        "E": "Normal — motor and sensory function normal",
    }
    neurogenic_shock = False
    vitals = patient.get("vitals", {})
    if grade in ("A", "B") and motor_level and "T6" in str(motor_level):
        hr = vitals.get("heart_rate", vitals.get("hr", 75))
        sbp = vitals.get("sbp", vitals.get("systolic_bp", 90))
        if hr < 60 and sbp < 100:
            neurogenic_shock = True
    return {
        "grade": grade,
        "description": descriptions.get(grade, "Unknown"),
        "neurological_level": motor_level,
        "is_complete": grade == "A",
        "neurogenic_shock_suspected": neurogenic_shock,
        "neurogenic_shock_note": "Bradycardia + hypotension above T6 → unopposed vagal tone; treat with vasopressors + atropine" if neurogenic_shock else None,
    }


def _assess_motor_power(patient: dict) -> dict:
    """MRC muscle power grading 0-5 for key muscle groups."""
    neuro = patient.get("neuro_exam", patient.get("neurological_exam", {}))
    power_raw = neuro.get("motor_power", neuro.get("muscle_power", neuro.get("power", {})))
    if isinstance(power_raw, dict):
        key_muscles = power_raw
    else:
        key_muscles = {"R_UE": 5, "L_UE": 5, "R_LE": 5, "L_LE": 5}
    abnormal = any(v < 5 for v in key_muscles.values() if isinstance(v, (int, float)))
    return {"power": key_muscles, "abnormal": abnormal, "scale": "MRC 0-5"}


# ── Business Process Functions ───────────────────────────────────────────

def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — GCS triage + Hunt-Hess if SAH suspected."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", p.get("labs", {}))
    dx = p.get("diagnosis", "")

    gcs = _calc_gcs(p)
    findings = [
        f"GCS: {gcs['total']}/15 — {gcs['severity']} (E{gcs['eye']}V{gcs['verbal']}M{gcs['motor']})",
        "瞳孔反应评估: 大小 + 光反射 (对称性/直接/间接)",
        "肢体肌力: 双侧上下肢 MRC 0-5",
        "影像初步: CT/MRI urgent if GCS ≤ 13 or trauma mechanism",
    ]

    is_sah = any(t in dx for t in ["蛛网膜", "SAH", "动脉瘤", "脑出血"])
    if "颅脑损" in dx or "脑出血" in dx or is_sah:
        findings.insert(0, "⚠ 颅脑损伤/脑出血/SAH 疾病匹配 — 急诊绿色通道")

    # SAH-specific triage
    if is_sah:
        hh = _calc_hunt_hess(p)
        fg = _calc_fisher_grade(p)
        wfns = _calc_wfns(p)
        findings.append(f"Hunt-Hess: 等级 {hh['grade']} ({hh['description'][:30]}...) 手术死亡率 {hh['surgical_mortality']}")
        findings.append(f"Fisher CT: 等级 {fg['grade']} — {fg['vasospasm_risk']} 血管痉挛风险")
        findings.append(f"WFNS: 等级 {wfns['label']}")

    # Cushing's triad check
    cushing = _check_cushing_triad(vitals)
    if cushing["emergency"]:
        findings.insert(0, f"⚠️ EMERGENCY: CUSHING'S TRIAD detected — {cushing['action']}")

    # ASIA if spinal
    if any(t in dx for t in ["脊柱", "脊髓", "spine", "cord"]):
        asia = _assess_asia(p)
        findings.append(f"ASIA: {asia['grade']} — {asia['description'][:40]}...")
        if asia["neurogenic_shock_suspected"]:
            findings.append(f"⚠ Neurogenic shock suspected: {asia['neurogenic_shock_note']}")

    # Lab alerts
    coag = labs.get("pt", labs.get("PT", 13)), labs.get("aptt", labs.get("APTT", 30)), labs.get("plt", labs.get("PLT", 200))
    alerts = vitals.get("alerts", [])
    if coag[2] < 80:
        alerts.append(f"PLT {coag[2]} — 凝血异常 (出血风险)")
    if coag[0] > 15 or coag[1] > 40:
        alerts.append("PT/APTT 延长 — 凝血障碍")

    checklist = [
        f"GCS ≥ 2 下降 (current: {gcs['total']})",
        "瞳孔不等大 (uncal herniation sign)",
        "新发神经功能缺损 (lateralizing sign)",
        "颅内感染: 发热 + 颈强直 + CT 异常",
        "癫痫持续状态 > 5min or 连续发作",
    ]
    findings.append(f"高危审核清单: {len(checklist)} 项")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("神经外科")
    return _agent.clinical_result(
        patient=p,
        stage="triage",
        summary=f"神经外科 — 急诊分诊完成 (GCS={gcs['total']}, {'CUSHING ALERT' if cushing['emergency'] else 'stable'})",
        findings=findings,
        guidelines=guides,
        rules=rules,
        alerts=alerts,
        recommendations=[f"GCS={gcs['total']} — 复评间隔: {'15min' if gcs['total'] <= 8 else '30min' if gcs['total'] <= 12 else '1h'}"],
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — comprehensive scoring: GCS, Hunt-Hess, Fisher, WFNS, ASIA."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    is_sah = any(t in dx for t in ["蛛网膜", "SAH", "动脉瘤", "脑出血"])

    gcs = _calc_gcs(p)
    motor = _assess_motor_power(p)
    findings = [
        f"GCS 评分: {gcs['total']}/15 [{gcs['severity']}] — E{gcs['eye']} V{gcs['verbal']} M{gcs['motor']}",
        f"MRI/CT: 急诊影像 — {'CT + CTA ± DSA (SAH 排查动脉瘤)' if is_sah else 'CT平扫 ± 增强'}",
        "脑电图: if seizure suspected or persistent coma",
        "神经电生理: SSEP/MEP if spinal or brainstem lesion suspected",
    ]

    if is_sah:
        hh = _calc_hunt_hess(p)
        fg = _calc_fisher_grade(p)
        wfns = _calc_wfns(p)
        findings.append(f"Hunt-Hess Grade: {hh['description']} — 手术死亡率 {hh['surgical_mortality']}")
        findings.append(f"Fisher CT Grade: {fg['description']} — 血管痉挛风险 {fg['vasospasm_risk']}")
        findings.append(f"WFNS Grade: {wfns['label']}")
        if hh["high_grade"]:
            findings.append("⚠ HIGH-GRADE SAH (Hunt-Hess IV-V): 延迟手术至 grade III 以下 if possible")

    if any(t in dx for t in ["脊柱", "脊髓"]):
        asia = _assess_asia(p)
        findings.append(f"ASIA Impairment Scale: {asia['grade']} — {asia['description']}")
        if asia["is_complete"]:
            findings.append("⚠ Complete injury (ASIA A): 预后不良 (<5% recovery beyond level)")

    cushing = _check_cushing_triad(vitals)
    if cushing["emergency"]:
        findings.insert(0, f"⚠️ CUSHING'S TRIAD: HR={vitals.get('heart_rate','?')} SBP={vitals.get('sbp','?')} RR={vitals.get('respiratory_rate','?')} — IMMEDIATE INTERVENTION")

    if motor["abnormal"]:
        findings.append(f"运动功能异常: {', '.join(f'{k}: {v}/5' for k, v in motor['power'].items() if v < 5)}")

    recommendations = [_icp_management(gcs, p)]
    if gcs["total"] <= 8:
        recommendations.append("Insert EVD for ICP monitoring + CSF drainage")
        recommendations.append("Repeat CT within 24h or if GCS drops ≥ 2 points")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("神经外科")
    return _agent.clinical_result(
        patient=p,
        stage="diagnosis",
        summary=f"神经外科 — 诊断评估完成 (GCS={gcs['total']}, Hunt-Hess={_calc_hunt_hess(p)['grade'] if is_sah else 'N/A'})",
        findings=findings,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
        recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — coag status, crossmatch, ICP optimization."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", p.get("labs", {}))
    gcs = _calc_gcs(p)
    dx = p.get("diagnosis", "")
    is_sah = any(t in dx for t in ["蛛网膜", "SAH", "动脉瘤"])

    findings = [
        f"凝血功能: PT={labs.get('pt','?')}s, APTT={labs.get('aptt','?')}s, INR={labs.get('inr','?')}, PLT={labs.get('plt','?')}×10⁹/L",
        "交叉配血: ABO + Rh type + antibody screen → 2-4 units PRBC crossmatched",
        "麻醉评估: ASA-PS classification, airway assessment (Mallampati), CV risk stratification",
        "抗癫痫药物: Levetiracetam 20mg/kg loading if cortical manipulation planned (or phenytoin 15-20mg/kg)",
    ]
    if is_sah:
        findings.insert(0, "SAH 术前: nimodipine 60mg q4h (prevent vasospasm), euvolemia, SBP < 160 before aneurysm securement")

    cushing = _check_cushing_triad(vitals)
    if cushing["emergency"]:
        findings.insert(0, "⚠️ PREOP EMERGENCY: Cushing's triad active — neurosurgical decompression may need to precede full preop workup")

    # ICP optimization
    icp_rx = _icp_management(gcs, p)
    findings.append(f"ICP 管理: head elevation 30°, {'mannitol indicated' if gcs['total'] <= 12 else 'monitor only'}")

    recommendations = icp_rx["recommendations"]
    plt = labs.get("plt", 200)
    if plt < 80:
        recommendations.insert(0, f"PLT {plt} — transfuse 1 unit apheresis platelets pre-incision (target >80)")
    inr = labs.get("inr", 1.0)
    if inr > 1.5:
        recommendations.insert(0, f"INR {inr} — reverse with 4-factor PCC ± vitamin K 10mg IV")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("神经外科")
    return _agent.clinical_result(
        patient=p,
        stage="preop",
        summary=f"神经外科 — 术前准备完成 (PLT={plt}, INR={inr}, GCS={gcs['total']})",
        findings=findings,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
        recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — ICP, herniation, vasospasm, infection risk."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    gcs = _calc_gcs(p)
    dx = p.get("diagnosis", "")
    is_sah = any(t in dx for t in ["蛛网膜", "SAH", "动脉瘤"])

    cushing = _check_cushing_triad(vitals)
    findings = [
        f"颅内压评估: {'⚠ HIGH ICP suspected' if cushing['emergency'] else 'ICP within compensatory range'} ({'Cushing triad present' if cushing['emergency'] else 'no Cushing sign'})",
        f"脑疝风险: {'HIGH — GCS ≤ 8 + pupil asymmetry → uncal herniation risk' if gcs['total'] <= 8 else 'moderate — monitor q15min neuro checks'}",
        "血管损伤风险: CTA/DSA if traumatic mechanism; carotid/vertebral dissection screen",
        "感染风险: EVD/ICP monitor duration > 5 days → ventriculitis risk; antibiotic-impregnated catheter recommended",
    ]

    if is_sah:
        fg = _calc_fisher_grade(p)
        hh = _calc_hunt_hess(p)
        if fg["grade"] >= 3:
            findings.append(f"⚠ VASOSPASM HIGH RISK: Fisher grade {fg['grade']} → daily TCDs, nimodipine 60mg q4h × 21d, triple-H therapy if symptomatic")
        findings.append(f"Hunt-Hess {hh['grade']} — surgical risk adjusted: mortality {hh['surgical_mortality']}")

    if any(t in dx for t in ["脊柱", "脊髓"]):
        findings.append("脊髓损伤: 静脉血栓栓塞 (VTE) 高风险 — 机械预防 + 低分子肝素 (72h post-injury)")
        findings.append("自主神经反射异常 (T6 以上) 风险筛查")

    icp_rx = _icp_management(gcs, p)
    recommendations = icp_rx["recommendations"]
    if gcs["total"] <= 8:
        recommendations.append("Serial CT q24h or if neuro exam change")
        recommendations.append("ICP waveform analysis: P2 > P1 → decreased compliance (Lundberg A waves imminent)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("神经外科")
    return _agent.clinical_result(
        patient=p,
        stage="risk",
        summary=f"神经外科 — 手术风险评估完成 (GCS={gcs['total']}, Cushing={cushing['emergency']}, Fisher={_calc_fisher_grade(p)['grade'] if is_sah else 'N/A'})",
        findings=findings,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
        recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — surgical approach selection based on scoring."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    gcs = _calc_gcs(p)
    dx = p.get("diagnosis", "")
    is_sah = any(t in dx for t in ["蛛网膜", "SAH", "动脉瘤"])

    findings = [
        "术式选择: 微创 (内镜/锁孔) vs 开颅 — 根据病变位置、GCS、Fisher 综合评估",
        f"手术入路: {'pterional (翼点) — aneurysm clipping / suprasellar' if is_sah else 'lesion-dependent (frontal/temporal/suboccipital)'}",
        "术中监测: SSEP + MEP + BAEP (brainstem cases) + EMG (CN monitoring)",
        "备选方案: 血管内介入 (coiling) vs 开颅夹闭 vs 保守治疗 (WFNS V / poor grade)",
    ]
    if is_sah:
        hh = _calc_hunt_hess(p)
        fg = _calc_fisher_grade(p)
        findings.insert(0, f"Hunt-Hess {hh['grade']} + Fisher {fg['grade']}: "
                            f"{'early surgery (<72h) if HH I-III' if hh['grade'] <= 3 else 'delayed surgery — neurocritical care optimization first'}")
    findings.append(f"GCS {gcs['total']}: {'clearance for surgery' if gcs['total'] >= 9 else 'MDT: risk/benefit of emergency decompression vs medical optimization'}")

    recommendations = []
    if is_sah:
        recommendations.append("Aneurysm: coiling preferred over clipping if age > 70 / posterior circulation / poor WFNS grade (ISAT trial data)")
        recommendations.append("Nimodipine 60mg PO/NG q4h × 21 days (Class I, Level A)")
    recommendations.append("Preoperative embolization if vascular tumor (meningioma / hemangioblastoma)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("神经外科")
    return _agent.clinical_result(
        patient=p,
        stage="mdt",
        summary=f"神经外科 — MDT 决策完成 (approach determined, {'SAH protocol' if is_sah else 'general neurosurgery'})",
        findings=findings,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
        recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — intraoperative ICP and monitoring."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    gcs = _calc_gcs(p)
    dx = p.get("diagnosis", "")

    findings = [
        f"手术方式: {'开颅血肿清除/动脉瘤夹闭' if any(t in dx for t in ['颅脑','脑出血','动脉瘤','SAH']) else '开颅/微创肿瘤切除'}",
        f"术中 GCS 起点: {gcs['total']}/15", "术中神经监测: SSEP/MEP 基线确认",
        "止血: bipolar coagulation + hemostatic matrix (Surgicel/Floseal)",
        "关颅: watertight dural closure ± dural graft",
    ]

    cushing = _check_cushing_triad(vitals)
    if cushing["emergency"]:
        findings.insert(0, "⚠ INTRAOP: Cushing's triad persists — rapid decompression required")

    recommendations = [
        "术中 ABG q1h: PaCO₂ 30-35 mmHg (mild hyperventilation), PaO₂ > 100 mmHg",
        "Mannitol 0.5-1g/kg at bone flap removal if brain tight",
        "Intraoperative CT/angiography if residual lesion suspected",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("神经外科")
    return _agent.clinical_result(
        patient=p,
        stage="surgery",
        summary=f"神经外科 — 手术执行完成 (GCS preop={gcs['total']})",
        findings=findings,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
        recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — ICP management, DVT prophylaxis, neuro checks."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    gcs = _calc_gcs(p)
    dx = p.get("diagnosis", "")

    icp_rx = _icp_management(gcs, p)
    findings = [
        f"神经功能监测: GCS q{'15min' if gcs['total'] <= 8 else '30min' if gcs['total'] <= 12 else '1h'} + pupil check + motor power",
        f"颅内压管理: {icp_rx['recommendations'][0]}",
        "感染预防: 围术期抗生素 (cefazolin 2g or vancomycin if MRSA risk) within 60min of incision, discontinue < 24h",
        "DVT 预防: SCDs bilateral + enoxaparin 40mg SC daily (hold 12h pre/post spinal procedures)",
    ]

    if gcs["total"] <= 8:
        findings.append("⚠ NEURO ICU: 1:1 nursing, ICP waveform trending, serial neuro checks q15min")
    if any(t in dx for t in ["脊柱", "脊髓"]):
        findings.append("脊柱护理: log-roll technique, pressure ulcer prevention q2h turning, brace/orthosis compliance")

    recommendations = list(icp_rx["recommendations"])
    recommendations.extend([
        "Blood glucose 110-180 mg/dL (avoid hypo/hyperglycemia — secondary brain injury)",
        "Na⁺ 140-145 mEq/L target (avoid hyponatremia — cerebral edema risk)",
        "Temperature < 37.5°C (fever = increased ICP + metabolic demand)",
    ])

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("神经外科")
    return _agent.clinical_result(
        patient=p,
        stage="nursing",
        summary=f"神经外科 — 围术期护理完成 (GCS={gcs['total']}, neuro checks q{'15min' if gcs['total'] <= 8 else '1h'})",
        findings=findings,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
        recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """术后随访 — neuro recovery, vasospasm surveillance, rehab referral."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    gcs = _calc_gcs(p)
    dx = p.get("diagnosis", "")
    is_sah = any(t in dx for t in ["蛛网膜", "SAH", "动脉瘤"])

    findings = [
        f"神经功能恢复: GCS {gcs['total']}/15, 定向力/语言/运动功能评估",
        "影像复查: CT/MRI at 24h/72h/3mo postop; CTA/MRA at 6-12mo for aneurysm remnant",
        "癫痫控制: EEG if clinical seizure; levetiracetam taper at 7d postop if no seizure",
        "康复转介: PT/OT/SLP evaluation; TBI rehabilitation pathway if GCS ≤ 12 at discharge",
    ]
    if is_sah:
        fg = _calc_fisher_grade(p)
        findings.append(f"血管痉挛监测: TCD daily × 14d (Fisher {fg['grade']} — {fg['vasospasm_risk']} risk); nimodipine continued × 21d")

    motor = _assess_motor_power(p)
    if motor["abnormal"]:
        findings.append(f"运动功能异常: {', '.join(f'{k}: {v}/5' for k, v in motor['power'].items() if v < 5)} — targeted PT referral")

    recommendations = [
        "Follow-up CT/MRI: 3mo, 6mo, 12mo, then annual",
        "DVT prophylaxis: continue LMWH × 14d postop (extend to 28d if SAH/immobile)",
        "Depression screening: PHQ-9 at 1mo, 3mo, 6mo (high prevalence post-TBI/SAH)",
        "Driving clearance: neuropsychological assessment + seizure-free ≥ 6mo",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("神经外科")
    return _agent.clinical_result(
        patient=p,
        stage="followup",
        summary=f"神经外科 — 术后随访完成 (GCS={gcs['total']}, rehab plan established)",
        findings=findings,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
        recommendations=recommendations,
        guideline_refs=_GUIDELINES,
    )
