"""惠侨医疗中心 — KnowledgeAgent-powered clinical reasoning.

Focus: 国际医疗与特需服务 — JCI standards, cross-cultural communication, VIP services, overseas referral
GUIDELINES: 惠侨医疗中心临床指南（2022）
Conditions: 国际患者, 特需医疗, 跨文化诊疗, 海外转诊

Real clinical concepts: JCI IPSG (6 goals), informed consent (i18n), cultural assessment, concierge medicine.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="huigiao", department="惠侨医疗中心")
_GUIDELINES = [
    "惠侨医疗中心临床指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def bp_reception(**kwargs) -> dict:
    """接诊评估 — 国际患者注册 + 语言服务 + 保险核实 + 医疗记录翻译."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "国际患者: 国籍/母语/签证/护照 — 需要语言翻译? (英语/日语/韩语/法语/阿拉伯语等)",
        "保险核实: 国际医疗保险(Travel/Expat/Corporate) + 预授权(preauthorization) + 自费担保/押金",
        "医疗记录: 获取来源国病历(翻译+认证 公证/海牙Apostille) + 既往史/过敏史/用药史/手术史",
        "文化评估: 宗教信仰(饮食禁忌/输血拒绝如耶和华见证人/临终关怀偏好) + 文化禁忌(体格检查/隐私/性别偏好)",
        "JCI IPSG: 患者身份识别(双重标识:姓名+出生日期/病历号) — 普通话/英语/来源国语言 三语姓名",
    ]

    if "国际" in dx or "overseas" in dx.lower():
        findings.insert(0, "国际患者注册: 惠侨国际医疗中心 — 多语种服务+VIP通道")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("惠侨")
    return _agent.clinical_result(
        summary="惠侨医疗中心 — 接诊评估完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["优先安排翻译员(现场/视频/电话)", "国际患者信息录入(多语种 EHR)", "接待: VIP休息室+专人陪同"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """检查检验 — VIP 通道 + 检查协调 + 翻译陪同 + 隐私保护."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "VIP 通道: 优先预约+快速检查(影像/实验室/内镜) + 独立候检区 + 专人陪同(检查衔接)",
        "检查协调: 整合多科室检查时间(同一天 减少等待) + 国际患者优先服务(长距离旅行患者)",
        "翻译陪同: 检查前说明(目的/过程/风险 来源国语言) + 知情同意(翻译后签署) + 检查中实时翻译(如 内镜/介入)",
        "隐私: VIP 单间 + 个人数据保护(中国《个人信息保护法》+ GDPR(欧洲患者)/HIPAA(美国患者))",
        "标本: 国际运送(如有需要 — 干冰/液氮保存+出口许可) + 远程病理(数字扫描传输)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("惠侨")
    return _agent.clinical_result(
        summary="惠侨医疗中心 — 检查检验完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["VIP 检查套餐(国际体检)", "报告(中文+英文 双语)", "远程会诊(送检查结果回来源国专家)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断确认 — MDT 组织 + 国际专家 + 双语诊疗方案."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 组织: 首席医师(中/英 双语) + 专科医师 + 来源国远程专家(视频会诊) + 翻译员 + 患者/家属",
        "国际专家: 来源国(美国/欧洲/日本/韩国等)对应领域专家 + 远程会诊平台(Zoom/Teams/专用医疗平台)",
        "诊疗方案: 双语(中文+英语)文档 — 诊断+分期/分级+治疗方案(国际指南 NCCN/ESC/KDIGO 等)",
        "第二诊疗意见: 如有需要可安排 — 国际权威医院(Mayo Clinic/MD Anderson/Johns Hopkins 等)远程会诊",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("惠侨")
    return _agent.clinical_result(
        summary="惠侨医疗中心 — 诊断确认完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["MDT 记录(中英文 会议纪要+决策)", "治疗方案双文(中文+英文)", "患者知情同意(来源国语言翻译版)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行 — 住院安排 + 手术绿色通道 + 康复计划 + 国际药房."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "住院安排: VIP 单人间/套房 + 家属陪护房 + 国际饮食(西餐/日式/清真/素食/过敏定制) + 卫星电视/网络",
        "手术绿色通道: 优先手术排程 + 国际顶级主刀医师(可安排) + 手术室(国际标准 JCI认证) + 麻醉(英文术前评估)",
        "康复计划: 物理治疗/作业治疗/言语治疗(英语/中英双语) + 国际康复师(可安排) + 出院计划(回国后期护理衔接)",
        "国际药房: 进口药品(中国未注册/临床试验药 特殊使用申请) + 药物核对(来源国药品 相互作用+中文说明翻译)",
        "JCI IPSG 关键: 准确患者识别(双标识) / 有效沟通(口头+书面医嘱 复述式Read-back) / 高警讯药物管理 / 正确手术(部位标记+Timeout术前暂停) / 医疗相关感染预防 / 跌倒预防",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("惠侨")
    return _agent.clinical_result(
        summary="惠侨医疗中心 — 治疗执行完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["JCI 6大国际患者安全目标(IPSG) 100%执行", "每日医患沟通(中英文 病情+治疗方案 更新)", "患者满意度调查(HCAHPS/定制)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """随访管理 — 随访协调 + 远程复诊 + 国际转运 + 医疗记录转发."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "随访协调: 回国前(医疗记录+影像 电子版+纸版) / 回国后(远程复诊 q1-3m或按需) + 随访计划(中英文) + 来源国医生协作",
        "远程复诊: 视频会诊平台 + 翻译陪同 + 电子病历更新 + 药物调整 + 检验/影像(来源国本地)远程判读",
        "国际转运: 医疗护送(商务舱担架/空中救护 固定翼医疗专机) + 医疗签证/通关 + 国际 SOS/保险公司 协调",
        "医疗记录转发: 出院小结(中英双语) + 手术记录/操作记录 + 病理报告 + 影像(CD/DVD/云端PACS链接)+ 药物清单(中英文)",
    ]

    recommendations = [
        "惠侨国际随访计划: 每周(术后1m) => 每月(3m) => 每 3m(长期)",
        "远程医疗平台: 惠侨国际远程会诊中心(24/7)",
        "国际保险: 直接结算(免现金流) + 治疗费用预授权更新",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("惠侨")
    return _agent.clinical_result(
        summary="惠侨医疗中心 — 随访管理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
