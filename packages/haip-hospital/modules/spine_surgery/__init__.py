"""脊柱骨科 — 脊柱外科核心临床评估工具集.

ASIA 脊髓损伤分级 / Cobb 角侧弯分度 / 腰椎管狭窄评估
Oswestry 功能障碍指数 / 术式路径建议 / 红旗征筛查

GUIDELINES: ASIA International Standards (2019) / SRS Schroth / NASS 2019
"""

from __future__ import annotations

from typing import Any

# ═══════════════════════════════════════════════════════════
# 1. ASIA 脊髓损伤分级 (A-E)
# ═══════════════════════════════════════════════════════════

ASIA_KEY_MUSCLES: dict[str, str] = {
    "c5": "C5 — 肘屈肌 (肱二头肌)", "c6": "C6 — 腕伸肌 (桡侧腕长/短伸肌)",
    "c7": "C7 — 肘伸肌 (肱三头肌)", "c8": "C8 — 指屈肌 (中指指深屈肌)",
    "t1": "T1 — 小指外展肌", "l2": "L2 — 髋屈肌 (髂腰肌)",
    "l3": "L3 — 膝伸肌 (股四头肌)", "l4": "L4 — 踝背伸肌 (胫前肌)",
    "l5": "L5 — 长伸趾肌", "s1": "S1 — 踝跖屈肌 (腓肠肌/比目鱼肌)",
}

DERMATOME_LEVELS: list[str] = [
    "C2", "C3", "C4", "C5", "C6", "C7", "C8",
    "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12",
    "L1", "L2", "L3", "L4", "L5",
    "S1", "S2", "S3", "S4-S5",
]


def asia_classification(
    motor_level: str = "",
    sensory_level: str = "",
    motor_scores: dict[str, int] | None = None,
    sacral_sparing: bool | None = None,
    anal_contraction: bool | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """ASIA 脊髓损伤分级 (A-E).

    参考: International Standards for Neurological Classification of SCI (ISNCSCI, 2019)

    Args:
        motor_level: 最尾端肌力 ≥3 级的节段
        sensory_level: 最尾端正常感觉的节段
        motor_scores: 10 对关键肌的 0-5 分评分
        sacral_sparing: S4-S5 感觉保留 (针刺或轻触)
        anal_contraction: 肛门自主收缩 (是/否)

    Returns:
        ASIA grade, neurological level, completeness
    """
    motor_scores = motor_scores or {}
    sacral_sparing = sacral_sparing if sacral_sparing is not None else False
    anal_contraction = anal_contraction if anal_contraction is not None else False

    upper_score = sum(motor_scores.get(k, 0) for k in ["c5", "c6", "c7", "c8", "t1"])
    lower_score = sum(motor_scores.get(k, 0) for k in ["l2", "l3", "l4", "l5", "s1"])
    total_motor = upper_score + lower_score

    nli = motor_level if motor_level else sensory_level if sensory_level else "未确定"

    if sacral_sparing and anal_contraction:
        if total_motor >= 90:
            grade = "E"
            grade_desc = "正常 — 所有神经功能正常"
        elif total_motor >= 45:
            grade = "D"
            grade_desc = "不完全损伤 — 神经平面以下大部分关键肌 ≥3 级"
        else:
            grade = "C"
            grade_desc = "不完全损伤 — 神经平面以下大部分关键肌 <3 级"
    elif sacral_sparing or anal_contraction:
        grade = "B"
        grade_desc = "不完全感觉 — 仅感觉功能保留至 S4-S5，无运动功能"
    else:
        if total_motor == 0 and "c4" in str(motor_level).lower():
            grade = "A"
            grade_desc = "完全损伤 — 骶段 S4-S5 无感觉/运动功能保留 (高位颈髓)"
        else:
            grade = "A"
            grade_desc = "完全损伤 — 骶段 S4-S5 无感觉/运动功能保留"

    completeness = "不完全性" if grade in ("B", "C", "D", "E") else "完全性"

    return {
        "status": "ok",
        "neurological_level": nli,
        "asia_grade": grade,
        "grade_description": grade_desc,
        "completeness": completeness,
        "motor_score": {"upper": upper_score, "lower": lower_score, "total": total_motor},
        "sacral_sparing": sacral_sparing,
        "anal_contraction": anal_contraction,
        "evidence": ["ISNCSCI 2019", "ASIA International Standards"],
        "note": "ASIA 分级需在 72h 后复查，脊髓休克期评定不准确",
    }


# ═══════════════════════════════════════════════════════════
# 2. Cobb 角脊柱侧弯分级 + Risser 骨龄
# ═══════════════════════════════════════════════════════════

def cobb_severity(
    cobb_angle: float = 0,
    risser_grade: int | None = None,
    age: int = 0,
    curve_type: str = "thoracic",
    progression_risk: str = "low",
    **kwargs: Any,
) -> dict[str, Any]:
    """脊柱侧弯 Cobb 角分级 + Risser 骨龄修正建议.

    参考: SRS (Scoliosis Research Society) + Schroth Best Practice

    Args:
        cobb_angle: Cobb 角 (度)
        risser_grade: Risser 骨龄分级 (0-5)
        age: 患者年龄
        curve_type: 弯曲类型 (thoracic/lumbar/thoracolumbar/double)
        progression_risk: 进展风险 (low/medium/high)

    Returns:
        分级/分度 + 治疗建议 + Risser 修正
    """
    if cobb_angle < 10:
        severity = "正常"
        grade = "normal"
        treatment = "无需治疗，建议每年体检观察"
        follow_up = "每 12 个月"
    elif cobb_angle <= 25:
        severity = "轻度侧弯"
        grade = "mild"
        if age < 18 and risser_grade is not None and risser_grade <= 3:
            treatment = "物理治疗 (Schroth/PSSE) + 每 4-6 个月复查 Cobb 角"
            follow_up = "每 4-6 个月 X 光复查"
        else:
            treatment = "观察 + 物理治疗"
            follow_up = "每 6-12 个月复查"
    elif cobb_angle <= 45:
        severity = "中度侧弯"
        grade = "moderate"
        if risser_grade is not None and risser_grade <= 4:
            treatment = "支具治疗 (Boston/TLSO) + Schroth 体操, 每日佩戴 18-23h"
            follow_up = "每 3-4 个月 X 光复查 Cobb 角变化"
        else:
            treatment = "支具治疗效果有限 (Risser ≥4 骨龄成熟), 建议物理治疗维持"
            follow_up = "每 4-6 个月复查"
    else:
        severity = "重度侧弯"
        grade = "severe"
        treatment = "手术治疗 (后路矫形内固定 + 植骨融合术)"
        follow_up = "术后 1/3/6/12 月 X 光复查"

    risser_note = ""
    if risser_grade is not None:
        risser_note = f"Risser {risser_grade} 级"
        if risser_grade <= 2:
            risser_note += " — 骨龄未成熟，进展风险高"
        elif risser_grade <= 4:
            risser_note += " — 骨龄部分成熟，仍有进展可能"
        else:
            risser_note += " — 骨龄成熟，进展风险低"

    progression_modifier = ""
    if progression_risk == "high":
        progression_modifier = " (高风险: Cobb 角进展 >5°/年 → 治疗升级)"
    elif progression_risk == "medium":
        progression_modifier = " (中风险: 密切随访)"

    if curve_type in ("thoracolumbar", "lumbar") and grade == "severe":
        treatment += " — 注意腰弯矫形需保留腰椎活动度"

    return {
        "status": "ok",
        "cobb_angle": cobb_angle,
        "severity": severity,
        "grade": grade,
        "treatment": treatment + progression_modifier,
        "follow_up": follow_up,
        "risser_grade": risser_grade,
        "risser_note": risser_note,
        "curve_type": curve_type,
        "evidence": ["SRS 侧弯指南", "Schroth Best Practice", "SOSORT 2018"],
        "surgery_indications": (
            ["Cobb ≥45° + 进展风险高", "Cobb ≥50° 胸弯 (成人)", "严重躯干失衡 (>2cm)"]
            if grade == "severe" else []
        ),
    }


# ═══════════════════════════════════════════════════════════
# 3. 腰椎管狭窄评估
# ═══════════════════════════════════════════════════════════

SCHIZAS_GRADES: dict[str, dict] = {
    "A": {"label": "正常/轻度", "csf_visible": True, "severity": "none"},
    "A1": {"label": "前 CSF 间隙部分闭塞", "csf_visible": True, "severity": "mild"},
    "A2": {"label": "前 CSF 间隙完全闭塞", "csf_visible": True, "severity": "mild"},
    "A3": {"label": "硬膜囊前缘变形", "csf_visible": True, "severity": "mild"},
    "A4": {"label": "硬膜囊受压但 CSF 可见", "csf_visible": True, "severity": "mild"},
    "B": {"label": "硬膜囊部分受压, CSF 部分消失", "csf_visible": False, "severity": "moderate"},
    "C": {"label": "硬膜囊完全受压, CSF 完全消失", "csf_visible": False, "severity": "severe"},
    "D": {"label": "硬膜囊完全受压 + 马尾完全阻塞", "csf_visible": False, "severity": "critical"},
}


def stenosis_assessment(
    symptoms: list[str] | None = None,
    walking_distance_m: float = 0,
    schizas_grade: str = "",
    segment_level: str = "",
    central_stenosis: bool = False,
    foraminal_stenosis: bool = False,
    age: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """腰椎管狭窄评估 — 症状/步行距离/Schizas 影像分级.

    参考: NASS 2019 腰椎管狭窄指南 / Schizas MRI 分级 (2010)

    Args:
        symptoms: 症状列表 (神经源性跛行/根性痛/感觉异常/膀胱功能障碍)
        walking_distance_m: 无痛步行距离 (米)
        schizas_grade: MRI Schizas 分级 (A/A1/A2/A3/A4/B/C/D)
        segment_level: 狭窄节段 (如 L4-L5)
        central_stenosis: 中央椎管狭窄
        foraminal_stenosis: 椎间孔狭窄

    Returns:
        严重度 + 保守/介入/手术建议
    """
    symptoms = symptoms or []
    s_lower = [s.lower() for s in symptoms]

    has_claudication = any(k in " ".join(s_lower) for k in ["跛行", "claudication"])
    has_radiculopathy = any(k in " ".join(s_lower) for k in ["根性", "放射", "radicul"])
    has_bladder = any(k in " ".join(s_lower) for k in ["膀胱", "尿", "便", "bladder"])

    if walking_distance_m >= 500:
        walk_severity = "正常 (≥500m)"
    elif walking_distance_m >= 200:
        walk_severity = "轻度受限 (200-500m)"
    elif walking_distance_m >= 50:
        walk_severity = "中度受限 (50-200m)"
    elif walking_distance_m > 0:
        walk_severity = "重度受限 (<50m)"
    else:
        walk_severity = "无法行走或未记录"

    schizas_info = SCHIZAS_GRADES.get(schizas_grade, {"label": "未分级", "severity": "unknown"})

    score = 0
    if has_claudication:
        score += 2
    if has_radiculopathy:
        score += 2
    if schizas_info["severity"] in ("severe", "critical"):
        score += 3
    elif schizas_info["severity"] == "moderate":
        score += 2
    if walking_distance_m < 200:
        score += 2
    if walking_distance_m < 50:
        score += 1
    if has_bladder:
        score += 3
    if foraminal_stenosis:
        score += 1

    if score >= 8 or has_bladder:
        severity = "重度"
        recommendation = "建议手术治疗 (椎板切除减压 + 融合)"
        urgency = "紧急 — 如伴马尾综合征需急诊手术"
    elif score >= 5:
        severity = "中度"
        recommendation = "硬膜外激素注射 + 药物 (加巴喷丁/普瑞巴林) + 理疗"
        urgency = "限期 — 如保守治疗 3-6 月无效考虑手术"
    elif score >= 2:
        severity = "轻度"
        recommendation = "保守治疗: NSAIDs + 核心肌群锻炼 + 物理治疗"
        urgency = "非紧急"
    else:
        severity = "极轻度/无症状"
        recommendation = "健康宣教 + 姿势矫正 + 定期随访"
        urgency = "非紧急"

    surgical_options: list[str] = []
    if score >= 5:
        if not central_stenosis and foraminal_stenosis:
            surgical_options.append("椎间孔切开术")
        if central_stenosis and not foraminal_stenosis:
            surgical_options.append("椎板切除术")
        if central_stenosis and foraminal_stenosis:
            surgical_options.append("椎板切除减压 + 椎间孔成形 + 融合 (TLIF/PLIF)")

    return {
        "status": "ok",
        "severity": severity,
        "score": score,
        "walking_capacity": walk_severity,
        "schizas_grade": schizas_grade,
        "schizas_label": schizas_info["label"],
        "symptoms_summary": {
            "neurogenic_claudication": has_claudication,
            "radiculopathy": has_radiculopathy,
            "bladder_dysfunction": has_bladder,
        },
        "segment": segment_level or "未指定",
        "recommendation": recommendation,
        "urgency": urgency,
        "surgical_options": surgical_options,
        "evidence": ["NASS Lumbar Spinal Stenosis Guideline 2019", "Schizas MRI Classification 2010"],
    }


# ═══════════════════════════════════════════════════════════
# 4. Oswestry 功能障碍指数 (ODI)
# ═══════════════════════════════════════════════════════════

ODI_ITEMS: list[dict] = [
    {"id": "pain_intensity", "label": "疼痛强度", "max_score": 5},
    {"id": "personal_care", "label": "个人自理 (洗漱/穿衣)", "max_score": 5},
    {"id": "lifting", "label": "提重物", "max_score": 5},
    {"id": "walking", "label": "行走", "max_score": 5},
    {"id": "sitting", "label": "坐", "max_score": 5},
    {"id": "standing", "label": "站立", "max_score": 5},
    {"id": "sleeping", "label": "睡眠", "max_score": 5},
    {"id": "sex_life", "label": "性生活 (如适用)", "max_score": 5},
    {"id": "social_life", "label": "社交生活", "max_score": 5},
    {"id": "traveling", "label": "外出/旅行", "max_score": 5},
]

ODI_ANSWERS: dict[str, list[str]] = {
    "pain_intensity": [
        "0: 无痛",
        "1: 疼痛很轻微, 无需止痛药",
        "2: 中度疼痛, 止痛药可缓解",
        "3: 疼痛较重, 止痛药部分缓解",
        "4: 严重疼痛, 止痛药效果差",
        "5: 极度疼痛, 止痛药无效",
    ],
    "personal_care": [
        "0: 自理无痛", "1: 自理有痛但可完成",
        "2: 自理疼痛明显, 需慢行", "3: 部分需要帮助",
        "4: 大部分需要帮助", "5: 完全依赖他人",
    ],
    "lifting": [
        "0: 提重物无痛", "1: 提重物有痛",
        "2: 疼痛限制提重物", "3: 只能提轻物",
        "4: 只能提极轻物", "5: 完全不能提物",
    ],
    "walking": [
        "0: 行走无痛", "1: >400m",
        "2: 200-400m", "3: 50-200m",
        "4: <50m", "5: 卧床/轮椅",
    ],
    "sitting": [
        "0: 坐任意时间", "1: >1h", "2: 30-60min",
        "3: 10-30min", "4: <10min", "5: 不能坐",
    ],
    "standing": [
        "0: 站立无痛", "1: >1h", "2: 30-60min",
        "3: 10-30min", "4: <10min", "5: 不能站立",
    ],
    "sleeping": [
        "0: 睡眠正常", "1: 偶尔因痛醒",
        "2: <6h 因痛", "3: <4h", "4: <2h", "5: 完全不能入睡",
    ],
    "sex_life": [
        "0: 正常", "1: 偶尔痛", "2: 经常痛",
        "3: 明显受限", "4: 几乎不能", "5: 完全不能",
    ],
    "social_life": [
        "0: 正常", "1: 偶尔受限",
        "2: 疼痛影响但可参加", "3: 频繁受影响",
        "4: 严重受限", "5: 无社交",
    ],
    "traveling": [
        "0: 任意出行", "1: >1h", "2: 30-60min",
        "3: 10-30min", "4: <10min", "5: 完全不能外出",
    ],
}


def odi_score(
    scores: dict[str, int] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Oswestry 功能障碍指数 (ODI v2.1).

    10 项, 每项 0-5 分, 满分 50 (或折算为百分比).

    Args:
        scores: {item_id: 0-5} 评分, 如 {"pain_intensity": 2, "walking": 3}
    """
    scores = scores or {}
    answered = 0
    raw_sum = 0
    detail: dict[str, dict] = {}

    for item in ODI_ITEMS:
        iid = item["id"]
        score = scores.get(iid, -1)
        if score >= 0 and score <= 5:
            answered += 1
            raw_sum += score
            detail[iid] = {"score": score, "label": item["label"],
                           "answer": ODI_ANSWERS.get(iid, [""] * 6)[score]}
        else:
            detail[iid] = {"score": None, "label": item["label"], "answer": "未作答"}

    if answered == 0:
        return {"status": "error", "error": "无有效评分项", "odi_pct": 0, "grade": "无法评估"}

    max_possible = answered * 5
    odi_pct = round(raw_sum / max_possible * 100, 1)

    if odi_pct <= 20:
        grade = "极轻度功能障碍"
        impact = "患者可应对大多数日常活动, 无需特殊治疗"
    elif odi_pct <= 40:
        grade = "中度功能障碍"
        impact = "疼痛和功能受限影响日常生活, 建议保守治疗"
    elif odi_pct <= 60:
        grade = "重度功能障碍"
        impact = "疼痛严重影响生活, 需积极治疗 (注射/手术评估)"
    elif odi_pct <= 80:
        grade = "严重残疾"
        impact = "生活几乎完全受限, 强烈建议手术干预评估"
    else:
        grade = "卧床或夸大症状"
        impact = "生活完全受限, 需全面评估心理/社会因素"

    return {
        "status": "ok",
        "odi_pct": odi_pct,
        "grade": grade,
        "impact": impact,
        "raw_score": raw_sum,
        "items_answered": answered,
        "total_items": 10,
        "detail": detail,
        "evidence": ["Fairbank JCT (1980)", "ODI v2.1", "Spine 2000;25:2940-53"],
    }


# ═══════════════════════════════════════════════════════════
# 5. 术式路径建议
# ═══════════════════════════════════════════════════════════

SPINE_PROCEDURES: dict[str, dict] = {
    "peld": {
        "name": "椎间孔镜 (PELD/TESSYS)",
        "approach": "经皮后外侧椎间孔入路",
        "indications": ["椎间盘突出 (旁中央型)", "椎间孔狭窄", "L1-S1 节段", "青年/中年患者"],
        "contraindications": ["严重中央椎管狭窄", "马尾综合征", "脊柱不稳"],
        "advantages": ["7mm 切口", "局部麻醉", "日间手术", "保留脊柱稳定性"],
        "length_stay": "日间 (6-24h)",
    },
    "ube": {
        "name": "单侧双通道内镜 (UBE)",
        "approach": "单侧双通道 (观察+工作)",
        "indications": ["中央椎管狭窄", "双侧减压", "椎间盘突出 (游离型)", "黄韧带肥厚"],
        "contraindications": ["重度脊柱不稳", "严重骨质疏松"],
        "advantages": ["视野清晰", "减压充分", "比开放手术创伤小"],
        "length_stay": "1-2 天",
    },
    "olif": {
        "name": "斜外侧腰椎椎间融合 (OLIF)",
        "approach": "腹膜后腰大肌前缘斜外侧",
        "indications": ["椎间盘退变性疾病", "轻度滑脱 (I-II°)", "椎间孔狭窄需间接减压", "L1-L5 节段"],
        "contraindications": ["L5-S1 (髂嵴遮挡)", "严重血管变异", "既往腹膜后手术史"],
        "advantages": ["不进入椎管", "大 cage 支撑", "间接减压效果好"],
        "length_stay": "2-3 天",
    },
    "tlif": {
        "name": "经椎间孔腰椎椎间融合 (TLIF)",
        "approach": "后方经椎间孔入路",
        "indications": ["腰椎滑脱 (I-III°)", "退变性椎间盘病", "翻修手术", "椎间孔狭窄"],
        "contraindications": ["严重骨质疏松 (需骨水泥强化)", "严重心肺功能不全"],
        "advantages": ["360° 融合", "直接减压 + 椎间融合", "融合率高 (>90%)"],
        "length_stay": "3-5 天",
    },
    "open": {
        "name": "开放减压固定融合术",
        "approach": "后正中入路",
        "indications": ["严重椎管狭窄 (多节段)", "退变性侧弯 (>30°)", "脊柱不稳/滑脱", "翻修/复杂病例"],
        "contraindications": ["严重内科合并症不能耐受手术"],
        "advantages": ["视野暴露充分", "多节段处理能力", "矫形能力强"],
        "length_stay": "5-7 天",
    },
}


def surgical_pathway(
    diagnosis: str = "",
    segment: str = "",
    t_score: float = -1.0,
    age: int = 0,
    multi_level: bool = False,
    instability: bool = False,
    prior_surgery: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """术式路径建议 — 按病种 + 节段 + 骨密度.

    Args:
        diagnosis: 诊断 (腰椎间盘突出/椎管狭窄/滑脱/退变性侧弯)
        segment: 责任节段 (如 L4-L5, L5-S1)
        t_score: 骨密度 T 值 (DXA)
        age: 患者年龄
        multi_level: 多节段病变
        instability: 脊柱不稳 (动力位 X 光 >3mm 移位)
        prior_surgery: 既往手术史

    Returns:
        推荐术式 + 备选方案 + 骨密度修正
    """
    dx_lower = diagnosis.lower()
    osteoporosis = t_score <= -2.5
    osteopenia = t_score <= -1.0 and t_score > -2.5

    primary = ""
    alternative = ""
    reasoning: list[str] = []

    if "间盘突出" in dx_lower or "disc herniation" in dx_lower:
        if segment.upper().startswith("L5") or segment.upper().startswith("S1"):
            primary = "peld"
            reasoning.append("L5-S1 节段适合 PELD 旁中央型突出")
        else:
            primary = "peld"
            reasoning.append("单纯椎间盘突出首选微创椎间孔镜")
        if multi_level:
            primary = "ube"
            reasoning.append("多节段椎间盘突出转为 UBE 双侧减压")
        alternative = "ube"

    elif "椎管狭窄" in dx_lower or "stenosis" in dx_lower:
        if multi_level:
            primary = "open"
            reasoning.append("多节段狭窄 → 开放减压固定融合")
        elif instability:
            primary = "tlif"
            reasoning.append("狭窄 + 不稳 → TLIF 360° 融合")
        else:
            primary = "ube"
            reasoning.append("单节段中央椎管狭窄 → UBE 双侧减压")
        alternative = "tlif" if primary == "ube" else "ube"

    elif "滑脱" in dx_lower or "spondylolisthesis" in dx_lower:
        primary = "tlif"
        reasoning.append("腰椎滑脱 → TLIF 复位 + 椎间融合")
        if age <= 50 and t_score > -2:
            alternative = "olif"
            reasoning.append("年轻、骨量正常患者可选 OLIF 间接减压+融合")

    elif "侧弯" in dx_lower or "scoliosis" in dx_lower:
        primary = "open"
        reasoning.append("退变性侧弯需开放矫形 + 多节段固定融合")
        alternative = "tlif"

    else:
        primary = "ube"
        reasoning.append("诊断不明，默认微创探查 (UBE)")
        alternative = "open"

    if prior_surgery:
        reasoning.append("翻修病例 — 瘢痕粘连增加手术难度，推荐开放手术")
        if primary != "open":
            alternative = primary
            primary = "open"

    if osteoporosis:
        reasoning.append(f"骨质疏松 (T={t_score}) — 需骨水泥强化或延长融合节段")
    elif osteopenia:
        reasoning.append(f"骨量减少 (T={t_score}) — 考虑 PEEK cage + 后路固定加强")

    proc = SPINE_PROCEDURES[primary]
    alt_proc = SPINE_PROCEDURES.get(alternative, {})

    return {
        "status": "ok",
        "diagnosis": diagnosis,
        "segment": segment,
        "primary_procedure": primary,
        "primary_name": proc["name"],
        "primary_approach": proc["approach"],
        "primary_advantages": proc["advantages"],
        "length_of_stay": proc["length_stay"],
        "alternative_procedure": alternative,
        "alternative_name": alt_proc.get("name", "N/A"),
        "indications": proc["indications"],
        "contraindications": proc["contraindications"],
        "bone_quality": "骨质疏松" if osteoporosis else "骨量减少" if osteopenia else "正常",
        "t_score": t_score,
        "reasoning": reasoning,
        "preop_requirements": [
            "腰椎正侧位 + 动力位 X 光",
            f"{segment} MRI (T1/T2/STIR)",
            "骨密度 DXA (若 >65 岁或有危险因素)",
            "下肢肌力 + 感觉查体记录",
            "心肺功能评估 (≥60 岁或 ASA ≥3)",
        ],
        "evidence": ["NASS 腰椎融合指南", "AO Spine 内固定原则", "中国骨质疏松性骨折诊疗指南 2022"],
    }


# ═══════════════════════════════════════════════════════════
# 6. 脊柱红旗征筛查
# ═══════════════════════════════════════════════════════════

CAUDA_EQUINA_FLAGS: list[str] = [
    "急性尿潴留", "膀胱功能障碍", "大便失禁", "鞍区麻木 (S2-S5)",
    "双侧坐骨神经痛", "进行性下肢无力", "突发步态异常",
]

TUMOR_RED_FLAGS: list[str] = [
    "夜间痛 (影响睡眠)", "无法解释的体重下降 (>5kg/6月)",
    "既往恶性肿瘤史", "持续性疼痛不缓解 (>6周保守治疗无效)",
    "年龄 >50 岁 + 首次腰背痛",
    "卧位痛加重",
]

INFECTION_RED_FLAGS: list[str] = [
    "发热 >38.0°C", "寒战/盗汗", "近期手术/注射史",
    "静脉药物滥用史", "免疫功能低下 (HIV/糖尿病/激素/放疗)",
    "脊柱局部压痛明显 + 叩击痛",
    "CRP >50 mg/L / ESR >50 mm/h",
]

FRACTURE_RED_FLAGS: list[str] = [
    "严重外伤史 (车祸/坠落)", "轻微外伤 (老年+骨质疏松)",
    "长期激素使用史", "年龄 >70 岁",
    "骨质疏松诊断 (DXA T ≤ -2.5)", "脊柱后凸畸形急性加重",
    "局部剧痛不能翻身",
]


def red_flags(
    patient_id: str = "",
    symptoms: list[str] | None = None,
    history: list[str] | None = None,
    age: int = 0,
    lab_crp: float = 0,
    lab_esr: float = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """脊柱红旗征筛查 — 马尾/肿瘤/感染/骨折 4 类急症.

    Args:
        symptoms: 当前症状列表
        history: 病史/危险因素列表
        age: 患者年龄
        lab_crp: CRP (mg/L)
        lab_esr: ESR (mm/h)

    Returns:
        命中红旗征列表 + 急诊升级建议
    """
    symptoms = symptoms or []
    history = history or []
    all_text = " ".join(s.lower() for s in symptoms + history + [str(age), "crp", str(lab_crp)])

    flags: list[dict] = []
    emergency_upgrade = False

    # ── 马尾综合征 ──
    cauda_hits: list[str] = []
    for f in CAUDA_EQUINA_FLAGS:
        if any(k in all_text for k in [f.lower(), f[:2].lower()]):
            cauda_hits.append(f)
    if cauda_hits:
        flags.append({"category": "马尾综合征", "hits": cauda_hits, "urgency": "急诊手术血",
                       "action": "立即 MRI (T2 矢状位+轴位) → 神经外科/脊柱外科急诊 → 24h 内手术减压",
                       "level": "critical"})
        emergency_upgrade = True

    # ── 肿瘤 ──
    tumor_hits: list[str] = []
    for f in TUMOR_RED_FLAGS:
        if any(k in all_text for k in [f[:3].lower(), "体重", "夜间", "肿瘤", "cancer"]):
            tumor_hits.append(f)
    if age > 50:
        tumor_hits.append("年龄 >50 岁 — 警惕转移/骨髓瘤")
    if tumor_hits and not cauda_hits:
        flags.append({"category": "脊柱肿瘤", "hits": tumor_hits, "urgency": "急诊影像",
                       "action": "MRI 增强 + 全身骨扫描/PET-CT → 脊柱肿瘤 MDT",
                       "level": "high"})
        emergency_upgrade = True

    # ── 感染 ──
    infection_hits: list[str] = []
    for f in INFECTION_RED_FLAGS:
        if any(k in all_text for k in ["发热", "寒战", "感染", "手术史", "iv", "hiv",
                                        "糖尿病", "免疫"]):
            infection_hits.append(f)
    if lab_crp > 50:
        if "CRP >50" not in infection_hits:
            infection_hits.append(f"CRP={lab_crp} mg/L (>50)")
    if lab_esr > 50:
        if "ESR >50" not in infection_hits:
            infection_hits.append(f"ESR={lab_esr} mm/h (>50)")
    if infection_hits and not cauda_hits:
        flags.append({"category": "脊柱感染", "hits": infection_hits, "urgency": "急诊评估",
                       "action": "血培养 + CRP/ESR/PCT → MRI 增强 → 感染科会诊 → 穿刺活检 (如 MRI 阳性)",
                       "level": "high"})
        emergency_upgrade = True

    # ── 骨折 ──
    fracture_hits: list[str] = []
    for f in FRACTURE_RED_FLAGS:
        if any(k in all_text for k in [f[:3].lower(), "外伤", "车祸", "坠落", "骨折", "骨质疏松",
                                        "t≤", "t <", "-2.5", "不能翻身", "后凸"]):
            fracture_hits.append(f)
    if age > 70:
        fracture_hits.append("年龄 >70 岁 — 骨质疏松性骨折高风险")
    if fracture_hits:
        flags.append({"category": "脊柱骨折", "hits": fracture_hits, "urgency": "急诊评估",
                       "action": "X 光 (正侧位) + CT (薄层扫描) → MRI (STIR 判断新鲜/陈旧) → "
                                 "脊柱外科 → 必要时骨水泥椎体成形 (PVP/PKP)",
                       "level": "high"})
        emergency_upgrade = True

    total_hits = sum(len(f["hits"]) for f in flags)

    return {
        "status": "ok",
        "patient_id": patient_id,
        "emergency_upgrade": emergency_upgrade,
        "flags": flags,
        "total_hits": total_hits,
        "categories": [f["category"] for f in flags],
        "recommendation": (
            "发现脊柱红旗征，建议立即升级为急诊处理流程 (绿色通道)"
            if emergency_upgrade else "未发现红旗征，可按常规流程继续诊疗"
        ),
        "evidence": [
            "NICE NG59 腰痛与坐骨神经痛 (2020)",
            "American College of Radiology — Appropriateness Criteria",
            "中国脊柱急症诊疗共识",
        ],
    }
