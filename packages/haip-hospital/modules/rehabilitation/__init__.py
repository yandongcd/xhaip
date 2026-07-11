"""康复医学科 — KnowledgeAgent-powered clinical reasoning.

Focus: 综合康复评估与治疗 — physical/occupational/speech therapy, ICF framework
GUIDELINES: 中国康复医学临床诊疗指南（2022）, APTA 老年髋部骨折物理治疗管理临床实践指南
Conditions: 脑卒中康复, 骨科术后康复, 脊髓损伤康复, 心肺康复, 儿科康复

Real clinical tools: Barthel Index/FIM, MMT (manual muscle testing), ROM, ICF classification, Berg Balance.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="rehabilitation", department="康复医学科")
_GUIDELINES = [
    "中国康复医学临床诊疗指南（2022）",
    "APTA 老年髋部骨折物理治疗管理临床实践指南",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reception(**kwargs) -> dict:
    """接诊评估 — 功能评估 + ADL 评分 + 疼痛 + 既往康复史."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    barthel = int(labs.get("Barthel", 60) or 60)
    findings = [
        f"ADL(Barthel Index): {barthel}/100 — {'重度依赖(<40)' if barthel<40 else '中度依赖(41-60)' if barthel<60 else '轻度依赖(61-99)' if barthel<100 else '完全独立(100)'}",
        "功能评估: 移动能力(床-椅/行走) + 平衡(坐/站) + 耐力(6分钟步行 6MWT)",
        f"疼痛评估: VAS/NRS(0-10) — {'重度(>=7)' if labs.get('VAS',0)>=7 else '中度(4-6)' if float(labs.get('VAS',0) or 0)>=4 else '轻度(1-3)' if float(labs.get('VAS',0) or 0)>=1 else '无痛(0)'}",
        "既往康复史: 以前康复经历/手术/合并症(心脏病/糖尿病/认知障碍)",
        "社会/环境: 家庭支持/建筑障碍(楼梯/扶手/卫生间) / 职业/学习需求",
    ]

    if "卒中" in dx or "stroke" in dx.lower():
        findings.insert(0, f"脑卒中后康复: Barthel={barthel} — NIHSS + 运动功能(Brunnstrom/Fugl-Meyer) + 言语/吞咽评估")
    if "骨折" in dx or "关节" in dx:
        findings.insert(0, "骨科康复: ROM+MMT+负重状态(术后 TBW/TTWB/PWB/WBAT) + 风险评估(跌倒/血栓/感染)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("康复")
    return _agent.clinical_result(
        summary=f"康复医学科 — 接诊评估完成 (S1) | Barthel={barthel}",
        patient=p, stage="S1", findings=findings,
        recommendations=["ICF 综合功能评估", "物理治疗(PT)+作业治疗(OT)+言语治疗(ST)联合评估", "康复目标设定(SMART原则)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """检查检验 — MMT + ROM + 平衡 + 步态 + 专项量表."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "肌力测试(MMT 0-5级): 关键肌群(上肢/下肢/躯干) — 0无收缩-5正常力 / 偏瘫-截瘫-四肢瘫定位",
        "关节活动度(ROM): 主动AROM+被动PROM — 关节挛缩/软组织缩短/痉挛(改良Ashworth 0-4分级)",
        "平衡评估: Berg 平衡量表(0-56 分) + TUG(起立-行走)测试 + 单腿站立 / MiniBESTest(动态平衡)",
        "步态分析: 视觉步态评估 + 10m步行测试(10MWT) + 6分钟步行(6MWT 耐力) + 功能性步行分类(FAC 0-5)",
        "专项量表: Fugl-Meyer(偏瘫运动)/NIHSS(卒中)/ASIA(脊髓损伤)/FIM(功能独立)/MoCA(认知)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("康复")
    return _agent.clinical_result(
        summary="康复医学科 — 检查检验完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["康复辅助具评估(轮椅/助行器/矫形器/假肢)", "环境评估(家居/工作/社区)", "辅助设备(站立架/平行杠/悬吊)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断确认 — ICF 分类 + 康复潜力 + 预后评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "ICF 分类(功能/残疾/健康): 损伤(身体功能/结构) + 活动限制 + 参与受限 + 环境/个人因素",
        "康复潜力: 年龄 + 既往功能水平 + 合并症 + 认知(MoCA>=26) + 主动性(康复动机指数 RMI) + 家庭支持",
        "预后评估: 功能恢复轨迹(神经可塑性时间窗3-6m 脑卒中)/恢复曲线(平台期)/预测返回社区可能性",
        "并发症风险: 跌倒(Morse 量表 0-125) + 压疮(Braden 6-23) + 深静脉血栓 + 误吸(饮水试验洼田)",
    ]

    if "卒中" in dx:
        findings.insert(0, "脑卒中: 运动恢复 Brunnstrom 分期(I=弛缓-VI=接近正常) + Fugl-Meyer 评分(上肢 66/下肢 34) => 康复潜力中/高")
    if "脊髓" in dx:
        findings.insert(0, "脊髓损伤: ASIA 分级(A=完全 B-D=不完全感觉/运动保留 E=正常) + 损伤平面(NLI)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("康复")
    return _agent.clinical_result(
        summary=f"康复医学科 — 诊断确认完成 (S3) | {dx[:20]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["ICF 核心组合(Core Set) 制定", "个体化康复目标(SMART)", "康复计划: 强度/频率/内容/预计疗程(4-6w)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行 — 物理治疗 + 作业治疗 + 言语治疗 + 康复辅具."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "物理治疗(PT): 运动疗法(ROM+肌力增强+耐力训练) + 神经发育技术(NDT/Bobath) + 平衡/步态训练 + 跌倒预防",
        "作业治疗(OT): ADL 训练(穿衣/进食/洗漱/如厕) + IADL(购物/烹饪/理财) + 手功能(精细动作/握力/协调) + 认知训练",
        "言语治疗(ST): 失语症(Schuell 刺激疗法/旋律音调MIT) + 构音障碍(口面肌训练) + 吞咽障碍(姿势/代偿/口腔-咽腔训练)",
        "物理因子: 电疗(TENS/NMES/FES) + 热/冷疗 + 超声 + 冲击波(ESWT 肌腱病) + 激光(LLLT)",
        "康复辅具: 矫形器(AFO/KAFO) + 假肢(上肢/下肢) + 助行器(手杖/腋杖/轮式助行器/轮椅) + 环境改造(扶手/斜坡/增宽门)",
    ]

    if "卒中" in dx:
        findings.insert(0, "脑卒中康复: 早期 24h 内开始(生命体征稳定) + 强度(>3h/d PT/OT/ST) + 任务导向训练 + CIMT(限制健侧-强化患侧 偏瘫)")
    if "骨折" in dx or "关节" in dx:
        findings.insert(0, "骨科康复: 保护(支具/免负重) + 早期 ROM(被动->主动) + 渐进性力量训练 + 平衡=proprioception 训练")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("康复")
    return _agent.clinical_result(
        summary="康复医学科 — 治疗执行完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["PT qd 45-60min + OT qd 30-45min + ST(需要时) qd 30min", "训练记录(治疗量/反应/进展)", "再评估(每2w 或每 10次)",
        ],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """随访管理 — 功能恢复 + 社会参与 + 生活质量 + 重返工作."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "功能恢复: Barthel/FIM 改善 + ROM/MMT 进步 + 行走能力(FAC/6MWT) + 平衡(Berg>=45 低跌倒风险)",
        "社会参与: ICF 参与量表(RPS) + 社区活动(购物/交通/社交) + 职业评估(FCE 功能能力评估) => 重返工作/学习",
        "生活质量: SF-36/SIP(疾病影响程度) / EQ-5D(欧洲五维) + 心理(焦虑/抑郁 PHQ-9/GAD-7)",
        "居家康复: 家庭锻炼计划(HEP 每周 3-5 次) + 卒中二级预防(ASA+降压+降脂+降糖+房颤抗凝)",
    ]

    recommendations = [
        "出院后: 门诊 PT/OT 每周 1-2 次(≥3-6m) + HEP 居家训练",
        "社区康复: 社区卫生站 + 远程康复(电话/视频/APP) + 日间康复",
        "评估周期: 每 1-3m 再评估(Barthel/FIM/步行 10MWT)",
        "社会支持: 残疾证/工作场所调整/无障碍交通/家庭护理培训",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("康复")
    return _agent.clinical_result(
        summary="康复医学科 — 随访管理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
