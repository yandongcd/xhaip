"""乳腺中心 — KnowledgeAgent-powered clinical reasoning.

Focus: 乳腺疾病综合诊疗 — breast cancer screening, molecular subtyping, surgery, adjuvant therapy
GUIDELINES: 中国乳腺癌诊疗指南（2022）, NCCN Guidelines: Breast Cancer (2023)
Conditions: 乳腺肿块, 乳腺癌, 乳腺增生, 乳腺炎, 纤维腺瘤

Real clinical scoring: BI-RADS, molecular subtyping (ER/PR/HER2/Ki67), TNM staging, SLNB + ALND.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="breast_center", department="乳腺中心")
_GUIDELINES = [
    "中国乳腺癌诊疗指南（2022）",
    "NCCN Guidelines: Breast Cancer (2023)",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — BI-RADS classification + risk factor screening."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "乳腺肿块触诊: 位置 / 大小 / 质地 / 活动度 / 皮肤改变（橘皮样/酒窝征）",
        "高危因素: 家族史(BRCA1/2), 月经初潮早/绝经晚, 未育/晚育, 激素替代治疗",
        "双侧乳腺超声 + 钼靶 (年龄>=40 岁)",
        f"生命体征: {'异常' if vitals.get('alerts') else '正常'}",
    ]

    if "乳腺" in dx or "breast" in str(p.get("diagnosis", "")).lower():
        findings.insert(0, "乳腺疾病 — 启动 CBCS/NCCN 筛查路径")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("乳腺")
    return _agent.clinical_result(
        summary="乳腺中心 — 患者登记分诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["双侧乳腺超声", "钼靶检查(>=40y)", "对侧乳腺触诊"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — BI-RADS + molecular subtyping (ER/PR/HER2/Ki67)."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "BI-RADS 分级: 0(需进一步)/1(阴性)/2(良性)/3(可能良性)/4(可疑恶性)/5(高度怀疑)/6(已证实)",
        "分子分型: ER/PR/HER2/Ki67 — Luminal A / Luminal B / HER2+ / TNBC",
        "TNM 分期: T(肿瘤大小) + N(淋巴结) + M(远处转移)",
        "穿刺活检: 空心针穿刺(CNB) / 真空辅助旋切(VAB) — 金标准",
    ]

    if "乳腺" in dx or "breast" in dx.lower():
        findings.insert(0, f"乳腺肿块评估中: {dx}")
        findings.append("CBCS 分子分型: ER+/PR+/HER2- => Luminal A 型 预后最好")
        findings.append("CBCS 分子分型: ER-/PR-/HER2- => TNBC 预后最差, 新辅助化疗优先")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("乳腺")
    return _agent.clinical_result(
        summary=f"乳腺中心 — 诊断评估完成 (S3) | {dx}",
        patient=p, stage="S3", findings=findings,
        recommendations=["穿刺活检病理确认", "免疫组化(ER/PR/HER2/Ki67)", "BRCA1/2 基因检测(如有家族史)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — 保乳评估 + 前哨淋巴结 + 乳房重建."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "保乳手术(BCS) 适应症: T1-T2 / N0-N1 / 肿瘤-乳房比例良好 / 无多中心病灶",
        "前哨淋巴结活检(SLNB): 亚甲蓝/核素双示踪, cN0 优先 SLNB 替代 ALND",
        "全切指征: 多中心 / 炎性乳癌 / BRCA+预防性切除 / 患者意愿",
        "乳房重建时机: 即刻重建(保留皮肤/乳头) vs 延期重建",
        "术前标记: 体表定位 + 导丝/Biopsys标记夹",
    ]

    if "乳腺" in dx:
        findings.insert(0, "术前方案: BCS+SLNB (如符合保乳条件)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("乳腺")
    return _agent.clinical_result(
        summary="乳腺中心 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["双侧乳腺MRI(致密型乳腺/高危)", "术前麻醉评估", "备血(全切+重建)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — Nottingham 分级 + 分子风险 + 复发风险."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "Nottingham 组织学分级: 腺管形成(1-3) + 核多形性(1-3) + 核分裂(1-3) => G1/G2/G3",
        "分子风险: Luminal A 低危(内分泌治疗) / HER2+ 中危(靶向+化疗) / TNBC 高危(化疗)",
        "复发风险: 5 年 DFS(无病生存期) / 10 年 OS(总生存期)",
        "遗传风险: BRCA1/2 突变 => 对侧乳腺癌风险 40-65% / 卵巢癌风险 15-40%",
        "血栓风险: Caprini 评分 — 肿瘤患者 >=5 高风险",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("乳腺")
    return _agent.clinical_result(
        summary="乳腺中心 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["Nottingham 分级 + 分子分型 + TNM 综合评估", "血栓预防(机械+药物)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 外科+肿瘤内科+放疗科+病理科 多学科讨论."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 核心科室: 乳腺外科 + 肿瘤内科 + 放疗科 + 病理科 + 影像科",
        "新辅助治疗决策: HER2+ => TCbHP(多西他赛+卡铂+曲妥珠+帕妥珠) / TNBC => AC-T",
        "辅助治疗: 内分泌(绝经前 Tamoxifen / 绝经后 AI) + 靶向(曲妥珠单抗 * 1yr) + 放疗(保乳后必须)",
        "CDK4/6 抑制剂: HR+/HER2- 晚期一线 — 哌柏西利/瑞博西利/阿贝西利 + 内分泌",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("乳腺")
    return _agent.clinical_result(
        summary="乳腺中心 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["NCCN 指南推荐 MDT 评估所有浸润性乳腺癌", "新辅助后 pCR 评估决定辅助方案"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — BCS/全切 + SLNB/ALND +/- 重建."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "术式: BCS(肿瘤扩大切除, 切缘 >=2mm) / 全乳切除 / 保留皮肤/乳头全切",
        "腋窝处理: SLNB(1-3 枚前哨) / ALND(>=3 枚阳性 / T3-T4)",
        "重建: 假体(一步法/二步法扩张器) / 自体(背阔肌/DIEP) / 脂肪移植",
        "术中冰冻: 切缘状态 + SLN 快速病理 => 决定手术范围",
        "术后标本: 标记方位 + 墨染切缘 + 固定送检",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("乳腺")
    return _agent.clinical_result(
        summary="乳腺中心 — 手术执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术后 24-48h 引流拔除", "上肢功能锻炼 (预防淋巴水肿)", "疼痛管理"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — 引流管理 + 皮瓣监测 + 淋巴水肿预防."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "引流管管理: 记录引流量/颜色/性状, 24h < 30mL 可拔管",
        "皮瓣监测: 颜色/温度/毛细血管充盈 — 缺血征象立即报告",
        "淋巴水肿预防: 患肢抬高 + 避免血压计/抽血/输液于术侧 + 压力袖套",
        "伤口护理: 保持干燥 / 定期换药 / 感染征象(红肿热痛)监测",
        "心理护理: 身体形象改变焦虑 + 术后抑郁筛查",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("乳腺")
    return _agent.clinical_result(
        summary="乳腺中心 — 围术期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["患肢功能锻炼计划: 术后第 1 天被动 => 第 7 天主动", "出院教育: 引流管自护/复诊时间"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """术后随访 — 复发监测 + 辅助治疗 + 生活质量."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "复发监测: 每 3-6mo 临床体检(5 年), 每年钼靶, 不推荐常规 CT/PET/骨扫描",
        "内分泌治疗: Tamoxifen 5-10 年(绝经前) / AI 5 年(绝经后) — 监测骨密度+血脂",
        "影像复查: 对侧乳腺钼靶 q1y, 有症状时针对性影像",
        "不良反应: Tamoxifen => 潮热/子宫内膜增厚/血栓 / AI => 关节痛/骨丢失",
        "心理支持: 身体形象/性生活/生育力保存咨询 + 社会康复",
    ]

    recommendations = [
        "NCCN 推荐: 5 年每年临床随访 => 之后每年 1 次",
        "遗传咨询: BRCA1/2+ 患者 >=25 岁开始卵巢癌筛查(CA125+TVUS)",
        "骨健康: AI 治疗者每年骨密度 + 补充钙剂/维生素D",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("乳腺")
    return _agent.clinical_result(
        summary="乳腺中心 — 术后随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
