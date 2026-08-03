"""感染内科 — KnowledgeAgent-powered clinical reasoning.

核心评分: CPIS临床肺部感染、qPitt菌血症严重度、IDSA抗生素疗程
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="infectious-disease", department="感染内科")
_GUIDELINES = ["IDSA 2023 Guidelines", "CDC NHSN Surveillance", "SSC 2021 Sepsis"]
_agent.rule_engine.load_all()

def _error(msg): return {"status":"error","agent":_agent.agent_name,"error":msg}

def assess_infection(**kwargs) -> dict:
    """综合感染评估: CPIS肺炎+qPitt菌血症严重度."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    wbc=float(labs.get("WBC",8)); crp=float(labs.get("CRP",20))
    temp=float(p.get("lab_results",{}).get("Temp",37.2))
    # CPIS simplified (pneumonia)
    cpis=0
    if temp>=38.5 or temp<=36: cpis+=1
    if wbc<4 or wbc>11: cpis+=1
    if crp>60: cpis+=1
    # qPitt simplified (bacteremia severity)
    qpitt=0
    if temp<36: qpitt+=2
    if p.get("age",0)>=65: qpitt+=1
    if "脓毒" in p.get("diagnosis",""): qpitt+=2
    risk_level="低危" if qpitt<=1 else ("中危" if qpitt<=3 else "高危")
    return _agent.clinical_result(
        summary=f"感染评估 — CPIS={cpis}/3, qPitt={qpitt} ({risk_level})",
        patient=p,guidelines=_GUIDELINES[:1],
        findings=[{"CPIS":f"{cpis}/3","qPitt":qpitt,"风险等级":risk_level,"CRP":f"{crp}mg/L","WBC":f"{wbc}"}],
        recommendations=[
            "qPitt≥4(高危)→血培养×2+广谱抗生素+IICU",
            "CPIS≥2→社区/院内肺炎抗生素治疗",
            "CRP下降≥25% in 48h→抗生素降阶梯",
        ])

def assess_antibiotic(**kwargs) -> dict:
    """IDSA抗生素疗程评估."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    recs=[  # IDSA 2023 duration recommendations
        "CAP: 5天 (临床稳定后+afebrile≥48h)",
        "HAP/VAP: 7天 (PCT指导降阶梯)",
        "腹腔感染: 4天 (source control后)",
        "UTI: 3-7天 (女性<65岁3天/复杂7天)",
        "菌血症(GNR): 7天 (非复杂性)",
    ]
    return _agent.clinical_result(summary="抗生素疗程评估 (IDSA 2023)",patient=p,guidelines=_GUIDELINES[:1],
        findings=[{"IDSA推荐":recs,"PCT指导":"PCT<0.5或下降>80%→考虑停用抗生素"}],
        recommendations=recs)

def bp_reception(**kwargs) -> dict:
    """感染科接诊 — 热型/感染灶定位 + 脓毒症识别."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    vitals=_agent.assess_vitals(p)
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    wbc=float(labs.get("WBC",8)); temp=float(labs.get("Temp",37.2))
    findings=[
        f"主诉: 发热(热型/畏寒/寒战) + 感染灶定位(呼吸道/泌尿道/腹腔/皮肤软组织/中枢) — {dx or '待查'}",
        f"生命体征: 体温={temp}℃, HR={vitals.get('heart_rate','?')}, BP={vitals.get('bp','?')}, RR={vitals.get('respiratory_rate','?')}",
        f"炎症指标: WBC={wbc}, CRP={labs.get('CRP','?')}mg/L, PCT={labs.get('PCT','?')}",
    ]
    alerts=list(vitals.get("alerts",[]))
    if temp>=38.5 or temp<=36: alerts.append("⚠ 高热/低体温 — 感染或脓毒症, 立即评估")
    if "脓毒" in dx or (labs.get("lactate") and float(labs.get("lactate",0))>2):
        alerts.append("⚠ 脓毒症/乳酸升高 — SSC 1小时集束化: 血培养×2+广谱抗生素+液体复苏")

    return _agent.clinical_result(
        summary=f"感染科 — 接诊: {dx or '感染待查'}",patient=p,stage="reception",
        findings=findings,recommendations=[
            "脓毒症休克 → 立即SSC集束化治疗",
            "无脓毒症 → 留取培养后经验性抗感染",
        ],alerts=alerts,guidelines=_GUIDELINES[:1])

def bp_exam(**kwargs) -> dict:
    """感染科检查计划 — 病原学+炎症指标+影像."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[
        "病原学: 血培养×2(发热高峰/寒战时) + 痰/尿/粪便培养 + 病灶穿刺/引流物培养",
        "炎症: CRP/PCT/WBC — PCT>0.5支持细菌感染, 指导抗生素疗程",
        "影像: 胸片/CT(肺炎) + 腹部CT/超声(脓肿) + 感染灶定位",
        "特殊: T-SPOT/γ干扰素释放试验(结核), CD4(免疫缺陷), 乙肝/丙肝病毒载量",
    ]
    if "肝" in dx or "病毒" in dx:
        findings.append(f"病毒性肝炎: 乙肝DNA={labs.get('乙肝DNA','?')}, 丙肝RNA={labs.get('丙肝RNA','?')} — 病毒复制评估")
    if labs.get("CD4") is not None:
        findings.append(f"CD4={labs.get('CD4')} — <200/mm³为AIDS期, 机会性感染预防")

    return _agent.clinical_result(
        summary="感染科检查计划",patient=p,stage="exam",
        findings=findings,recommendations=[
            "经验性用药前务必留取培养(否则无法降阶梯)",
            "持续发热>48h → 复查血培养+影像+考虑非感染原因",
        ],guidelines=_GUIDELINES[:1])

def bp_diagnosis(**kwargs) -> dict:
    """感染诊断 — 病原学确认与严重度分层."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[f"主诊断: {dx or '待明确'}"]
    if "肺炎" in dx:
        findings.append("肺炎: 社区/院内分类 + 严重度( CURB-65/PSI) + 病原学(痰培养+尿抗原)")
    if "脓毒" in dx or "败血" in dx:
        findings.append(f"脓毒症: qSOFA/SOFA评分 + 血培养 + 感染源控制 — 乳酸={labs.get('lactate','?')}")
    if "肝" in dx:
        findings.append(f"病毒性肝炎: 乙肝DNA={labs.get('乙肝DNA','?')}, 丙肝RNA={labs.get('丙肝RNA','?')} — 抗病毒指征评估")
    if "结核" in dx:
        findings.append("结核: T-SPOT+痰涂片/培养+胸片 — 影像与病原学结合确诊")

    return _agent.clinical_result(
        summary=f"感染科诊断 — {dx or '待明确'}",patient=p,stage="diagnosis",
        findings=findings,recommendations=[
            "确诊依赖病原学 — 降阶梯基于培养结果",
            "48-72h无效 → 复查培养+影像+扩大鉴别",
        ],guidelines=_GUIDELINES[:1])

def bp_plan(**kwargs) -> dict:
    """抗感染计划 — 经验性/目标性治疗分层."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx=p.get("diagnosis","")

    plan=["抗感染原则: 尽早+足量+疗程适宜(最短有效疗程)"]
    if "肺炎" in dx:
        plan+=["CAP: β内酰胺+大环内酯 或 呼吸喹诺酮, 疗程5天(稳定后)", "HAP/VAP: 覆盖MRSA+铜绿假单胞菌, PCT指导降阶梯"]
    elif "脓毒" in dx or "败血" in dx:
        plan+=["脓毒症: 1小时内广谱抗生素(覆盖GNR+MRSA+真菌风险) + 感染源控制"]
    elif "肝" in dx:
        plan+=["病毒性肝炎: NAs(恩替卡韦/替诺福韦)或DAAs + 肝功能监测"]
    else:
        plan+=["根据培养结果调整目标治疗", "疗程: 血培养阴性后5-7天, 菌血症GNR 7天"]

    return _agent.clinical_result(
        summary=f"抗感染计划 — {dx or '待定'}",patient=p,stage="plan",
        findings=[{"计划":plan}],recommendations=plan,guidelines=_GUIDELINES[:2])

def bp_treatment(**kwargs) -> dict:
    """抗感染治疗执行 — 药物选择与监测."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[]
    if "肺炎" in dx:
        findings.append("经验性: 头孢曲松2g qd + 阿奇霉素0.5g qd (CAP) — 过敏者呼吸喹诺酮")
    if "脓毒" in dx or "败血" in dx:
        findings.append("脓毒症: 哌拉西林他唑巴坦 4.5g q6h 或 美罗培南1g q8h + 万古霉素(覆盖MRSA)")
    if "肝" in dx:
        findings.append(f"抗病毒: 恩替卡韦0.5mg qd — 病毒学应答评估(乙肝DNA={labs.get('乙肝DNA','?')})")
    findings.append("PK/PD: 时间依赖性β内酰胺延长输注; 浓度依赖性喹诺酮qd给药")

    return _agent.clinical_result(
        summary=f"抗感染治疗执行 — {dx or '待定'}",patient=p,stage="treatment",
        findings=findings,recommendations=[
            "监测: PCT下降/CRP下降≥25%(48h) → 降阶梯或停用",
            "肾功能不全者按eGFR调整抗生素剂量",
        ],guidelines=_GUIDELINES[:1])

def bp_followup(**kwargs) -> dict:
    """感染随访 — 疗程/复查/再评估."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")

    plan=[
        "48-72h: 疗效评估(热峰/WBC/CRP/PCT) — 无效则复查培养+影像",
        "疗程: 感染控制后5-7天(菌血症7天/心内膜炎4-6周)",
        "PCT<0.5或下降>80% → 停用抗生素(降阶梯)",
        "出院随访: 2-4周复查炎症指标 + 原发病处理",
    ]
    return _agent.clinical_result(
        summary="感染科随访计划",patient=p,stage="followup",
        findings=[{"随访节点":plan}],recommendations=plan,guidelines=_GUIDELINES[:1])
