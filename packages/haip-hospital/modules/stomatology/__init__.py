"""口腔科 — KnowledgeAgent-powered clinical reasoning.

Focus: 口腔疾病诊疗 — caries, periodontitis, oral surgery, implant, oral cancer
GUIDELINES: 中国口腔科临床诊疗指南（2022）
Conditions: 龋病, 牙周炎, 牙髓炎, 智齿, 种植牙, 口腔癌

Real clinical concepts: DMFT/DMFS caries index, periodontitis staging I-IV, pulp vitality tests, CBCT planning.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="stomatology", department="口腔科")
_GUIDELINES = [
    "中国口腔科临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def bp_screening(**kwargs) -> dict:
    """筛查与初诊 — 口腔全面检查 + 龋风险评估 + 牙周筛查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "口腔全面检查: 牙体(龋洞/充填/隐裂) + 牙周(牙龈出血/牙周袋/附着丧失) + 黏膜(溃疡/白斑/红斑)",
        "龋风险评估: 菌斑指数(PI) + 唾液流速/缓冲力 + 氟暴露 + 饮食(糖频率)",
        "牙周筛查: CPI 社区牙周指数(0-4) / BPE 基本牙周检查(0-4*) + 探诊出血(BOP)",
        f"生命体征: {'异常 ' + str(len(vitals.get('alerts', []))) + ' 项' if vitals.get('alerts') else '正常'}",
    ]

    if "龋" in dx or "caries" in dx.lower():
        findings.insert(0, "龋病筛查: DMFT/DMFS 指数 + ICDAS 分级(0-6)")
    if "牙周" in dx or "periodont" in dx.lower():
        findings.insert(0, "牙周病筛查: 全口探诊 + 附着丧失记录 + 根分叉病变")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("口腔")
    return _agent.clinical_result(
        summary="口腔科 — 筛查与初诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["全口根尖片(初筛) / 全景片(OPG)", "龋风险评估问卷", "口腔卫生宣教"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """专科检查 — 影像 + 牙髓活力 + 牙周 + CBCT."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "X 线片: 根尖片(龋深/根尖病变 1-2牙) / 咬翼片(邻面龋) / 全景片(OPG 全口腔概览)",
        "CBCT(锥形束 CT): 种植评估(骨量/骨密度) / 阻生牙(智齿距下牙槽神经) / 根折/额外根管",
        "牙髓活力: 温度测试(冷/热)/电活力测试(EPT) — 不可复性牙髓炎=>冷痛持续>15s",
        "牙周评估: 探诊深度(PPD>5mm)/临床附着丧失(CAL)/根分叉病变(I/II/III/IV度)/牙齿松动度",
    ]

    if "种植" in dx:
        findings.insert(0, "种植 CBCT: 骨高度/宽度/密度 + 重要结构(下牙槽神经/上颌窦/邻牙根间距)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("口腔")
    return _agent.clinical_result(
        summary="口腔科 — 专科检查完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["CBCT(种植/复杂根管/阻生牙)", "牙周图表(六点探诊)", "口内扫描(iTero/TRIOS)数字化"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊定级 — 龋病分级 + 牙周炎分度 + 牙髓状态."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "龋病分级: ICDAS 0-6(0健康/1-2釉质/3-4牙本质浅层/5-6深层或侵犯牙髓)",
        "牙周炎分期: I期(轻度<2mm附着丧失)/II期(中度2-4mm)/III期(重度>=5mm+牙缺失<=4颗)/IV期(同上+>=5颗缺失)",
        "牙周炎分级: A级(慢进展<0.25/年)/B级(中 0.25-1.0)/C级(快>1.0)",
        "牙髓状态: 可复性牙髓炎/不可复性/急性化脓性/牙髓坏死/根尖周炎(急性/慢性)",
        "口腔癌筛查: 唇/舌(边缘)/口底/颊黏膜/腭/牙龈 可疑病变(溃疡>2w/白斑/红斑/肿块) => 活检",
    ]

    if "牙周" in dx:
        findings.insert(0, "牙周炎分期: 全口牙周探诊(PPD+CAL+BOP) => Stage/Grade 确定")
    if "牙髓" in dx or "根管" in dx:
        findings.insert(0, "牙髓诊断: 冷刺激+EPT => 不可复性牙髓炎 => 根管治疗(RCT) 适应症")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("口腔")
    return _agent.clinical_result(
        summary=f"口腔科 — 确诊定级完成 (S3) | {dx[:20]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["数字化工作流程(CAD/CAM)", "正畸-修复-种植联合治疗方案"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗操作 — 充填/根管/牙周/拔牙/修复/种植."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "充填(补牙): 树脂(直接) — 去腐 => 酸蚀(37%磷酸) => 粘接(第六/七代) => 分层充填 + 光固化(40s)",
        "根管治疗(RCT): 根管预备(镍钛锉) + 冲洗(次氯酸钠+EDTA超声波) + 充填(牙胶尖+AH Plus) => 冠部修复",
        "牙周治疗: 龈上洁治 + 龈下刮治(SRP 分区4次) => 再评估(6w) + 必要时牙周手术(翻瓣/再生)",
        "拔牙: 常规钳拔 / 外科(切开去骨+分根) — 禁忌(放射治疗区/双膦酸盐类MRONJ风险)",
        "种植: 一期(植入 3-5月骨结合) => 二期(愈合基台) => 修复(取模+戴冠) — 初始稳定性>35Ncm",
    ]

    if "抗生素" not in dx:
        findings.append("抗生素预防: 仅推荐感染性心内膜炎高危(人工瓣膜/心内膜炎史/紫绀先心) / 免疫功能低下")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("口腔")
    return _agent.clinical_result(
        summary="口腔科 — 治疗操作完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["术后镇痛(NSAIDs/对乙酰氨基酚)", "口腔卫生维护(软毛牙刷/氯己定漱口)", "术后饮食(流质/半流/软食 24-48h)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """定期复查 — 口腔卫生 + 修复体 + 牙周维护."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "口腔卫生: 菌斑检出率 < 20% / 改良出血指数(mSBI) < 10% / 探诊出血(BOP)恢复",
        "修复体维护: 充填体边缘密合/染色/磨损 / 冠/桥(松动/崩瓷/继发龋) — 每 6-12m 检查",
        "牙周维护: SPT(支持性牙周治疗) 每 3-6m(视风险) — 口腔卫生再指导+龈上/下洁治",
        "种植维护: 每 6-12m 复查(种植体周围黏膜炎/种植体周围炎 — 探诊深度+出血+边缘骨吸收)",
        "口腔癌筛查(高危: 吸烟+饮酒): 每年黏膜检查 — 可疑病变(持续>2w) => 活检",
    ]

    recommendations = [
        "低龋风险: 每 12-18m 复诊 / 高龋风险: 每 6m 复诊 + 氟保护漆",
        "牙周维护: SPT 每 3m(重度/快速进展) => 每 6m(中度) => 每 12m(轻度稳定)",
        "种植: 每 6m 第 1 年 => 每 12m 长期 + 种植专用牙线/水线",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("口腔")
    return _agent.clinical_result(
        summary="口腔科 — 定期复查完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
