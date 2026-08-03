"""nurse_general — General Nursing Agent for xhaip v1.2.

Covers 6 core nursing functions:
  1. braden_score — Braden Pressure Ulcer Risk Assessment (6 items)
  2. morse_fall_score — Morse Fall Scale (6 factors)
  3. caprini_dvt — Caprini DVT Risk Assessment + Prevention
  4. vte_nursing_bundle — 4-stage Perioperative Nursing Bundle
  5. handover_summary — SBAR Handover Summary
  6. vital_signs_alert — Vital Signs Interpretation + EWS

Guidelines referenced:
  - Braden Scale (Braden & Bergstrom, 1988)
  - Morse Fall Scale (Morse et al., 1989)
  - Caprini DVT Risk Assessment (Caprini, 2005)
  - NICE CG74 Surgical Site Infection (2008, updated 2017)
  - SBAR Communication Standard (IHI)
  - NEWS2 / EWS Early Warning Score (RCP London, 2017)
"""

from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="nurse-general", department="护理部")
_GUIDELINES = [
    "Braden Scale for Predicting Pressure Sore Risk (1988)",
    "Morse Fall Scale (1989)",
    "Caprini VTE Risk Assessment Model (2005)",
    "NICE CG74 Surgical Site Infection (2017)",
    "SBAR Communication Standard (IHI)",
    "NEWS2 Early Warning Score (RCP London 2017)",
    "中国医院协会《患者安全目标》",
]
_agent.rule_engine.load_all()

# ═══════════════════════════════════════════════════════════
# 1. Braden 压疮风险评估
# ═══════════════════════════════════════════════════════════

BRADEN_ITEMS: dict[str, dict[str, int]] = {
    "sensory_perception": {
        "完全受限": 1, "大部分受限": 2, "轻度受限": 3, "未受损": 4,
    },
    "moisture": {
        "持续潮湿": 1, "经常潮湿": 2, "偶尔潮湿": 3, "极少潮湿": 4,
    },
    "activity": {
        "卧床": 1, "轮椅": 2, "偶尔行走": 3, "经常行走": 4,
    },
    "mobility": {
        "完全无法移动": 1, "大部分受限": 2, "轻度受限": 3, "未受限": 4,
    },
    "nutrition": {
        "严重不足": 1, "可能不足": 2, "充足": 3, "极佳": 4,
    },
    "friction_shear": {
        "存在问题": 1, "潜在问题": 2, "无明显问题": 3,
    },
}


def braden_score(
    sensory: str = "",
    moisture: str = "",
    activity: str = "",
    mobility: str = "",
    nutrition: str = "",
    friction: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Braden 压疮风险评分 — 6 项 1-4 分，总分 6-23。

    Risk levels:
      ≤9  极高危 — 立即启动压疮预防集束
      10-12 高危 — 动态减压床垫 + q2h 翻身
      13-14 中危 — 泡沫敷料 + 定时翻身
      15-18 低危 — 标准护理
      ≥19  无风险 — 常规皮肤评估

    Reference: Braden BJ, Bergstrom N. Nurs Res 1988;37(4):205-210.
    """
    item_map = {
        "sensory_perception": (sensory, BRADEN_ITEMS["sensory_perception"]),
        "moisture": (moisture, BRADEN_ITEMS["moisture"]),
        "activity": (activity, BRADEN_ITEMS["activity"]),
        "mobility": (mobility, BRADEN_ITEMS["mobility"]),
        "nutrition": (nutrition, BRADEN_ITEMS["nutrition"]),
        "friction_shear": (friction, BRADEN_ITEMS["friction_shear"]),
    }

    scores: dict[str, int] = {}
    total = 0
    details: list[dict[str, Any]] = []

    for key, (value, mapping) in item_map.items():
        score = mapping.get(value, 0)
        if score == 0 and value:
            score = _braden_fuzzy_match(value, mapping)
        scores[key] = score
        total += score
        details.append({
            "item": key,
            "value": value,
            "score": score,
        })

    if total <= 9:
        risk_level = "极高危"
        recommendations = [
            "立即启动压疮预防集束化措施",
            "动态减压床垫 + q2h 翻身",
            "减压敷料 (泡沫/水胶体) 覆盖骨突处",
            "皮肤完整性评估 q8h",
            "营养支持: 蛋白质 ≥1.2g/kg/d + 热量 ≥30kcal/kg/d",
            "每日 Braden 评分复查",
        ]
    elif total <= 12:
        risk_level = "高危"
        recommendations = [
            "动态减压床垫 + q2h 翻身",
            "泡沫敷料覆盖骨突处",
            "皮肤评估 q12h",
            "营养评估 + 补充方案",
            "Braden 评分每3天复查",
        ]
    elif total <= 14:
        risk_level = "中危"
        recommendations = [
            "泡沫敷料保护骨突处",
            "定时翻身 q2-3h",
            "皮肤评估 q24h",
            "保持皮肤清洁干燥",
        ]
    elif total <= 18:
        risk_level = "低危"
        recommendations = [
            "标准护理床垫",
            "按时翻身",
            "Braden 评分每周复查",
        ]
    else:
        risk_level = "无风险"
        recommendations = [
            "常规皮肤评估",
            "保持活动与营养",
        ]

    return {
        "status": "ok",
        "assessment": f"Braden 总分 {total}/23，压疮风险 {risk_level}",
        "total_score": total,
        "risk_level": risk_level,
        "scores": scores,
        "details": details,
        "recommendations": recommendations,
        "reference": "Braden BJ, Bergstrom N. Nurs Res 1988;37(4):205-210",
    }


def _braden_fuzzy_match(value: str, mapping: dict[str, int]) -> int:
    vl = value.lower()
    best_score = 0
    for k, v in mapping.items():
        if any(w in vl for w in k.lower().split()):
            best_score = v
            break
    return best_score


# ═══════════════════════════════════════════════════════════
# 2. Morse 跌倒风险评估
# ═══════════════════════════════════════════════════════════

MORSE_ITEMS: dict[str, dict[str, int]] = {
    "fall_history": {"是/近3月有跌倒": 25, "无": 0},
    "secondary_diagnosis": {"≥2个": 15, "1个": 0, "无": 0},
    "ambulatory_aid": {"行走辅助用具": 15, "扶墙/家具行走": 30, "轮椅/卧床": 0, "无/正常": 0},
    "iv_heparin_lock": {"有静脉输液/肝素锁": 20, "无": 0},
    "gait": {"异常步态/虚弱": 10, "卧床/轮椅": 0, "正常/不适用": 0},
    "mental_status": {"认知障碍/高估活动能力": 15, "正常/知晓活动能力": 0},
}


def morse_fall_score(
    fall_history: str = "",
    secondary_diagnosis: str = "",
    ambulatory_aid: str = "",
    iv_heparin_lock: str = "",
    gait: str = "",
    mental_status: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Morse 跌倒风险评估 — 6 因子，总分 0-125。

    Risk levels:
      <25    低危 — 基础防跌措施
      25-45  中危 — 标准防跌措施
      >45    高危 — 强化防跌措施

    Reference: Morse JM et al. J Gerontol Nurs 1989;15(9):20-26.
    """
    item_map = {
        "fall_history": (fall_history, MORSE_ITEMS["fall_history"]),
        "secondary_diagnosis": (secondary_diagnosis, MORSE_ITEMS["secondary_diagnosis"]),
        "ambulatory_aid": (ambulatory_aid, MORSE_ITEMS["ambulatory_aid"]),
        "iv_heparin_lock": (iv_heparin_lock, MORSE_ITEMS["iv_heparin_lock"]),
        "gait": (gait, MORSE_ITEMS["gait"]),
        "mental_status": (mental_status, MORSE_ITEMS["mental_status"]),
    }

    scores: dict[str, int] = {}
    total = 0
    details: list[dict[str, Any]] = []

    for key, (value, mapping) in item_map.items():
        score = mapping.get(value, 0)
        if score == 0 and value:
            score = _morse_fuzzy_match(value, mapping)
        scores[key] = score
        total += score
        details.append({"item": key, "value": value, "score": score})

    if total > 45:
        risk_level = "高危"
        prevention = [
            "跌倒高危标识牌 (床头+手腕)",
            "床栏使用 + 病床最低位",
            "呼叫铃放置手边 + 常用物品触手可及",
            "每小时巡视",
            "如厕协助 (不使用床旁便壶时)",
            "防滑袜/防滑鞋",
            "环境安全检查 (地面干燥/照明充足/无障碍物)",
            "必要时使用离床报警器",
            "护士交班明确告知跌倒高风险",
        ]
    elif total >= 25:
        risk_level = "中危"
        prevention = [
            "跌倒中危标识",
            "呼叫铃放置手边",
            "q2h 巡视",
            "防滑袜/鞋",
            "环境安全检查",
            "起床三步法教育 (坐30秒→站30秒→走)",
        ]
    else:
        risk_level = "低危"
        prevention = [
            "入院防跌倒宣教",
            "环境安全检查",
            "必要时使用呼叫铃",
        ]

    return {
        "status": "ok",
        "assessment": f"Morse 总分 {total}/125，跌倒风险 {risk_level}",
        "total_score": total,
        "risk_level": risk_level,
        "scores": scores,
        "details": details,
        "prevention": prevention,
        "reference": "Morse JM et al. J Gerontol Nurs 1989;15(9):20-26",
    }


def _morse_fuzzy_match(value: str, mapping: dict[str, int]) -> int:
    vl = value.lower()
    best_score = 0
    for k, v in mapping.items():
        kws = k.lower().replace("/", " ").split()
        if any(kw in vl for kw in kws if len(kw) > 1):
            best_score = v
            break
    return best_score


# ═══════════════════════════════════════════════════════════
# 3. Caprini DVT 风险评估
# ═══════════════════════════════════════════════════════════

CAPRINI_1_POINT = [
    "年龄 41-60", "小手术", "BMI > 25", "下肢肿胀", "静脉曲张",
    "妊娠/产后", "不明原因流产", "口服避孕药/激素替代", "败血症 (<1月)",
    "严重肺部疾病/肺炎 (<1月)", "肺功能异常", "急性心肌梗死",
    "充血性心衰 (<1月)", "炎症性肠病史", "卧床内科患者",
]

CAPRINI_2_POINTS = [
    "年龄 61-74", "关节镜手术", "大型开放手术 (>45min)",
    "腹腔镜手术 (>45min)", "恶性肿瘤", "卧床 >72h", "石膏固定",
    "中心静脉通路",
]

CAPRINI_3_POINTS = [
    "年龄 ≥75", "DVT/PE 史", "DVT/PE 家族史",
    "凝血因子 V Leiden 阳性", "凝血酶原 G20210A 阳性",
    "狼疮抗凝物阳性", "抗心磷脂抗体阳性", "高同型半胱氨酸血症",
    "肝素诱导血小板减少症",
]

CAPRINI_5_POINTS = [
    "脑卒中 (<1月)", "择期髋/膝关节置换术", "髋/骨盆/下肢骨折",
    "急性脊髓损伤 (<1月)",
]


def caprini_dvt(
    age: int = 0,
    bmi: float = 0.0,
    surgery_type: str = "",
    surgery_duration_min: int = 0,
    conditions: list[str] | None = None,
    medications: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Caprini DVT 风险评估 — 40+ 风险因子，总分驱动分级预防。

    Risk levels:
      0-1   低危 — 基础预防 (踝泵 + 早下床)
      2     中危 — 物理预防 (IPC + GCS)
      3-4   高危 — 物理 + 必要时药物预防
      ≥5    极高危 — 物理 + 药物预防 (LMWH)

    Reference: Caprini JA. Dis Mon 2005;51(2-3):70-78.
    """
    conditions = conditions or []
    medications = medications or []
    combined = " ".join(c.lower() for c in conditions + medications)

    score = 0
    triggered: list[str] = []

    # 1-point factors
    if 41 <= age <= 60:
        score += 1
        triggered.append("年龄 41-60")
    if bmi > 25:
        score += 1
        triggered.append("BMI > 25")
    for kw in ["肿胀", "swelling", "edema"]:
        if kw in combined:
            score += 1
            triggered.append("下肢肿胀")
            break
    for kw in ["静脉曲张", "varicose"]:
        if kw in combined:
            score += 1
            triggered.append("静脉曲张")
            break
    for kw in ["妊娠", "产后", "pregnant", "postpartum"]:
        if kw in combined:
            score += 1
            triggered.append("妊娠/产后")
            break
    for kw in ["败血症", "sepsis"]:
        if kw in combined:
            score += 1
            triggered.append("败血症 (<1月)")
            break
    for kw in ["心衰", "heart failure", "chf"]:
        if kw in combined:
            score += 1
            triggered.append("充血性心衰")
            break
    for kw in ["copd", "肺炎", "pneumonia"]:
        if kw in combined:
            score += 1
            triggered.append("严重肺部疾病")
            break
    for kw in ["卧床", "bed rest", "immobile"]:
        if kw in combined:
            score += 1
            triggered.append("卧床内科患者")
            break

    # 2-point factors
    if 61 <= age <= 74:
        score += 2
        triggered.append("年龄 61-74")
    if surgery_duration_min > 45 and surgery_type:
        score += 2
        triggered.append(f"大型手术 >45min ({surgery_type})")
    for kw in ["恶性肿瘤", "cancer", "malignancy"]:
        if kw in combined:
            score += 2
            triggered.append("恶性肿瘤")
            break
    for kw in ["石膏", "cast"]:
        if kw in combined:
            score += 2
            triggered.append("石膏固定")
            break

    # 3-point factors
    if age >= 75:
        score += 3
        triggered.append("年龄 ≥75")
    for kw in ["dvt史", "pe史", "血栓史", "dvt history", "pe history"]:
        if kw in combined:
            score += 3
            triggered.append("DVT/PE 史")
            break

    # 5-point factors
    for kw in ["髋关节置换", "膝关节置换", "tha", "tka", "hip replacement", "knee replacement"]:
        if kw in combined:
            score += 5
            triggered.append("择期髋/膝置换")
            break
    for kw in ["髋部骨折", "骨盆骨折", "下肢骨折", "hip fracture", "pelvic fracture"]:
        if kw in combined:
            score += 5
            triggered.append("髋/骨盆/下肢骨折")
            break
    for kw in ["脑卒中", "stroke", "脊髓", "spinal cord"]:
        if kw in combined:
            score += 5
            triggered.append("脑卒中/脊髓损伤 <1月")
            break

    if score <= 1:
        risk_level = "低危"
        dvt_rate = "<0.5%"
        prevention = [
            "基础预防: 踝泵运动 20次/h",
            "早期下床活动",
            "充足饮水",
        ]
    elif score == 2:
        risk_level = "中危"
        dvt_rate = "1-2%"
        prevention = [
            "物理预防: 间歇充气加压装置 (IPC) 2×/天",
            "梯度压力弹力袜 (GCS)",
            "踝泵运动 20次/h",
            "早期下床活动",
        ]
    elif score <= 4:
        risk_level = "高危"
        dvt_rate = "3-6%"
        prevention = [
            "物理预防: IPC 2×/天 + GCS",
            "必要时药物预防: 低分子肝素 (LMWH)，出血风险低者",
            "踝泵运动 20次/h",
            "监测 D-二聚体",
            "每日评估出血风险",
        ]
    else:
        risk_level = "极高危"
        dvt_rate = ">6%"
        prevention = [
            "药物预防: 低分子肝素 (LMWH) qd (CrCl≥30)",
            "物理预防: IPC + GCS 联合",
            "术前即启动预防 (高出血风险者可推迟)",
            "术后延长预防至 28-35 天 (关节置换)",
            "监测血小板 (警惕 HIT)",
            "踝泵运动 20次/h",
        ]

    return {
        "status": "ok",
        "assessment": f"Caprini 总分 {score}，DVT 风险 {risk_level} (发生率 {dvt_rate})",
        "total_score": score,
        "risk_level": risk_level,
        "dvt_incidence": dvt_rate,
        "triggered_factors": triggered,
        "prevention": prevention,
        "reference": "Caprini JA. Dis Mon 2005;51(2-3):70-78",
    }


# ═══════════════════════════════════════════════════════════
# 4. 围术期护理 4 阶段方案 (VTE Nursing Bundle)
# ═══════════════════════════════════════════════════════════

def vte_nursing_bundle(
    procedure: str = "",
    age: int = 0,
    conditions: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """围术期护理 4 阶段方案 — 条目化 checklist。

    Stages:
      1. 术前护理 (入院-术前)
      2. 术日护理 (D0)
      3. 术后 24-72h (D1-D3)
      4. 出院指导
    """
    conditions = conditions or []
    combined = " ".join(c.lower() for c in conditions)

    stages = [
        {
            "stage": "术前护理",
            "order": 1,
            "items": [
                {"id": "pre_01", "content": "健康宣教: 手术流程 + 疼痛管理 + 康复预期", "category": "教育"},
                {"id": "pre_02", "content": "皮肤准备: 术区清洁 + 全身皮肤评估 (Braden)", "category": "皮肤"},
                {"id": "pre_03", "content": "禁食指导: 术前6h禁食 / 术前2h禁水", "category": "饮食"},
                {"id": "pre_04", "content": "VTE风险筛查 (Caprini) + 基础预防教育", "category": "安全"},
                {"id": "pre_05", "content": "跌倒风险评估 (Morse) + 防跌措施准备", "category": "安全"},
                {"id": "pre_06", "content": "心理护理: 缓解焦虑，讲解手术必要性", "category": "心理"},
                {"id": "pre_07", "content": "呼吸功能训练: 腹式呼吸 + 有效咳嗽排痰", "category": "呼吸"},
                {"id": "pre_08", "content": "术前排便训练: 床上排便", "category": "排汇"},
            ],
        },
        {
            "stage": "术日护理 (D0)",
            "order": 2,
            "items": [
                {"id": "d0_01", "content": "生命体征监测: q1h×4 → q4h (T/P/R/BP/SpO2)", "category": "监测"},
                {"id": "d0_02", "content": "体位管理: 患肢功能位, 抬高15-30° (根据术式调整)", "category": "体位"},
                {"id": "d0_03", "content": "切口/伤口观察: 渗血/肿胀/皮温/引流量及性状", "category": "伤口"},
                {"id": "d0_04", "content": "疼痛评估: VAS/NRS q4h, 目标 ≤3分, 遵医嘱多模式镇痛", "category": "疼痛"},
                {"id": "d0_05", "content": "DVT物理预防: IPC 2×/天 + GCS + 踝泵运动指导", "category": "安全"},
                {"id": "d0_06", "content": "压疮预防: Braden评分 + q2h翻身 (手术结束判断体位限制)", "category": "皮肤"},
                {"id": "d0_07", "content": "管道护理: 引流管/尿管/深静脉管路固定及通畅", "category": "管道"},
            ],
        },
        {
            "stage": "术后24-72h (D1-D3)",
            "order": 3,
            "items": [
                {"id": "d1_01", "content": "饮食过渡: 流质→半流质→普食, 高蛋白 + 高维生素", "category": "饮食"},
                {"id": "d1_02", "content": "功能锻炼: 踝泵 + 等长收缩 + 被动/主动关节活动", "category": "康复"},
                {"id": "d1_03", "content": "导管管理: 评估拔除时机 (引流<30ml/24h, 尿管拔除)", "category": "管道"},
                {"id": "d1_04", "content": "排便管理: 预防便秘 (腹部按摩/饮食/必要时通便药)", "category": "排汇"},
                {"id": "d1_05", "content": "心理护理: 焦虑/抑郁筛查, 必要时心理科会诊", "category": "心理"},
                {"id": "d1_06", "content": "防跌倒: 起床三步法 + 呼叫铃 + 防滑鞋", "category": "安全"},
            ],
        },
        {
            "stage": "出院指导",
            "order": 4,
            "items": [
                {"id": "dc_01", "content": "伤口护理: 清洁/观察/换药频次", "category": "伤口"},
                {"id": "dc_02", "content": "用药指导: 抗凝药/镇痛药/抗生素 用法及注意事项", "category": "用药"},
                {"id": "dc_03", "content": "功能锻炼: 居家康复方案 (踝泵/肌肉训练/渐进负重)", "category": "康复"},
                {"id": "dc_04", "content": "复诊安排: 术后1月/3月/6月门诊时间", "category": "随访"},
                {"id": "dc_05", "content": "红旗症状识别: 发热>38.5°C/伤口红肿渗液/胸痛/呼吸困难/下肢肿胀", "category": "安全"},
                {"id": "dc_06", "content": "照顾者培训: 翻身/转移/助行器使用", "category": "教育"},
            ],
        },
    ]

    highlights: list[str] = []
    if age >= 80:
        highlights.append("高龄: 加强谵妄监测 + 防跌倒 + 营养支持")
    if age >= 65:
        highlights.append("老年: 注意镇静药物代谢, 评估认知功能")
    if any(kw in combined for kw in ["糖尿病", "dm", "diabetes"]):
        highlights.append("糖尿病: 围术期血糖目标 6-10 mmol/L, 监测末梢血糖 q6h")
    if any(kw in combined for kw in ["高血压", "htn"]):
        highlights.append("高血压: 控制血压 <160/100, 避免低血压")
    if any(kw in combined for kw in ["copd", "哮喘", "asthma"]):
        highlights.append("呼吸系统: 呼吸训练 + 雾化 + 体位引流 + 监测SpO2")
    if any(kw in combined for kw in ["抗凝", "anticoag", "华法林", "warfarin", "氯吡格雷"]):
        highlights.append("抗凝药物: 注意术后出血风险, 遵医嘱桥接方案")
    if any(kw in combined for kw in ["骨质疏松", "osteoporosis"]):
        highlights.append("骨质疏松: 术后启动钙+VitD 补充, 防二次骨折")
    if any(kw in combined for kw in ["认知", "痴呆", "dementia"]):
        highlights.append("认知障碍: 定向力支持 + 家属陪伴 + 减少约束 + 防拔管")

    return {
        "status": "ok",
        "procedure": procedure,
        "stages": stages,
        "highlights": highlights,
        "total_checklist_items": sum(len(s["items"]) for s in stages),
        "reference": "NICE CG74 (2008, updated 2017); DVT Consensus 2024",
    }


# ═══════════════════════════════════════════════════════════
# 5. SBAR 交班摘要生成
# ═══════════════════════════════════════════════════════════

def handover_summary(
    patient_id: str = "",
    patient_name: str = "",
    age: int = 0,
    diagnosis: str = "",
    current_status: str = "",
    key_events: str = "",
    recommendations: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """SBAR 交班摘要 — 结构化交班文本。

    SBAR framework (IHI):
      S — Situation (患者基本信息 + 当前问题)
      B — Background (诊断 + 既往史 + 关键事件)
      A — Assessment (护理评估结论)
      R — Recommendation (建议/待办事项)

    Returns structured SBAR text in a nursing handover format.
    """
    recommendations = recommendations or []

    situation = f"{age}岁，{diagnosis}，现状态: {current_status}"

    background_parts = [f"诊断: {diagnosis}"]
    if key_events:
        background_parts.append(f"关键事件: {key_events}")

    assessment = current_status if current_status else "生命体征平稳，护理评估进行中"

    rec_text = "; ".join(recommendations) if recommendations else "继续现行护理方案，注意病情变化"

    sbar_text = (
        f"【S — 现状】\n"
        f"  患者 {patient_name}({patient_id})，{age}岁，诊断: {diagnosis}。\n"
        f"  当前状态: {current_status}\n"
        f"\n"
        f"【B — 背景】\n"
        f"  {'; '.join(background_parts)}\n"
        f"\n"
        f"【A — 评估】\n"
        f"  {assessment}\n"
        f"\n"
        f"【R — 建议】\n"
        f"  {rec_text}\n"
    )

    return {
        "status": "ok",
        "patient_id": patient_id,
        "sbar_text": sbar_text,
        "sections": {
            "situation": situation,
            "background": "; ".join(background_parts),
            "assessment": assessment,
            "recommendation": rec_text,
        },
        "reference": "IHI SBAR Communication Tool",
    }


# ═══════════════════════════════════════════════════════════
# 6. 生命体征判读 + EWS
# ═══════════════════════════════════════════════════════════

EWS_THRESHOLDS = {
    "temperature": [
        {"min": -float("inf"), "max": 35.0, "score": 3},
        {"min": 35.0, "max": 36.0, "score": 1},
        {"min": 36.0, "max": 38.0, "score": 0},
        {"min": 38.0, "max": 39.0, "score": 1},
        {"min": 39.0, "max": float("inf"), "score": 2},
    ],
    "pulse": [
        {"min": -float("inf"), "max": 40, "score": 3},
        {"min": 40, "max": 50, "score": 1},
        {"min": 50, "max": 90, "score": 0},
        {"min": 90, "max": 110, "score": 1},
        {"min": 110, "max": 130, "score": 2},
        {"min": 130, "max": float("inf"), "score": 3},
    ],
    "respiration": [
        {"min": -float("inf"), "max": 9, "score": 3},
        {"min": 9, "max": 12, "score": 1},
        {"min": 12, "max": 20, "score": 0},
        {"min": 20, "max": 25, "score": 2},
        {"min": 25, "max": float("inf"), "score": 3},
    ],
    "systolic_bp": [
        {"min": -float("inf"), "max": 90, "score": 3},
        {"min": 90, "max": 100, "score": 2},
        {"min": 100, "max": 110, "score": 1},
        {"min": 110, "max": 220, "score": 0},
        {"min": 220, "max": float("inf"), "score": 3},
    ],
    "spo2": [
        {"min": -float("inf"), "max": 85, "score": 3, "note": "严重低氧"},
        {"min": 85, "max": 89, "score": 2, "note": "中度低氧"},
        {"min": 89, "max": 92, "score": 1, "note": "轻度低氧"},
        {"min": 92, "max": 94, "score": 0, "note": "临界正常"},
        {"min": 94, "max": float("inf"), "score": 0, "note": "正常"},
    ],
}

AVPU_SCORES = {"alert": 0, "v": 1, "p": 2, "u": 3, "清醒": 0, "语言": 1, "疼痛": 2, "无反应": 3}


def _ews_score(value: float, thresholds: list[dict]) -> int:
    for t in thresholds:
        if t["min"] <= value < t["max"]:
            return t["score"]
    return 0


def vital_signs_alert(
    temperature: float = 36.5,
    pulse: int = 72,
    respiration: int = 16,
    systolic_bp: int = 120,
    spo2: float = 97.0,
    avpu: str = "alert",
    **kwargs: Any,
) -> dict[str, Any]:
    """生命体征逐项判读 + EWS 简化早期预警评分。

    EWS score:
      0-1  常规观察
      2-3  通知值班医师, q4h 监测
      4-5  ≥q2h 监测, 考虑升级
      6    ≥q1h 监测, 通知上级医师
      ≥7   紧急呼叫抢救小组

    Reference: RCP London NEWS2 (2017)
    """
    alerts: list[dict[str, Any]] = []
    ews_total = 0

    # Temperature
    t_score = _ews_score(temperature, EWS_THRESHOLDS["temperature"])
    ews_total += t_score
    if temperature >= 39.0:
        alerts.append({"sign": "体温", "value": f"{temperature}°C", "level": "high",
                       "score": t_score, "note": "高热, 通知医师"})
    elif temperature >= 38.0:
        alerts.append({"sign": "体温", "value": f"{temperature}°C", "level": "medium",
                       "score": t_score, "note": "低热, 观察"})
    elif temperature <= 35.0:
        alerts.append({"sign": "体温", "value": f"{temperature}°C", "level": "critical",
                       "score": t_score, "note": "低体温, 紧急会诊"})
    elif temperature < 36.0:
        alerts.append({"sign": "体温", "value": f"{temperature}°C", "level": "high",
                       "score": t_score, "note": "体温偏低, 注意保暖"})

    # Pulse
    p_score = _ews_score(pulse, EWS_THRESHOLDS["pulse"])
    ews_total += p_score
    if pulse < 40:
        alerts.append({"sign": "心率", "value": f"{pulse} bpm", "level": "critical",
                       "score": p_score, "note": "严重心动过缓, 紧急评估"})
    elif pulse < 50:
        alerts.append({"sign": "心率", "value": f"{pulse} bpm", "level": "high",
                       "score": p_score, "note": "心动过缓"})
    elif pulse >= 130:
        alerts.append({"sign": "心率", "value": f"{pulse} bpm", "level": "critical",
                       "score": p_score, "note": "严重心动过速, 紧急评估"})
    elif pulse >= 110:
        alerts.append({"sign": "心率", "value": f"{pulse} bpm", "level": "high",
                       "score": p_score, "note": "心动过速, 通知医师"})
    elif pulse >= 90:
        alerts.append({"sign": "心率", "value": f"{pulse} bpm", "level": "medium",
                       "score": p_score, "note": "心率偏快, 观察"})

    # Respiration
    r_score = _ews_score(respiration, EWS_THRESHOLDS["respiration"])
    ews_total += r_score
    if respiration < 9:
        alerts.append({"sign": "呼吸", "value": f"{respiration} bpm", "level": "critical",
                       "score": r_score, "note": "呼吸抑制, 紧急评估"})
    elif respiration < 12:
        alerts.append({"sign": "呼吸", "value": f"{respiration} bpm", "level": "high",
                       "score": r_score, "note": "呼吸偏慢"})
    elif respiration >= 25:
        alerts.append({"sign": "呼吸", "value": f"{respiration} bpm", "level": "critical",
                       "score": r_score, "note": "呼吸急促, 紧急评估"})
    elif respiration >= 21:
        alerts.append({"sign": "呼吸", "value": f"{respiration} bpm", "level": "high",
                       "score": r_score, "note": "呼吸偏快"})

    # Systolic BP
    bp_score = _ews_score(systolic_bp, EWS_THRESHOLDS["systolic_bp"])
    ews_total += bp_score
    if systolic_bp < 90:
        alerts.append({"sign": "收缩压", "value": f"{systolic_bp} mmHg", "level": "critical",
                       "score": bp_score, "note": "低血压休克, 紧急会诊"})
    elif systolic_bp < 100:
        alerts.append({"sign": "收缩压", "value": f"{systolic_bp} mmHg", "level": "high",
                       "score": bp_score, "note": "低血压, 通知医师"})
    elif systolic_bp < 110:
        alerts.append({"sign": "收缩压", "value": f"{systolic_bp} mmHg", "level": "medium",
                       "score": bp_score, "note": "血压偏低, 观察"})
    elif systolic_bp >= 220:
        alerts.append({"sign": "收缩压", "value": f"{systolic_bp} mmHg", "level": "critical",
                       "score": bp_score, "note": "高血压危象, 紧急会诊"})

    # SpO2
    s_score = _ews_score(spo2, EWS_THRESHOLDS["spo2"])
    ews_total += s_score
    if spo2 < 85:
        alerts.append({"sign": "SpO2", "value": f"{spo2}%", "level": "critical",
                       "score": s_score, "note": "严重低氧血症, 紧急抢救"})
    elif spo2 < 89:
        alerts.append({"sign": "SpO2", "value": f"{spo2}%", "level": "high",
                       "score": s_score, "note": "中度低氧, 予氧疗"})
    elif spo2 < 92:
        alerts.append({"sign": "SpO2", "value": f"{spo2}%", "level": "medium",
                       "score": s_score, "note": "轻度低氧, 观察"})
    elif spo2 < 94:
        alerts.append({"sign": "SpO2", "value": f"{spo2}%", "level": "low",
                       "score": s_score, "note": "临界正常"})

    # AVPU
    avpu_lower = avpu.lower()
    avpu_score = AVPU_SCORES.get(avpu_lower, AVPU_SCORES.get(avpu, 0))
    ews_total += avpu_score
    if avpu_score >= 3:
        alerts.append({"sign": "意识", "value": avpu, "level": "critical",
                       "score": avpu_score, "note": "意识丧失, 立即抢救"})
    elif avpu_score >= 2:
        alerts.append({"sign": "意识", "value": avpu, "level": "high",
                       "score": avpu_score, "note": "意识障碍 (仅对疼痛有反应)"})
    elif avpu_score >= 1:
        alerts.append({"sign": "意识", "value": avpu, "level": "medium",
                       "score": avpu_score, "note": "意识改变 (仅对语言有反应)"})

    if ews_total >= 7:
        ews_action = "紧急呼叫抢救小组, 持续监测, 准备ICU"
        escalation = "emergency"
    elif ews_total >= 6:
        ews_action = "q1h 监测, 通知上级医师, 考虑升级监护"
        escalation = "urgent"
    elif ews_total >= 4:
        ews_action = "≥q2h 监测, 通知值班医师"
        escalation = "watchful"
    elif ews_total >= 2:
        ews_action = "q4h 监测, 通知值班医师"
        escalation = "observation"
    else:
        ews_action = "常规观察, 按护理计划执行"
        escalation = "routine"

    return {
        "status": "ok",
        "vital_signs": {
            "temperature": f"{temperature}°C",
            "pulse": f"{pulse} bpm",
            "respiration": f"{respiration} bpm",
            "systolic_bp": f"{systolic_bp} mmHg",
            "spo2": f"{spo2}%",
            "avpu": avpu,
        },
        "ews_total": ews_total,
        "escalation_level": escalation,
        "ews_action": ews_action,
        "alerts": alerts,
        "alert_count": len(alerts),
        "reference": "RCP London NEWS2 (2017); National Early Warning Score 2",
    }
