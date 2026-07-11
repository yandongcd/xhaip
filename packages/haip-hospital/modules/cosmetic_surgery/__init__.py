"""整形美容科 — KnowledgeAgent-powered clinical reasoning.

Focus: 美容整形外科 — facial rejuvenation, breast augmentation, liposuction, injectables
GUIDELINES: 中国整形美容临床诊疗指南（2022）
Conditions: 面部年轻化, 乳房整形, 脂肪移植, 微创注射(肉毒素/填充剂), 瘢痕修复

Real clinical concepts: ptosis grading, Baker breast capsule classification, vascular occlusion emergency.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="cosmetic_surgery", department="整形美容科")
_GUIDELINES = [
    "中国整形美容临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — 美学评估 + 心理筛查 + 禁忌症排查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "美学需求评估: 面部年轻化 / 乳房整形 / 体型雕塑 / 微创注射",
        "心理筛查: 体象障碍(BDD)筛查 — Yale-Brown 强迫量表改良版",
        "既往史: 瘢痕体质 / 自身免疫病 / 糖尿病 / 凝血障碍",
        "药物史: 抗凝药(阿司匹林/华法林)停用 >= 7 天",
        "禁忌症: 妊娠/哺乳期/活动性感染/未控制的慢性病",
    ]

    if "面部" in dx or "乳房" in dx:
        findings.insert(0, f"美容评估: {dx[:30]}")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("整形美容")
    return _agent.clinical_result(
        summary="整形美容科 — 患者登记分诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["术前照相(正/侧/45/90度)", "心理评估问卷", "实名制就医+知情同意"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — 面部老化评级 + 乳房分型 + 局部美学缺陷."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "面部老化: Glogau 分级(I-IV) / Fitzpatrick 皮肤分型(I-VI)",
        "上睑松弛: 轻度(<1mm遮盖)/中度(1-2mm)/重度(>2mm遮盖瞳孔)",
        "乳房评估: 下垂分度(Regnault 轻/中/重) / 不对称 / 胸廓畸形",
        "鼻部: 鼻尖突出度 / 鼻背高度 / 鼻翼宽度 / 鼻小柱-上唇角",
        "脂肪分布: BMI + 皮下脂肪厚度(超声) + 皮肤弹性",
    ]

    if "乳房" in dx:
        findings.insert(0, f"乳房评估: Baker 分型 + 乳房下垂分度")
    if "面部" in dx:
        findings.insert(0, "面部年轻化评估: 上面部(额纹/眉间纹) + 中面部(法令纹/苹果肌) + 下面部(木偶纹/下颌缘)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("整形美容")
    return _agent.clinical_result(
        summary=f"整形美容科 — 诊断评估完成 (S3) | {dx[:30]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["3D 扫描/影像采集", "皮肤检测仪(VISIA)分析", "个性化美学方案设计"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — 术式选择 + 材料准备 + 标记设计."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "术式选择: 线雕(PDO/PLLA/PCL) / 光电(CO2/IPL/射频/超声刀) / 填充(HA/胶原蛋白/自体脂肪)",
        "乳房术式: 假体隆乳(腋下/乳晕/下皱襞切口) / 脂肪移植隆乳 / 乳房悬吊/缩小",
        "肉毒素剂量计算: 眉间纹 20U / 鱼尾纹 24U(双侧) / 额纹 10-20U — 保妥适/衡力选择",
        "填充剂选择: 交联HA(乔雅登/瑞蓝) — G'值匹配不同层次 — 浅层用小分子/深层用大分子",
        "术前标记: 坐位/立位标记 — 切口线/剥离范围/填充区域网格",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("整形美容")
    return _agent.clinical_result(
        summary="整形美容科 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["签署知情同意(含并发症)", "抗生素预防(假体植入)", "停用活血化瘀药 14 天"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — 血管栓塞/感染/假体并发症/麻醉风险."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "血管栓塞(填充剂最严重并发症): 鼻背/眉间/鼻唇沟高危区 — 地图样紫癜/剧烈疼痛 => 立即透明质酸酶注射",
        "感染风险: 假体植入后感染率 1-2% — 金黄色葡萄球菌/表皮葡萄球菌最常见",
        "假体包膜挛缩: Baker I-IV 级 — I-II 无需处理, III-IV 需手术松解/更换",
        "血肿/血清肿: 术后 24h 内发生 — 引流/加压包扎",
        "深静脉血栓/肺栓塞: 大面积吸脂>5L — Caprini 评分 + LMWH 预防",
    ]

    if "填充" in dx or "注射" in dx:
        findings.insert(0, "填充剂注射: 配备透明质酸酶(1500U)急救包 + 热敷/硝酸甘油贴备用")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("整形美容")
    return _agent.clinical_result(
        summary="整形美容科 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["血管栓塞应急流程演练", "术前凝血功能+血常规", "抗生素皮试(青霉素/头孢)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 多学科美学方案 + 心理评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 团队: 整形外科医师 + 皮肤科医师 + 麻醉医师 + 心理咨询师",
        "美学方案: 分层设计 — 骨膜层(支撑) / SMAS层(提升) / 皮下层(填充) / 真皮层(肤质)",
        "综合方案: 手术+微创联合 — 上面部(肉毒素) + 中面部(填充/线雕) + 下面部(吸脂/拉皮)",
        "心理评估: 不合理期望识别 — 期望术后生活/职业/人际关系根本改变 => 手术禁忌",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("整形美容")
    return _agent.clinical_result(
        summary="整形美容科 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["阶段化方案: 先轮廓后细节, 间隔 >=3 个月", "术后模拟(3D Vectra) 确认效果", "心理评估通过后方可手术"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — 严格无菌 + 分层操作 + 即刻效果评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "麻醉: 局麻(利多卡因+肾上腺素) / MAC(镇静+局麻) / 全麻(大面积/长时间手术)",
        "肉毒素注射: 标记注射点 + 垂直肌腹进针 + 剂量按部位精确分配",
        "填充剂: 钝针(23-25G)优先/锐针辅助 — 回抽试验阴性 + 缓慢推注 + 立即按压止血",
        "假体植入: 严格无菌(NuSurg/引流水) + 双平面(胸大肌下)优化上极轮廓",
        "即刻评估: 坐位/立位检查对称性 + 触摸平整度 + 活动时动态外观",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("整形美容")
    return _agent.clinical_result(
        summary="整形美容科 — 手术/操作执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术中照片记录", "标本(如有)送病理", "术后即刻冰敷 20min q2h * 24h"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — 冰敷/压迫 + 姿势管理 + 并发症预警."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "冰敷护理: 术后 48h 间歇冰敷(20min q2h) — 防冻伤(毛巾包裹)",
        "体位管理: 面部手术—抬高床头 30°/ 隆胸—半卧位 / 吸脂—弹力衣 24h 穿",
        "引流管: 记录引流量, <30mL/24h 拔除 / 弹力绷带加压 5-7 天",
        "并发症预警: 血管栓塞=>突发剧痛+紫癜=>立即通知医师; 血肿=>进行性肿胀+疼痛",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("整形美容")
    return _agent.clinical_result(
        summary="整形美容科 — 围术期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术后 7 天拆线(面部) / 10-14 天(躯干)", "弹力衣/头套持续 1-3 月", "术后 1 月禁剧烈运动"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """术后随访 — 恢复过程 + 并发症 + 满意度."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "恢复过程: 肿胀消退(1-2 周) / 形态稳定(1-3 月) / 最终效果(6-12 月)",
        "并发症: 不对称 => 观察 6 月后考虑修复; 包膜挛缩 => Baker III-IV 手术干预",
        "满意度: Likert 5 级量表 + 愿意再次选择/推荐他人评估",
        "二次修复: 填充剂溶解(透明质酸酶) / 肉毒素效果消退(3-6 月) / 假体更换(10-15 年)",
    ]

    recommendations = [
        "术后 1w/1m/3m/6m/1y 定期随访",
        "填充剂: 每 6-18 月补充; 肉毒素: 每 3-6 月补充",
        "长期防晒: SPF50+ PA+++ 每日 — 预防色素沉着+光老化",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("整形美容")
    return _agent.clinical_result(
        summary="整形美容科 — 术后随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
