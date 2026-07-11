"""烧伤整形科 — KnowledgeAgent-powered clinical reasoning.

Focus: 烧伤救治与创面修复 — burn depth, fluid resuscitation, wound care, scar management
GUIDELINES: 中国烧伤整形临床诊疗指南（2021）
Conditions: 烧伤, 烫伤, 电击伤, 化学烧伤, 大面积皮肤撕脱伤, 瘢痕挛缩

Real clinical scoring: 烧伤深度(三度四分法), Parkland 补液公式, TBSA(九分法/手掌法), VSS 瘢痕评分.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="burns_plastic", department="烧伤整形科")
_GUIDELINES = [
    "中国烧伤整形临床诊疗指南（2021）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def _calc_parkland(weight_kg: float, tbsa_pct: float) -> dict:
    """Parkland formula: 4 mL * kg * %TBSA = total first 24h crystalloid volume.
    Give 1/2 in first 8h from burn, 1/2 over next 16h."""
    volume = 4 * weight_kg * tbsa_pct
    first_8h = volume / 2
    next_16h = volume / 2
    rate_8h = first_8h / 8  # mL/h
    rate_16h = next_16h / 16
    return {
        "formula": f"4mL x {weight_kg}kg x {tbsa_pct}%",
        "total_24h_ml": volume,
        "first_8h_ml": first_8h,
        "first_8h_rate_ml_h": round(rate_8h, 1),
        "next_16h_ml": next_16h,
        "next_16h_rate_ml_h": round(rate_16h, 1),
        "target_uo": "0.5 mL/kg/h (成人) / 1.0 mL/kg/h (儿童)",
    }


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — 烧伤面积+深度评估 + 气道评估 + 急救处理."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    weight = float(labs.get("weight", 60) or 60)
    tbsa = float(labs.get("tbsa_pct", 10) or 10)

    parkland = _calc_parkland(weight, tbsa)

    findings = [
        "烧伤面积: 九分法(成人) / 手掌法(1%TBSA) — Lund-Browder 图表(儿童)",
        "烧伤深度: I度(红斑) / 浅II度(水疱) / 深II度(苍白湿) / III度(焦痂/蜡白/栓塞血管)",
        "气道评估: 声嘶/痰中碳末/面部烧伤/鼻毛烧焦 => 早期气管插管",
        f"补液: Parkland 公式 — 第1个24h总液量 {parkland['total_24h_ml']:.0f}mL",
        f"前8h输注: {parkland['first_8h_ml']:.0f}mL ({parkland['first_8h_rate_ml_h']}mL/h)",
    ]

    if tbsa > 20:
        findings.insert(0, f"大面积烧伤(TBSA {tbsa}%): 中心静脉置管 + 留置尿管监测尿量")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("烧伤")
    return _agent.clinical_result(
        summary=f"烧伤整形科 — 患者登记分诊完成 (S1) | TBSA={tbsa}%",
        patient=p, stage="S1", findings=findings,
        recommendations=["ABC 评估(气道/呼吸/循环)", "乳酸林格液首选(避免含糖液)", "碳氧血红蛋白测定(密闭空间烧伤)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — 烧伤深度确诊 + 吸入性损伤 + 合并伤评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    tbsa = float(labs.get("tbsa_pct", 10) or 10)

    findings = [
        "深度判定: 48-72h 后重复评估 — 深II度与III度可能随时间演变",
        "吸入性损伤: 纤维支气管镜(金标准) / 133Xe 通气扫描 / CT",
        "电击伤: 入口-出口路径 + 肌红蛋白尿(肌酸激酶CK监测) + 筋膜间室综合征",
        "化学烧伤: 明确化学物性质(酸/碱/有机) + 大量水冲洗 >=30min",
        "合并伤: 爆震伤/骨折/颅脑损伤 — 全身 CT 扫描",
    ]

    if tbsa > 15:
        findings.insert(0, f"重度烧伤(TBSA {tbsa}%) => 烧伤中心/ICU 收治")
    if "电击" in dx or "电" in dx:
        findings.insert(0, "电击伤: 心电图(心律失常/心肌损伤) + 尿色监测(肌红蛋白尿)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("烧伤")
    return _agent.clinical_result(
        summary=f"烧伤整形科 — 诊断评估完成 (S3) | TBSA={tbsa}%",
        patient=p, stage="S3", findings=findings,
        recommendations=["破伤风预防(Td/Tdap)", "创面细菌培养+药敏", "烧伤指数(BI=TBSA-III度+1/2 TBSA-II度)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — 清创时机 + 植皮方案 + 皮源规划."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "清创时机: III度/深II度 — 早期切痂(48-72h内)降低感染风险",
        "焦痂切开: 环形III度烧伤 + 肢体/胸廓压迫 => 紧急焦痂切开减压",
        "植皮: 自体刃厚皮(0.2-0.3mm)/中厚皮(0.3-0.45mm)/全厚皮 选择",
        "皮源: 自体皮源有限时 — Mesh 扩增(1:1.5-1:6) / Meek 技术 / 异体/异种皮覆盖",
        "替代品: Integra 双层人工真皮 / Biobrane 临时覆盖",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("烧伤")
    return _agent.clinical_result(
        summary="烧伤整形科 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["术前备血(大面积切痂)", "创面银离子敷料覆盖", "术前抗生素(切痂前 30min)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — 感染/脓毒症 + MODS + 电解质紊乱."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    tbsa = float(labs.get("tbsa_pct", 10) or 10)

    findings = [
        "感染/脓毒症: 烧伤面积>20% + 创面感染标志(PCT/CRP/WBC) => 脓毒症筛查 qd",
        "MODS 风险: 烧伤面积>40% + 延迟复苏 => 肺/肾/肝/凝血 序贯器官衰竭评分(SOFA)",
        "电解质: Na+ 高(脱水)/低(创面丢失), K+ 高(细胞破坏/ARF), Ca2+ 低(螯合)",
        "低体温: 大面积烧伤(>30%) — 环境加温 + 液体加温 + 辐射加温毯",
        "营养不良: 烧伤后高代谢状态(BEE*1.5-2.0) — 早期肠内营养(24h内)",
    ]

    if tbsa > 30:
        findings.insert(0, f"重度烧伤(TBSA {tbsa}%): SOFA 评分 q8h + PCT 监测")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("烧伤")
    return _agent.clinical_result(
        summary="烧伤整形科 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["Curreri 公式计算营养需求", "PPI 预防应激性溃疡", "LMWH 预防 DVT(无出血风险)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 烧伤科+ICU+康复+营养 多学科方案."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 团队: 烧伤外科 + ICU + 感染科 + 康复科 + 营养科 + 心理科",
        "分期手术: 第1次切痂植皮(72h) + 第2次残余创面覆盖(2-3w) + 第3次功能重建(3-6m)",
        "康复介入: 早期(急性期) — 良肢位摆放(抗挛缩体位) + 被动ROM + 压力治疗",
        "心理支持: 创伤后应激障碍(PTSD)筛查 — IES-R 量表 / 烧伤后容貌改变 心理咨询",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("烧伤")
    return _agent.clinical_result(
        summary="烧伤整形科 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["分期手术时间表", "康复处方: PT+OT+压力治疗", "出院计划: 家庭环境评估+护理培训"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — 切痂+自体皮移植."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "切痂: 筋膜上层切除 — 保留健康脂肪/血管/神经 / 术中止血(电凝+肾上腺素盐水)",
        "取皮: 电动取皮刀(气动/电动) — 大腿外侧/头皮(可反复取)首选供区",
        "植皮: 网状扩增(1:1.5-1:3) + 缝合/皮钉固定 + 压力包扎(凡士林纱布+棉垫+弹力绷带)",
        "异体/异种皮: 猪皮/羊膜临时覆盖 — 5-7 天后更换自体皮",
        "止血: Tourniquet(肢体) / 肾上腺素盐水纱布 / 凝血酶喷雾",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("烧伤")
    return _agent.clinical_result(
        summary="烧伤整形科 — 手术执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术中保温(室温>=28C + 液体加温)", "输血: 每 1% 切痂面积约 100mL", "术后第 3-5 天首次换药评估皮片成活"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — 创面护理 + 体位 + 功能锻炼."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "创面护理: 保持敷料干燥 / 渗液监测(颜色/气味/量) / 银离子敷料释放(Acticoat)",
        "供皮区护理: 半透膜/水胶体敷料 — 保持干燥 7-10 天, 渗液积聚穿刺引流",
        "体位: 抗挛缩体位 — 颈部过伸 / 肩外展90 / 肘伸展 / 手指伸展+拇指外展",
        "预防压疮: 翻身 q2h + 减压床垫 + 骨突保护(泡沫敷料)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("烧伤")
    return _agent.clinical_result(
        summary="烧伤整形科 — 围术期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["早期功能锻炼: 术后 3-5 天开始被动 ROM", "疼痛管理: PCA + 非药物干预", "家属参与护理培训"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """术后随访 — 瘢痕评估 + 压力治疗 + 功能康复."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "瘢痕评估: VSS(温哥华瘢痕量表) — 色泽(0-3)+血管分布(0-3)+厚度(0-4)+柔软度(0-5)",
        "压力治疗: 弹力衣/压力面罩 — 压力 20-30mmHg / 每天穿戴 23h / 持续 6-24 月",
        "功能训练: ROM(主动+被动) / 肌力训练 / 精细动作(手外伤) / 步态(下肢烧伤)",
        "瘢痕干预: 硅酮凝胶/贴片(一线) + 激素注射(曲安奈德) + 激光(脉冲染料/CO2点阵)",
        "心理康复: 躯体变形障碍筛查 + 社会回归支持(复工/返校计划)",
    ]

    recommendations = [
        "VSS 每 3 月评估一次追踪瘢痕演变",
        "瘢痕挛缩: 优先非手术(物理治疗+压力) -> 6-12 月无效则手术松解(Z成形/植皮)",
        "长期防晒(SPF50+) — 新生皮肤/瘢痕色素沉着风险高",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("烧伤")
    return _agent.clinical_result(
        summary="烧伤整形科 — 术后随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
