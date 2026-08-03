"""老年病科 — KnowledgeAgent-powered clinical reasoning.

核心能力:
- Fried衰弱表型评估 (5项)
- Beers标准潜在不适当用药筛查
- MNA-SF简易营养评估
- 跌倒风险评估 (Morse) + 认知筛查 (Mini-Cog)
- 多重用药审查 (≥5种药物)

Guidelines: AGS Beers 2023, Fried Frailty 2001, MNA-SF
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="geriatrics", department="老年病科")
_GUIDELINES = [
    "AGS Beers Criteria 2023",
    "Fried Frailty Phenotype 2001",
    "MNA-SF Mini Nutritional Assessment",
    "中国老年医学学会老年综合评估专家共识",
]
_agent.rule_engine.load_all()


def _error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def assess_frailty(**kwargs) -> dict:
    """Fried衰弱表型5项评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")

    age = p.get("age", 0)
    weight = p.get("weight_kg", 60)
    dx = p.get("diagnosis", "")

    # Simplified Fried frailty (5 phenotype items)
    criteria = []
    score = 0
    # 1. Unintentional weight loss (from diagnosis/context)
    if "消瘦" in dx or "营养不良" in dx or weight < 50:
        criteria.append("体重下降 (>5% in 1yr)")
        score += 1
    # 2. Exhaustion (proxy: age + comorbidities)
    if age >= 80:
        criteria.append("疲乏 (高龄≥80)")
        score += 1
    # 3. Low physical activity (proxy)
    if age >= 75:
        criteria.append("活动减少 (年龄≥75)")
        score += 1
    # 4. Slowness (proxy: age ≥80)
    if age >= 85:
        criteria.append("步速减慢 (年龄≥85)")
        score += 1
    # 5. Weakness (proxy: low weight + age)
    if weight < 45 or (age >= 80 and weight < 50):
        criteria.append("握力减弱 (低体重)")
        score += 1

    level = "健壮 (0/5)" if score == 0 else ("前衰弱" if score <= 2 else f"衰弱 ({score}/5)")
    guides = _agent.search_guidelines("老年综合评估") or _GUIDELINES

    return _agent.clinical_result(
        summary=f"Fried衰弱评估 — {level}",
        patient=p, guidelines=guides[:2],
        findings=[{"Fried评分": f"{score}/5", "衰弱分级": level, "标准": criteria}],
        recommendations=[
            "衰弱→综合老年评估(CGA)+营养+康复干预",
            "前衰弱→运动处方(抗阻训练)+蛋白质补充",
            "健壮→年度随访+预防保健",
        ],
    )


def assess_beers(**kwargs) -> dict:
    """Beers标准潜在不适当用药筛查 (简版)."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")

    age = p.get("age", 0)
    dx = p.get("diagnosis", "")
    # Medications check from diagnosis keywords
    beers_flags = []
    if "失眠" in dx or "焦虑" in dx:
        beers_flags.append("苯二氮䓬类 — Beers 2023: 避免 (跌倒/认知风险)")
    if "糖尿" in dx:
        beers_flags.append("磺脲类长效 — Beers 2023: 避免 (低血糖风险)")
    if "高血压" in dx and age >= 75:
        beers_flags.append("α1阻滞剂 — Beers 2023: 避免 (体位性低血压)")
    if "骨质疏松" in dx or age >= 75:
        beers_flags.append("PPI长期 — Beers 2023: 避免>8周 (骨折/C.diff风险)")

    risk = "无Beers不适当用药" if not beers_flags else f"{len(beers_flags)}种潜在不适当用药"

    return _agent.clinical_result(
        summary=f"Beers用药审查 — {risk}",
        patient=p, guidelines=_GUIDELINES[:1],
        findings=[{"Beers标志": beers_flags or ["未检出潜在不适当用药"]}],
        recommendations=[
            "≥5种药物→进行多重用药审查(Medication Reconciliation)",
            "每次就诊/入院/转科时重新审查用药清单",
        ],
    )


def assess_mna(**kwargs) -> dict:
    """MNA-SF简易营养评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")

    weight = p.get("weight_kg", 0)
    age = p.get("age", 0)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    alb = labs.get("ALB", labs.get("albumin", 35))

    score = 0
    # Food intake decline
    if "营养不良" in dx or weight < 45:
        score += 0  # severe decrease
    else:
        score += 1  # moderate or no decrease
    # Weight loss
    if weight < 50:
        score += 0
    elif weight < 60 and age >= 75:
        score += 1
    else:
        score += 2
    # Mobility
    score += 1 if age >= 80 else 2
    # Acute disease/stress
    score += 1
    # Neuropsychological
    score += 1
    # BMI
    bmi = weight / ((p.get("height_cm", 160) / 100) ** 2) if p.get("height_cm") else 22
    if bmi < 19:
        score += 0
    elif bmi < 21:
        score += 1
    elif bmi < 23:
        score += 2
    else:
        score += 3

    level = "营养不良 (<8)" if score <= 7 else ("有营养风险 (8-11)" if score <= 11 else "营养正常 (≥12)")
    return _agent.clinical_result(
        summary=f"MNA-SF营养评估 — {level} (总分{score}/14)",
        patient=p, guidelines=_GUIDELINES[:2],
        findings=[{"MNA-SF": f"{score}/14", "分级": level, "BMI": f"{bmi:.1f}"}],
        recommendations=[
            "≤11分→全面MNA评估+营养干预(ONS/EN/PN)",
            "≥12分→定期重新筛查(每3-6个月)",
            f"白蛋白{alb}g/L→{'低白蛋白血症, 需营养支持' if alb < 35 else '正常'}",
        ],
    )


def bp_reception(**kwargs) -> dict:
    """老年综合评估(CGA)接诊 — 多维初筛 + 危险信号."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    age = p.get("age", 0)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        f"年龄: {age}岁 — 老年多病共存/多重用药/功能下降风险评估",
        f"生命体征: HR={vitals.get('heart_rate','?')}, BP={vitals.get('bp','?')}, SpO₂={vitals.get('spo2','?')}%",
        f"用药: {labs.get('药物种类', 0)}种药物 (≥5种=多重用药, 需Beers审查)",
        f"跌倒史: {labs.get('跌倒史', '无')} — 跌倒高风险需Morse评估+环境干预",
    ]
    alerts = list(vitals.get("alerts", []))
    if labs.get("MMSE") is not None and int(labs.get("MMSE", 30)) < 24:
        alerts.append(f"⚠ MMSE={labs.get('MMSE')} — 认知障碍, 需痴呆评估流程")
    if age >= 80:
        alerts.append("⚠ 高龄(≥80) — 衰弱/谵妄/跌倒高风险, 慎用致谵妄药物")

    return _agent.clinical_result(
        summary=f"老年病科 — CGA接诊: {dx or '老年综合评估'}", patient=p, stage="reception",
        findings=findings, recommendations=[
            "≥65岁入院 → 系统性CGA(功能/认知/营养/用药/心理)",
            "多重用药(≥5种) → 用药重整(Medication Reconciliation)",
        ],
        alerts=alerts, guidelines=_GUIDELINES[:2])


def bp_exam(**kwargs) -> dict:
    """老年专项检查 — 功能/认知/营养/感官评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs = p.get("lab_results", {})
    age = p.get("age", 0)

    findings = [
        f"认知: MMSE={labs.get('MMSE','未评估')}/30 — <24分需神经心理全套",
        f"营养: MNA-SF + 白蛋白 + BMI (体重={p.get('weight_kg','?')}kg)",
        "跌倒: Morse评分 + 起立-行走测试(TUG) + 药物/视力/足部评估",
        "功能: ADL/IADL + 握力 + 4m步速 (衰弱表型)",
    ]
    if age >= 75:
        findings.append("骨骼: 骨密度(DXA) — 骨质疏松/骨折风险, 75岁+常规筛查")
    if labs.get("药物种类", 0) and int(labs.get("药物种类", 0)) >= 5:
        findings.append("用药: 多重用药清单审查 — Beers 2023标准逐项核对")

    return _agent.clinical_result(
        summary="老年科检查计划 — CGA多维评估", patient=p, stage="exam",
        findings=findings, recommendations=[
            "筛查异常 → 专科深化评估(神经心理/营养科/康复)",
            "跌倒高危 → 防跌倒干预(平衡训练+环境改造+药物精简)",
        ], guidelines=_GUIDELINES[:2])


def bp_diagnosis(**kwargs) -> dict:
    """老年综合征诊断 — 衰弱/认知/营养/用药问题定位."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    weight = p.get("weight_kg", 0)
    age = p.get("age", 0)

    findings = [f"主诊断: {dx or '待明确'}"]
    if "衰弱" in dx:
        findings.append("衰弱诊断: Fried表型评估确认(≥3/5项) — 排除可逆因素(营养/药物/抑郁)")
    if labs.get("MMSE") is not None and int(labs.get("MMSE", 30)) < 24:
        findings.append("认知障碍: MMSE<24 — 需鉴别阿尔茨海默/血管性/路易体/可逆性(甲减/B12/梅毒)")
    if weight < 45 or "营养不良" in dx:
        findings.append("营养不良: 低体重+白蛋白↓ — MNA-SF确诊, 排除吞咽困难/吸收障碍")
    if int(labs.get("药物种类", 0)) >= 5:
        findings.append("多重用药: ≥5种 — Beers审查+STOPP/START标准复核")

    return _agent.clinical_result(
        summary=f"老年科诊断 — {dx or '老年综合征待评估'}", patient=p, stage="diagnosis",
        findings=findings, recommendations=[
            "老年综合征常多病共存 — 采用CGA综合管理而非单病种处理",
            "鉴别可逆性认知/功能下降(药物/谵妄/抑郁/甲状腺)",
        ], guidelines=_GUIDELINES[:2])


def bp_plan(**kwargs) -> dict:
    """综合管理计划 — 老年多维度干预."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    plan = ["目标: 维持功能独立与生活质量 — 以患者意愿为中心"]
    if "衰弱" in dx or (p.get("age", 0) >= 75):
        plan.append("衰弱干预: 抗阻+有氧运动处方 + 蛋白质补充(1.2-1.5g/kg/d)")
    if int(labs.get("药物种类", 0)) >= 5:
        plan.append("用药精简: 停用Beers不适当药物, 每次就诊重新评估获益/风险")
    if labs.get("MMSE") is not None and int(labs.get("MMSE", 30)) < 24:
        plan.append("认知管理: 胆碱酯酶抑制剂/美金刚评估 + 照料者支持 + 安全防护")
    if "骨质疏松" in dx or "骨折" in dx:
        plan.append("骨骼管理: 钙+VitD+抗骨吸收药物 + 防跌倒环境改造")

    return _agent.clinical_result(
        summary=f"老年科管理计划 — {dx or 'CGA综合管理'}", patient=p, stage="plan",
        findings=[{"干预计划": plan}], recommendations=plan, guidelines=_GUIDELINES[:2])


def bp_treatment(**kwargs) -> dict:
    """老年治疗执行 — 谨慎用药原则."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")
    labs = p.get("lab_results", {})
    age = p.get("age", 0)
    dx = p.get("diagnosis", "")

    findings = [
        "用药原则: Start低剂量 → 缓慢加量 (Start low, go slow)",
        f"肾功能: 肌酐={labs.get('Cr','?')} — 按eGFR调整剂量, 避免NSAIDs/二甲双胍(禁忌时)",
        "精神药物: 抗胆碱能药物避免(谵妄/跌倒/认知风险)",
    ]
    if "失眠" in dx or "焦虑" in dx:
        findings.append("苯二氮䓬类避免 — 改用非药物干预+褪黑素/短效非BZD(短期)")
    if "高血压" in dx and age >= 80:
        findings.append("降压目标放宽: SBP 130-150mmHg(80岁+) — 避免过度降压致跌倒")

    return _agent.clinical_result(
        summary=f"老年科治疗执行 — {dx or '综合干预'}", patient=p, stage="treatment",
        findings=findings, recommendations=[
            "每新增药物前: 指征明确? 获益>风险? 有无替代?",
            "出院前药物重整 + 简化方案(依从性)",
        ], guidelines=_GUIDELINES[:1])


def bp_followup(**kwargs) -> dict:
    """老年随访 — 功能/用药/跌倒持续监测."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _error(f"Patient {pid} not found")

    plan = [
        "2-4周: 新药疗效与不良反应评估, 血压/血糖/用药依从性",
        "每3月: 衰弱评估(体重/步速/握力) + 跌倒询问",
        "每6-12月: MMSE认知复评 + ADL功能 + 营养状态(MNA-SF)",
        "每年: 流感/肺炎疫苗接种 + 骨密度复查(骨质疏松者)",
    ]
    return _agent.clinical_result(
        summary="老年科随访计划", patient=p, stage="followup",
        findings=[{"随访节点": plan}], recommendations=plan, guidelines=_GUIDELINES[:2])
