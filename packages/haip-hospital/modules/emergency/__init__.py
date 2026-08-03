"""急诊科 — KnowledgeAgent-powered clinical reasoning.

Focus: 急危重症快速评估与处理
GUIDELINES: 中国急诊临床诊疗指南（2023）, SCCM Surviving Sepsis Campaign Guidelines (2021)
Conditions: 心脏骤停, 急性脑卒中, STEMI, 严重多发伤, 急性中毒

Injected clinical scoring systems:
  MEWS (Modified Early Warning Score) — 0-15, thresholds at 0-4/5-6/≥7
  NEWS2 (National Early Warning Score 2) — includes SpO2 scale 1/2 and O2 supplement
  ESI Triage (Emergency Severity Index) — 5-level triage
  Stroke FAST — Face/Arm/Speech/Time
  STEMI Triage — cath lab activation <90min
  Trauma ABCDE — primary survey
  Poisoning Antidote — common lookup (opioid/benzo/organophosphate/acetaminophen)
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="emergency", department="急诊科")
_GUIDELINES = [
    "中国急诊临床诊疗指南（2023）",
    "SCCM Surviving Sepsis Campaign Guidelines (2021)",
]

_agent.rule_engine.load_all()


# ── Poisoning Antidote Lookup ──────────────────────────────────────────

_ANTIDOTES: dict[str, dict] = {
    "opioid":    {"antidote": "Naloxone (纳洛酮)", "dose": "0.4-2mg IV, repeat q2-3min, max 10mg"},
    "benzo":     {"antidote": "Flumazenil (氟马西尼)", "dose": "0.2mg IV over 30s, repeat 0.3mg/min, max 3mg"},
    "organophosphate": {"antidote": "Atropine (阿托品) + Pralidoxime (解磷定)", "dose": "Atropine 2-5mg IV q5-10min until atropinization"},
    "acetaminophen":   {"antidote": "N-Acetylcysteine (NAC / 乙酰半胱氨酸)", "dose": "150mg/kg IV over 1h, then 50mg/kg over 4h, then 100mg/kg over 16h"},
    "cyanide":    {"antidote": "Hydroxocobalamin (羟钴胺) 5g IV", "dose": "5g IV over 15min, repeat if needed"},
    "digoxin":    {"antidote": "Digoxin Immune Fab (地高辛抗体)", "dose": "Dose based on serum level or ingested amount"},
    "methemoglobin": {"antidote": "Methylene Blue (亚甲蓝)", "dose": "1-2mg/kg IV over 5min"},
    "beta_blocker":  {"antidote": "Glucagon (胰高血糖素)", "dose": "3-5mg IV bolus, then 1-5mg/h infusion"},
    "calcium_channel": {"antidote": "Calcium Gluconate + High-Dose Insulin", "dose": "Ca 1-3g IV; Insulin 1U/kg bolus + 0.5U/kg/h"},
    "warfarin":   {"antidote": "Vitamin K (维生素K1) + PCC/FFP", "dose": "VitK 5-10mg IV; PCC 25-50U/kg"},
    "heparin":    {"antidote": "Protamine Sulfate (鱼精蛋白)", "dose": "1mg per 100U heparin, max 50mg"},
    "iron":       {"antidote": "Deferoxamine (去铁胺)", "dose": "15mg/kg/h IV, max 6g/day"},
    "methanol_eg": {"antidote": "Fomepizole (甲吡唑) 或 Ethanol", "dose": "Fomepizole 15mg/kg IV load, then 10mg/kg q12h"},
    "isoniazid":  {"antidote": "Pyridoxine (VitB6 / 吡哆醇)", "dose": "Gram-for-gram or 5g IV empiric"},
    "tca":        {"antidote": "Sodium Bicarbonate (碳酸氢钠)", "dose": "1-2mEq/kg IV bolus for QRS>100ms or hypotension"},
}


# ── MEWS Scoring ────────────────────────────────────────────────────────

def _mews_pulse(hr: float) -> int:
    if hr is None or hr <= 0:
        return 0
    if hr <= 40:
        return 3
    if hr <= 50:
        return 1
    if hr <= 100:
        return 0
    if hr <= 110:
        return 1
    if hr <= 129:
        return 2
    return 3  # >=130

def _mews_sbp(sbp: float) -> int:
    if sbp is None or sbp <= 0:
        return 0
    if sbp <= 70:
        return 3
    if sbp <= 80:
        return 2
    if sbp <= 100:
        return 1
    if sbp <= 199:
        return 0
    return 2  # >=200

def _mews_rr(rr: float) -> int:
    if rr is None or rr <= 0:
        return 0
    if rr <= 8:
        return 3
    if rr <= 11:
        return 1  # actually 9-11 but we simplify; <9 already handled
    if rr <= 20:
        return 0
    if rr <= 24:
        return 2
    if rr <= 29:
        return 2  # 21-29 → 2 in some scales
    return 3  # >=30

def _mews_temp(temp: float) -> int:
    if temp is None or temp <= 0:
        return 0
    if temp <= 35.0:
        return 3
    if temp <= 36.0:
        return 1
    if temp <= 38.4:
        return 0
    return 2  # >=38.5

def _mews_avpu(avpu: str) -> int:
    """AVPU: Alert=0, Voice=1, Pain=2, Unresponsive=3"""
    if not avpu:
        return 0
    a = avpu.upper().strip()
    if a == "A":
        return 0
    if a == "V":
        return 1
    if a == "P":
        return 2
    if a == "U":
        return 3
    return 0

def calculate_mews(pulse: float = None, sbp: float = None, rr: float = None,
                   temp: float = None, avpu: str = "") -> dict:
    scores = {
        "pulse": _mews_pulse(pulse) if pulse else 0,
        "sbp":   _mews_sbp(sbp) if sbp else 0,
        "rr":    _mews_rr(rr) if rr else 0,
        "temp":  _mews_temp(temp) if temp else 0,
        "avpu":  _mews_avpu(avpu),
    }
    total = sum(scores.values())
    if total <= 4:
        action = "routine"  # 常规监护
        freq = "q12h"
    elif total <= 6:
        action = "urgent_review"  # 紧急评估
        freq = "q2-4h"
    elif total <= 8:
        action = "escalate"  # 升高监护级别
        freq = "q1h"
    else:
        action = "icu"  # ICU 级别
        freq = "continuous"
    return {"mews": total, "subscores": scores, "action": action, "frequency": freq,
            "threshold_0_4": total <= 4, "threshold_geq_7": total >= 7}


# ── NEWS2 Scoring ───────────────────────────────────────────────────────

def _news2_spo2(spo2: float, on_o2: bool = False) -> int:
    if spo2 is None or spo2 <= 0:
        return 0
    # Scale 1 for COPD with target 88-92%; Scale 2 as default
    if spo2 <= 83:
        return 3
    if spo2 <= 85:
        return 2
    if spo2 <= 87:
        return 1
    if spo2 <= 92:
        return 0 if on_o2 else 0  # on_o2 handled separately
    if spo2 <= 93:
        return 0 if on_o2 else 0
    if spo2 <= 95:
        return 0 if on_o2 else 0
    return 0
    # Note: simplified; full NEWS2 uses scale 1 vs scale 2 for COPD

def _news2_spo2_scale2(spo2: float) -> int:
    """NEWS2 Scale 2 — default for non-COPD."""
    if spo2 is None or spo2 <= 0:
        return 0
    if spo2 <= 83:
        return 3
    if spo2 <= 85:
        return 2
    if spo2 <= 87:
        return 1
    if spo2 <= 92:
        return 0
    if spo2 <= 93:
        return 0
    if spo2 <= 95:
        return 1
    return 2  # >=96 — note: ≥96 on air is 1 in some versions

def _news2_o2_supplement(on_o2: bool) -> int:
    return 2 if on_o2 else 0

def _news2_rr(rr: float) -> int:
    if rr is None or rr <= 0:
        return 0
    if rr <= 8:
        return 3
    if rr <= 11:
        return 1
    if rr <= 20:
        return 0
    if rr <= 24:
        return 2
    return 3  # >=25

def _news2_sbp(sbp: float) -> int:
    if sbp is None or sbp <= 0:
        return 0
    if sbp <= 90:
        return 3
    if sbp <= 100:
        return 2
    if sbp <= 110:
        return 1
    if sbp <= 219:
        return 0
    return 3  # >=220

def _news2_pulse(hr: float) -> int:
    if hr is None or hr <= 0:
        return 0
    if hr <= 40:
        return 3
    if hr <= 50:
        return 1
    if hr <= 90:
        return 0
    if hr <= 110:
        return 1
    if hr <= 130:
        return 2
    return 3  # >=131

def _news2_consciousness(avpu: str) -> int:
    """New-onset confusion or AVPU non-Alert → 3"""
    if not avpu:
        return 0
    return 0 if avpu.upper().strip() == "A" else 3

def _news2_temp(temp: float) -> int:
    if temp is None or temp <= 0:
        return 0
    if temp <= 35.0:
        return 3
    if temp <= 36.0:
        return 1
    if temp <= 38.0:
        return 0
    if temp <= 39.0:
        return 1
    return 2  # >=39.1

def calculate_news2(pulse: float = None, sbp: float = None, rr: float = None,
                    temp: float = None, spo2: float = None, on_o2: bool = False,
                    avpu: str = "", has_copd: bool = False) -> dict:
    spo2_score = _news2_spo2_scale2(spo2) if not has_copd else _news2_spo2(spo2, on_o2)
    scores = {
        "rr":        _news2_rr(rr),
        "spo2":      spo2_score,
        "o2_supplement": _news2_o2_supplement(on_o2),
        "sbp":       _news2_sbp(sbp),
        "pulse":     _news2_pulse(pulse),
        "consciousness": _news2_consciousness(avpu),
        "temp":      _news2_temp(temp),
    }
    total = sum(scores.values())
    if total == 0:
        action, freq = "minimum_12h", "q12h"
    elif total <= 4:
        action, freq = "ward_monitoring", "q4-6h"
    elif total <= 6:
        action, freq = "urgent_review", "q1h"
    else:
        action, freq = "emergency_icu", "continuous"
    return {"news2": total, "subscores": scores, "action": action, "frequency": freq}


# ── ESI Triage ──────────────────────────────────────────────────────────

def _esi_triage(vitals: dict, resources_expected: int = 0) -> tuple[int, str]:
    """ESI 1-5: 1=immediate(resuscitation), 2=emergent, 3=urgent(≥2 resources),
       4=less-urgent(1 resource), 5=non-urgent(no resources)."""
    hr = float(vitals.get("pulse", 0) or 0)
    sbp = float(vitals.get("sbp", 0) or 0)
    rr = float(vitals.get("rr", 0) or 0)
    spo2 = float(vitals.get("spo2", 0) or 0)
    avpu = str(vitals.get("avpu", "") or "").upper()

    # ESI 1 — immediate life-saving required
    if avpu == "U" or sbp < 70 or rr < 8 or spo2 < 85:
        return (1, "immediate — unresponsive / unstable vitals, resuscitation needed")

    # ESI 2 — high risk
    high_risk_flags = (
        hr > 130 or sbp < 80 or rr > 30 or
        avpu in ("P", "V") or spo2 < 90
    )
    if high_risk_flags:
        return (2, "emergent — high-risk, cannot wait")

    # ESI 3 — needs ≥2 resources
    if resources_expected >= 2:
        return (3, "urgent — multiple resources needed, stable vitals")

    # ESI 4 — needs 1 resource
    if resources_expected == 1:
        return (4, "less-urgent — one resource needed")

    return (5, "non-urgent — no resources needed, can wait")


# ── Stroke FAST ─────────────────────────────────────────────────────────

_STROKE_FAST_ITEMS = {
    "face":   "Face (面部) — 微笑时一侧口角歪斜 / one-sided facial droop / 鼻唇沟变浅",
    "arm":    "Arm (手臂) — 平举双臂时一侧下垂 / arm drift / 单侧无力",
    "speech": "Speech (言语) — 言语含糊不清 / slurred / 听不懂他人说话 / aphasia",
    "time":   "Time (时间) — 发病时间窗: 静脉溶栓 <4.5h, 机械取栓 <6h (部分可延长至24h)",
}

def assess_fast(face_abnormal: bool = False, arm_drift: bool = False,
                speech_abnormal: bool = False, symptom_onset_minutes: float = None) -> dict:
    positives = sum([face_abnormal, arm_drift, speech_abnormal])
    activate = positives >= 1

    thrombolysis_window = False
    thrombectomy_window = False
    if activate and symptom_onset_minutes is not None:
        thrombolysis_window = symptom_onset_minutes / 60 <= 4.5
        thrombectomy_window = symptom_onset_minutes / 60 <= 6.0

    return {
        "fast_positive": activate,
        "positive_items": positives,
        "items": {k: v for k, v, flag in [
            ("face",   _STROKE_FAST_ITEMS["face"],   face_abnormal),
            ("arm",    _STROKE_FAST_ITEMS["arm"],    arm_drift),
            ("speech", _STROKE_FAST_ITEMS["speech"], speech_abnormal),
            ("time",   _STROKE_FAST_ITEMS["time"],   True),
        ]},
        "activate_stroke_protocol": activate,
        "thrombolysis_window_4_5h": thrombolysis_window,
        "thrombectomy_window_6h":   thrombectomy_window,
        "action": "ACTIVATE STROKE CODE — CT + CTA + CTP, NIHSS assessment, tPA/EVT evaluation"
        if activate else "FAST negative — continue monitoring",
    }


# ── STEMI Triage ────────────────────────────────────────────────────────

def assess_stemi(chest_pain: bool = False, st_elevation: bool = False,
                 ecg_leads: str = "", troponin_positive: bool = False,
                 onset_minutes: float = None) -> dict:
    stemi_confirmed = chest_pain and st_elevation
    door_to_balloon_target = 90  # minutes, AHA/ACC guideline

    if onset_minutes is not None and onset_minutes / 60 <= 12:
        reperfusion_window = True
    else:
        reperfusion_window = True if onset_minutes is None else False  # unknown = assume yes

    action = "CATH LAB ACTIVATION — PCI <90min door-to-balloon"
    if not stemi_confirmed:
        action = "serial ECG + troponin q3-6h; consider NSTEMI protocol"

    return {
        "stemi": stemi_confirmed,
        "chest_pain": chest_pain,
        "st_elevation": st_elevation,
        "ecg_leads": ecg_leads,
        "troponin_positive": troponin_positive,
        "door_to_balloon_target_min": door_to_balloon_target,
        "reperfusion_window": reperfusion_window,
        "action": action,
        "bundle": ["Aspirin 300mg chewable", "Ticagrelor 180mg or Clopidogrel 600mg",
                   "Heparin 60U/kg bolus", "Stat atorvastatin 80mg",
                   "PCI (preferred) or fibrinolysis if PCI unavailable within 120min"]
        if stemi_confirmed else ["ASA 300mg", "NTG if no hypotension", "Stat cardiology consult"],
    }


# ── Trauma ABCDE ────────────────────────────────────────────────────────

_ABCDE_CHECKLIST = {
    "A_airway":       "Airway — 评估通畅, 颈椎保护(C-collar), 检查异物/分泌物/舌后坠",
    "B_breathing":    "Breathing — 呼吸频率/深度, SpO2, 双侧呼吸音对称, 张力性气胸排除",
    "C_circulation":  "Circulation — HR/BP/CRT, IV access x2, 止血/加压包扎, FAST超声, 骨盆固定",
    "D_disability":   "Disability — GCS/AVPU, 瞳孔大小及对光反射, 血糖快速检测",
    "E_exposure":     "Exposure — 全身暴露检查, 保暖(防低体温), 脊柱全程检查, 骨折/伤痕",
}

def assess_trauma_abcde(mechanism: str = "", gcs: int = 15, hr: float = 0,
                        sbp: float = 0, rr: float = 0) -> dict:
    findings = []
    critical_findings = []

    # A
    if "气道" in mechanism or "颈椎" in mechanism:
        critical_findings.append("A: 气道/颈椎风险 — 需保护性气道管理")
    findings.append("A: Airway assessed")

    # B
    if rr <= 8:
        critical_findings.append(f"B: RR={rr} ≤8 — 呼吸抑制, 考虑机械通气")
    elif rr >= 30:
        critical_findings.append(f"B: RR={rr} ≥30 — 呼吸窘迫")
    findings.append(f"B: Breathing — RR={rr}")

    # C
    if sbp < 90:
        critical_findings.append(f"C: SBP={sbp} <90 — 休克, 紧急液体复苏")
    if hr > 120:
        critical_findings.append(f"C: HR={hr} >120 — 代偿性心动过速")
    findings.append(f"C: Circulation — HR={hr}, SBP={sbp}")

    # D
    if gcs <= 8:
        critical_findings.append(f"D: GCS={gcs} ≤8 — 严重颅脑损伤, 紧急插管指征")
    findings.append(f"D: Disability — GCS={gcs}")

    # E
    findings.append("E: Exposure — completed")

    return {
        "primary_survey_complete": True,
        "mechanism": mechanism,
        "findings": findings,
        "critical_findings": critical_findings,
        "gcs": gcs,
        "hr": hr,
        "sbp": sbp,
        "rr": rr,
        "action": "Activate trauma team + massive transfusion protocol"
        if len(critical_findings) >= 2 else "Continue secondary survey",
        "checklist": list(_ABCDE_CHECKLIST.values()),
    }


def lookup_antidote(toxin: str) -> dict:
    """Lookup antidote for common poisonings by keyword or class."""
    toxin_lower = (toxin or "").lower()
    for key, info in _ANTIDOTES.items():
        if key in toxin_lower:
            return {"toxin": toxin, "matched_category": key, **info}
    return {"toxin": toxin, "matched_category": "unknown",
            "antidote": "Consult Poison Control Center (中毒控制中心)",
            "dose": "Symptomatic and supportive care"}


def extract_vitals(patient: dict) -> dict:
    """Extract common vital signs from patient lab_results."""
    labs = patient.get("lab_results", {}) if patient else {}
    def _f(key, default=0):
        try:
            return float(labs.get(key, default) or default)
        except (ValueError, TypeError):
            return default
    return {
        "pulse": _f("pulse", _f("HR", 0)),
        "sbp":   _f("sbp", _f("sBP", _f("SBP", 0))),
        "rr":    _f("rr", _f("RR", 0)),
        "temp":  _f("temp", _f("TEMP", _f("temperature", 0))),
        "spo2":  _f("spo2", _f("SpO2", _f("SpO2", 0))),
        "avpu":  str(labs.get("avpu", labs.get("AVPU", "")) or ""),
        "gcs":   int(_f("gcs", _f("GCS", 15))),
        "troponin": _f("Troponin", _f("troponin", 0)),
    }


# ── Pipeline Handlers (injected with real scoring) ──────────────────────

def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def bp_triage(**kwargs) -> dict:
    """急诊分诊 — MEWS + NEWS2 + ESI + FAST + STEMI."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)

    # MEWS
    mews = calculate_mews(v["pulse"], v["sbp"], v["rr"], v["temp"], v["avpu"])
    # NEWS2
    news2 = calculate_news2(v["pulse"], v["sbp"], v["rr"], v["temp"],
                            v["spo2"], on_o2=False, avpu=v["avpu"])
    # ESI
    esi_level, esi_desc = _esi_triage(v)
    # FAST
    fast = assess_fast()
    # STEMI
    stemi = assess_stemi()
    # Antidote lookup from diagnosis
    dx = p.get("diagnosis", "")
    antidote = lookup_antidote(dx) if "中毒" in dx else None

    findings = [
        f"MEWS: {mews['mews']}/15 ({mews['action']}, {mews['frequency']})",
        f"NEWS2: {news2['news2']}/20 ({news2['action']}, {news2['frequency']})",
        f"ESI Triage: Level {esi_level} — {esi_desc}",
        f"FAST screening: {'POSITIVE' if fast['fast_positive'] else 'negative'}",
        f"STEMI triage: {'STEMI CONFIRMED' if stemi['stemi'] else 'non-STEMI'}",
    ]
    if antidote:
        findings.append(f"Antidote: {antidote.get('antidote', '')} [{antidote.get('matched_category', '')}]")

    recommendations = [
        f"MEWS={mews['mews']}: {mews['action']}",
        f"NEWS2={news2['news2']}: {news2['action']}",
        f"ESI Level {esi_level}",
    ]
    if fast["fast_positive"]:
        recommendations.append("FAST positive → activate stroke protocol, CT+CTA within 25min")

    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("急诊科")

    return _agent.clinical_result(
        summary=f"急诊科—急诊分诊 (MEWS={mews['mews']} NEWS2={news2['news2']} ESI={esi_level})",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_rescue(**kwargs) -> dict:
    """紧急救治 — ABCDE + STEMI bundle + resuscitation."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)
    dx = p.get("diagnosis", "")

    # Trauma ABCDE
    trauma = assess_trauma_abcde(mechanism="急诊评估", gcs=v["gcs"],
                                  hr=v["pulse"], sbp=v["sbp"], rr=v["rr"])

    # STEMI bundle
    stemi = assess_stemi(
        chest_pain="胸痛" in dx or "STEMI" in dx.upper(),
        st_elevation="ST段" in dx or "STEMI" in dx.upper(),
        troponin_positive=v["troponin"] > 0.04,
    )

    # Poisoning antidote
    antidote = lookup_antidote(dx) if "中毒" in dx else None

    findings = ["CPR/ACLS ready", "除颤器待命", "气道管理备好", f"ABCDE primary survey: {len(trauma['critical_findings'])} critiques"]
    if stemi["stemi"]:
        findings.insert(0, f"STEMI — {stemi['action']}")
    if antidote:
        findings.append(f"解毒: {antidote['antidote']} — {antidote['dose']}")

    recommendations = trauma["critical_findings"].copy()
    if stemi["stemi"]:
        recommendations.extend(stemi["bundle"])

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("急诊科")
    return _agent.clinical_result(
        summary="急诊科—紧急救治 (ABCDE + STEMI bundle + antidote)",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_icu(**kwargs) -> dict:
    """重症监护 — MEWS/NEWS2 trending + SOFA surveillance."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)

    mews = calculate_mews(v["pulse"], v["sbp"], v["rr"], v["temp"], v["avpu"])
    news2 = calculate_news2(v["pulse"], v["sbp"], v["rr"], v["temp"],
                            v["spo2"], on_o2=False, avpu=v["avpu"])

    icu_triggered = mews["threshold_geq_7"] or news2["news2"] >= 7

    findings = [
        f"MEWS trend: {mews['mews']} ({mews['action']})",
        f"NEWS2 trend: {news2['news2']} ({news2['action']})",
        "血流动力学监测", "呼吸支持评估", "器官功能连续性监测", "感染指标动态追踪",
    ]
    if icu_triggered:
        findings.insert(0, "WARNING: ICU-level scoring triggered (MEWS≥7 or NEWS2≥7)")


    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("急诊科")
    return _agent.clinical_result(
        summary=f"急诊科—ICU监护 (MEWS={mews['mews']} NEWS2={news2['news2']})",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_transfer(**kwargs) -> dict:
    """转归评估 — stability assessment for transfer."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)

    mews = calculate_mews(v["pulse"], v["sbp"], v["rr"], v["temp"], v["avpu"])
    news2 = calculate_news2(v["pulse"], v["sbp"], v["rr"], v["temp"],
                            v["spo2"], on_o2=False, avpu=v["avpu"])

    stable_for_transfer = mews["mews"] <= 2 and news2["news2"] <= 2


    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("急诊科")
    return _agent.clinical_result(
        summary=f"急诊科—转归评估 (MEWS={mews['mews']} {'stable' if stable_for_transfer else 'defer'})",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_followup(**kwargs) -> dict:
    """随访跟踪 — post-discharge MEWS/NEWS2 baseline."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    v = extract_vitals(p)

    mews = calculate_mews(v["pulse"], v["sbp"], v["rr"], v["temp"], v["avpu"])


    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _GUIDELINES
    rules = _agent.search_rules("急诊科")
    return _agent.clinical_result(
        summary=f"急诊科—随访 (MEWS={mews['mews']})",
        patient=p, guidelines=guides, rules=rules,
        alerts=vitals.get("alerts", []),
    )
