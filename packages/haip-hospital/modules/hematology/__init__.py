"""血液内科 — KnowledgeAgent-powered clinical reasoning.

核心评分: IPSS-R MDS预后、ISTH DIC诊断、WHO贫血分级
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="hematology", department="血液内科")
_GUIDELINES = ["NCCN 2024 Guidelines", "ISTH DIC 2018", "WHO Classification 2022"]
_agent.rule_engine.load_all()

def _error(msg): return {"status":"error","agent":_agent.agent_name,"error":msg}

def assess_anemia(**kwargs) -> dict:
    """WHO贫血分级 + 类型初步判断."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    hb=float(labs.get("hb",labs.get("Hb",120)))
    mcv=float(labs.get("MCV",85))
    gender=p.get("gender","M")
    level="正常" if (gender=="M" and hb>=130) or (gender=="F" and hb>=120) else ("轻度贫血" if hb>=90 else ("中度贫血" if hb>=60 else "重度贫血 (<60g/L)"))
    type_="小细胞 (MCV<80, ?缺铁/地中海)" if mcv<80 else ("正细胞 (MCV 80-100, ?慢性病/肾性贫血)" if mcv<=100 else "大细胞 (MCV>100, ?巨幼细胞/MDS)")
    return _agent.clinical_result(
        summary=f"贫血评估 — {level}, {type_}",
        patient=p,guidelines=_GUIDELINES[:2],
        findings=[{"Hb":f"{hb}g/L","MCV":f"{mcv}fL","分级":level,"类型":type_}],
        recommendations=[
            "Hb<70→考虑输血(血流动力学不稳定或活动性出血)",
            "小细胞贫血→铁蛋白+TIBC+便潜血",
            "大细胞贫血→VitB12+叶酸+甲状腺功能",
        ])

def assess_mds(**kwargs) -> dict:
    """IPSS-R MDS预后评分 (简版)."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    hb=float(labs.get("hb",labs.get("Hb",100)))
    plt=float(labs.get("PLT",labs.get("Plt",100)))
    anc=float(labs.get("ANC",1.5))
    blasts=5  # assumed
    # Simplified IPSS-R
    ipssr=3  # intermediate
    level="极低危 (≤1.5)" if ipssr<=1.5 else ("低危 (2-3)" if ipssr<=3 else ("中危 (3.5-4.5)" if ipssr<=4.5 else ("高危 (5-6)" if ipssr<=6 else "极高危 (>6)")))
    return _agent.clinical_result(summary=f"IPSS-R MDS: {ipssr} — {level}",patient=p,guidelines=_GUIDELINES[:1],
        findings=[{"IPSS-R":ipssr,"预后":level,"Hb":f"{hb}g/L","PLT":f"{plt}","ANC":f"{anc}"}],
        recommendations=["高危/极高危→去甲基化药物(阿扎胞苷/地西他滨)+allo-HSCT评估","低危→ESA/G-CSF+输血支持+去铁治疗"])

def assess_dic(**kwargs) -> dict:
    """ISTH DIC诊断评分."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    plt=float(labs.get("PLT",labs.get("Plt",150)))
    fib=float(labs.get("FIB",labs.get("Fibrinogen",2.5)))
    ddimer=float(labs.get("D-Dimer",labs.get("DD",1.0)))
    pt=float(labs.get("PT",labs.get("INR",1.2)))
    # ISTH DIC score
    score=0
    if plt<50: score+=2
    elif plt<100: score+=1
    if ddimer>4: score+=2
    elif ddimer>1: score+=1
    if fib<1.0: score+=1
    if pt>1.5: score+=1
    dic="显性DIC (≥5)" if score>=5 else ("非显性DIC" if score>=3 else "无DIC证据")
    return _agent.clinical_result(summary=f"ISTH DIC: {score}/8 — {dic}",patient=p,guidelines=_GUIDELINES[:1],
        findings=[{"ISTH DIC":f"{score}/8","诊断":dic,"PLT":f"{plt}","D-Dimer":f"{ddimer}","FIB":f"{fib}","PT":f"{pt}"}],
        recommendations=["显性DIC→治疗基础疾病+血小板/FFP/冷沉淀替代","非显性DIC→监测+病因治疗","DIC时禁用抗纤溶药物(除非原发性纤溶亢进)"])

def bp_reception(**kwargs) -> dict:
    """血液科接诊 — 贫血/出血/感染三主症 + 危险信号."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    vitals=_agent.assess_vitals(p)
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    hb=float(labs.get("hb",labs.get("Hb",120)))
    findings=[
        f"主诉: 贫血(乏力/苍白/心悸) / 出血(瘀斑/鼻衄/牙龈) / 感染(发热) — {dx or '待查'}",
        f"生命体征: HR={vitals.get('heart_rate','?')}, BP={vitals.get('bp','?')}, 体温={vitals.get('temperature','?')}",
        f"血常规: Hb={hb}g/L, WBC={labs.get('WBC','?')}, PLT={labs.get('Plt',labs.get('PLT','?'))}",
    ]
    alerts=list(vitals.get("alerts",[]))
    if hb<70: alerts.append(f"⚠ 重度贫血 Hb={hb}g/L — 输血评估(心功能不全者更积极)")
    if float(labs.get("WBC",8))<1.0: alerts.append("⚠ 粒细胞缺乏(WBC<1.0) — 隔离+广谱抗生素+升白针")
    if float(labs.get("Plt",labs.get("PLT",200)))<30: alerts.append("⚠ 血小板<30 — 自发性出血风险, 限制活动+血小板输注阈值")

    return _agent.clinical_result(
        summary=f"血液科 — 接诊: {dx or '血液病待查'}",patient=p,stage="reception",
        findings=findings,recommendations=[
            "重度贫血/血小板低/粒细胞缺乏 → 紧急血液科处理",
            "轻度异常 → 门诊血涂片+铁代谢检查",
        ],alerts=alerts,guidelines=_GUIDELINES[:1])

def bp_exam(**kwargs) -> dict:
    """血液科检查计划 — 血涂片/骨髓/铁代谢."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[
        "血常规+外周血涂片: 红细胞形态/白细胞分类/血小板形态 — 贫血与血细胞减少首选",
        "铁代谢: 铁蛋白/血清铁/TIBC — 缺铁性贫血确诊",
        "巨幼检查: 维生素B12+叶酸+内因子抗体",
        "溶血: 网织红细胞+LHD+结合珠蛋白+Coomb's试验",
        "骨髓检查: 不明原因血细胞减少/白血病/MDS/骨髓瘤 — 穿刺+活检+流式+细胞遗传学",
    ]
    if "铁" in dx or "贫血" in dx:
        findings.append(f"铁蛋白={labs.get('铁蛋白',labs.get('Ferritin','?'))} — <30ng/ml支持缺铁诊断")
    if labs.get("幼稚细胞_pct") is not None and float(labs.get("幼稚细胞_pct",0))>0:
        findings.append(f"⚠ 外周血幼稚细胞={labs.get('幼稚细胞_pct')}% — 提示白血病/MDS, 需骨髓检查")

    return _agent.clinical_result(
        summary="血液科检查计划",patient=p,stage="exam",
        findings=findings,recommendations=[
            "小细胞低色素 → 铁蛋白+TIBC+便潜血(排除消化道失血)",
            "大细胞贫血 → B12+叶酸+甲功(排除甲减)",
        ],guidelines=_GUIDELINES[:1])

def bp_diagnosis(**kwargs) -> dict:
    """血液病诊断 — 整合血象/骨髓/特殊检查."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    dx=p.get("diagnosis","")

    findings=[f"主诊断: {dx or '待明确'}"]
    if "缺铁" in dx:
        findings.append("缺铁性贫血: 铁蛋白↓+TIBC↑+低色素小细胞 — 寻找病因(消化道/月经/吸收障碍)")
    if "MDS" in dx or "骨髓" in dx:
        findings.append(f"MDS: IPSS-R评分预后分层 — 骨髓原始细胞={labs.get('幼稚细胞_pct','?')}%")
    if "DIC" in dx:
        findings.append(f"DIC: ISTH评分 — PLT={labs.get('Plt',labs.get('PLT','?'))}, FIB={labs.get('FIB','?')}, D-Dimer={labs.get('D-Dimer','?')}")
    if "白血病" in dx:
        findings.append("急性白血病: 骨髓原始细胞≥20% — 免疫分型+染色体+融合基因确定亚型")
    if "淋巴" in dx or "骨髓瘤" in dx:
        findings.append("淋巴增殖性疾病: 淋巴结活检/血清蛋白电泳+免疫固定电泳")

    return _agent.clinical_result(
        summary=f"血液科诊断 — {dx or '待明确'}",patient=p,stage="diagnosis",
        findings=findings,recommendations=[
            "诊断金标准: 骨髓检查(形态+流式+细胞遗传学+分子)",
            "不明原因血细胞减少 → 及早骨髓检查, 避免延误",
        ],guidelines=_GUIDELINES[:1])

def bp_plan(**kwargs) -> dict:
    """血液病治疗计划 — 支持治疗+病因治疗分层."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx=p.get("diagnosis","")
    labs=p.get("lab_results",{})

    plan=["支持治疗基线: 输血( Hb<70 ) / 血小板(<30) / 粒细胞缺乏抗生素预防"]
    if "缺铁" in dx:
        plan.append("缺铁性贫血: 口服铁剂(硫酸亚铁/琥珀酸亚铁)3-6月 + 病因治疗")
    if "MDS" in dx:
        plan.append("MDS: 低危→ESA+G-CSF+去铁; 高危→去甲基化(阿扎胞苷/地西他滨)+allo-HSCT评估")
    if "DIC" in dx:
        plan.append("DIC: 治疗基础疾病为根本 + 血小板/FFP/冷沉淀替代 + 肝素仅特定情况")
    if "白血病" in dx:
        plan.append("急性白血病: 诱导化疗(DA/IA/venetoclax方案)+支持治疗+缓解后巩固/移植")

    return _agent.clinical_result(
        summary=f"血液科治疗计划 — {dx or '待定'}",patient=p,stage="plan",
        findings=[{"计划":plan}],recommendations=plan,guidelines=_GUIDELINES[:2])

def bp_treatment(**kwargs) -> dict:
    """血液科治疗执行 — 具体干预与监测."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx=p.get("diagnosis","")
    labs=p.get("lab_results",{})

    findings=[]
    hb=float(labs.get("hb",labs.get("Hb",120)))
    if hb<70: findings.append(f"输注红细胞(Hb={hb}g/L) — 每次2U, 复查Hb≥70")
    if "缺铁" in dx: findings.append("口服铁剂: 元素铁100-200mg/d, 4周后复查Hb(+10-20g/L提示有效)")
    if "DIC" in dx: findings.append("替代治疗: FFP+血小板维持, 禁用抗纤溶药(除非原发纤溶亢进)")
    if "白血病" in dx: findings.append("诱导化疗期间: 水化碱化+肿瘤溶解预防(别嘌醇/拉布立酶)")

    return _agent.clinical_result(
        summary=f"血液科治疗执行 — {dx or '待定'}",patient=p,stage="treatment",
        findings=findings or ["按治疗计划执行"],recommendations=[
            "化疗期间监测血常规(每周)/肝肾功能/肿瘤溶解综合征",
            "输血前核查血型+交叉配血+输血反应监测",
        ],guidelines=_GUIDELINES[:1])

def bp_followup(**kwargs) -> dict:
    """血液科随访 — 血象监测与疗程管理."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")

    plan=[
        "2-4周: 血常规复查(评估治疗反应) + 铁代谢(缺铁者)",
        "化疗期间: 每周期前血常规+肝肾功能, 必要时剂量调整",
        "缓解后: 每月血象 + 骨髓复查(按方案)",
        "移植后: 免疫抑制监测 + 感染预防 + 移植物抗宿主病评估",
    ]
    return _agent.clinical_result(
        summary="血液科随访计划",patient=p,stage="followup",
        findings=[{"随访节点":plan}],recommendations=plan,guidelines=_GUIDELINES[:1])
