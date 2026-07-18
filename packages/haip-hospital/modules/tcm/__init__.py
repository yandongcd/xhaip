"""中医科 — KnowledgeAgent-powered clinical reasoning.

Focus: 中医药辨证论治 — TCM pattern differentiation (八纲/脏腑/气血津液/六经/卫气营血)
GUIDELINES: 国家中医药临床诊疗指南（2022）
Conditions: 内科杂病, 妇科, 儿科, 骨伤, 肿瘤辅助, 未病先防

Real TCM diagnostic systems: 八纲辨证, 脏腑辨证, 气血津液辨证, 六经辨证, 卫气营血辨证.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="tcm", department="中医科")
_GUIDELINES = [
    "国家中医药临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reception(**kwargs) -> dict:
    """接诊与初步评估 — 望闻问切 四诊合参."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "望诊: 面色(青/赤/黄/白/黑) + 舌象(舌质淡白/红绛/瘀斑/胖大/齿痕/裂纹 + 舌苔薄白/黄腻/白厚/剥落)",
        "闻诊: 声音洪亮/低微(气虚) + 气味(口臭=胃热/口甜=脾湿/腥臭=肺痈)",
        "问诊: 十问歌 — 寒热/汗出/头身/二便/饮食/胸腹/七情/耳聋/口渴/经带",
        "切诊: 脉象(浮/沉/迟/数/虚/实/滑/涩/弦/濡/弱/结代/芤) + 腹诊(压痛/痞块/胀满/振水音)",
        "中医体质: 平和质/气虚质/阳虚质/阴虚质/痰湿质/湿热质/血瘀质/气郁质/特禀质",
    ]

    if "虚" in dx or "气血" in dx:
        findings.insert(0, "气血辨证初步: 气虚(神疲乏力+面色白+脉弱) / 血虚(面色苍白+眩晕+爪甲不荣+脉细)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("中医")
    return _agent.clinical_result(
        summary="中医科 — 四诊合参完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["八纲辨证(表里+寒热+虚实+阴阳)", "脏腑辨证(五脏六腑定位)", "中医体质辨识"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """辅助检查 — 舌诊/脉诊 客观化 + 相关理化检查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "舌诊细化: 舌色(淡白/淡红/红/绛/紫) + 舌形(苍老/娇嫩/胖大/瘦薄/点刺/裂纹/齿痕) + 舌苔(薄/厚/腻/腐/剥/少/无/灰黑)",
        "脉诊客观化: 脉象仪/多普勒(脉图波形 h1/h3/h4/h5 参数) — 弦脉(主波高+重搏波前波抬高)/滑脉(主波幅度+重搏波存在)",
        "相关理化检查: 血常规/肝肾功能(中西结合) + 炎症指标(CRP/ESR 中医热毒/湿热) + 免疫(IgE/IgG 过敏体质)",
        "经络测评: 十二经脉原穴/井穴 生物电阻抗/热成像(经络异常能量失衡 = 寒热虚实)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("中医")
    return _agent.clinical_result(
        summary="中医科 — 辅助检查完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["症候量化评分(中医证候积分)", "相关西医检查(排除/共病)", "舌象/脉象记录+照片存档"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊与分型分期 — 辨证体系确定 + 病名+证型."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "八纲辨证: 表里(邪气深浅)+寒热(病性)+虚实(邪正盛衰)+阴阳(总纲) — 定位+定性",
        "脏腑辨证: 心(心悸/失眠/神志)/肝(胁痛/目赤/易怒/筋急)/脾(腹胀/食欲/便溏/出血)/肺(咳/喘/痰/胸痛)/肾(腰酸/耳鸣/生殖/水肿)",
        "气血津液辨证: 气滞(胀满游走性)+血瘀(刺痛固定+舌紫瘀斑瘀点+脉涩)+痰湿(体胖/苔腻/身重)+津亏(口干/燥/苔少)",
        "六经辨证(外感伤寒): 太阳(表证 发热恶寒)/阳明(里热盛 大汗大渴脉洪大)/少阳(半表半里 寒热往来)/太阴(脾虚寒 腹满时痛)/少阴(心肾阳虚 脉微细)/厥阴(寒热交错)",
        "中医病名+证型: 如\"胃痛(脾胃湿热证)\" / \"心悸(心脾两虚证)\" / \"咳嗽(风寒束肺证)\"",
    ]

    if "虚" in dx:
        findings.insert(0, "虚证: 气虚(乏力+脉弱) / 血虚(面白+头晕) / 阴虚(五心烦热+盗汗+脉细数) / 阳虚(畏寒+肢冷+脉沉迟无力)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("中医")
    return _agent.clinical_result(
        summary=f"中医科 — 辨证确诊完成 (S3) | {dx[:30]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["确定治则治法(八法: 汗/吐/下/和/温/清/消/补)", "方药选择(经方/时方/验方/自拟方)", "辨证施治个体化方案"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_plan(**kwargs) -> dict:
    """治疗方案制定 — 中药+针灸+推拿+外治 + 养生."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "中药处方: 君臣佐使配伍原则(君药主攻证/臣药协助/佐药辅治+制约/使药引经) + 剂量(克/剂) + 煎服法(先煎/后下/包煎/烊化/冲服/泡服)",
        "针灸处方: 经络选穴(局部+远端+特定穴五输/原络/俞募/八会/郄) + 针刺手法(提插捻转补泻/呼吸补泻/疾徐补泻/烧山火/透天凉)",
        "针法: 毫针/温针(针上加灸)/电针(疏密波-止痛+连续波-补气)/头针/耳针/腹针/火针(热证+痈肿)",
        "灸法: 温和灸/隔姜灸(虚寒)/隔蒜灸(痈肿)/隔附子饼灸(阳虚重)/雷火神针(实按灸)/温针灸(针上加灸)",
        "推拿: 一指禅/滚法/揉法/按法/扳法/拨法 — 松解筋膜+调整关节(整脊/正骨手法)",
        "养生: 四时养生(春生夏长秋收冬藏) + 饮食(五谷为养+药膳 辨证食疗) + 运动(太极拳/八段锦/五禽戏/气功)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("中医")
    return _agent.clinical_result(
        summary="中医科 — 治疗方案制定完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["中药外治(贴敷/熏洗/溻渍/药浴)", "拔罐/刮痧/耳穴压豆", "中医情志疗法(七情致病与七情防病)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行与监测 — 中药/针灸/推拿/外治."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "中药执行: 煎煮法(急煎30min/慢煎1-2h 矿物/贝壳类先煎30min+芳香后下5min) + 服药时间(空腹/饭后/睡前/发作前1h)",
        "针灸操作: 消毒(穴位碘伏) + 针刺深度(0.5-3寸 依部位/体质) + 留针15-30min + 观察(晕针/滞针/弯针/断针/气胸)",
        "推拿: 介质(凡士林/滑石粉/精油) + 补泻交替 + 治疗量(20-40min/次) — 禁忌(骨折/感染/肿瘤/出血体质/皮肤破损)",
        "中药外治: 贴敷(穴位贴敷三伏/三九贴) + 熏洗(中药蒸汽/药液浸泡 15-20min qd) + 溻渍(药液湿敷)",
        "治疗监测: 中药(肝肾功能 q3m+胃部不适/腹泻/皮疹) + 针灸(针刺感+局部血肿) + 疗程(中药2-4w+ 针灸10-15次/疗程)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("中医")
    return _agent.clinical_result(
        summary="中医科 — 治疗执行与监测完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["中成药(口服+注射) 辨证使用", "不良反应监测(肝/肾 毒性/过敏)", "疗程中辨证调整(3-7d 复诊)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """随访与长期管理 — 证候变化 + 方药调整 + 养生指导."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "证候变化: 舌脉动态跟踪(3-7d 急性/2-4w 慢性) + 症状评分(中医证候积分 TCM-SS) + 证型转化(热转寒/实转虚)",
        "方药调整: 随证加减(证变方变) + 减量(症状控制后 1-2w 复诊减半量->巩固->停药) + 长期调理(丸剂/膏方 冬季进补)",
        "养生指导: 四季调摄(春养肝-疏泄/夏养心-清心/长夏健脾-化湿/秋养肺-润燥/冬养肾-温补) + 饮食有节(五谷为养/药食同源)",
        "治未病: 未病先防(天人相应/正气存内/精神内守) + 既病防变(已病防传变) + 瘥后防复(恢复期防复发)",
    ]

    recommendations = [
        "慢病管理: 中药调理(丸剂/膏方/茶饮 长期) + 针灸保健(足三里/关元/气海/命门 5-10次/疗程/季) + 功法(八段锦/太极拳 每日 30min)",
        "复诊: 急性 3-7d / 慢性 2-4w / 稳定 1-3m",
        "防复发: 避免诱因(寒凉生冷/油腻甜腻/房室不节/情志过极) + 增强体质(运动/睡眠/情绪管理)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("中医")
    return _agent.clinical_result(
        summary="中医科 — 随访与长期管理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
