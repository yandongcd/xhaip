"""EndoInsight v2.0 — 消化内镜智能解析: Paris/Forrest/JNET分型 + 术后管理 + 风险评估 + 患者宣教.

Guidelines: ESGE 2022, JGES 2020, 中国消化内镜诊疗指南 (2023)
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="endo-insight", department="消化内科")
_GUIDELINES = [
    "中国消化内镜诊疗相关肠道准备指南 (2023)",
    "ESGE 欧洲消化内镜学会指南 (2022)",
    "JGES 日本消化内镜学会指南 (2020)",
    "中国早期胃癌筛查流程专家共识 (2023)",
    "中国结直肠癌早诊早治专家共识 (2023)",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ Endoscopic Classification Systems ═══════

_PARIS_CLASSIFICATION = {
    "0-I": "隆起型病变 (I型)",
    "0-Ip": "有蒂型息肉",
    "0-Is": "广基型/无蒂隆起",
    "0-IIa": "表浅隆起型",
    "0-IIb": "平坦型",
    "0-IIc": "表浅凹陷型",
    "0-III": "凹陷型/溃疡型",
}

_FORREST_CLASSIFICATION = {
    "Ia": {"grade": "高危", "rebleed": "55-90%", "action": "内镜下止血治疗 (注射/APC/止血夹/热凝)"},
    "Ib": {"grade": "高危", "rebleed": "55-90%", "action": "内镜下止血治疗 (冲洗确认活动性出血)"},
    "IIa": {"grade": "高危", "rebleed": "40-50%", "action": "内镜下止血治疗 (可见血管)"},
    "IIb": {"grade": "中危", "rebleed": "20-30%", "action": "附着血凝块 — 冲洗后评估, IIa者止血"},
    "IIc": {"grade": "低危", "rebleed": "5-10%", "action": "平坦黑斑 — 保守治疗"},
    "III": {"grade": "低危", "rebleed": "<5%", "action": "清洁基底 — 可早期出院"},
}

_JNET_CLASSIFICATION = {
    "1": {"type": "增生性息肉/SSL", "vessel": "不可见", "surface": "规则的深色/白点", "strategy": "无需治疗或内镜切除"},
    "2A": {"type": "低级别腺瘤", "vessel": "规则的网状", "surface": "规则的管状/分枝状", "strategy": "内镜切除(EMR/息肉切除)"},
    "2B": {"type": "高级别腺瘤/浅表SM癌", "vessel": "不规则的网状", "surface": "不规则的绒毛/管状", "strategy": "整块切除(ESD/en-bloc EMR)"},
    "3": {"type": "深部SM浸润癌", "vessel": "不规则/中断的粗血管", "surface": "无结构区域", "strategy": "外科手术"},
}

# Post-procedure diet stages
_DIET_PROGRESSION = {
    "diagnostic": {"stage": "诊断性", "0-2h": "禁食水", "2-6h": "饮清水(无呛咳)", "6-24h": "温凉流质/半流质",
                   "24h+": "软食/普通饮食", "warning": "观察有无腹痛/黑便/呕血"},
    "biopsy": {"stage": "活检", "0-2h": "禁食水", "2-6h": "饮清水", "6-24h": "温凉流质",
               "24-48h": "半流质→软食", "warning": "避免粗糙/过热饮食, 停抗血小板药1-3天"},
    "polypectomy": {"stage": "息肉切除", "0-24h": "禁食水/流质", "24-48h": "温凉流质",
                    "48-72h": "半流质", "72h+": "软食", "warning": "卧床休息24h, 避免剧烈活动1周, 停抗凝/抗血小板"},
    "esd_emr": {"stage": "ESD/EMR", "0-24h": "禁食水(PPI持续输注)", "24-48h": "流质",
                "48-72h": "半流质", "72h-1w": "软食", "warning": "留院观察>24h, 绝对卧床, 监测出血/穿孔/感染征象"},
}

# Followup intervals by pathology (ESGE 2020 / JGES / China consensus)
_FOLLOWUP_INTERVALS = {
    "增生性息肉_直乙结肠": "10年 (或无需随访)",
    "增生性息肉_近端结肠": "5年",
    "管状腺瘤_LGD_1-2个_<10mm": "5-10年",
    "管状腺瘤_LGD_3-10个": "3年",
    "管状腺瘤_HGD": "3年",
    "绒毛状腺瘤": "3年",
    "锯齿状病变_SSL_<10mm_无细胞异型": "5年",
    "锯齿状病变_SSL_>=10mm_或细胞异型": "3年",
    "TSA_传统锯齿状腺瘤": "3年",
    "早癌_ESD术后": "3月→6月→12月→每年×3年→每2-3年",
    "萎缩性胃炎_轻中度": "3年",
    "萎缩性胃炎_重度_或肠化": "1年",
    "Barrett食管_无异性增生": "3-5年",
    "Barrett食管_LGD": "6月→12月→每年",
    "消化性溃疡_十二指肠": "无需常规复查 (确认HP根除后)",
    "消化性溃疡_胃": "8-12周后复查胃镜 (确认愈合+排除恶性)",
    "IBD_UC_全结肠炎_8-10年": "每1-2年结肠镜+多部位活检 (异型增生筛查)",
    "IBD_CD": "每1-3年 (依病变范围+炎症程度)",
}


# ═══════ Handler Functions ═══════


def report_parse(patient_id: str = "", report_text: str = "",
                 **kwargs: Any) -> dict:
    """内镜报告结构化解析 — Paris/Forrest/JNET + HP + 部位 + 活检."""
    p, err = _get_patient({"patient_id": patient_id})
    text = report_text.lower()

    findings: dict[str, str] = {}
    paris_type = ""
    forrest_class = ""
    jnet_type = ""
    hp = "未检测"

    # Location
    locations = []
    for loc, kw in [("食管", ["食管", "esophagus"]), ("贲门", ["贲门", "cardia"]),
                     ("胃底", ["胃底", "fundus"]), ("胃体", ["胃体", "body"]),
                     ("胃角", ["胃角", "angulus"]), ("胃窦", ["胃窦", "antrum"]),
                     ("幽门", ["幽门", "pylorus"]), ("十二指肠球部", ["十二指肠球", "bulb"]),
                     ("十二指肠降部", ["十二指肠降", "D2"]), ("回肠末端", ["回肠", "ileum"]),
                     ("盲肠", ["盲肠", "cecum"]), ("升结肠", ["升结肠", "ascending"]),
                     ("横结肠", ["横结肠", "transverse"]), ("降结肠", ["降结肠", "descending"]),
                     ("乙状结肠", ["乙状结肠", "sigmoid"]), ("直肠", ["直肠", "rectum"])]:
        if any(kw_item in text for kw_item in kw):
            locations.append(loc)

    location = " + ".join(locations) if locations else "未标注"

    # Paris classification
    for code, desc in _PARIS_CLASSIFICATION.items():
        if code.lower() in text or code in text:
            paris_type = f"{code} ({desc})"
            break

    # Forrest classification (upper GI bleeding)
    for code, info in _FORREST_CLASSIFICATION.items():
        if f"forrest {code.lower()}" in text or f"forrest{code.lower()}" in text:
            forrest_class = f"Forrest {code} ({info['grade']}出血风险, 再出血{info['rebleed']})"
            break

    # JNET classification (colon polyps)
    for code, info in _JNET_CLASSIFICATION.items():
        if f"jnet {code}" in text or f"jnet{code}" in text:
            jnet_type = f"JNET {code} ({info['type']})"
            break

    # Diagnosis keywords
    _FINDINGS_MAP = {
        "胃炎": ("慢性胃炎", "gastritis"),
        "萎缩性胃炎": ("萎缩性胃炎", "atrophic_gastritis"),
        "肠上皮化生": ("肠化", "intestinal_metaplasia"),
        "息肉": ("结直肠息肉", "polyp"),
        "腺瘤": ("腺瘤性息肉", "adenoma"),
        "溃疡": ("消化性溃疡", "peptic_ulcer"),
        "糜烂": ("黏膜糜烂", "erosion"),
        "反流性食管炎": ("反流性食管炎", "reflux_esophagitis"),
        "Barrett食管": ("Barrett食管", "barrett_esophagus"),
        "早癌": ("早期胃癌/结直肠癌", "early_cancer"),
        "进展期癌": ("进展期癌", "advanced_cancer"),
        "ESD": ("内镜黏膜下剥离术后", "esd"),
        "EMR": ("内镜黏膜切除术", "emr"),
        "静脉曲张": ("食管/胃底静脉曲张", "varices"),
        "憩室": ("消化道憩室", "diverticulum"),
        "IBD": ("炎性肠病", "ibd"),
        "克罗恩": ("克罗恩病", "crohn"),
        "溃疡性结肠炎": ("溃疡性结肠炎", "ulcerative_colitis"),
    }
    for kw, (cn, _) in _FINDINGS_MAP.items():
        if kw in text:
            findings[kw] = cn

    # HP
    if any(kw in text for kw in ["hp阳性", "hp+", "hp +", "幽门螺杆菌 阳性"]):
        hp = "阳性"
    elif any(kw in text for kw in ["hp阴性", "hp-", "hp -", "幽门螺杆菌 阴性"]):
        hp = "阴性"

    # Biopsy
    biopsy_sites = []
    if "活检" in text:
        for loc in locations:
            if loc in text.split("活检")[0][-20:] or True:
                biopsy_sites.append(loc)

    # Procedure type
    procedure = "胃镜" if any(l in locations for l in ["食管", "胃", "十二指肠"]) else "未知"
    if any(l in locations for l in ["回肠", "盲肠", "结肠", "乙状结肠", "直肠"]):
        procedure = "肠镜" if procedure == "未知" else "胃镜+肠镜"

    summary = f"内镜解析 — {', '.join(findings.values()) if findings else '未见明显异常'} | {location} | HP{hp}"
    if forrest_class:
        summary += f" | {forrest_class.split(' (')[0]}"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "procedure_type": procedure,
        "examination_scope": locations,
        "primary_location": location,
        "findings": findings,
        "paris_classification": paris_type,
        "forrest_classification": forrest_class,
        "jnet_classification": jnet_type,
        "hp_status": hp,
        "biopsy_sites": biopsy_sites,
        "biopsy_taken": len(biopsy_sites) > 0,
        "summary": summary,
    }


def risk_assessment(patient_id: str = "", findings: dict | None = None,
                    procedure_type: str = "diagnostic",
                    anticoagulation: str = "none",
                    **kwargs: Any) -> dict:
    """术后风险评估 — 出血/穿孔/感染 三轴 + 抗凝管理."""
    p, err = _get_patient({"patient_id": patient_id})
    findings = findings or {}

    # Bleeding risk
    bleed_risk = "低危"
    bleed_actions = []
    if "ESD" in str(findings) or "EMR" in str(findings):
        bleed_risk = "高危"
        bleed_actions = ["内镜术后止血评估 (Forrest分级)", "术后24h内禁食+PPI持续输注",
                         "监测: HR/BP q4h, 腹痛, 黑便/呕血, 血常规次日"]
    elif "息肉切除" in str(findings) or "polypectomy" in str(procedure_type):
        bleed_risk = "中危"
        bleed_actions = ["PPI口服qd (PPI iv 若>2cm)", "流质→半流质饮食过渡",
                         "观察: 腹痛, 黑便, Hb下降"]
    elif "活检" in str(findings) or "biopsy" in str(procedure_type):
        bleed_risk = "低危"
        bleed_actions = ["PPI口服 (必要时)", "软食, 避免粗糙食物"]
    else:
        bleed_actions = ["常规观察, 无特殊预防"]

    # Perforation risk
    perf_risk = "低危"
    perf_actions = []
    if "ESD" in str(findings) or "EMR" in str(findings) or "深溃疡" in str(findings):
        perf_risk = "中危"
        perf_actions = ["术后行腹部X线/CT排除游离气体 (若腹痛/腹膜炎体征)",
                        "严密监测腹膜炎体征(压痛/反跳痛/板状腹)"]
    else:
        perf_actions = ["常规观察"]

    # Infection risk
    inf_risk = "低危"
    inf_actions = ["术前抗生素预防仅某些操作 (经皮内镜胃造瘘/胰腺假性囊肿引流等)"]
    if len(findings) > 3:
        inf_risk = "低危"

    # Anticoagulation management
    ac_advice = ""
    if anticoagulation == "warfarin":
        ac_advice = "华法林: 诊断性内镜无需停药(INR<3.5); 治疗性操作(息肉切除/ESD)需停药5天+LMWH桥接; 确认止血后24h恢复"
    elif anticoagulation in ("doac", "noac"):
        ac_advice = "NOAC: 诊断性内镜停药24h; 息肉切除停药24-48h; ESD停药48-72h (依CrCl调整); 确认止血后48-72h恢复"
    elif anticoagulation == "antiplatelet":
        ac_advice = "抗血小板: 阿司匹林无需停药(诊断性/小息肉); 息肉切除(>1cm)停药3-5天; 氯吡格雷停药5-7天; ESD停药7天"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "bleeding_risk": bleed_risk,
        "bleeding_actions": bleed_actions,
        "perforation_risk": perf_risk,
        "perforation_actions": perf_actions,
        "infection_risk": inf_risk,
        "infection_actions": inf_actions,
        "anticoagulation_advice": ac_advice,
        "summary": f"风险评估 — 出血{bleed_risk} / 穿孔{perf_risk} / 感染{inf_risk}",
    }


def post_procedure_plan(patient_id: str = "", procedure_type: str = "diagnostic",
                        findings: dict | None = None,
                        biopsy: bool = False, **kwargs: Any) -> dict:
    """术后管理方案 — 饮食进阶 + 活动 + 用药 + 随访."""
    p, err = _get_patient({"patient_id": patient_id})

    findings = findings or {}
    # Determine severity tier
    if "ESD" in str(findings) or "EMR" in str(findings):
        tier = "esd_emr"
    elif "息肉切除" in str(findings) or procedure_type == "polypectomy":
        tier = "polypectomy"
    elif biopsy:
        tier = "biopsy"
    else:
        tier = "diagnostic"

    diet_plan = _DIET_PROGRESSION[tier]

    # PPI strategy
    ppi_plan = ""
    if tier in ("esd_emr", "polypectomy"):
        ppi_plan = "PPI静脉输注 (泮托拉唑 80mg IV bolus→8mg/h 持续 72h) → 口服PPI qd 4-8周"
    elif tier == "biopsy":
        ppi_plan = "PPI口服 qd 2-4周 (如胃溃疡/糜烂)"
    else:
        ppi_plan = "无需常规PPI (除非胃食管反流/溃疡)"

    # Activity
    activity = ""
    if tier == "esd_emr":
        activity = "绝对卧床24h → 床上活动48h → 室内活动72h → 1周内避免剧烈运动/重物"
    elif tier == "polypectomy":
        activity = "卧床休息24h → 1周内避免剧烈运动/提重物"
    else:
        activity = "当日避免驾驶/高空作业 (麻醉), 次日正常活动"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "procedure_severity": diet_plan["stage"],
        "diet_progression": [
            {"timeframe": "0-2h", "diet": diet_plan["0-2h"]},
            {"timeframe": "2-6h", "diet": diet_plan["2-6h"]},
            {"timeframe": "6-24h", "diet": diet_plan["6-24h"]},
            {"timeframe": "24h+", "diet": diet_plan.get("24h+", diet_plan.get("24-48h", ""))},
        ],
        "ppi_strategy": ppi_plan,
        "activity_restriction": activity,
        "warning_signs": diet_plan["warning"],
        "when_to_return": [
            "持续腹痛不缓解",
            "黑便/呕血/便血",
            "发热>38.5C",
            "吞咽困难/胸骨后痛 (穿孔征象)",
            "上述症状出现 → 立即返院急诊",
        ],
        "summary": f"术后管理 — {diet_plan['stage']}: {diet_plan['warning']}",
    }


def followup_reminder(patient_id: str = "", pathology: str = "",
                      procedure_date: str = "", polyp_count: int = 1,
                      polyp_size_mm: str = "<10", polyps_high_risk: bool = False,
                      **kwargs: Any) -> dict:
    """随访提醒 — ESGE/JGES/中国共识导向的个体化复查间隔."""
    p, err = _get_patient({"patient_id": patient_id})

    path_lower = pathology.lower()
    interval = "5年"
    rationale = ""

    if not pathology:
        interval = "5年"
        rationale = "未见明确病理异常, 常规筛查间隔"
    elif "高" in pathology and "腺瘤" in pathology:
        interval = "3年"
        rationale = "高级别腺瘤(HGD) — ESGE 推荐 3年后复查"
    elif "绒毛" in pathology or "管状绒毛" in pathology:
        interval = "3年"
        rationale = "绒毛状腺瘤 — ESGE 推荐 3年后复查"
    elif "锯齿" in pathology and (polyps_high_risk or ">=10mm" in polyp_size_mm):
        interval = "3年"
        rationale = "高风险锯齿状息肉 (>=10mm或细胞异型) — ESGE 推荐 3年"
    elif "锯齿" in pathology:
        interval = "5年"
        rationale = "低风险锯齿状病变 — ESGE 推荐 5年"
    elif "管状腺瘤" in pathology and "低级别" in pathology:
        if polyp_count >= 3:
            interval = "3年"
            rationale = "≥3个管状腺瘤(LGD) — ESGE 推荐 3年"
        else:
            interval = "5-10年"
            rationale = "1-2个管状腺瘤(LGD, <10mm) — ESGE 推荐 5-10年"
    elif "腺瘤" in pathology:
        interval = "3年"
        rationale = "腺瘤性息肉 — ESGE 推荐 3年"
    elif "增生" in pathology:
        interval = "5年"
        rationale = "增生性息肉(近端结肠) — ESGE 推荐 5年"
    elif "ESD" in pathology or "早癌" in pathology:
        interval = "3月→6月→12月→每年"
        rationale = "早期癌ESD术后 — JGES/中国共识: 3月→6月→12月→每年×3年→每2-3年"
    elif "萎缩" in pathology:
        if "重度" in pathology or "肠化" in pathology:
            interval = "1年"
            rationale = "重度萎缩+肠化 — 中国共识推荐 1年复查"
        else:
            interval = "3年"
            rationale = "轻中度萎缩性胃炎 — 中国共识推荐 3年复查"
    elif "Barrett" in pathology and "低级别" in pathology:
        interval = "6月→12月→每年"
        rationale = "Barrett食管伴LGD — ESGE 推荐 6月→12月→每年×3年"
    elif "Barrett" in pathology:
        interval = "3-5年"
        rationale = "Barrett食管无异性增生 — ESGE 推荐 3-5年"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "pathology": pathology,
        "procedure_date": procedure_date,
        "followup_interval": interval,
        "rationale": rationale,
        "guideline_ref": "ESGE 2020 / JGES 2020 / 中国早癌筛查共识 2023",
        "summary": f"随访 — {interval}后复查 | {rationale}",
    }


def patient_education(patient_id: str = "", findings: dict | None = None,
                      procedure_type: str = "diagnostic",
                      **kwargs: Any) -> dict:
    """患者宣教 — 去术语化翻译 + 个性化指导."""
    p, err = _get_patient({"patient_id": patient_id})
    findings = findings or {}

    explanations = []
    for finding_en, finding_cn in findings.items():
        if "胃炎" in finding_cn or "胃炎" in finding_en:
            explanations.append("慢性胃炎: 胃黏膜的慢性炎症, 很常见, 类似'胃的皮肤长期受刺激'。注意规律饮食, 避免辛辣刺激食物, 按医嘱服用胃药。")
        elif "息肉" in finding_cn or "息肉" in finding_en:
            explanations.append("息肉: 胃镜/肠镜下发现的小肉疙瘩, 绝大多数是良性的。医生已切除(如果有的话), 你需要按时间回来复查。就像给庄稼地除杂草, 除掉后要定期回去看看有没有新长的。")
        elif "溃疡" in finding_cn or "溃疡" in finding_en:
            explanations.append("溃疡: 胃/十二指肠上出现了'破口'或'糜烂', 就像口腔溃疡长在了胃里。需要服用抑制胃酸的药物(PPI)促进愈合, 通常4-8周。若有幽门螺杆菌感染, 需要抗生素根治。")
        elif "早癌" in finding_cn:
            explanations.append("早期癌: 在癌细胞还长在很表层的时候被发现的, 幸运的是这个阶段几乎可以100%治愈。医生已经做了内镜下切除, 你的任务是按时回来复查, 确保彻底治愈。")
        elif "萎缩" in finding_cn or "肠化" in finding_cn:
            explanations.append("萎缩性胃炎/肠化: 胃黏膜变薄了, 有点像是土壤肥力下降。需要定期复查观察有无变化。注意少吃腌制/烟熏食物, 多吃新鲜蔬果, 如果有幽门螺杆菌感染要根治。")
        elif "反流" in finding_cn:
            explanations.append("反流性食管炎: 胃酸反流到食管引起的炎症, 就像酸性液体烫伤了食管。晚上枕头垫高, 饭后不要立即躺下, 少吃甜食/咖啡/浓茶, 按医嘱服用抑酸药。")
        elif "憩室" in finding_cn:
            explanations.append("消化道憩室: 肠壁上出现的小'口袋'或小'暗袋', 通常无害。保持大便通畅, 多喝水, 多吃纤维食物。很少需要治疗。")
        elif "IBD" in finding_cn or "克罗恩" in finding_cn or "溃疡性结肠炎" in finding_cn:
            explanations.append("炎性肠病: 这是一种慢性肠道炎症性疾病, 需要长期管理。按时服药(5-ASA/免疫抑制剂/生物制剂), 定期复查肠镜, 保持健康饮食和良好心态。")

    dietary = {
        "通用建议": [
            "术后24h内避免辛辣、油腻、过烫的食物",
            "少量多餐 (每日5-6顿, 每顿7-8分饱)",
            "充分咀嚼, 每口咀嚼20-30次",
            "避免暴饮暴食, 细嚼慢咽",
        ],
        "禁用/慎用": [
            "阿司匹林/布洛芬/消炎痛等止痛药 (除非医生特别指示) — 改用对乙酰氨基酚(扑热息痛)",
            "烟酒 — 术后1周内禁烟酒",
            "粗糙食物: 坚果/油炸/硬壳类 — 术后3天内避免",
        ],
    }

    if procedure_type in ("esd_emr", "polypectomy"):
        dietary["通用建议"].insert(0, "术后24h: 禁食或清流质 (白水/米汤/藕粉)")
        dietary["通用建议"].append("1周内: 避免高纤维食物(芹菜/韭菜/粗粮/全麦面包)")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "explanations": explanations if explanations else ["本次内镜检查未见明显异常, 恭喜! 建议保持健康饮食, 定期体检。"],
        "dietary_guidance": dietary,
        "when_to_worry": [
            "出现持续腹痛不缓解 → 立即就医",
            "黑便/柏油样便/呕血/咖啡色呕吐物 → 立即急诊",
            "发热>38.5C 持续不降 → 就医",
            "吞咽困难/胸骨后剧烈疼痛 → 立即急诊 (穿孔!)",
        ],
        "summary": f"患者宣教 — {len(explanations)}项解释 | {procedure_type}术后指导",
        "disclaimer": "此为通俗化解读, 具体诊疗方案请以主治医生意见为准",
    }
