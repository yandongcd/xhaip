"""Neuro Preconsult v2.0 — 神外预咨询: 定向病史+GCS+红旗征12项+影像分流+手术时机评估.

Guidelines: NICE NG127, AHA/ASA 2023, 中国神外术后加速康复(2023)
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="neuro-preconsult", department="神经外科")
_GUIDELINES = [
    "中国神经外科术后加速康复专家共识 (2023)",
    "NICE NG127 颅内肿瘤管理指南",
    "AHA/ASA 2023 脑血管病管理指南",
    "WFNS 蛛网膜下腔出血分级",
    "NASCET 颈动脉内膜切除术标准",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ GCS + Red Flags ═══════

_NS_RED_FLAGS = [
    ("突发剧烈头痛", "蛛网膜下腔出血/动脉瘤破裂 — WFNS分级评估", "emergent", "急诊头颅CT+CTA, 神经外科值班立即评估"),
    ("进行性意识障碍", "颅内高压/脑疝 — 需立即降颅压", "emergent", "甘露醇 1g/kg IV + 床头抬高30° + 急诊CT+神外急会诊"),
    ("瞳孔不等大", "脑疝(颞叶钩回疝) — 单侧瞳孔散大=同侧", "emergent", "甘露醇+过度通气+急诊开颅减压"),
    ("Cushing三联征", "颅内高压晚期 — 高血压+心动过缓+呼吸不规则", "emergent", "立即气管插管+甘露醇+急诊CT+手术"),
    ("进行性下肢无力+鞍区麻木", "脊髓压迫/马尾综合征 — 24h窗口期!", "emergent", "急诊MRI脊柱+激素+神外急会诊(24h内减压)"),
    ("急性视力丧失", "视交叉压迫/垂体卒中", "emergent", "急诊MRI垂体+激素替代(氢化可的松100mg IV)+神外评估"),
    ("癫痫持续状态", "颅内占位/脑出血/脑炎", "emergent", "劳拉西泮2mg IV q2min+苯妥英20mg/kg+CT+脑电图"),
    ("GCS下降≥2分", "颅内病情恶化", "emergent", "立即CT复查+甘露醇+神外急会诊"),
    ("反复呕吐+晨间头痛", "颅内高压(慢性) — 脑肿瘤/脑积水", "urgent", "CT/MRI+眼底镜(视乳头水肿)+神外门诊"),
    ("进行性单侧肢体无力/麻木", "颅内占位/脑卒中", "urgent", "CT平扫+MRI增强+MRA/DSA评估"),
    ("眩晕+听力下降+耳鸣+面瘫", "听神经瘤/CPA区占位", "urgent", "MRI颅底薄层+听力图+BAEP+神外门诊"),
    ("内分泌异常+视力视野缺损", "鞍区/垂体占位(垂体腺瘤/颅咽管瘤)", "urgent", "MRI垂体+PRL/GH/ACTH+视野检查+神外门诊"),
]

_GCS_COMPONENTS = {
    "eye": {"4": "自动睁眼", "3": "呼唤睁眼", "2": "刺痛睁眼", "1": "无"},
    "verbal": {"5": "正常交谈", "4": "言语错乱", "3": "不适当词汇", "2": "无意义声音", "1": "无"},
    "motor": {"6": "遵嘱运动", "5": "定位疼痛", "4": "回缩", "3": "屈曲(去皮层)", "2": "伸直(去大脑)", "1": "无"},
}

_WFNS_SAH = {
    "I": {"gcs": 15, "motor_deficit": False, "mortality": "5-10%", "action": "早期动脉瘤治疗(<24h) → 尼莫地平+EVD"},
    "II": {"gcs": 13, "motor_deficit": False, "mortality": "10-15%", "action": "同上 + 严密监测DCI/血管痉挛(TCD qd)"},
    "III": {"gcs": 13, "motor_deficit": True, "mortality": "20-30%", "action": "同上"},
    "IV": {"gcs": 7, "motor_deficit": "±", "mortality": "30-40%", "action": "EVD+ICP监测+延迟动脉瘤治疗(神经功能改善后)"},
    "V": {"gcs": 3, "motor_deficit": "±", "mortality": "50-70%", "action": "ICP管理+呼吸机+支持治疗, 预后差考虑不手术"},
}


def _gcs_score(eye: int, verbal: int, motor: int) -> dict:
    gcs = eye + verbal + motor
    if gcs >= 13:
        level = "轻度意识障碍" if gcs < 15 else "意识清楚"
    elif gcs >= 9:
        level = "中度意识障碍"
    elif gcs >= 4:
        level = "重度意识障碍(昏迷)"
    else:
        level = "极重度(深昏迷)"
    return {"score": gcs, "level": level, "e": eye, "v": verbal, "m": motor}


# ═══════ Handler Functions ═══════


def history_collect(patient_id: str = "", chief_complaint: str = "",
                    **kwargs: Any) -> dict:
    """定向病史采集 — 主诉+现病史+既往史+GCS+专科追问."""
    p, err = _get_patient({"patient_id": patient_id})

    age = p.get("age", "?") if p else "?"
    dx = p.get("diagnosis", "") if p else ""

    # Symptom-specific drilling
    drill_questions = {
        "头痛": ["头痛部位? 持续/阵发? 有无晨间加重?", "VAS评分(0-10)?", "有无恶心/呕吐?", "有无搏动感(偏头痛)?"],
        "抽搐/癫痫": ["有无意识丧失? 持续时间?", "发作类型(局灶/全面)?", "发作后有无Todd麻痹/意识模糊?"],
        "无力/麻木": ["哪侧肢体? 上肢/下肢?", "有无伴随面部歪斜/言语不清(卒中)?", "进行性加重还是突发?"],
        "视力改变": ["单眼/双眼? 视力下降/复视/视野缺损?", "有无头痛(垂体卒中)?"],
        "头晕/眩晕": ["旋转感/不稳感?", "有无听力下降/耳鸣(听神经瘤)?", "体位改变有无加重?"],
        "腰痛/下肢": ["有无鞍区麻木/大小便障碍(马尾!)?", "有无下肢放射痛(坐骨神经)?"],
    }

    questions = ["请描述症状起始时间(何时开始/急性or渐进)", "有无外伤史(近期头部撞击/跌倒)"]
    for kw, qs in drill_questions.items():
        if kw in chief_complaint:
            questions = qs + questions
            break

    if not questions or len(questions) < 3:
        questions = ["症状何时开始?", "有无头痛/呕吐?", "有无肢体无力/麻木?", "有无癫痫?", "有无意识改变?"]

    # Medication review
    anticoag_warning = ""
    meds = p.get("medications", []) if p else []
    if any("warfarin" in str(m).lower() or "华法林" in str(m) or "抗凝" in str(m) or "clopidogrel" in str(m).lower() or "阿司匹林" in str(m) for m in meds):
        anticoag_warning = "患者服用抗凝/抗血小板药物 — 神经外科手术需停药并桥接评估"

    return {
        "status": "ok", "patient_id": patient_id,
        "chief_complaint": chief_complaint,
        "patient_info": {"age": age, "diagnosis": dx},
        "questions": questions[:8],
        "anticoagulation_warning": anticoag_warning,
        "summary": f"病史采集 — {chief_complaint[:30]} | {len(questions)}个追问",
    }


def red_flag_screen(patient_id: str = "", symptoms: list | None = None,
                    gcs_e: int = 4, gcs_v: int = 5, gcs_m: int = 6,
                    **kwargs: Any) -> dict:
    """红旗征筛查 — 12项神经外科急症 + GCS分级 + WFNS分级."""
    p, err = _get_patient({"patient_id": patient_id})
    symptoms = symptoms or []
    sx_text = " ".join(str(s) for s in symptoms).lower()

    flags = []
    highest_urgency = "routine"

    for pattern, condition, urgency, action in _NS_RED_FLAGS:
        if pattern in sx_text:
            flags.append({"flag": pattern, "condition": condition, "urgency": urgency, "action": action})
            if urgency == "emergent":
                highest_urgency = "emergent"
            elif urgency == "urgent" and highest_urgency != "emergent":
                highest_urgency = "urgent"

    # GCS
    gcs = _gcs_score(gcs_e, gcs_v, gcs_m)
    if gcs["score"] < 13:
        flags.append({"flag": f"GCS={gcs['score']}(E{gcs_e}V{gcs_v}M{gcs_m})",
                      "condition": f"意识障碍 — {gcs['level']}",
                      "urgency": "emergent",
                      "action": "立即CT+甘露醇+神外急会诊+ICU评估(EVD/ICP监测)"})
        highest_urgency = "emergent"

    # WFNS for SAH symptoms
    wfns = None
    if any(kw in sx_text for kw in ["蛛网膜", "动脉瘤", "突发剧", "劈裂样"]):
        wfns_grade = "I" if gcs["score"] == 15 else ("IV" if gcs["score"] <= 7 else "II" if gcs["score"] >= 13 else "III")
        wfns = _WFNS_SAH.get(wfns_grade, _WFNS_SAH["I"])

    return {
        "status": "ok", "patient_id": patient_id,
        "red_flags": flags, "flag_count": len(flags),
        "highest_urgency": highest_urgency,
        "gcs": gcs,
        "wfns_sah": wfns,
        "alert": "IMMEDIATE ACTION REQUIRED!" if highest_urgency == "emergent" else "",
        "summary": f"红旗征 — {'EMERGENT!' if highest_urgency == 'emergent' else 'URGENT' if highest_urgency == 'urgent' else '无紧急征象'} | GCS={gcs['score']}",
    }


def summary_generate(patient_id: str = "", history: dict | None = None,
                     red_flags: list | None = None,
                     gcs: dict | None = None,
                     chief_complaint: str = "",
                     **kwargs: Any) -> dict:
    """结构化预咨询摘要 — 病史+红旗征+GCS+WFNS+影像建议+手术时机."""
    p, err = _get_patient({"patient_id": patient_id})
    history = history or {}
    red_flags = red_flags or []
    gcs = gcs or {}

    age = history.get("age", p.get("age", "?"))
    dx = history.get("diagnosis", p.get("diagnosis", "")) if p else ""

    # Red flags section
    flags_text = ""
    if red_flags:
        for f in red_flags:
            flags_text += f"\n| {f.get('flag','')} | {f.get('condition','')} | {f.get('urgency','')} | {f.get('action','')[:50]} |"
    else:
        flags_text = "\n| 无 | — | — | 常规预咨询流程 |"

    # Imaging recommendations
    imaging = []
    if any("出血" in f.get("condition", "") for f in red_flags):
        imaging.append("急诊头颅CT平扫(排除出血)")
    if any("占位" in f.get("condition", "") for f in red_flags) or "肿瘤" in dx:
        imaging.append("头颅MRI平扫+增强(评估占位性质/大小/位置)")
    if any("血管" in f.get("condition", "") for f in red_flags) or any("动脉瘤" in f.get("condition", "") for f in red_flags):
        imaging.append("CTA/MRA/DSA(评估脑血管)")
    if any("脊髓" in f.get("condition", "") for f in red_flags) or any("鞍区" in f.get("condition", "") for f in red_flags):
        imaging.append("脊柱MRI(评估脊髓/马尾压迫)")
    if not imaging:
        imaging.append("头颅MRI平扫+增强(常规评估)")

    # Surgical timing
    timing = ""
    if any(f.get("urgency") == "emergent" for f in red_flags):
        timing = "立即手术 — 颅内高压/脑疝/动脉瘤破裂需<6h内手术"
    elif any(f.get("urgency") == "urgent" for f in red_flags):
        timing = "优先手术 — 24-72h内安排"
    else:
        timing = "择期手术 — 完善检查后安排(1-4周)"

    # Anticoag management
    ac_mgmt = ""
    if history.get("anticoagulation_warning"):
        ac_mgmt = "抗凝/抗血小板管理: 华法林停5天+LMWH桥接(INR<1.5可手术); 氯吡格雷停5-7天; 阿司匹林停3-5天(脊柱手术)"

    summary = f"""## 神经外科预咨询摘要
**患者ID**: {patient_id} | **年龄**: {age} | **诊断**: {dx}
**主诉**: {chief_complaint}

### GCS评分: {gcs.get('score','N/A')}/15 (E{gcs.get('e','')}V{gcs.get('v','')}M{gcs.get('m','')} — {gcs.get('level','')})

### 红旗征 ({len(red_flags)}项)
| 征象 | 疾病 | 紧急度 | 处置 |
|------|------|--------|------|
{flags_text}

### 建议影像学检查
{chr(10).join(f'- {i}' for i in imaging)}

### 手术时机评估
- {timing}
{ac_mgmt}

### 神经外科专科查体要点
- 神经系统: GCS/瞳孔/肢体肌力(0-5级)/感觉平面/病理征(Babinski)
- 眼底: 视乳头水肿(颅内高压)"""

    return {
        "status": "ok", "patient_id": patient_id,
        "summary": summary,
        "red_flag_count": len(red_flags),
        "imaging_required": imaging,
        "surgical_timing": timing,
        "disclaimer": "AI辅助生成摘要, 须经神经外科主治医师审核确认后纳入病历",
    }
