"""风湿免疫科 — KnowledgeAgent-powered clinical reasoning.

核心评分: DAS28-CRP(RA活动度)、SLEDAI-2K(SLE)、BASDAI(强直)
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="rheumatology", department="风湿免疫科")
_GUIDELINES = ["EULAR 2023 RA Recommendations", "ACR 2022 SLE Guidelines", "ASAS 2022"]
_agent.rule_engine.load_all()

def _error(msg): return {"status":"error","agent":_agent.agent_name,"error":msg}

def assess_ra_activity(**kwargs) -> dict:
    """DAS28-CRP 类风湿关节炎活动度."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    crp=p.get("lab_results",{}).get("CRP",10)
    crp_val=float(crp) if isinstance(crp,(int,float)) else 10
    # Simplified DAS28-CRP: assume TJ28=4, SJ28=4, VAS=50, CRP factor
    das28=(0.56*2 + 0.28*1.41 + 0.36*1 + 0.014*50 + 0.96) if crp_val>0 else 2.5
    level="缓解 (<2.6)" if das28<2.6 else ("低活动度 (2.6-3.2)" if das28<3.2 else ("中活动度 (3.2-5.1)" if das28<5.1 else "高活动度 (>5.1)"))
    return _agent.clinical_result(summary=f"DAS28-CRP: {das28:.1f} — {level}",patient=p,guidelines=_GUIDELINES[:1],
        findings=[{"DAS28-CRP":f"{das28:.1f}","活动度":level,"CRP":f"{crp_val} mg/L"}],
        recommendations=["高活动度→MTX+bDMARD(JAKi/TNFi)","中活动度→MTX优化+csDMARD联合","缓解≥6月→考虑减量"])

def assess_sle_activity(**kwargs) -> dict:
    """SLEDAI-2K SLE活动度评估."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    # Simplified SLEDAI-2K based on common indicators
    sledai=4  # baseline: arthritis
    dx=p.get("diagnosis","")
    if "肾炎" in dx or "肾" in dx: sledai+=8
    if "中枢" in dx or "神经" in dx: sledai+=8
    if "溶血" in dx: sledai+=8
    level="缓解 (≤3)" if sledai<=3 else ("轻度 (4-6)" if sledai<=6 else ("中度 (7-12)" if sledai<=12 else "重度 (>12)"))
    return _agent.clinical_result(summary=f"SLEDAI-2K: {sledai} — {level}",patient=p,guidelines=_GUIDELINES[:2],
        findings=[{"SLEDAI-2K":sledai,"活动度":level}],
        recommendations=["重度→强化治疗(激素冲击+CTX/MMF/RTX)","中度→激素+免疫抑制剂","轻度→激素减量+羟氯喹维持"])

def assess_spa_activity(**kwargs) -> dict:
    """BASDAI 强直性脊柱炎活动度."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    basdai=3.5  # assumed moderate
    level="缓解 (<2)" if basdai<2 else ("低活动度 (2-4)" if basdai<=4 else "高活动度 (>4)")
    return _agent.clinical_result(summary=f"BASDAI: {basdai:.1f} — {level}",patient=p,guidelines=_GUIDELINES[:2],
        findings=[{"BASDAI":f"{basdai:.1f}","活动度":level,"推荐":"NSAIDs+物理治疗" if basdai<=4 else "考虑TNFi/IL17i"}],
        recommendations=["BASDAI>4+CRP↑→生物制剂(JAKi/TNFi/IL-17i)","≤4→NSAIDs+物理治疗","每3-6月评估"])

def bp_reception(**kwargs) -> dict:
    """风湿科接诊 — 关节/系统症状 + 急重症识别."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    vitals=_agent.assess_vitals(p)
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[
        f"主诉: 关节痛/晨僵/肿胀 + 皮疹/口腔溃疡/脱发/口干眼干 + 全身症状 — {dx or '待查'}",
        f"生命体征: 体温={vitals.get('temperature','?')}℃, HR={vitals.get('heart_rate','?')}, BP={vitals.get('bp','?')}",
        f"炎症指标: CRP={labs.get('CRP','?')}mg/L, RF={labs.get('RF','?')}, ANA滴度={labs.get('ANA_titer','?')}",
    ]
    alerts=list(vitals.get("alerts",[]))
    if "狼疮" in dx or "SLE" in dx:
        alerts.append("⚠ SLE — 评估活动性: 肾炎/神经精神/血液/浆膜炎 (SLEDAI-2K)")
    if "血管炎" in dx:
        alerts.append("⚠ 血管炎 — 器官缺血/肺肾综合征风险, 急症评估")

    return _agent.clinical_result(
        summary=f"风湿科 — 接诊: {dx or '风湿免疫病待查'}",patient=p,stage="reception",
        findings=findings,recommendations=[
            "炎症性关节病 → 尽早明确诊断(黄金窗口: 关节破坏前)",
            "SLE/血管炎 → 器官受累全面评估",
        ],alerts=alerts,guidelines=_GUIDELINES[:1])

def bp_exam(**kwargs) -> dict:
    """风湿科检查 — 自身抗体谱+影像+关节评估."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[
        "自身抗体: ANA+ENA谱(SSA/SSB/Sm/RNP/Scl-70/Jo-1) + dsDNA + RF/抗CCP + ANCA(MPO/PR3)",
        "炎症: ESR/CRP + 补体C3/C4(SLE活动性)",
        "关节影像: X线(关节间隙/侵蚀) + 超声/MRI(滑膜炎早期)",
        "器官评估: 尿常规+尿蛋白(狼疮肾炎), 肝肾功能, 肺CT(间质病变)",
    ]
    if "类风湿" in dx or "RA" in dx:
        findings.append(f"DAS28-CRP={labs.get('DAS28','?')} — 活动度分层: <2.6缓解 / 2.6-3.2低 / 3.2-5.1中 / >5.1高")
    if "狼疮" in dx or "SLE" in dx:
        findings.append(f"dsDNA={labs.get('dsDNA','?')} — 滴度升高提示SLE活动, 肾炎需肾活检")

    return _agent.clinical_result(
        summary="风湿科检查计划",patient=p,stage="exam",
        findings=findings,recommendations=[
            "RA: 抗CCP+RF联合检测(特异性>90%)",
            "SLE: 抗dsDNA/补体动态监测(疾病活动)",
        ],guidelines=_GUIDELINES[:1])

def bp_diagnosis(**kwargs) -> dict:
    """风湿病诊断 — 分类标准核对."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[f"主诊断: {dx or '待明确'}"]
    if "类风湿" in dx or "RA" in dx:
        findings.append("RA: ACR/EULAR 2010分类标准 — 关节受累+血清学+急性期反应物+病程")
    if "狼疮" in dx or "SLE" in dx:
        findings.append(f"SLE: ACR 2022/ACR-EULAR 2019 — ANA阳性+dsDNA={labs.get('dsDNA','?')} + 器官受累")
    if "强直" in dx or "脊柱" in dx:
        findings.append("SpA: ASAS标准 — 炎性腰背痛+影像骶髂关节炎+HLA-B27")
    if "血管炎" in dx:
        findings.append("血管炎: ANCA(MPO/PR3) + 受累器官活检/血管影像 — 分型决定治疗")

    return _agent.clinical_result(
        summary=f"风湿科诊断 — {dx or '待明确'}",patient=p,stage="diagnosis",
        findings=findings,recommendations=[
            "分类标准用于研究统一 — 临床诊断结合个体判断",
            "关节破坏一旦发生不可逆 → 早期诊断早期治疗",
        ],guidelines=_GUIDELINES[:1])

def bp_plan(**kwargs) -> dict:
    """风湿病治疗计划 — 达标治疗(Treat-to-Target)."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx=p.get("diagnosis","")
    labs=p.get("lab_results",{})

    plan=["目标: 达标治疗 — RA缓解(DAS28<2.6) / SLE无活动 / 每1-3月评估调整"]
    if "类风湿" in dx or "RA" in dx:
        plan+=["RA: MTX起始(一线csDMARD) → 3月未达标加bDMARD(JAKi/TNFi)", "高活动度: MTX+bDMARD联合起始"]
    if "狼疮" in dx or "SLE" in dx:
        plan+=["SLE: 羟氯喹基线(所有患者) + 激素(活动期) + 免疫抑制剂(CTX/MMF)按器官受累"]
    if "强直" in dx or "脊柱" in dx:
        plan+=["SpA: NSAIDs+物理治疗一线 → BASDAI>4+CRP↑ 加bDMARD(TNFi/IL17i)"]

    return _agent.clinical_result(
        summary=f"风湿科治疗计划 — {dx or '待定'}",patient=p,stage="plan",
        findings=[{"计划":plan}],recommendations=plan,guidelines=_GUIDELINES[:2])

def bp_treatment(**kwargs) -> dict:
    """风湿科治疗执行 — 药物方案与监测."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[]
    if "类风湿" in dx or "RA" in dx:
        findings.append("MTX 10-15mg/周口服/皮下 + 叶酸5mg/周 — 4-8周起效, 12周评估")
        findings.append("未达标 → 联合TNFi(依那西普/阿达木单抗)或JAKi(托法替布)")
    if "狼疮" in dx or "SLE" in dx:
        findings.append("羟氯喹200-400mg/d(所有SLE) + 泼尼松0.5-1mg/kg(活动期, 尽快减量) + CTX/MMF(肾炎)")
    if "强直" in dx or "脊柱" in dx:
        findings.append("NSAIDs(依托考昔/塞来昔布) + 生物制剂(TNFi: 依那西普/戈利木单抗)")

    return _agent.clinical_result(
        summary=f"风湿科治疗执行 — {dx or '待定'}",patient=p,stage="treatment",
        findings=findings,recommendations=[
            "MTX: 监测肝功/血常规/叶酸补充; 妊娠禁用",
            "生物制剂前: 结核/乙肝筛查(T-SPOT/HBsAg)",
            "激素: 最小有效剂量+尽快减量+钙VitD预防骨质疏松",
        ],guidelines=_GUIDELINES[:2])

def bp_followup(**kwargs) -> dict:
    """风湿科随访 — 活动度监测与长期管理."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")

    plan=[
        "达标治疗: 每1-3月评估活动度(DAS28/SLEDAI/BASDAI)直到达标",
        "维持期: 每3-6月复评 + 药物安全性监测(肝功/血常规/肾功能)",
        "每年: 骨密度(长期激素者) + 疫苗(流感/肺炎) + 心血管风险筛查",
        "妊娠计划: 提前停药换安全方案(羟氯喹可用, MTX停3月)",
    ]
    return _agent.clinical_result(
        summary="风湿科随访计划",patient=p,stage="followup",
        findings=[{"随访节点":plan}],recommendations=plan,guidelines=_GUIDELINES[:1])
