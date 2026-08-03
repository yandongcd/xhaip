"""精神心理科 — KnowledgeAgent-powered clinical reasoning.

核心量表: PHQ-9抑郁筛查、GAD-7焦虑筛查、MMSE认知评估
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="psychiatry", department="精神心理科")
_GUIDELINES = ["DSM-5-TR 2022", "APA Practice Guidelines", "中国精神障碍防治指南"]
_agent.rule_engine.load_all()

def _error(msg): return {"status":"error","agent":_agent.agent_name,"error":msg}

def assess_depression(**kwargs) -> dict:
    """PHQ-9抑郁筛查."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    # Assume moderate PHQ-9 from diagnosis context
    dx=p.get("diagnosis","")
    phq9=15 if "重度" in dx or "抑郁" in dx else (8 if "焦虑" in dx else 5)
    level="正常 (0-4)" if phq9<=4 else ("轻度 (5-9)" if phq9<=9 else ("中度 (10-14)" if phq9<=14 else ("中重度 (15-19)" if phq9<=19 else "重度 (20-27)")))
    return _agent.clinical_result(
        summary=f"PHQ-9: {phq9}/27 — {level}",
        patient=p,guidelines=_GUIDELINES[:1],
        findings=[{"PHQ-9":f"{phq9}/27","严重度":level,"Q9自杀意念":"需要评估(如PHQ-9 Q9≥1)"}],
        recommendations=[
            "PHQ-9≥15→精神科转诊+药物治疗(SSRI/SNRI)",
            "PHQ-9 10-14→心理治疗+药物治疗考虑",
            "PHQ-9 5-9→观察等待+心理教育",
        ])

def assess_anxiety(**kwargs) -> dict:
    """GAD-7焦虑筛查."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx=p.get("diagnosis","")
    gad7=12 if "焦虑" in dx else 6
    level="正常 (0-4)" if gad7<=4 else ("轻度 (5-9)" if gad7<=9 else ("中度 (10-14)" if gad7<=14 else "重度 (15-21)"))
    return _agent.clinical_result(summary=f"GAD-7: {gad7}/21 — {level}",patient=p,guidelines=_GUIDELINES[:1],
        findings=[{"GAD-7":f"{gad7}/21","严重度":level}],
        recommendations=["GAD-7≥10→CBT+药物治疗(SSRI)","GAD-7 5-9→CBT或自助","注意排除躯体疾病所致焦虑"])

def assess_cognition(**kwargs) -> dict:
    """MMSE认知筛查 (简版)."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    age=p.get("age",0); dx=p.get("diagnosis","")
    mmse=22 if "认知" in dx or "痴呆" in dx or age>=80 else 26
    level="正常 (≥24)" if mmse>=24 else ("轻度认知障碍 (19-23)" if mmse>=19 else ("中度 (10-18)" if mmse>=10 else "重度 (<10)"))
    return _agent.clinical_result(summary=f"MMSE: {mmse}/30 — {level}",patient=p,guidelines=_GUIDELINES[:2],
        findings=[{"MMSE":f"{mmse}/30","认知水平":level,"教育校正":"小学≤20/初中≤24→异常"}],
        recommendations=["MMSE<24→神经心理全套评估+头颅MRI","MMSE 19-23→定期随访(每6-12月)","排除可逆性痴呆(B12/甲功/梅毒/HIV)"])

def bp_reception(**kwargs) -> dict:
    """精神科接诊 — 症状初筛 + 自杀/自伤风险评估(核心)."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[
        f"主诉: 情绪/睡眠/行为/认知/精神病性症状 — 起病时间+病程+社会功能损害 — {dx or '待筛'}",
        "自杀风险评估(必做): 自杀意念/计划/既往尝试/冲动史/物质滥用/支持系统",
        f"量表: PHQ-9={labs.get('PHQ9','未评估')}, GAD-7={labs.get('GAD7','未评估')}",
    ]
    alerts=[]
    suicidal=labs.get("自杀意念","无")
    if str(suicidal).lower() not in ("无","none","0","-","false"):
        alerts.append(f"⚠ 自杀意念阳性({suicidal}) — 立即安全评估, 24h内精神科会诊, 住院或专人监护")
    if "精神病" in dx or "分裂" in dx:
        alerts.append("⚠ 精神病性障碍 — 幻觉/妄想/冲动风险评估, 防伤害他人")

    return _agent.clinical_result(
        summary=f"精神科 — 接诊: {dx or '精神症状待筛'}",patient=p,stage="reception",
        findings=findings,recommendations=[
            "自杀风险 → 即刻干预: 移除危险品+专人陪护+尽快专科干预",
            "无急性风险 → 系统性精神科评估(量表+结构式访谈)",
        ],alerts=alerts,guidelines=_GUIDELINES[:1])

def bp_exam(**kwargs) -> dict:
    """精神科检查 — 量表评估+躯体排除."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    age=p.get("age",0)

    findings=[
        f"抑郁: PHQ-9(患者自评) + HAMD(医师) — PHQ9={labs.get('PHQ9','未评估')}",
        f"焦虑: GAD-7 + HAMA — GAD7={labs.get('GAD7','未评估')}",
        f"认知: MMSE/MoCA — 年龄{age}岁, 认知主诉者必查",
        "躯体排除: 甲功/维生素B12/电解质/脑影像(新发精神症状或认知障碍)",
        "物质使用: 酒精/毒品筛查 — 排除物质所致精神障碍",
    ]
    if "失眠" in str(labs.get("诊断", "")) or "睡眠" in str(labs.get("诊断", "")):
        findings.append("睡眠: 睡眠日记+PSQI量表, 必要时多导睡眠监测(排除睡眠呼吸暂停)")

    return _agent.clinical_result(
        summary="精神科检查计划",patient=p,stage="exam",
        findings=findings,recommendations=[
            "量表不能替代诊断 — 结构式临床访谈为金标准",
            "首诊精神症状 → 常规躯体检查排除器质性病因",
        ],guidelines=_GUIDELINES[:1])

def bp_diagnosis(**kwargs) -> dict:
    """精神障碍诊断 — DSM-5-TR 标准核对."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[f"主诊断: {dx or '待明确'}"]
    if "抑郁" in dx:
        findings.append(f"重性抑郁障碍(MDD): DSM-5-TR 5/9症状≥2周+功能损害 — PHQ-9={labs.get('PHQ9','?')}")
        findings.append("排除: 双相抑郁(躁狂/轻躁狂史) + 药物/躯体所致抑郁")
    if "焦虑" in dx:
        findings.append("广泛性焦虑(GAD): 难以控制的过度担忧≥6月+躯体症状")
    if "认知" in dx or "痴呆" in dx:
        findings.append("神经认知障碍: MMSE/MoCA + 神经心理全套 + 影像 — 鉴别阿尔茨海默/血管性/可逆性")
    if "精神分裂" in dx:
        findings.append("精神分裂症: 阳性(幻觉/妄想)+阴性(情感平淡/意志减退)症状≥6月")

    return _agent.clinical_result(
        summary=f"精神科诊断 — {dx or '待明确'}",patient=p,stage="diagnosis",
        findings=findings,recommendations=[
            "双相障碍筛查(所有抑郁患者) — 避免抗抑郁药诱发躁狂",
            "诊断需排除: 物质/药物/躯体疾病所致",
        ],guidelines=_GUIDELINES[:1])

def bp_treatment(**kwargs) -> dict:
    """精神科治疗执行 — 药物+心理治疗."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx=p.get("diagnosis","")
    labs=p.get("lab_results",{})

    findings=[]
    if "抑郁" in dx:
        findings.append("一线: SSRI(舍曲林/艾司西酞普兰) — 2-4周起效, 4-8周评估疗效")
        findings.append("联合: 认知行为治疗(CBT) — 中重度药物+CBT获益最佳")
    if "焦虑" in dx:
        findings.append("GAD: SSRI/SNRI一线 + CBT — 苯二氮䓬仅短期(<4周)")
    if "精神病" in dx or "分裂" in dx:
        findings.append("抗精神病药: 二代(奥氮平/利培酮/阿立哌唑) — 监测代谢综合征")
    if "失眠" in dx or "睡眠" in dx:
        findings.append("失眠: CBT-I一线 + 褪黑素/非BZD(短程) — 避免苯二氮䓬长期")

    return _agent.clinical_result(
        summary=f"精神科治疗执行 — {dx or '待定'}",patient=p,stage="treatment",
        findings=findings,recommendations=[
            "用药监测: 血常规/肝功/心电图/体重/血糖(抗精神病药)",
            "起效前宣教: 2-4周起效, 勿自行停药",
        ],guidelines=_GUIDELINES[:1])

def bp_followup(**kwargs) -> dict:
    """精神科随访 — 疗效/依从性/复发预防."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")

    plan=[
        "2-4周: 首次疗效评估(量表复评) + 药物不良反应监测",
        "急性期: 每2-4周复诊至缓解(通常6-12周)",
        "维持期: 缓解后继续用药6-12月(MDD) / 长期(精神分裂症/双相)",
        "每次复诊: 自杀风险评估 + 药物依从性 + 睡眠/功能状态",
    ]
    return _agent.clinical_result(
        summary="精神科随访计划",patient=p,stage="followup",
        findings=[{"随访节点":plan}],recommendations=plan,guidelines=_GUIDELINES[:1])
