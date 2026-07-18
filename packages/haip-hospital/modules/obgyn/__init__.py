"""妇产科 — KnowledgeAgent-powered clinical reasoning (Deep-Optimized).

Focus: 孕产期管理及妇科疾病诊疗
GUIDELINES: 中国妇产科学临床指南（2022）, ACOG Practice Bulletins
Conditions: 妊娠期高血压, 妊娠期糖尿病, 产程异常, 妇科肿瘤, 异常子宫出血

Injected clinical systems: Gestational age calculator, Preeclampsia criteria (ACOG),
GDM OGTT screening (IADPSG), Labor stages + partogram, PPH 4T's, Bishop score,
Cervical cancer screening (ASCCP).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="obgyn", department="妇产科")
_GUIDELINES = [
    "中国妇产科学临床指南（2022）",
    "ACOG Practice Bulletin No. 222 — Gestational Hypertension and Preeclampsia (2020)",
    "IADPSG Criteria for GDM (2010)",
    "ACOG Practice Bulletin No. 202 — PPH",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


# ── Clinical Scoring Systems ─────────────────────────────────────────

def _gestational_age_calculator(lmp_date: str) -> dict:
    """Calculate gestational age from LMP using Naegele's rule."""
    try:
        lmp = datetime.strptime(lmp_date, "%Y-%m-%d")
        today = datetime.now()
        ga_days = (today - lmp).days
        if ga_days < 0:
            return {"ga_weeks": 0, "ga_days": 0, "edd": "Invalid LMP", "trimester": "Unknown",
                    "error": "LMP is in the future"}
        ga_weeks = ga_days // 7
        ga_rem_days = ga_days % 7
        edd = lmp + timedelta(days=280)
        trimester = "1st" if ga_weeks < 14 else ("2nd" if ga_weeks < 28 else "3rd")
        return {
            "lmp": lmp_date, "ga_weeks": ga_weeks, "ga_days": ga_rem_days,
            "edd": edd.strftime("%Y-%m-%d"), "trimester": trimester,
            "estimated_weight": f"{_estimate_fetal_weight(ga_weeks)}g" if ga_weeks >= 20 else "N/A (<20w)",
        }
    except (ValueError, TypeError):
        return {"ga_weeks": 0, "ga_days": 0, "edd": "Unknown", "trimester": "Unknown",
                "error": "Invalid LMP format; use YYYY-MM-DD"}


def _estimate_fetal_weight(weeks: int) -> int:
    """Hadlock formula estimated fetal weight (crude)."""
    if weeks < 20:
        return 0
    return int(1000 * (2.5 ** ((weeks - 20) / 10.0)))


def _preeclampsia_criteria(sbp: int, dbp: int, proteinuria_mg24h: float = 0,
                           upc_ratio: float = 0, weeks: int = 28, plt: float = 150,
                           ast: float = 30, creatinine: float = 0.8) -> dict:
    """ACOG criteria for preeclampsia and severity classification."""
    hypertensive = sbp >= 140 or dbp >= 90
    severe_bp = sbp >= 160 or dbp >= 110

    if not hypertensive or weeks < 20:
        return {
            "diagnosis": "Gestational hypertension" if hypertensive and weeks < 20 else "Normal",
            "preeclampsia": False, "severe": False, "hellp": False,
            "bp": f"{sbp}/{dbp}", "proteinuria": f"{proteinuria_mg24h}mg/24h",
            "management": "Routine antenatal care"
        }

    severe_features = []
    if severe_bp:
        severe_features.append(f"SBP≥160 or DBP≥110 ({sbp}/{dbp})")
    if plt < 100:
        severe_features.append(f"PLT<100K ({plt}K) → HELLP risk")
    if ast > 70:
        severe_features.append(f"AST>70 ({ast}) → HELLP risk")
    if creatinine > 1.1:
        severe_features.append(f"Cr>{1.1} ({creatinine}) → renal impairment")
    if proteinuria_mg24h >= 5000:
        severe_features.append("Proteinuria≥5g/24h")

    is_hellp = plt < 100 and ast > 70
    is_severe = bool(severe_features)

    management = (
        "EMERGENCY: Deliver within 24-48h; IV magnesium sulfate; IV labetalol/hydralazine for severe HTN"
        if is_severe else
        "Expectant management <37w; weekly labs; oral labetalol/nifedipine if BP≥150/100; deliver at 37w"
    )

    return {
        "diagnosis": ("HELLP Syndrome" if is_hellp else
                      "Preeclampsia with severe features" if is_severe else "Preeclampsia"),
        "preeclampsia": True, "severe": is_severe, "hellp": is_hellp,
        "bp": f"{sbp}/{dbp}", "proteinuria": f"{proteinuria_mg24h}mg/24h",
        "severe_features": severe_features,
        "management": management,
        "magnesium_sulfate": is_severe,
    }


def _gdm_screening(fasting: float, h1: float, h2: float) -> dict:
    """IADPSG criteria for GDM diagnosis (75g OGTT at 24-28 weeks)."""
    results = [
        ("fasting", fasting, 5.1, fasting >= 5.1),
        ("1h", h1, 10.0, h1 >= 10.0),
        ("2h", h2, 8.5, h2 >= 8.5),
    ]
    abnormal_count = sum(1 for _, _, _, abnormal in results if abnormal)
    gdm = abnormal_count >= 1
    return {
        "gdm": gdm, "abnormal_count": abnormal_count,
        "results": {name: f"{val} mmol/L (cutoff {cutoff})" for name, val, cutoff, _ in results},
        "management": (
            "Dietary counseling + glucose monitoring 4× daily; if fasting≥5.3 or 2hPP≥6.7 → insulin/metformin"
            if gdm else "Routine antenatal care; repeat OGTT if risk factors"
        ),
        "delivery_timing": "38-39w if well-controlled; 37-38w if requiring medication" if gdm else "Routine",
    }


def _labor_stage_assessment(cervical_dilation: float, effacement_pct: int = 0,
                            contraction_freq_min: int = 10, station: int = -3) -> dict:
    """Assess labor stage based on cervical exam and contraction pattern."""
    if cervical_dilation >= 10:
        stage = "Stage 2 (Pushing)"
        action = "Active pushing; monitor FHR q5-15min; prepare for delivery"
    elif cervical_dilation >= 6:
        stage = "Stage 1 — Active Phase"
        action = "Monitor progress; amniotomy/oxytocin if arrest; pain management"
    elif cervical_dilation >= 0:
        stage = "Stage 1 — Latent Phase"
        action = "Expectant management; may be prolonged (≤20h nullip, ≤14h multip)"
    else:
        stage = "Not in labor"
        action = "Outpatient management"
    return {
        "stage": stage, "cervical_dilation": cervical_dilation,
        "effacement_pct": effacement_pct, "contraction_freq": f"q{contraction_freq_min}min",
        "station": station, "action": action,
        "partogram_alert": cervical_dilation < 4 and contraction_freq_min > 3,
    }


def _pph_assessment(blood_loss_ml: int, delivery_type: str = "vaginal") -> dict:
    """Postpartum hemorrhage assessment — 4T's framework."""
    pph = (delivery_type == "vaginal" and blood_loss_ml > 500) or (delivery_type == "cs" and blood_loss_ml > 1000)
    severity = "Massive" if blood_loss_ml > 2000 else ("Major" if blood_loss_ml > 1000 else
                ("Moderate" if blood_loss_ml > 500 else "Normal"))
    four_ts = {
        "Tone": "Uterine atony (70%) — fundal massage + oxytocin 10 IU IM + misoprostol 800mcg PR + tranexamic acid 1g IV",
        "Trauma": "Cervical/vaginal/uterine laceration — examine + repair; uterine inversion — manual replacement",
        "Tissue": "Retained placenta/membranes — manual removal / curettage",
        "Thrombin": "Coagulopathy (DIC) — check PT/PTT/fibrinogen/PLT; transfuse FFP+cryo+PLT",
    }
    return {
        "pph": pph, "blood_loss_ml": blood_loss_ml, "severity": severity,
        "four_ts_checklist": four_ts,
        "management": "EMERGENCY: Massive transfusion protocol; call OR team; Bakri balloon / B-Lynch suture / hysterectomy"
        if blood_loss_ml > 2000 else
        "Uterotonic agents + uterine massage + IV fluids + monitor vitals q15min" if pph else
        "Routine postpartum monitoring",
    }


def _bishop_score(dilation: float, effacement_pct: int, station: int,
                  consistency: str = "medium", position: str = "mid") -> dict:
    """Bishop score for cervical favorability — induction readiness."""
    def _score_dilation(d): return 0 if d == 0 else (1 if 1 <= d <= 2 else (2 if 3 <= d <= 4 else 3))
    def _score_effacement(e): return 0 if e <= 30 else (1 if 31 <= e <= 50 else (2 if 51 <= e <= 80 else 3))
    def _score_station(s): return 0 if s == -3 else (1 if s == -2 else (2 if -1 <= s <= 0 else 3))
    def _score_consistency(c): return 0 if c == "firm" else (1 if c == "medium" else 2)
    def _score_position(p): return 0 if p == "posterior" else (1 if p == "mid" else 2)

    scores = {
        "dilation": (_score_dilation(dilation), f"{dilation}cm"),
        "effacement": (_score_effacement(effacement_pct), f"{effacement_pct}%"),
        "station": (_score_station(station), f"{station}"),
        "consistency": (_score_consistency(consistency), consistency),
        "position": (_score_position(position), position),
    }
    total = sum(v[0] for v in scores.values())
    return {
        "bishop_score": total,
        "components": {k: f"{v[1]} ({v[0]}pts)" for k, v in scores.items()},
        "favorable": total >= 8,
        "recommendation": "Favorable for induction" if total >= 8 else
        "Unfavorable — consider cervical ripening (PGE2/balloon catheter)" if total <= 6 else
        "Moderately favorable — may attempt induction",
    }


def _cervical_cancer_screening(age: int, hpv: str = "unknown", pap: str = "unknown",
                               last_hpv: str = None, last_pap: str = None) -> dict:
    """ASCCP cervical cancer screening guidelines."""
    if age < 21:
        rec = "No screening"
        interval = "N/A"
    elif 21 <= age <= 29:
        rec = "Cervical cytology (Pap) alone"
        interval = "Every 3 years"
    elif 30 <= age <= 65:
        if hpv == "positive" and pap != "NILM":
            rec = "Immediate colposcopy"
            interval = "Now"
        elif hpv == "positive" and pap == "NILM":
            rec = "Repeat HPV+Pap co-test"
            interval = "In 1 year"
        else:
            rec = "HPV + Pap co-test (preferred) or Pap alone"
            interval = "Every 5 years (co-test) or 3 years (Pap alone)"
    else:
        rec = "Discontinue if adequate prior screening and no CIN2+ in last 10 years"
        interval = "Individualized"
    return {
        "age": age, "recommendation": rec, "interval": interval,
        "hpv_status": hpv, "pap_status": pap,
        "colposcopy_indicated": hpv == "positive" and pap != "NILM",
    }


# ── Business Process Functions ───────────────────────────────────────

def bp_reception(**kwargs) -> dict:
    """接诊评估 — Gestational age + preeclampsia screening + GDM screening."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    # ── Injected clinical scoring ──
    lmp = p.get("lmp", labs.get("lmp", ""))
    ga = _gestational_age_calculator(lmp) if lmp else {"ga_weeks": 0, "ga_days": 0, "edd": "Unknown", "trimester": "Unknown"}
    bp_sys = int(vitals.get("sbp", p.get("sbp", 120)))
    bp_dia = int(vitals.get("dbp", p.get("dbp", 80)))
    preeclampsia = _preeclampsia_criteria(bp_sys, bp_dia, float(labs.get("proteinuria_24h", 0)),
                                          float(labs.get("upc_ratio", 0)), ga.get("ga_weeks", 28))
    ogtt = _gdm_screening(float(labs.get("ogtt_fasting", 4.5)), float(labs.get("ogtt_1h", 8.0)),
                          float(labs.get("ogtt_2h", 7.0)))

    findings = [
        f"Gestational Age: {ga['ga_weeks']}w{ga['ga_days']}d — EDD: {ga['edd']} — {ga['trimester']} trimester",
        f"BP: {bp_sys}/{bp_dia} → {preeclampsia['diagnosis']}",
        f"OGTT: FPG {labs.get('ogtt_fasting',4.5)} / 1h {labs.get('ogtt_1h',8.0)} / 2h {labs.get('ogtt_2h',7.0)} → {'GDM' if ogtt['gdm'] else 'Normal'}",
        "孕产次: " + str(p.get('gravida', '?')) + "/" + str(p.get('para', '?')),
        "高危因素: " + (", ".join(preeclampsia["severe_features"]) if preeclampsia["severe_features"] else "无"),
    ]
    recommendations = [preeclampsia["management"]]
    if ogtt["gdm"]:
        recommendations.append(ogtt["management"])
    if preeclampsia["magnesium_sulfate"]:
        recommendations.append("MgSO4 4g IV load → 1-2g/h maintenance; monitor reflexes/respiratory rate/urine output")
    if "妊娠期" in dx:
        findings.insert(0, f"妊娠期疾病 {dx} 匹配")
    checklist = ["子痫发作", "胎盘早剥", "产后出血>500mL", "胎儿窘迫", "子宫破裂"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注: Hb/PLT/尿蛋白/OGTT")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("妇产科")
    return _agent.clinical_result(
        summary=f"妇产科—初诊 GA{ga['ga_weeks']}w (stage S1)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_exam(**kwargs) -> dict:
    """专项检查 — Bishop score + GDM + GBS + cervical screening."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    # ── Injected clinical scoring ──
    bishop = _bishop_score(float(labs.get("dilation", 1)), int(labs.get("effacement", 30)),
                           int(labs.get("station", -3)), labs.get("consistency", "medium"),
                           labs.get("position", "mid"))
    screen = _cervical_cancer_screening(int(p.get("age", 30)), labs.get("hpv", "unknown"),
                                        labs.get("pap", "unknown"))

    findings = [
        f"Bishop Score: {bishop['bishop_score']} → {'Favorable' if bishop['favorable'] else 'Unfavorable'} for induction",
        f"Cervical Cancer Screening: {screen['recommendation']} (age {screen['age']})",
        "胎心监护: NST (reactive/non-reactive) + 生物物理评分 BPP",
        "B超: BPD/HC/AC/FL → EFW; 胎盘位置+分级; 羊水指数 AFI",
        "OGTT 75g (24-28w): FPG ≥5.1 / 1h ≥10.0 / 2h ≥8.5",
        "GBS筛查 (35-37w): 阴道+直肠拭子培养",
    ]
    if "妊娠期" in dx:
        findings.insert(0, "妊娠期疾病专项检查方案")
    recommendations = [
        bishop["recommendation"],
        f"Cervical screening: {screen['recommendation']} — {screen['interval']}",
    ]
    if screen["colposcopy_indicated"]:
        recommendations.append("HPV+/abnormal Pap → 阴道镜检查 + 必要时宫颈活检")
    checklist = ["子痫发作", "胎盘早剥", "产后出血>500mL", "胎儿窘迫", "子宫破裂"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("妇产科")
    return _agent.clinical_result(
        summary=f"妇产科—检查 Bishop{bishop['bishop_score']} (stage S2)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断分级 — Preeclampsia severity + labor stage + GDM classification."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    # ── Injected clinical scoring ──
    bp_sys = int(vitals.get("sbp", p.get("sbp", 120)))
    bp_dia = int(vitals.get("dbp", p.get("dbp", 80)))
    preeclampsia = _preeclampsia_criteria(bp_sys, bp_dia, float(labs.get("proteinuria_24h", 0)),
                                          float(labs.get("upc_ratio", 0)),
                                          int(labs.get("ga_weeks", 28)),
                                          float(labs.get("platelets", 150)),
                                          float(labs.get("ast", 30)),
                                          float(labs.get("creatinine", 0.8)))
    labor = _labor_stage_assessment(float(labs.get("cervical_dilation", 2)),
                                    int(labs.get("effacement", 30)),
                                    int(labs.get("contraction_freq", 10)),
                                    int(labs.get("station", -3)))

    findings = [
        f"Preeclampsia: {preeclampsia['diagnosis']} — {'Severe' if preeclampsia['severe'] else 'Mild'} — MgSO4={'YES' if preeclampsia['magnesium_sulfate'] else 'No'}",
        f"Labor Stage: {labor['stage']} — Dilation {labor['cervical_dilation']}cm",
        f"HELLP: {'YES — EMERGENCY' if preeclampsia['hellp'] else 'No'}",
        "FGR评估: EFW<10th percentile; UA Doppler (absent/reversed EDF)",
        "胎位判定: 头位/臀位/横位 × 衔接情况",
        "妇科肿瘤分期: FIGO staging (宫颈癌/内膜癌/卵巢癌)",
    ]
    if preeclampsia["severe_features"]:
        findings.append(f"严重特征: {'; '.join(preeclampsia['severe_features'])}")
    recommendations = [
        preeclampsia["management"],
        labor["action"],
    ]
    if preeclampsia["hellp"]:
        recommendations.append("HELLP → 立即分娩(无论孕周) + 地塞米松促肺成熟 + 输注血小板(PLT<20K)")
    if "妊娠期" in dx:
        findings.insert(0, f"妊娠期疾病 诊断确认: {dx}")
    checklist = ["子痫发作", "胎盘早剥", "产后出血>500mL", "胎儿窘迫", "子宫破裂"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("妇产科")
    return _agent.clinical_result(
        summary=f"妇产科—诊断 {preeclampsia['diagnosis']} (stage S3)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_treatment(**kwargs) -> dict:
    """分娩/治疗执行 — Labor management + PPH prevention + MgSO4 protocol."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    # ── Injected clinical scoring ──
    labor = _labor_stage_assessment(float(labs.get("cervical_dilation", 6)),
                                    int(labs.get("effacement", 80)),
                                    int(labs.get("contraction_freq", 3)),
                                    int(labs.get("station", -1)))
    pph = _pph_assessment(int(labs.get("blood_loss_ml", 300)), labs.get("delivery_type", "vaginal"))

    findings = [
        f"产程管理: {labor['stage']} — Dilation {labor['cervical_dilation']}cm — q{labs.get('contraction_freq',3)}min",
        f"PPH Risk: Blood loss {pph['blood_loss_ml']}mL → {pph['severity']} — {'PPH!' if pph['pph'] else 'Normal'}",
        "硫酸镁方案: " + ("4g IV/15-20min → 1-2g/h; 监测膝反射/呼吸≥12/min/尿量≥25mL/h" if dx and "妊娠期高血压" in dx else "N/A"),
        "终止妊娠时机: " +
        ("37w (无严重特征); 34w (严重特征稳定后)" if dx and "妊娠期高血压" in dx else
         "40w+0 (常规); 41w+0 (建议引产)"),
        "分娩方式: 阴道分娩(首选) vs 剖宫产(产科指征)",
    ]
    recommendations = [labor["action"], pph["management"]]
    if pph["pph"]:
        for k, v in pph["four_ts_checklist"].items():
            recommendations.append(f"4T-{k}: {v}")
    if labor["partogram_alert"]:
        recommendations.append("⚠ Partogram alert: labor arrest suspected → oxytocin augmentation or C/S")
    if "妊娠期" in dx:
        findings.insert(0, f"妊娠期疾病 治疗执行: {dx}")
    checklist = ["子痫发作", "胎盘早剥", "产后出血>500mL", "胎儿窘迫", "子宫破裂"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("妇产科")
    return _agent.clinical_result(
        summary=f"妇产科—{labor['stage']} (stage S4)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_nursing(**kwargs) -> dict:
    """产后/儿科护理 — PPH monitoring + newborn care + breastfeeding."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")
    pph = _pph_assessment(int(labs.get("blood_loss_ml", 300)), labs.get("delivery_type", "vaginal"))

    findings = [
        f"产后出血监测: {pph['blood_loss_ml']}mL → {pph['severity']}",
        "子宫复旧: 宫底高度每日下降1cm; 产后10天入盆",
        "恶露观察: 红色(3-4d) → 浆液性(10d) → 白色(3-4w)",
        "母乳喂养: 早接触+早吸吮(产后30min); 按需喂养 q2-3h",
        "新生儿护理: Apgar 1min/5min; 维生素K 1mg IM; 眼炎预防(红霉素)",
    ]
    recommendations = [
        "产后2h Q15min监测生命体征+宫缩+出血",
        "产后24h鼓励下床活动 → VTE预防",
        "产后42天门诊复查: 盆底评估 + 伤口愈合 + 避孕咨询",
    ]
    if pph["pph"]:
        recommendations.insert(0, pph["management"])
    if "妊娠期" in dx:
        findings.insert(0, f"产后管理: {dx}")
    checklist = ["子痫发作", "胎盘早剥", "产后出血>500mL", "胎儿窘迫", "子宫破裂"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("妇产科")
    return _agent.clinical_result(
        summary="妇产科—产后护理 (stage S4b)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )


def bp_followup(**kwargs) -> dict:
    """随访与保健 — Postpartum visit + contraception + chronic disease."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")
    screen = _cervical_cancer_screening(int(p.get("age", 30)), labs.get("hpv", "unknown"),
                                        labs.get("pap", "unknown"))

    findings = [
        "42天复查: 子宫复旧/伤口愈合/盆地功能评估",
        f"Cervical screening: {screen['recommendation']} ({screen['interval']})",
        "盆底康复: Kegel训练 + 电刺激/生物反馈 (POP-Q评估)",
        "避孕指导: LARC(IUD/Implant)优先; 哺乳期可用单纯孕激素",
        "慢病管理: " +
        ("GDM → 产后6-12w OGTT; 每年DM筛查" if dx and "糖尿病" in dx else
         "妊娠期高血压 → 产后BP监测; 心血管风险评估" if dx and "高血压" in dx else
         "无特殊"),
    ]
    recommendations = [
        f"{screen['recommendation']} — {screen['interval']}",
        "避孕: 产后3w可用单纯孕激素; 产后6w可用IUD(排除感染)",
        "下次妊娠: 间隔≥18月; 补充叶酸0.4mg/d",
    ]
    if screen["colposcopy_indicated"]:
        recommendations.append("HPV+/abnormal Pap → 阴道镜检查")
    if "妊娠期" in dx:
        findings.insert(0, f"妊娠期疾病 长期随访: {dx}")
    checklist = ["子痫发作", "胎盘早剥", "产后出血>500mL", "胎儿窘迫", "子宫破裂"]
    findings.append(f"高危审核: {len(checklist)} 项")
    if vitals.get("alerts"):
        recommendations.append("检验异常需关注")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("妇产科")
    return _agent.clinical_result(
        summary="妇产科—产后随访 (stage S5)",
        patient=p, guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        findings=findings, recommendations=recommendations,
    )
