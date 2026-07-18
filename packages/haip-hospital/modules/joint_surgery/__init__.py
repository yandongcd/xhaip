"""关节与骨病外科 — 关节置换核心临床评估工具集.

Harris 髋关节评分 / KSS 膝关节评分 / 假体周围感染诊断
THA/TKA 术前规划 / ERAS 路径 / 翻修评估

GUIDELINES: AAOS / AAHKS / MSIS-ICM 2018 / ERAS Society
"""

from __future__ import annotations

from typing import Any

# ═══════════════════════════════════════════════════════════
# 1. Harris 髋关节评分 (0-100)
# ═══════════════════════════════════════════════════════════

HARRIS_PAIN: dict[int, dict] = {
    44: {"label": "无痛", "best": True},
    40: {"label": "偶尔轻微疼痛, 不影响活动", "best": False},
    30: {"label": "轻度疼痛, 日常活动不受限; 活动后可服 NSAIDs", "best": False},
    20: {"label": "中度疼痛, 可忍受但需常服止痛药; 活动受限", "best": False},
    10: {"label": "重度疼痛, 日常活动严重受限", "best": False},
    0:  {"label": "完全残疾: 疼痛卧床, 无法行走", "best": False},
}

HARRIS_GAIT: dict[str, int] = {"无跛行": 11, "轻度跛行": 8, "中度跛行": 5, "重度跛行": 0}
HARRIS_SUPPORT: dict[str, int] = {"无": 11, "偶尔手杖": 7, "单手杖": 5, "双拐": 3, "双拐+助行器": 0, "不能行走": 0}
HARRIS_DISTANCE: dict[str, int] = {"不受限": 11, ">1.6km": 8, "0.8-1.6km": 5, "0.3-0.8km": 2, "仅室内": 0}


def harris_hip_score(
    pain_level: str = "none",
    gait: str = "无跛行",
    support: str = "无",
    walking_distance: str = "不受限",
    stairs: str = "正常上下楼",
    sitting: str = "舒适坐1h+",
    shoes_socks: str = "容易",
    public_transport: str = "可乘公交",
    fixed_flexion: int = 0,
    fixed_abduction: int = 0,
    fixed_adduction: int = 0,
    fixed_internal_rotation: int = 0,
    leg_length_discrepancy_cm: float = 0,
    flexion_rom: int = 120,
    abduction_rom: int = 40,
    adduction_rom: int = 30,
    external_rotation_rom: int = 40,
    internal_rotation_rom: int = 40,
    **kwargs: Any,
) -> dict[str, Any]:
    """Harris 髋关节评分 (Harris Hip Score, modified).

    4 个域: 疼痛 (0-44) + 功能 (0-47) + 畸形 (0-4) + 活动度 (0-5) = 总分 100.

    参考: Harris WH (1969), JBJS 51-A:737-755

    Returns:
        总分, 分级, 各域得分
    """
    # ── 1. 疼痛 (0-44) ──
    pain_map = {"none": 44, "mild": 40, "light": 40, "moderate": 20, "mod": 20,
                "severe": 10, "severe_disabled": 0, "disabled": 0}
    pain_score = pain_map.get(pain_level.lower(), 0)
    if pain_score >= 40:
        pain_label = "A — 无痛/偶尔轻微"
    elif pain_score >= 20:
        pain_label = "B — 轻度至中度 (可忍受)"
    else:
        pain_label = "C — 重度疼痛 (显著受限)"

    # ── 2. 功能 (0-47) ──
    gait_score = HARRIS_GAIT.get(gait, 6)
    support_score = HARRIS_SUPPORT.get(support, 5)
    distance_score = HARRIS_DISTANCE.get(walking_distance, 3)

    stairs_map = {"正常上下楼": 4, "正常但需扶栏": 2, "困难": 1, "不能": 0}
    stairs_score = stairs_map.get(stairs, 2)

    sitting_map = {"舒适坐1h+": 5, "舒适坐30min": 3, "不能舒适坐": 0}
    sitting_score = sitting_map.get(sitting, 3)

    shoes_map = {"容易": 4, "困难": 2, "不能": 0}
    shoes_score = shoes_map.get(shoes_socks, 2)

    transport_map = {"可乘公交": 1, "不能乘公交": 0}
    transport_score = transport_map.get(public_transport, 1)

    function_score = gait_score + support_score + distance_score + stairs_score + sitting_score + shoes_score + transport_score
    function_score = min(function_score, 47)

    # ── 3. 畸形 (0-4) ──
    deformity_score = 4
    if fixed_flexion > 30:
        deformity_score -= 1
    if fixed_adduction > 10:
        deformity_score -= 1
    if fixed_internal_rotation > 10:
        deformity_score -= 1
    if leg_length_discrepancy_cm > 3.2:
        deformity_score -= 1
    deformity_score = max(deformity_score, 0)

    # ── 4. 活动度 ROM (0-5) ──
    rom_sum = (
        flexion_rom + abduction_rom + adduction_rom
        + external_rotation_rom + internal_rotation_rom
    )
    if rom_sum >= 300:
        rom_score = 5
    elif rom_sum >= 260:
        rom_score = 4
    elif rom_sum >= 210:
        rom_score = 3
    elif rom_sum >= 160:
        rom_score = 2
    elif rom_sum >= 100:
        rom_score = 1
    else:
        rom_score = 0

    total = pain_score + function_score + deformity_score + rom_score
    total = min(total, 100)

    if total >= 90:
        grade = "优 (Excellent)"
    elif total >= 80:
        grade = "良 (Good)"
    elif total >= 70:
        grade = "可 (Fair)"
    else:
        grade = "差 (Poor)"

    return {
        "status": "ok",
        "total_score": total,
        "grade": grade,
        "domains": {
            "pain": {"score": pain_score, "max": 44, "label": pain_label},
            "function": {"score": function_score, "max": 47, "subscores": {
                "gait": gait_score, "support": support_score, "distance": distance_score,
                "stairs": stairs_score, "sitting": sitting_score,
                "shoes_socks": shoes_score, "public_transport": transport_score,
            }},
            "deformity": {"score": deformity_score, "max": 4},
            "rom": {"score": rom_score, "max": 5, "rom_sum": rom_sum},
        },
        "evidence": ["Harris WH (1969) JBJS 51-A:737-755", "AAOS Clinical Practice Guideline"],
    }


# ═══════════════════════════════════════════════════════════
# 2. KSS 膝关节评分 (Knee Society Score)
# ═══════════════════════════════════════════════════════════

def kss_score(
    pain: int = 50,
    rom_degrees: int = 120,
    mediolateral_stability_mm: int = 3,
    anteroposterior_stability_mm: int = 3,
    flexion_contracture_deg: int = 0,
    extensor_lag_deg: int = 0,
    alignment_degrees: int = 0,
    walk_blocks: int = 10,
    stairs_up_down: int = 20,
    walking_aid: str = "none",
    **kwargs: Any,
) -> dict[str, Any]:
    """KSS 膝关节评分 (Knee Society Score, 2011).

    双表: 临床评分 (0-100) + 功能评分 (0-100).

    参考: Insall JN et al. CORR 1989; Scuderi GR et al. CORR 2012

    Args:
        pain: 疼痛评分 (0-50), 50=无痛, 45=轻微, 30=中度, 0=重度
        rom_degrees: 膝关节活动度 (0-140°)
        mediolateral_stability_mm: 内外侧不稳定 (<5mm / 5-9mm / ≥10mm)
        anteroposterior_stability_mm: 前后不稳定 (<5mm / 5-9mm / ≥10mm)
        flexion_contracture_deg: 屈曲挛缩 (°)
        extensor_lag_deg: 伸膝迟滞 (°)
        alignment_degrees: 力线偏倚 (°), 0=正常 5-10° 外翻
        walk_blocks: 可走街区数 (0, 1, 2-3, 4-6, 7-10, >10 → 对应分数)
        stairs_up_down: 上下楼能力 (0-50)
        walking_aid: 行走辅助

    Returns:
        clinical_score, functional_score, grades
    """
    # ── Clinical Score (0-100) ──
    clinical = 0

    # Pain (max 50)
    clinical += min(pain, 50)

    # ROM (max 25): 1 point per 5 degrees
    rom_pts = min(rom_degrees, 125) // 5
    clinical += rom_pts

    # Stability (max 25)
    if mediolateral_stability_mm < 5 and anteroposterior_stability_mm < 5:
        clinical += 25
    elif mediolateral_stability_mm < 10 and anteroposterior_stability_mm < 10:
        clinical += 15
    else:
        clinical += 10

    # Deductions
    if flexion_contracture_deg <= 5:
        pass
    elif flexion_contracture_deg <= 10:
        clinical = max(0, clinical - 2)
    elif flexion_contracture_deg <= 20:
        clinical = max(0, clinical - 5)
    else:
        clinical = max(0, clinical - 10)

    if extensor_lag_deg < 10:
        pass
    elif extensor_lag_deg <= 20:
        clinical = max(0, clinical - 5)
    else:
        clinical = max(0, clinical - 10)

    if alignment_degrees >= 0 and alignment_degrees <= 10:
        pass
    elif alignment_degrees < 0 or alignment_degrees > 15:
        clinical = max(0, clinical - 10)
    else:
        clinical = max(0, clinical - 3)

    clinical = min(clinical, 100)

    # ── Functional Score (0-100) ──
    functional = 0

    walk_map = {0: 0, 1: 10, 2: 20, 3: 20, 4: 30, 5: 30, 6: 30, 7: 40, 8: 40, 9: 40,
                10: 50, 11: 50, 15: 50, 20: 50, 99: 50}
    closest = min(walk_map.keys(), key=lambda k: abs(k - walk_blocks))
    functional += walk_map.get(closest, 0)

    functional += min(stairs_up_down, 50)

    aid_deduction_map = {"none": 0, "cane": -5, "single_cane": -5, "crutch": -10,
                         "two_canes": -10, "walker": -20, "wheelchair": -30}
    functional = max(0, functional + aid_deduction_map.get(walking_aid.lower(), 0))

    functional = min(functional, 100)

    def _grade(score: int) -> str:
        if score >= 85:
            return "优 (Excellent)"
        elif score >= 70:
            return "良 (Good)"
        elif score >= 60:
            return "可 (Fair)"
        return "差 (Poor)"

    return {
        "status": "ok",
        "clinical_score": clinical,
        "clinical_grade": _grade(clinical),
        "functional_score": functional,
        "functional_grade": _grade(functional),
        "details": {
            "pain": min(pain, 50), "rom_pts": rom_pts, "rom_degrees": rom_degrees,
            "mediolateral_stability_mm": mediolateral_stability_mm,
            "anteroposterior_stability_mm": anteroposterior_stability_mm,
            "flexion_contracture_deg": flexion_contracture_deg,
            "extensor_lag_deg": extensor_lag_deg,
            "alignment_degrees": alignment_degrees,
        },
        "evidence": ["Insall JN et al. CORR 1989;248:13-14", "Scuderi GR et al. CORR 2012"],
    }


# ═══════════════════════════════════════════════════════════
# 3. 假体周围感染 (PJI) — MSIS/ICM 2018
# ═══════════════════════════════════════════════════════════

PJI_MAJOR_CRITERIA: dict[str, int] = {
    "sinus_tract": None,  # 直接判定感染
    "two_positive_cultures": None,  # 直接判定感染
}

PJI_MINOR_CRITERIA: dict[str, dict] = {
    "elevated_crp": {"points": 2, "label": "CRP >10 mg/L 或 D-dimer >860 μg/L"},
    "elevated_esr": {"points": 1, "label": "ESR >30 mm/h"},
    "elevated_synovial_wbc": {"points": 3, "label": "滑液 WBC >3000/μL 或 LE ++"},
    "elevated_pmn_pct": {"points": 2, "label": "滑液 PMN >80%"},
    "alpha_defensin": {"points": 3, "label": "α-defensin 阳性 (信号/截止比 >1.0)"},
    "single_positive_culture": {"points": 1, "label": "单次培养阳性"},
    "frozen_section_positive": {"points": 3, "label": "冰冻切片 >5 PMN/HPF (×400)"},
    "intraop_purulence": {"points": 3, "label": "术中肉眼可见脓液"},
}


def pji_diagnosis(
    sinus_tract: bool = False,
    positive_cultures: int = 0,
    same_organism: bool = False,
    crp: float = 0,
    esr: float = 0,
    synovial_wbc: float = 0,
    pmn_pct: float = 0,
    alpha_defensin_positive: bool = False,
    frozen_section_positive: bool = False,
    intraop_purulence: bool = False,
    d_dimer: float = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """假体周围感染 (PJI) 诊断 — MSIS/ICM 2018 标准.

    参考: Parvizi J et al. J Arthroplasty 2018;33:1309-1314

    主要标准 (任一命中 = 感染):
      - 窦道与关节腔相通
      - 两处或以上独立培养同种病原体

    次要标准 (累计 ≥6 分 = 感染; 2-5 分 = 可能感染; <2 分 = 未感染):
      - CRP >10 / D-dimer >860 (2 分)
      - ESR >30 (1 分)
      - 滑液 WBC >3000 / LE ++ (3 分)
      - 滑液 PMN >80% (2 分)
      - α-defensin 阳性 (3 分)
      - 单次培养阳性 (1 分)
      - 冰冻切片 >5 PMN/HPF (3 分)
      - 术中脓液 (3 分)

    Returns:
        diagnosis, score, criteria_detail
    """
    # Major criteria check
    major_hits: list[str] = []
    if sinus_tract:
        major_hits.append("窦道与关节腔相通 → 直接判定感染")
    if positive_cultures >= 2 and same_organism:
        major_hits.append("≥2 次独立培养同种病原体 → 直接判定感染")

    if major_hits:
        return {
            "status": "ok",
            "diagnosis": "感染 (Confirmed Infection)",
            "confidence": "确诊",
            "major_criteria_hit": True,
            "major_hits": major_hits,
            "minor_score": 0,
            "minor_threshold": "N/A (主要标准已满足)",
            "recommendation": "建议二期翻修 (间隔器取出 + 抗生素骨水泥 spacer + 延迟再置入)",
            "evidence": ["MSIS/ICM 2018 PJI Definition", "Parvizi J et al. J Arthroplasty 2018"],
        }

    # Minor criteria scoring
    minor_score = 0
    minor_hits: list[dict] = []

    if crp > 10 or d_dimer > 860:
        minor_score += 2
        minor_hits.append({"criterion": "elevated_crp", "points": 2,
                           "detail": f"CRP={crp}, D-dimer={d_dimer}"})
    if esr > 30:
        minor_score += 1
        minor_hits.append({"criterion": "elevated_esr", "points": 1, "detail": f"ESR={esr}"})
    if synovial_wbc > 3000:
        minor_score += 3
        minor_hits.append({"criterion": "elevated_synovial_wbc", "points": 3,
                           "detail": f"Synovial WBC={synovial_wbc}"})
    if pmn_pct > 80:
        minor_score += 2
        minor_hits.append({"criterion": "elevated_pmn_pct", "points": 2, "detail": f"PMN={pmn_pct}%"})
    if alpha_defensin_positive:
        minor_score += 3
        minor_hits.append({"criterion": "alpha_defensin", "points": 3, "detail": "阳性"})
    if positive_cultures == 1:
        minor_score += 1
        minor_hits.append({"criterion": "single_positive_culture", "points": 1, "detail": "单次培养阳性"})
    if frozen_section_positive:
        minor_score += 3
        minor_hits.append({"criterion": "frozen_section_positive", "points": 3, "detail": ">5 PMN/HPF"})
    if intraop_purulence:
        minor_score += 3
        minor_hits.append({"criterion": "intraop_purulence", "points": 3, "detail": "术中脓液"})

    if minor_score >= 6:
        diagnosis = "感染 (Confirmed Infection)"
        confidence = "确诊"
        recommendation = "建议二期翻修 (取出假体 + 抗生素骨水泥 spacer + 静脉抗生素 6 周 + "
        recommendation += "二期再置入)"
    elif minor_score >= 2:
        diagnosis = "可疑感染 (Possibly Infected)"
        confidence = "疑似"
        recommendation = "建议关节穿刺 + 滑液分析 (WBC/PMN/培养/α-defensin) → "
        recommendation += "若满足条件考虑清创保留假体 (DAIR)"
    else:
        diagnosis = "未感染 (Not Infected)"
        confidence = "排除"
        recommendation = "考虑无菌性松动/磨损/不稳等非感染原因 → 可行一期翻修"

    return {
        "status": "ok",
        "diagnosis": diagnosis,
        "confidence": confidence,
        "major_criteria_hit": False,
        "major_hits": [],
        "minor_score": minor_score,
        "minor_hits": minor_hits,
        "minor_threshold": f"≥6=感染 | 2-5=可能感染 | <2=未感染 (当前={minor_score})",
        "recommendation": recommendation,
        "evidence": ["MSIS/ICM 2018 PJI Definition", "Parvizi J et al. J Arthroplasty 2018"],
    }


# ═══════════════════════════════════════════════════════════
# 4. THA/TKA 术前规划
# ═══════════════════════════════════════════════════════════

THA_INDICATIONS: list[str] = [
    "晚期骨关节炎 (Kellgren-Lawrence III-IV)",
    "股骨头坏死 (ARCO III-IV)",
    "发育性髋关节发育不良 (DDH Crowe II-IV)",
    "股骨颈骨折 (Garden III-IV, 高龄)",
    "类风湿关节炎终末期",
    "强直性脊柱炎累及髋关节",
]

TKA_INDICATIONS: list[str] = [
    "晚期膝骨关节炎 (Kellgren-Lawrence III-IV)",
    "类风湿关节炎终末期",
    "创伤后关节炎",
    "膝关节内翻/外翻畸形 >15°",
    "膝关节僵硬 (ROM <50°)",
]

CONTRAINDICATIONS: list[str] = [
    "活动性感染 (局部/全身)",
    "严重血管疾病 (下肢缺血)",
    "伸膝装置功能丧失 (TKA 禁忌)",
    "Charcot 关节病",
    "严重内科合并症 (不能耐受手术, ASA ≥4)",
]


def tha_tka_planning(
    joint: str = "",
    diagnosis: str = "",
    age: int = 0,
    bmi: float = 0,
    infection_risk: str = "low",
    bone_quality: str = "normal",
    deformity_degree: str = "",
    prior_surgery: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """THA/TKA 置换术前规划 — 适应证核对 + 假体类型建议.

    Args:
        joint: 关节 (hip/knee)
        diagnosis: 诊断
        age: 年龄
        bmi: BMI
        infection_risk: 感染风险 (low/medium/high)
        bone_quality: 骨质量 (normal/osteopenia/osteoporosis)
        deformity_degree: 畸形度 (轻度/中度/重度)
        prior_surgery: 既往手术史

    Returns:
        适应证核对 + 假体类型 + 固定方式
    """
    joint_lower = joint.lower()
    dx_lower = diagnosis.lower()

    if "hip" in joint_lower or "髋" in joint_lower:
        procedure_type = "THA (人工全髋关节置换)"
        indications_list = THA_INDICATIONS
        bone_quality_info = {
            "normal": "生物型 (cementless) — 多孔涂层 + HA 喷涂",
            "osteopenia": "生物型 + 大直径股骨头 (36mm+) 降低脱位风险",
            "osteoporosis": "骨水泥型 (cemented) 或混合固定 (hybrid)",
        }
        approach_options = ["后外侧入路 (Moore)", "直接前入路 (DAA / AMIS)", "前外侧入路 (Watson-Jones)"]
        specific_note = ("髋臼侧: 压配式生物杯 (正常骨量) / 骨水泥杯 (骨质疏松); "
                         "股骨侧: 锥形柄 (Dorr A-B) / 骨水泥柄 (Dorr C)")
    elif "knee" in joint_lower or "膝" in joint_lower:
        procedure_type = "TKA (人工全膝关节置换)"
        indications_list = TKA_INDICATIONS
        bone_quality_info = {
            "normal": "生物型 + 骨水泥辅助 (hybrid)",
            "osteopenia": "骨水泥型 (cemented) — 标准胫骨托 + 股骨组件",
            "osteoporosis": "骨水泥型 + 延长杆 / 楔形垫块",
        }
        approach_options = ["前正中切口 + 内侧髌旁入路", "经股内侧肌入路 (mid-vastus)", "微创 (MIS-TKA)"]
        specific_note = ("CR (后交叉韧带保留型) — 适合 PCL 功能良好; "
                         "PS (后稳定型) — PCL 缺失/严重畸形 >15°; "
                         "CCK (髁限制型) — 内外侧副韧带功能不全")
    else:
        return {"status": "error", "error": "请指定关节类型 (hip/knee)"}

    matched = []
    for ind in indications_list:
        for kw in ind.split("—")[0].split("/"):
            if kw.strip().lower()[:3] in dx_lower or kw.strip().lower() in dx_lower:
                matched.append(ind)
                break
    if not matched and age >= 60:
        matched.append(f"年龄 {age} 岁 — 关节置换适应年龄范围")

    contraindicated: list[str] = []
    if infection_risk == "high":
        contraindicated.append("感染风险高 — 需先控制感染/排除 PJI")
    if bmi > 40:
        contraindicated.append(f"BMI={bmi} >40 — 感染/并发症风险显著增加, 建议减重后再手术")

    fixation = bone_quality_info.get(bone_quality, bone_quality_info["normal"])
    approach = approach_options[0] if age < 75 else "后外侧入路 (标准, 更适合高龄)"

    if deformity_degree in ("重度", "severe") and "knee" in joint_lower:
        specific_note += "; 严重畸形需考虑 CCK 假体或增加延长杆"

    return {
        "status": "ok",
        "procedure": procedure_type,
        "joint": "髋关节" if "hip" in joint_lower else "膝关节",
        "diagnosis": diagnosis,
        "indications_matched": matched,
        "indications_count": len(matched),
        "contraindications": contraindicated,
        "cleared_for_surgery": len(contraindicated) == 0,
        "fixation": fixation,
        "approach_options": approach_options,
        "recommended_approach": approach,
        "specific_note": specific_note,
        "preop_checklist": [
            "术前模板测量 (数字化 X 光片)",
            "双下肢全长 X 光 (TKA — 力线评估)",
            "骨盆正位 + 蛙式位 (THA)",
            "感染筛查: CRP/ESR/IL-6 + 必要时关节穿刺",
            "血液科/心内科/麻醉科会诊 (≥65 岁)",
            "备血 (THA) / 氨甲环酸 (TKA+THA)",
            "牙齿/泌尿/皮肤感染灶排查",
        ],
        "evidence": ["AAOS THA CPG 2023", "AAHKS TKA Guidelines", "中国关节置换围术期管理指南 2022"],
    }


# ═══════════════════════════════════════════════════════════
# 5. ERAS 路径 (THA/TKA)
# ═══════════════════════════════════════════════════════════

ERAS_CHECKLIST: dict[str, list[dict]] = {
    "preop_day1": [
        {"id": "education", "item": "术前宣教 (手术流程 + 康复预期 + 疼痛管理)",
         "responsible": "主管医师/护士", "done": False},
        {"id": "nutrition", "item": "术前营养评估 (Alb/前Alb) + 营养支持",
         "responsible": "营养科", "done": False},
        {"id": "anemia", "item": "贫血筛查 (Hb) + 术前纠正 (EPO/铁剂)",
         "responsible": "主管医师", "done": False},
        {"id": "smoking", "item": "戒烟指导 (术前 ≥4 周)", "responsible": "护士", "done": False},
        {"id": "comorbidity", "item": "合并症优化 (血糖 HbA1c<7.5%, 血压<160/100)",
         "responsible": "主管医师/内科", "done": False},
    ],
    "preop_day0": [
        {"id": "fasting", "item": "术前 6h 禁食 / 2h 禁水 / 术前 2h 饮碳水化合物 200ml",
         "responsible": "护士", "done": False},
        {"id": "premed", "item": "术前口服塞来昔布 400mg + 加巴喷丁 300mg (多模式镇痛)",
         "responsible": "麻醉医师", "done": False},
    ],
    "intraop": [
        {"id": "txa", "item": "氨甲环酸 (TXA): 切皮前 1g IV + 局部 1g 关节腔注射",
         "responsible": "麻醉医师", "done": False},
        {"id": "lai", "item": "关节周围局部浸润镇痛 (罗哌卡因 + 酮咯酸 + 肾上腺素)",
         "responsible": "术者", "done": False},
        {"id": "fluid", "item": "目标导向液体管理 (维持 MAP>65, 尿量>0.5ml/kg/h)",
         "responsible": "麻醉医师", "done": False},
        {"id": "temp", "item": "术中保温 ≥36°C (加温毯 + 液体加温)",
         "responsible": "麻醉护士", "done": False},
        {"id": "drain", "item": "不常规放置引流管 (无益+增加感染)",
         "responsible": "术者", "done": False},
        {"id": "catheter", "item": "不常规留置尿管 (如留置, 24h 内拔除)",
         "responsible": "术者/麻醉医师", "done": False},
    ],
    "postop_day0": [
        {"id": "mobilize_d0", "item": "术后 4-6h 首次下地站立/行走 (助行器辅助)",
         "responsible": "护士/康复师", "done": False},
        {"id": "analgesia_d0", "item": "多模式镇痛: 塞来昔布 200mg bid + 对乙酰氨基酚 1g q6h + "
                                     "冰敷 20min q4h", "responsible": "护士", "done": False},
        {"id": "nausea", "item": "PONV 预防: 昂丹司琼 4mg IV prn", "responsible": "护士", "done": False},
        {"id": "dvt_d0", "item": "DVT 预防: IPC + GCS + 踝泵 20 次/h",
         "responsible": "护士/康复师", "done": False},
    ],
    "postop_day1": [
        {"id": "mobilize_d1", "item": "每日下地 3 次 + 步行训练 (渐进距离)",
         "responsible": "康复师", "done": False},
        {"id": "wound", "item": "伤口观察 (渗血/红肿/皮温) + 换药",
         "responsible": "护士/医师", "done": False},
        {"id": "labs", "item": "复查 Hb + CRP + ESR (疑感染时第 3 天)",
         "responsible": "主管医师", "done": False},
        {"id": "dvt_med", "item": "利伐沙班 10mg qd 或 LMWH (术后 6-12h 启动)",
         "responsible": "主管医师", "done": False},
    ],
    "discharge": [
        {"id": "dc_pain", "item": "VAS ≤3 (静息) + ≤5 (活动)", "responsible": "主管医师", "done": False},
        {"id": "dc_wound", "item": "伤口干燥无感染征象", "responsible": "护士/医师", "done": False},
        {"id": "dc_mobilize", "item": "可独立转移 + 助行器行走 ≥50m + 上下楼梯 ≥3 级",
         "responsible": "康复师", "done": False},
        {"id": "dc_education", "item": "出院指导 (用药/伤口/康复/红旗征/复查时间)",
         "responsible": "护士", "done": False},
    ],
}


def eras_pathway(
    procedure: str = "",
    patient_id: str = "",
    age: int = 0,
    comorbidities: list[str] | None = None,
    current_phase: str = "preop",
    **kwargs: Any,
) -> dict[str, Any]:
    """THA/TKA ERAS 快速康复路径 (增强术后恢复).

    参考: ERAS Society Guidelines for THA/TKA (2021) + 中国 ERAS 关节置换专家共识 2022

    Args:
        procedure: 手术类型 (THA/TKA)
        patient_id: 患者 ID
        age: 患者年龄
        comorbidities: 合并症列表
        current_phase: 当前阶段 (preop/intraop/postop/discharge)

    Returns:
        各阶段 checklist + 完成标准
    """
    comorbidities = comorbidities or []
    proc_lower = procedure.upper()
    if "THA" in proc_lower:
        proc_name = "人工全髋关节置换术 (THA)"
    elif "TKA" in proc_lower:
        proc_name = "人工全膝关节置换术 (TKA)"
    else:
        proc_name = procedure

    phases = {}

    for phase_name, items in ERAS_CHECKLIST.items():
        phases[phase_name] = {
            "label": phase_name.replace("_", " ").title(),
            "items": [dict(i) for i in items],
            "total": len(items),
        }

    high_risk_mods: list[str] = []
    combs_lower = " ".join(com.lower() for com in comorbidities)

    if any(k in combs_lower for k in ["糖尿病", "dm", "diabete"]):
        high_risk_mods.append("糖尿病患者: 围术期血糖目标 6-10 mmol/L, 术前 HbA1c <7.5%")
    if any(k in combs_lower for k in ["冠心病", "心衰", "cad", "chf"]):
        high_risk_mods.append("心脏病患者: 心内科会诊 + 术中监测 + 术后 ECG")
    if any(k in combs_lower for k in ["copd", "哮喘"]):
        high_risk_mods.append("肺部疾病: 呼吸训练 + 雾化 + 早期下地预防肺炎")
    if age >= 80:
        high_risk_mods.append("高龄 (>80): 加强谵妄监测 + 防跌倒 + 营养支持")
    if "血栓" in combs_lower or "dvt" in combs_lower:
        high_risk_mods.append("VTE 高风险: 术后抗凝延长至 35 天")

    discharge_criteria_met = all(
        phases["discharge"]["items"][i]["done"]
        for i in range(len(phases["discharge"]["items"]))
    ) or False

    expected_los = "1-2 天" if all(not m for m in high_risk_mods) else "3-5 天"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "procedure": proc_name,
        "phases": phases,
        "high_risk_modifications": high_risk_mods,
        "expected_length_of_stay": expected_los,
        "discharge_criteria": [item["item"] for item in phases["discharge"]["items"]],
        "discharge_criteria_met": discharge_criteria_met,
        "evidence": [
            "ERAS Society Guidelines for THA/TKA (2021)",
            "中国 ERAS 关节置换专家共识 2022",
            "JBJS ERAS Pathways 2020",
        ],
        "key_principles": [
            "多模式镇痛 — 减少阿片类药物使用",
            "氨甲环酸 (TXA) — 减少失血和输血",
            "早期下地 (D0) — 缩短住院日 + 降低 DVT",
            "不常规留置引流管/尿管 — 降低感染率",
            "DVT 药物预防 14-35 天",
        ],
    }


# ═══════════════════════════════════════════════════════════
# 6. 翻修评估
# ═══════════════════════════════════════════════════════════

LOOSENING_PATTERNS: dict[str, dict] = {
    "mechanical_loosening": {
        "label": "无菌性松动 (Mechanical Loosening)",
        "xray_findings": ["假体周围透亮线 ≥2mm (连续)", "假体移位 >3mm", "骨水泥断裂", "骨-骨水泥界面透亮带"],
        "symptoms": ["启动痛 (活动开始时疼痛)", "负重痛加重", "静止时疼痛减轻"],
        "revision_strategy": "一期翻修 (更换假体 + 必要时植骨 / 垫块加强)",
    },
    "septic_loosening": {
        "label": "感染性松动 (Septic Loosening)",
        "xray_findings": ["假体周围不规则透亮线", "骨膜反应", "窦道形成", "快速进展的骨溶解"],
        "symptoms": ["静息痛", "夜间痛", "局部红肿热", "发热/寒战", "CRP/ESR 升高"],
        "revision_strategy": "二期翻修: 取出假体 + 抗生素骨水泥 spacer + IV 抗生素 6 周 + 再置入",
    },
}

WEAR_PATTERNS: dict[str, dict] = {
    "poly_wear": {
        "label": "聚乙烯磨损",
        "finding": "关节间隙不对称变窄 + 关节线偏移",
        "revision": "更换聚乙烯内衬 (liner exchange) + 必要时更换股骨头",
    },
    "osteolysis": {
        "label": "骨溶解",
        "finding": "假体周围囊性/扇形骨吸收 >5mm",
        "revision": "植骨 (同种异体/人工骨) + 更换假体组件",
    },
    "metallosis": {
        "label": "金属病 (Metallosis)",
        "finding": "金属-金属界面磨损 → 软组织金属染色 (ALVAL)",
        "revision": "更换为非金属界面 (陶瓷-聚乙烯 或 陶瓷-陶瓷)",
    },
}

INSTABILITY_PATTERNS: dict[str, dict] = {
    "thk_dislocation": {
        "label": "THA 脱位",
        "mechanism": ["位置不当 (杯/柄前倾角异常)", "软组织松弛", "撞击 (impingement)", "肌力减退"],
        "revision": "更换双动杯 (dual mobility) / 限制性内衬 / 纠正位置",
    },
    "tka_instability": {
        "label": "TKA 不稳",
        "mechanism": ["屈曲不稳", "伸直不稳", "膝反屈"],
        "revision": "更换为 PS / CCK / 铰链膝 (根据不稳类型)",
    },
}


def revision_assessment(
    joint: str = "",
    issue_type: str = "",
    lab_crp: float = 0,
    lab_esr: float = 0,
    symptoms: list[str] | None = None,
    xray_findings: list[str] | None = None,
    prior_revision_count: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """翻修评估 — 松动/磨损/不稳分型 → 翻修策略.

    参考: AAOS Revision THA/TKA Guidelines / Paprosky 分型 / AAHKS

    Args:
        joint: 关节 (hip/knee)
        issue_type: 主要问题 (loosening/wear/instability/pain)
        lab_crp: CRP (mg/L)
        lab_esr: ESR (mm/h)
        symptoms: 症状
        xray_findings: X 光/CT 发现
        prior_revision_count: 既往翻修次数

    Returns:
        病因分型 + 翻修策略 + 骨缺损分级
    """
    symptoms = symptoms or []
    xray_findings = xray_findings or []
    all_symptoms = " ".join(s.lower() for s in symptoms)
    all_xray = " ".join(x.lower() for x in xray_findings)
    all_text = all_symptoms + " " + all_xray

    infection_likely = lab_crp > 10 or lab_esr > 30 or any(
        k in all_text for k in ["红肿", "发热", "窦道", "静息痛", "夜间痛", "红肿热"]
    )

    etiology: list[dict] = []
    revision_plan: list[str] = []

    if issue_type.lower() in ("loosening", "松动"):
        if infection_likely:
            etiology.append({"type": "septic_loosening", **LOOSENING_PATTERNS["septic_loosening"]})
            revision_plan.append("取出所有假体组件 + 抗生素骨水泥 spacer")
            revision_plan.append("静脉抗生素 6 周 (根据培养/药敏)")
            revision_plan.append("二期再置入 (CRP/ESR 正常后)")
        else:
            etiology.append({"type": "mechanical_loosening", **LOOSENING_PATTERNS["mechanical_loosening"]})
            revision_plan.append("一期翻修更换假体")
            if "溶骨" in all_xray or "骨吸收" in all_xray:
                revision_plan.append("植骨 (同种异体颗粒骨 / 结构性植骨)")
            if any(k in all_xray for k in ["大段", ">5mm"]):
                revision_plan.append("垫块/延长杆/杯笼 (Paprosky IIIA/IIIB)")

    if issue_type.lower() in ("wear", "磨损", "骨溶解"):
        for wear_type, info in WEAR_PATTERNS.items():
            if any(k in all_text for k in [wear_type[:4], info["label"][:3]]):
                etiology.append({"type": wear_type, **info})
                revision_plan.append(info["revision"])
        if issue_type in ("磨损", "wear") and "骨溶解" not in all_text:
            etiology.append(WEAR_PATTERNS["poly_wear"])
            etiology[-1]["type"] = "poly_wear"
            revision_plan.append(WEAR_PATTERNS["poly_wear"]["revision"])

    if issue_type.lower() in ("instability", "不稳", "脱位"):
        if "hip" in joint.lower() or "髋" in joint.lower() or "th" in joint.lower():
            pattern = INSTABILITY_PATTERNS["thk_dislocation"]
        else:
            pattern = INSTABILITY_PATTERNS["tka_instability"]
        etiology.append({"type": "instability", **pattern})
        revision_plan.append(pattern["revision"])

    if not etiology:
        etiology.append({"type": "unknown", "label": "待明确 — 需进一步检查",
                         "revision_strategy": "关节穿刺 + 增强 MRI/CT + 核素扫描 (Tc-99m/SPECT-CT)"})
        revision_plan.append("诊断性检查: CRP/ESR/IL-6 + 关节穿刺培养 + 核素扫描")

    risk_level = "high" if infection_likely or prior_revision_count >= 2 else "moderate" if prior_revision_count >= 1 else "standard"

    return {
        "status": "ok",
        "joint": "髋关节" if "hip" in joint.lower() else "膝关节" if "knee" in joint.lower() else joint,
        "etiology": etiology,
        "infection_likely": infection_likely,
        "revision_plan": revision_plan,
        "risk_level": risk_level,
        "prior_revision_count": prior_revision_count,
        "preop_workup": [
            "CRP + ESR + IL-6 (感染筛查)",
            "关节穿刺: 细胞计数 + PMN% + 培养 (需氧+厌氧) + α-defensin",
            "X 光 (正侧位 + 斜位) / CT 薄层扫描 (骨缺损评估)",
            "核素扫描 (Tc-99m MDP + 白细胞标记) — 怀疑感染时",
            "术前模板测量 + 备好翻修假体 (延长杆/垫块/限制性内衬)",
        ],
        "revision_implants_required": [
            "取出器械 (通用/特殊)",
            "抗生素骨水泥 spacer (感染) / 翻修假体系统 (无菌)",
            "垫块 (金属/聚乙烯) / 延长杆",
            "植骨材料 (同种异体骨/人工骨)",
            "限制性内衬 / CCK / 铰链膝 (根据不稳类型)",
        ],
        "evidence": ["AAOS Revision THA CPG", "AAHKS Revision TKA Guidelines", "Paprosky Classification 1994"],
    }
