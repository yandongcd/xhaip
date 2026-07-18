"""健康管理科 — KnowledgeAgent-powered clinical reasoning.

Focus: 健康体检与慢病筛查 — health checkup, chronic disease screening, risk assessment, lifestyle intervention
GUIDELINES: 中国健康管理临床指南（2022）, 老年髋部骨折诊疗与管理指南（2022年版）
Conditions: 健康体检, 四高筛查(高血压/高血糖/高血脂/高尿酸), 肿瘤早筛, 心血管风险评估

Real clinical tools: Framingham Risk Score, China-PAR, FINDRISC diabetes, health risk appraisal (HRA).
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="health_management", department="健康管理科")
_GUIDELINES = [
    "中国健康管理临床指南（2022）",
    "老年髋部骨折诊疗与管理指南（2022年版）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reception(**kwargs) -> dict:
    """接诊评估 — 基本信息 + 既往史 + 家族史 + 生活习惯 + 体检项目设定."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    age = int(p.get("age", 45) or 45)

    findings = [
        f"基本信息: 年龄={age}, 性别={p.get('gender','?')} — 体检套餐推荐(基础/深度/专项)",
        "既往史: 慢性病(高血压/糖尿病/冠心病/卒中/肿瘤) + 手术史 + 过敏史",
        "家族史: 直系亲属(父母/兄弟姐妹/子女) 肿瘤/心血管/糖尿病/遗传病",
        "生活习惯: 吸烟(包年)/饮酒(克/周)/饮食结构/运动(频次+强度)/睡眠(时长+质量)",
        f"生命体征: BP={labs.get('SBP','?')}/{labs.get('DBP','?')}mmHg, BMI={labs.get('BMI','?')}",
    ]

    if age >= 40:
        findings.insert(0, "40 岁以上: 启动四高(血压/血糖/血脂/尿酸)+肿瘤早筛+心血管风险评估")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("健康管理")
    return _agent.clinical_result(
        summary=f"健康管理科 — 接诊评估完成 (S1) | 年龄={age}",
        patient=p, stage="S1", findings=findings,
        recommendations=["健康风险评估(HRA 问卷)", "个性化体检方案制定(年龄/性别/风险分层)", "生活方式问卷调查"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """检查检验 — 体格检查 + 化验 + 影像 + 功能检查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "体格检查: 身高/体重/BMI/腰围(男<85/女<80cm) + BP + 脉搏 + 视力/听力(初筛)",
        "化验: 血常规+肝肾功能+血脂四项(TC/LDL/HDL/TG)+空腹血糖+HbA1c+尿酸+TSH(甲状腺)",
        "肿瘤标志物(年龄/性别/风险): CEA / AFP(肝癌 乙肝携带者) / CA19-9 / CA125(卵巢 女性) / PSA(前列腺 男性>50y)",
        "影像: 胸部低剂量CT(LDCT 50-80y+30包年吸烟史=>NLST) / 腹部超声(肝/胆/胰/脾/肾) / 乳腺超声/钼靶(女性>=40y)",
        "功能检查: 心电图(ECG) + 肺功能(spirometry 吸烟/COPD风险) + 骨密度(DXA >=65y女性/>=70y男性)",
        "接种疫苗评估: 流感/肺炎/带状疱疹(>=50y)/HPV(9-45y女性+男性)/乙肝(未免疫者) + Tdap(每10y)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("健康管理")
    return _agent.clinical_result(
        summary="健康管理科 — 检查检验完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["宫颈癌: HPV+TCT(21-65y 女性 q3-5y)", "结肠癌: 结肠镜(45-75y q10y)/FIT(每年)", "乳腺: 钼靶(40-74y q1-2y)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断确认 — 异常指标解读 + 慢病风险 + 肿瘤风险 + 心血管风险."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    age = int(p.get("age", 45) or 45)
    sbp = float(labs.get("SBP", 130) or 130)
    tc = float(labs.get("TC", 5.0) or 5.0)
    hdl = float(labs.get("HDL", 1.2) or 1.2)

    findings = [
        "异常指标汇总: 重点关注(高血压/高血糖/高血脂/高尿酸/肝功能/肾功能/贫血/肿瘤标志物/影像异常)",
        "慢病风险: 四高(血压>=140/90->高血压 / HbA1c>=6.5%->糖尿病 / LDL>=3.4->高胆固醇 / UA>=420->高尿酸)",
        "心血管风险评估: Framingham 10年ASCVD风险(TC/HDL/SBP/吸烟/糖尿病/年龄/性别) — 低(<5%)/边界(5-7.4%)/中(7.5-19.9%)/高(>=20%)",
        f"风险因素: SBP={sbp}mmHg / TC={tc}mmol/L / HDL={hdl}mmol/L / {'吸烟' if labs.get('smoking','N')=='Y' else '不吸烟'} / {'糖尿病' if labs.get('DM','N')=='Y' else '血糖正常'}",
        "肿瘤风险: 肺癌(LDCT 30包年)/结直肠癌(结肠镜)/乳腺癌(钼靶)/宫颈癌(HPV)/前列腺(PSA>=4ng/mL)/肝癌(乙肝+超声)",
        "骨质疏松风险: 65y+/70y+ DXA T值<= -2.5=>骨质疏松 / FRAX 骨折风险(10y 主要骨质疏松性骨折概率)",
    ]

    if sbp >= 140 or float(labs.get("DBP", 80) or 80) >= 90:
        findings.insert(0, f"高血压评估: SBP={sbp} >=140 -> 高血压分级(1级 140-159=>轻度 / 2级 160-179=>中度 / 3级>=180=>重度)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("健康管理")
    return _agent.clinical_result(
        summary=f"健康管理科 — 诊断确认完成 (S3) | 年龄={age}",
        patient=p, stage="S3", findings=findings,
        recommendations=["ASCVD 10年风险分层 + 目标管理", "China-PAR 风险评估(中国人群体)", "糖尿病风险评分(FINDRISC)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """健康干预 — 生活方式 + 营养指导 + 运动处方 + 疫苗接种."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "生活方式干预: 戒烟(简短干预5A Ask/Advise/Assess/Assist/Arrange) + 限酒(男<25g/d 女<15g) + 睡眠(7-9h)",
        "营养指导: 低盐(<5g/d 高血压) + 低脂(饱和脂肪<7%热量 LDL优化) + 低GI(糖尿病) + 增加膳食纤维(25-30g/d) + DASH/地中海饮食模式",
        "运动处方(FITT-VP原则): 频率(>=5d/wk有氧+2-3d/wk力量) + 强度(中等 RPE 12-13/60-70%HRR) + 时间(30-60min/d有氧+20-30min力量)",
        "疫苗接种(成人免疫): 流感(每年>=6m) + 肺炎(PPSV23 65y+&高危+PCV13 序贯) + 带状疱疹(RZV Shingrix 50y+ 2剂) + Tdap(每10y+每次妊) + HPV(<=26y 3剂)",
        "心理健康: 压力管理(正念/Mindfulness + 深呼吸 4-7-8法+渐进性肌肉放松) + 睡眠卫生(固定作息+暗光+卧室凉爽+电子设备睡前1h停用)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("健康管理")
    return _agent.clinical_result(
        summary="健康管理科 — 健康干预完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["健康管理目标(BP<140/90/LDL<2.6/HbA1<7%/BMI<24)", "自我监测(BP/血糖/体重每周) + 记录", "健康教育(慢性病管理+药物依从)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """随访管理 — 定期复查 + 风险控制 + 健康教育 + 慢病管理."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "定期复查: 体检(每年 基础) + 四高复查(高血压 q1-3m / 糖尿病 HbA1c q3m 血糖+血脂+肾功能 / 高血脂 LDL q6-12m)",
        "风险控制: 血压达标<140/90(一般) / 糖尿病 HbA1c<7% + 无低血糖 + 血脂 LDL<2.6(中危)/<1.8(高危 已有CVD)/<1.4(极高危)",
        "健康教育: 慢病自我管理教育(DSME/S 糖尿病) + 药物依从性(高血压 40-60%非依从) + 危险信号识别(胸痛/F-A-S-T卒中一侧面瘫/肢体无力/言语不清 急打120)",
        "肿瘤早筛复检: 结直肠(FIT 每年/结肠镜 10y) 乳腺(钼靶 q1-2y) 宫颈(HPV+细胞学 q5y) 肺(LDCT 每年 30包年) 前列腺(PSA q1-2y >50)",
    ]

    recommendations = [
        "健康档案: 个人电子健康记录(EHR) 年度更新 + 风险再评估",
        "达标目标: BP<130/80(糖尿病患者) / LDL<1.8(极高危) / HbA1c<7%",
        "老年评估: 跌倒风险(Timed Up-and-Go/30秒坐站) + 认知(MMSE/MoCA) + 营养(MNA-SF) + 多重用药(Beers标准)",
        "健康促进: 每年制定健康管理计划(饮食+运动+戒烟+限酒+睡眠)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("健康管理")
    return _agent.clinical_result(
        summary="健康管理科 — 随访管理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
