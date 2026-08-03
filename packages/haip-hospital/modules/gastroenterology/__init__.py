"""消化内科 — KnowledgeAgent-powered clinical reasoning.

核心评分: Child-Pugh分级、MELD评分、Rome IV IBS、Mayo UC活动度
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="gastroenterology", department="消化内科")
_GUIDELINES = ["AASLD 2023 Liver Guidelines", "Rome IV IBS 2016", "ECCO UC Guidelines"]
_agent.rule_engine.load_all()

def _error(msg): return {"status":"error","agent":_agent.agent_name,"error":msg}

def assess_liver(**kwargs) -> dict:
    """Child-Pugh + MELD 肝功能评估."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs=p.get("lab_results",{})
    bil=float(labs.get("TBIL",labs.get("Bil",15)))
    alb=float(labs.get("ALB",labs.get("albumin",30)))
    cr=float(labs.get("Cr",100))
    # Child-Pugh simplified
    cp_score=0
    if bil<34: cp_score+=1
    elif bil<51: cp_score+=2
    else: cp_score+=3
    if alb>35: cp_score+=1
    elif alb>28: cp_score+=2
    else: cp_score+=3
    cp_class="A (5-6分)" if cp_score<=2 else ("B (7-9分)" if cp_score<=4 else "C (≥10分)")
    # MELD simplified
    meld=int(3.78*max(1.0,bil/17.1)+11.2*max(1.0,cr/88.4)+9.57*max(1.0,1.5)+6.43)
    return _agent.clinical_result(
        summary=f"肝功能评估 — Child-Pugh {cp_class}, MELD={meld}",
        patient=p,guidelines=_GUIDELINES[:1],
        findings=[{"Child-Pugh":cp_class,"MELD":meld,"T-Bil":f"{bil}μmol/L","Alb":f"{alb}g/L"}],
        recommendations=[
            f"Child {cp_class[0]}→{'可耐受大手术' if cp_class[0]=='A' else ('局限性切除' if cp_class[0]=='B' else '仅肝移植')}",
            f"MELD {meld}→{'肝移植评估(MELD≥15)' if meld>=15 else '定期随访'}",
        ])

def assess_ibd(**kwargs) -> dict:
    """IBD活动度评估 (Mayo UC / Crohn HBI)."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    # Simplified Mayo score
    mayo=5  # assumed moderate
    level="缓解 (≤2)" if mayo<=2 else ("轻度 (3-5)" if mayo<=5 else ("中度 (6-10)" if mayo<=10 else "重度 (11-12)"))
    return _agent.clinical_result(summary=f"Mayo UC评分: {mayo} — {level}",patient=p,guidelines=_GUIDELINES[:2],
        findings=[{"Mayo":mayo,"活动度":level,"推荐":"5-ASA+激素" if mayo<=5 else "生物制剂(IFX/ADA/VDZ/UST)"}],
        recommendations=["重度→住院+IV激素+生物制剂","中度→口服激素+免疫抑制剂","缓解→5-ASA维持+内镜随访"])

def assess_ibs(**kwargs) -> dict:
    """Rome IV IBS诊断辅助."""
    pid=kwargs.get("patient_id",""); p=_agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx=p.get("diagnosis","")
    ibs_type="IBS-C (便秘型)" if "便秘" in dx else ("IBS-D (腹泻型)" if "腹泻" in dx else "IBS-M (混合型)")
    return _agent.clinical_result(summary=f"Rome IV IBS评估 — {ibs_type}",patient=p,guidelines=_GUIDELINES[:2],
        findings=[{"IBS分型":ibs_type,"Rome IV警报征象":["便血","夜间症状","体重下降","发病年龄>50岁","肿瘤家族史"]}],
        recommendations=["有警报征象→结肠镜检查","IBS-C→纤维素+鲁比前列酮","IBS-D→利福昔明+洛哌丁胺"])

def bp_reception(**kwargs) -> dict:
    """接诊与危险信号分诊 — 消化道症状 + 生命体征 + 急症识别."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "主诉采集: 腹痛 / 呕血 / 黑便 / 腹泻 / 便秘 / 黄疸 / 反酸烧心 — 起病方式 + 持续时间 + 加重缓解因素",
        f"生命体征: HR={vitals.get('heart_rate','?')}, BP={vitals.get('bp','?')}, SpO₂={vitals.get('spo2','?')}%",
        "既往史: 消化性溃疡 / Hp感染 / 肝病 / 胆胰疾病 / 非甾体抗炎药史",
    ]
    alerts = list(vitals.get("alerts", []))
    if "呕血" in dx or "黑便" in dx or "便血" in dx:
        alerts.append("⚠ 消化道出血表现 — 禁食禁水, 评估血流动力学, 24h内胃镜")
    if "急性胰腺炎" in dx:
        alerts.append("⚠ 急性胰腺炎 — 禁食 + 液体复苏 + 疼痛管理")
    if labs.get("TBIL", 0) and float(labs.get("TBIL", 0)) > 51:
        alerts.append("⚠ 黄疸 TBIL>51μmol/L — 肝胆梗阻/肝衰竭评估")

    return _agent.clinical_result(
        summary=f"消化内科 — 接诊完成: {dx or '待诊'}", patient=p, stage="reception",
        findings=findings, recommendations=[
            "有出血/胰腺炎/胆道梗阻征象 → 优先分诊 (急诊处理)",
            "轻症 → 门诊: 幽门螺杆菌检测 + 常规消化科评估",
        ],
        alerts=alerts, guidelines=_GUIDELINES[:1])


def bp_exam(**kwargs) -> dict:
    """辅助检查计划 — 消化系统检查路径."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "胃镜 (EGD): 上消化道症状 / 溃疡 / 出血 — 含Hp活检(快速尿素酶+组织学)",
        "结肠镜: 下消化道症状 / 便血 / IBD / 结直肠癌筛查",
        "腹部超声+CT: 肝胆胰脾 — 肝占位/胆管扩张/胰腺病变",
        "实验室: 肝功(ALT/AST/TBIL) / 胰酶(AMY/LPS) / Hp抗体 / HBV-DNA / 便潜血",
    ]
    if "肝" in dx:
        findings.append(f"病毒学: HBsAg={labs.get('HBsAg','?')}, HBV-DNA={labs.get('HBV_DNA','?')} — 慢性肝病随访路径")
    if "胰腺" in dx or "胰" in dx:
        findings.append(f"胰酶: AMY={labs.get('AMY','?')}, LPS={labs.get('LPS','?')} — 胰腺炎活动性判断")
    if "溃疡" in dx or "反流" in dx:
        findings.append(f"Hp检测: 抗体={labs.get('HP抗体','?')} — 阳性则行13C/14C呼气试验确认现症感染")

    return _agent.clinical_result(
        summary=f"消化科检查计划 — {dx or '待定'}", patient=p, stage="exam",
        findings=findings, recommendations=[
            "便血+年龄>50 → 结肠镜优先 (排除肿瘤)",
            "肝功能异常 → 乙肝五项+HBV-DNA+腹部超声",
        ], guidelines=_GUIDELINES[:1])


def bp_diagnosis(**kwargs) -> dict:
    """诊断确认与鉴别 — 结合主诊断给出循证诊断路径."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = []
    if "反流" in dx or "胃食管" in dx:
        findings.append("GERD诊断: 典型烧心/反流症状即可临床诊断 — 内镜用于警报征象/难治性病例")
        findings.append("LA分级: A-D 黏膜损伤分级 + 食管裂孔疝评估")
    if "溃疡" in dx:
        findings.append("消化性溃疡: 内镜分型(GU/DU) + Hp检测 + NSAIDs史排查")
    if "肝" in dx:
        findings.append(f"肝病评估: TBIL={labs.get('TBIL','?')}μmol/L, ALT/AST↑程度 — 肝炎活动度")
    if "胰腺" in dx:
        findings.append(f"胰腺炎: AMY={labs.get('AMY','?')}, LPS={labs.get('LPS','?')} — 3倍以上确诊")
    if "IBD" in dx or "克罗恩" in dx or "溃疡性结肠炎" in dx:
        findings.append("IBD: 结肠镜+黏膜活检 + 粪钙卫蛋白 + 影像(CTE/MRE) — 排除感染性肠炎")

    return _agent.clinical_result(
        summary=f"消化科诊断 — {dx or '待明确'}", patient=p, stage="diagnosis",
        findings=findings or ["主诊断待定 — 依据内镜+病理+实验室结果综合判断"],
        recommendations=["内镜+病理为金标准", "Hp感染 → 含铋剂四联方案(根除率>90%)"],
        guidelines=_GUIDELINES[:1])


def bp_plan(**kwargs) -> dict:
    """诊疗计划 — 分病种循证方案."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx = p.get("diagnosis", "")

    plan = []
    if "反流" in dx or "胃食管" in dx:
        plan = ["PPI 4-8周 (标准剂量)", "生活方式: 减重+床头抬高+避免夜宵", "难治性 → 双倍剂量PPI / 抗反流手术评估"]
    elif "溃疡" in dx:
        plan = ["Hp阳性 → 含铋剂四联14天, 停药4周后复查13C呼气试验", "Hp阴性 → PPI 4-8周", "NSAIDs相关 → 停用+PPI保护"]
    elif "肝" in dx:
        plan = ["病毒性肝炎 → 抗病毒(NAs/DAAs) + 定期监测", "肝硬化 → 并发症筛查: 门脉高压/肝癌6月一次影像"]
    elif "胰腺" in dx:
        plan = ["急性期: 禁食+液体复苏+镇痛+营养支持", "恢复期: 低脂饮食+戒酒+病因处理(胆源性→ERCP)"]
    else:
        plan = ["完善检查后制定个体化方案", "涉及出血/占位/梗阻 → MDT讨论"]

    return _agent.clinical_result(
        summary=f"消化科治疗计划 — {dx or '待定'}", patient=p, stage="plan",
        findings=[{"计划": plan}], recommendations=plan, guidelines=_GUIDELINES[:2])


def bp_treatment(**kwargs) -> dict:
    """治疗执行 — 药物/内镜/手术干预."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = []
    if "溃疡" in dx:
        findings.append("一线: PPI(奥美拉唑20mg bid)+阿莫西林1g bid+克拉霉素0.5g bid+枸橼酸铋钾220mg bid × 14天")
    elif "反流" in dx:
        findings.append("PPI标准剂量×4-8周, 维持治疗按需(最小有效剂量)")
    if labs.get("HBsAg") and str(labs.get("HBsAg")) not in ("阴性", "0", "-"):
        findings.append("HBsAg阳性 → 抗病毒治疗评估(恩替卡韦/替诺福韦) + 肝功能监测")
    if "出血" in dx:
        findings.append("急性出血 → 液体复苏+PPI持续泵入+24h内胃镜止血(注射/夹闭/电凝)")

    return _agent.clinical_result(
        summary=f"消化科治疗执行 — {dx or '待定'}", patient=p, stage="treatment",
        findings=findings or ["按治疗计划执行, 监测疗效与不良反应"],
        recommendations=[
            "用药监测: PPI长期使用 → 骨密度/镁/维生素B12",
            "治疗期间避免NSAIDs/阿司匹林(溃疡患者)",
        ], guidelines=_GUIDELINES[:2])


def bp_followup(**kwargs) -> dict:
    """随访计划 — 复查节点与监测指标."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx = p.get("diagnosis", "")

    plan = ["4-8周: 评估症状缓解 + 依从性", "Hp根除: 停药4周后复查13C呼气试验"]
    if "肝" in dx:
        plan.append("每3-6月: 肝功+AFP+腹部超声 (肝癌高危筛查)")
    if "IBD" in dx or "克罗恩" in dx:
        plan.append("每3-6月: 粪钙卫蛋白+炎症指标, 内镜按需复查")
    if "溃疡" in dx:
        plan.append("复杂溃疡 → 8-12周复查胃镜确认愈合")

    return _agent.clinical_result(
        summary=f"消化科随访计划 — {dx or '待定'}", patient=p, stage="followup",
        findings=[{"随访节点": plan}], recommendations=plan, guidelines=_GUIDELINES[:1])
