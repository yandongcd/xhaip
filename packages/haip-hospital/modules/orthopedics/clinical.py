"""骨科 — X光分析 + LLM增强 + Harris评分 + 量表."""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════
# 1. 骨折 X 光图像分析 (fracture_analyzer)
# ═══════════════════════════════════════════════

EVANS_CLASSIFICATION = {
    "type_I": {"stable": True, "description": "单纯骨折, 无移位或轻微移位", "surgery": "PFNA/InterTAN"},
    "type_II": {"stable": False, "description": "内侧壁不完整, 小转子骨折", "surgery": "PFNA"},
    "type_III": {"stable": False, "description": "粉碎性, 不稳定", "surgery": "PFNA + 螺旋刀片"},
    "type_IV": {"stable": False, "description": "反斜行, 严重不稳定", "surgery": "PFNA/InterTAN/人工股骨头"},
}


def analyze_xray(
    patient_id: str = "",
    view: str = "AP",
    findings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """X 光骨折分析 (规则引擎, 非深度学习).

    输入:
        findings: {"location": "femoral_neck/neck/trochanteric/subtroch",
                   "displacement": "none/mild/moderate/severe",
                   "communition": bool,
                   "medial_wall": bool,
                   "reverse_oblique": bool,
                   "neck_shaft_angle": float}
    """
    findings = findings or {}
    location = findings.get("location", "unknown")
    displacement = findings.get("displacement", "none")
    comminution = findings.get("communition", False)
    medial_wall = findings.get("medial_wall", True)
    reverse_oblique = findings.get("reverse_oblique", False)
    nsa = findings.get("neck_shaft_angle", 130)

    # Evans 分型
    evans_type = "unknown"
    if not comminution and medial_wall:
        evans_type = "type_I"
    elif comminution and medial_wall:
        evans_type = "type_II"
    elif comminution and not medial_wall and not reverse_oblique:
        evans_type = "type_III"
    elif reverse_oblique:
        evans_type = "type_IV"

    evans_info = EVANS_CLASSIFICATION.get(evans_type, {"stable": True, "description": "", "surgery": "需进一步评估"})
    stable = evans_info["stable"]
    surgery = evans_info["surgery"]

    # Garden 分型 (股骨颈)
    garden = "unknown"
    if location == "femoral_neck":
        if displacement == "none":
            garden = "I/II (无移位/嵌插)"
        elif displacement in ("mild", "moderate"):
            garden = "III (部分移位)"
        else:
            garden = "IV (完全移位)"

    # AO/OTA
    ao_type = ""
    if location == "femoral_neck":
        ao_type = "31-B"
    elif location == "trochanteric":
        ao_type = "31-A1" if stable else "31-A2" if not reverse_oblique else "31-A3"
    elif location == "subtroch":
        ao_type = "32-A"

    return {
        "patient_id": patient_id, "view": view,
        "evans_type": evans_type, "evans_desc": evans_info["description"],
        "garden": garden, "ao_ota": ao_type,
        "stable": stable, "surgery_recommendation": surgery,
        "confidence": "high" if evans_type != "unknown" else "low",
    }


# ═══════════════════════════════════════════════
# 2. LLM 增强解析 (llm_entry — 规则引擎模式)
# ═══════════════════════════════════════════════

CLINICAL_PATTERNS = {
    "age": [r"(\d+)岁", r"age[:：]\s*(\d+)"],
    "gender": [r"男", r"女", r"male", r"female"],
    "diagnosis": [r"诊断[:：]\s*(.+?)(?:[。\n]|$)", r"入院诊断[:：]\s*(.+?)(?:[。\n]|$)"],
    "fracture_type": [r"(股骨颈|转子间|转子下|股骨干|肱骨|桡骨|胫骨|腰椎)",
                    r"(femoral neck|intertrochanteric|subtrochanteric)"],
    "surgery_type": [r"(THA|HA|PFNA|DHS|CCS|全髋|半髋|髓内钉)", r"拟行[:：]\s*(.+?)(?:[。\n]|$)"],
    "comorbidity": [r"(高血压|糖尿病|冠心病|COPD|心衰|肾功能不全|肝硬化|卒中)"],
    "medication": [r"(华法林|阿司匹林|氯吡格雷|利伐沙班|阿哌沙班|依诺肝素|他汀|胰岛素|二甲双胍)"],
    "allergy": [r"(青霉素|头孢|磺胺|阿司匹林|NSAIDs|造影剂)"],
}

import re


def parse_clinical_text(text: str) -> dict[str, Any]:
    """规则引擎解析自然语言临床文本 → 结构化患者数据。

    输入: "78岁男性，因摔伤致左髋疼痛2小时入院。诊断:左股骨转子间骨折。
          高血压病史10年，口服华法林2.5mg qd。青霉素过敏。"

    输出: {"age": 78, "gender": "M", "diagnosis": "左股骨转子间骨折", ...}
    """
    result: dict[str, Any] = {}
    text_lower = text.lower()

    # 年龄
    import re
    m = re.search(r"(\d+)岁", text)
    if m:
        result["age"] = int(m.group(1))

    # 性别
    if "女" in text:
        result["gender"] = "F"
    elif "男" in text:
        result["gender"] = "M"

    # 诊断
    m = re.search(r"诊断[:：]\s*(.+?)[。\n,，]", text)
    if m:
        result["diagnosis"] = m.group(1).strip()

    # 骨折类型
    ft_map = {"股骨颈": "femoral neck", "转子间": "intertrochanteric",
              "转子下": "subtrochanteric", "股骨干": "femoral shaft"}
    for cn, en in ft_map.items():
        if cn in text:
            result["fracture_type"] = en
            result["hip_fracture"] = True if en != "femoral shaft" else False
            break

    # 手术方式
    surgery_map = {"THA": "THA", "全髋": "THA", "HA": "HA", "半髋": "HA",
                   "PFNA": "PFNA", "髓内钉": "PFNA/InterTAN",
                   "DHS": "DHS", "CCS": "CCS"}
    for kw, proc in surgery_map.items():
        if kw in text:
            result["planned_surgery"] = proc
            break

    # 合并症
    comorbidities = []
    for kw in ["高血压", "糖尿病", "冠心病", "COPD", "心衰", "肾功能不全", "肝硬化", "卒中"]:
        if kw in text:
            comorbidities.append(kw)
    if comorbidities:
        result["comorbidities"] = comorbidities

    # 药物
    meds = []
    for kw in ["华法林", "阿司匹林", "氯吡格雷", "利伐沙班", "阿哌沙班", "依诺肝素"]:
        if kw in text:
            meds.append(kw)
    if meds:
        result["medications"] = meds

    # 过敏
    allergies = []
    for kw in ["青霉素", "头孢", "磺胺", "阿司匹林过敏", "NSAIDs", "造影剂"]:
        if kw in text:
            allergies.append(kw)
    if allergies:
        result["allergies"] = allergies

    # 紧急标志
    result["emergency"] = any(kw in text for kw in ["绿色通道", "急诊", "紧急", "emergency", "urgent", "48h"])
    result["mdt_required"] = any(kw in text for kw in ["多学科", "MDT", "联合会诊"])

    return result


# ═══════════════════════════════════════════════
# 3. Harris 髋关节评分
# ═══════════════════════════════════════════════

class HarrisHipScore:
    """Harris 髋关节评分 (100分制).

    - 疼痛 (44): 无/轻微/中度/重度/完全不能
    - 功能 (47): 步态(11)+支撑(11)+距离(11)+楼梯(4)+穿袜(4)+坐(5)+交通(1)
    - 畸形 (4): 固定内收/内旋/屈曲挛缩/下肢不等长
    - 活动度 (5): 屈曲/外展/内收/外旋/内旋 综合
    """

    @staticmethod
    def calculate(
        pain: str = "none",
        gait: str = "normal",
        support: str = "none",
        distance: str = "unlimited",
        stairs: str = "normal",
        socks: str = "easy",
        sitting: str = "comfortable",
        transport: str = "easy",
        deformity: list[str] | None = None,
        rom: int = 5,
    ) -> dict[str, Any]:
        deformity = deformity or []
        score = 0

        # Pain (0-44)
        pain_map = {"none": 44, "slight": 40, "mild": 30, "moderate": 20, "severe": 10, "disabled": 0}
        score += pain_map.get(pain, 30)

        # Gait (0-11)
        gait_map = {"normal": 11, "slight_limp": 8, "moderate_limp": 5, "severe_limp": 0}
        score += gait_map.get(gait, 8)

        # Support (0-11)
        support_map = {"none": 11, "cane_long": 7, "cane_short": 5, "crutch": 4, "two_canes": 2, "walker": 0}
        score += support_map.get(support, 7)

        # Distance (0-11)
        dist_map = {"unlimited": 11, "six_blocks": 8, "three_blocks": 5, "indoor": 2, "bed": 0}
        score += dist_map.get(distance, 8)

        # Stairs (0-4)
        stairs_map = {"normal": 4, "rail": 2, "difficult": 1, "unable": 0}
        score += stairs_map.get(stairs, 2)

        # Socks/Shoes (0-4)
        socks_map = {"easy": 4, "difficult": 2, "unable": 0}
        score += socks_map.get(socks, 3)

        # Sitting (0-5)
        sit_map = {"comfortable": 5, "high_chair": 3, "uncomfortable": 0}
        score += sit_map.get(sitting, 4)

        # Transport (0-1)
        score += 1 if transport == "easy" else 0

        # Deformity (0-4, 扣分制)
        ded = min(4, len(deformity))
        score -= ded

        # ROM (0-5)
        score += max(0, min(5, rom))

        grade = "优" if score >= 90 else "良" if score >= 80 else "可" if score >= 70 else "差"
        return {"harris_score": max(0, min(100, score)), "grade": grade,
                "components": {"pain": pain, "gait": gait, "support": support},
                "target_reached": score >= 80}


def harris_score(**kwargs) -> dict[str, Any]:
    return HarrisHipScore.calculate(**kwargs)


# ═══════════════════════════════════════════════
# 4. 骨折分型 (fracture_classifier — rule-based only)
# ═══════════════════════════════════════════════

GARDEN_CLASSIFICATION: list[dict[str, Any]] = [
    {"type": "Garden IV", "description": "完全骨折伴完全移位", "stability": "不稳定",
     "treatment": "关节置换术"},
    {"type": "Garden III", "description": "完全骨折伴部分移位", "stability": "不稳定",
     "treatment": "内固定/关节置换"},
    {"type": "Garden II", "description": "完全骨折但无移位", "stability": "稳定",
     "treatment": "内固定术"},
    {"type": "Garden I", "description": "不完全骨折或外展嵌插骨折", "stability": "稳定",
     "treatment": "可考虑保守治疗或内固定"},
]

EVANS_CLASSIFICATION_FULL: list[dict[str, Any]] = [
    {"type": "Evans I", "subtypes": "IA(无移位)/IB(有移位但后内侧皮质完整)/IC(后内侧皮质断裂)/ID(转子下延伸)",
     "stability": "IA稳定/IB-D不稳定", "treatment": "PFNA/InterTAN"},
    {"type": "Evans II", "description": "逆斜型骨折", "stability": "不稳定",
     "treatment": "PFNA/InterTAN(注意防内翻)"},
    {"type": "Evans III", "description": "转子下延伸型骨折", "stability": "极不稳定",
     "treatment": "长PFNA/钢板"},
]

AO_OTA_HIP: list[dict[str, Any]] = [
    {"code": "31-A", "description": "股骨转子间骨折",
     "subtypes": "A1(简单)/A2(多块)/A3(逆斜)"},
    {"code": "31-B", "description": "股骨颈骨折",
     "subtypes": "B1(头下型轻移位)/B2(经颈型)/B3(头下型明显移位)"},
    {"code": "31-C", "description": "股骨头骨折",
     "subtypes": "C1(劈裂)/C2(伴凹陷)/C3(伴颈骨折)"},
]

_POSTOP_KEYWORDS: list[str] = [
    "术后", "内固定术后", "关节置换术后", "PFNA术后", "InterTAN术后",
    "THA术后", "HA术后", "钢板内固定术后", "空心钉术后", "骨水泥",
    "假体", "翻修", "愈合", "骨痂", "内固定物", "螺钉位置",
    "骨折愈合", "骨折线模糊", "内固定位置良好", "假体位置",
]


def _is_postop(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in _POSTOP_KEYWORDS)


def _match_classification(fracture_type: str, text: str) -> tuple[str, str, str, str]:
    """Match classification system and result."""
    if fracture_type == "股骨颈骨折":
        for g in GARDEN_CLASSIFICATION:
            if g["type"].lower() in text.lower() or g["description"] in text:
                return "Garden 分型", g["type"], g["stability"], g["treatment"]
        if "嵌插" in text or "外展" in text:
            return "Garden 分型", "Garden I(推测)", "稳定", "可考虑保守治疗或内固定"
        if "移位" not in text:
            return "Garden 分型", "Garden II(推测)", "稳定", "内固定术"
        if "完全移位" in text or "明显移位" in text:
            return "Garden 分型", "Garden IV(推测)", "不稳定", "关节置换术"
        return "Garden 分型", "Garden III(推测)", "不稳定", "内固定/关节置换"

    if fracture_type == "股骨转子间骨折":
        for e in EVANS_CLASSIFICATION_FULL:
            if e["type"].lower() in text.lower():
                return "Evans 分型", e["type"], e["stability"], e["treatment"]
        if "稳定" in text or "无移位" in text:
            return "Evans 分型", "Evans IA(推测)", "稳定", "PFNA/InterTAN"
        return "Evans 分型", "Evans 不稳定型(推测)", "不稳定", "PFNA/InterTAN"

    return "", "", "N/A", ""


def classify_hip_fracture(
    diagnosis: str = "",
    exam_result: str = "",
    patient_data: dict | None = None,
    phase: str = "preop",
) -> dict[str, Any]:
    """Classify hip fracture — rule-based (Garden I-IV, Evans I-III, AO/OTA 31-A/B/C).

    Args:
        diagnosis: Clinical diagnosis text.
        exam_result: Image description text.
        patient_data: Optional patient metadata (for compat).
        phase: "preop"(pre-op) | "postop"(post-op).

    Returns:
        Classification result dict. If phase="postop" or post-op keywords detected,
        returns redirect_to_stage_9 marker.
    """
    text = f"{diagnosis} {exam_result}"

    if phase == "postop" or _is_postop(text):
        return {
            "fracture_type": "术后评估",
            "side": "",
            "classification_system": "",
            "classification_type": "",
            "stability": "N/A",
            "surgery_recommendation": "",
            "details": "",
            "phase": "postop",
            "redirect_to_stage_9": True,
            "message": "术后评估由 Stage 9（术后影像评估）独立处理。",
        }

    side = "不确定"
    if "左" in text and "右" in text:
        side = "双侧"
    elif "左" in text:
        side = "左侧"
    elif "右" in text:
        side = "右侧"

    fracture_type = "不确定"
    if any(kw in text for kw in ["股骨颈", "股骨颈骨折", "femoral neck"]):
        fracture_type = "股骨颈骨折"
    elif any(kw in text for kw in ["转子间", "粗隆间", "转子间骨折", "intertrochanteric"]):
        fracture_type = "股骨转子间骨折"
    elif any(kw in text for kw in ["转子下", "粗隆下", "转子下骨折", "subtrochanteric"]):
        fracture_type = "股骨转子下骨折"
    elif any(kw in text for kw in ["髋部", "髋部骨折", "hip fracture"]):
        fracture_type = "髋部骨折(具体部位待影像确认)"

    system, ctype, stability, surgery = _match_classification(fracture_type, text)

    details_parts = []
    for kw in ["骨折", "骨皮质", "骨折线", "错位", "成角", "压缩", "粉碎"]:
        if kw in text:
            idx = text.find(kw)
            details_parts.append(text[max(0, idx - 10):idx + len(kw) + 20])

    return {
        "fracture_type": fracture_type,
        "side": side,
        "classification_system": system,
        "classification_type": ctype or "待影像确认分型",
        "stability": stability,
        "surgery_recommendation": surgery or "根据分型及患者全身状况综合决定",
        "details": ";".join(details_parts[:3]) if details_parts else "",
        "phase": "preop",
    }
