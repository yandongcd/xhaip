"""麻醉风险评估智能体 — ASA分级/困难气道/抗凝桥接/麻醉方案/术前优化."""
from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="anesthesia", department="麻醉科")
_GUIDELINES = [
    "ASA Physical Status Classification System (2020)",
    "2022 ASA Difficult Airway Algorithm",
    "美国区域麻醉与疼痛医学学会(ASRA)抗凝指南 2025",
    "中国麻醉学指南与专家共识 (2024)",
]
_agent.rule_engine.load_all()


def asa_assessment(**kwargs) -> dict:
    """ASA体格状态分级评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    age = p.get("age", 0)
    comorbidities = []
    # Check common ASA factors
    vitals = _agent.assess_vitals(p)
    if age >= 75:
        comorbidities.append("高龄(≥75岁)")
    if p.get("diagnosis", ""):
        comorbidities.append(f"基础疾病: {p['diagnosis']}")

    # ASA classification logic
    asa_class = 2  # default mild systemic disease
    alerts = []
    if not comorbidities or len(comorbidities) <= 1:
        asa_class = 1
    elif any(kw in str(comorbidities) for kw in ["心衰", "COPD", "肾衰竭", "肝硬化"]):
        asa_class = 3
    if vitals.get("alerts"):
        asa_class = max(asa_class, 3)
        alerts = vitals.get("alerts", [])

    guides = _agent.search_guidelines("ASA分级") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"ASA评估完成 — ASA {asa_class}级",
        patient=p,
        guidelines=guides,
        alerts=alerts,
        findings=[{"ASA分级": asa_class, "合并症": comorbidities, "警示": alerts}],
        recommendations=[f"ASA {asa_class}级患者围术期管理建议: 根据分级确定监测级别和麻醉方案"],
    )


def airway_evaluation(**kwargs) -> dict:
    """困难气道评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    # Mallampati/Mallampati分级需临床检查，AI提供评估指引
    bmi = float(p.get("bmi", 0) or 0)
    findings = {
        "Mallampati分级": "需临床评估(I-IV级)",
        "BMI": f"{bmi:.1f} kg/m²" if bmi else "未知",
        "甲颏间距": "需临床测量(正常≥6.5cm)",
        "张口度": "需临床测量(正常≥3指)",
    }
    alerts = []
    if bmi and bmi > 35:
        alerts.append(f"BMI {bmi:.1f} >35 — 肥胖是困难气道的独立危险因素")

    guides = _agent.search_guidelines("困难气道") or _GUIDELINES
    return _agent.clinical_result(
        summary="困难气道评估指引 — 需配合临床体格检查完成",
        patient=p,
        guidelines=guides,
        alerts=alerts,
        findings=[findings],
        recommendations=["建议麻醉医师完成床旁Mallampati分级/甲颏间距/张口度/颈围测量"],
    )


def anticoagulation_bridge(**kwargs) -> dict:
    """抗凝桥接管理."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    meds = p.get("medications", [])
    antithrombotic_meds = [m for m in meds if any(
        kw in str(m).lower() for kw in ["华法林", "warfarin", "阿司匹林", "aspirin",
                                          "氯吡格雷", "clopidogrel", "替格瑞洛", "ticagrelor",
                                          "利伐沙班", "rivaroxaban", "达比加群", "dabigatran",
                                          "阿哌沙班", "apixaban", "依度沙班", "edoxaban"])]

    recommendations = []
    alerts = []
    for med in antithrombotic_meds:
        med_name = med.get("name", str(med))
        recommendations.append(f"{med_name}: 需根据手术出血风险和血栓风险制定桥接方案")
        alerts.append(f"⚠️ 抗栓药物 {med_name} 需术前停药管理")

    if not antithrombotic_meds:
        recommendations.append("未检测到抗栓药物使用，常规术前评估即可")

    guides = _agent.search_guidelines("抗凝桥接") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"抗凝桥接评估 — 检测到{len(antithrombotic_meds)}种抗栓药物",
        patient=p,
        guidelines=guides,
        alerts=alerts,
        findings=[{"抗栓药物": [str(m) for m in antithrombotic_meds]}],
        recommendations=recommendations,
    )


def anesthesia_plan(**kwargs) -> dict:
    """麻醉方案推荐."""
    pid = kwargs.get("patient_id", "")
    surgery_type = kwargs.get("surgery_type", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    age = p.get("age", 0)
    plans = []
    if age >= 70 or surgery_type in ["髋部骨折", "关节置换", "剖腹产"]:
        plans.append("区域麻醉/椎管内麻醉 (适用于老年/骨科/产科)")
    else:
        plans.append("全身麻醉 (适用于腹部/胸部/神外手术)")
    plans.append("监测下麻醉镇静 (适用于短小手术/内镜检查)")

    guides = _agent.search_guidelines("麻醉方案") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"麻醉方案推荐 — 手术类型: {surgery_type or '未指定'}",
        patient=p,
        guidelines=guides,
        findings=[{"手术类型": surgery_type, "年龄": age}],
        recommendations=plans,
    )


def preoperative_optimization(**kwargs) -> dict:
    """术前优化建议."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    recs = [
        "禁食: 清液体2h / 母乳4h / 轻食6h / 脂肪餐8h (ASA 2023指南)",
        "术前用药: 根据患者情况评估是否需要术前镇静/抗焦虑",
        "容量管理: 维持正常血容量，避免术前过度脱水",
        "血糖控制: 糖尿病患者围术期血糖目标 6-10 mmol/L",
        "β受体阻滞剂: 长期服用者继续使用，避免术前突然停药",
    ]

    guides = _agent.search_guidelines("术前优化") or _GUIDELINES
    return _agent.clinical_result(
        summary="术前优化建议 — 基于ASA最新指南",
        patient=p,
        guidelines=guides,
        recommendations=recs,
    )
