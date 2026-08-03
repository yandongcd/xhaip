# @origin: haip-0710/src/agents/domains/haip/orthopedic_surgery/core/fracture_classifier.py
# @origin_repo: https://github.com/yandongcd/haip
# @ported_date: 2026-07-12
# @status: ADAPTED (imports rewritten for xhaip engine)
#   Key deps to adapt:
#     agents.domains.haip.core.* -> packages/haip-hospital/modules/shared/
#     agents.harness.* -> packages/haip-core/haip/
#     Rule path resolution -> packages/haip-hospital/knowledge/rules/
"""F3.1 骨折分型判断 — 术前-only 分型 + 术后引导至 Stage 9.

核心原则（v2.0）:
    分型仅从术前数据判断：X线描述 + CT报告 + 临床诊断 + 患者主诉。
    术后评估由 Stage 9（术后影像评估）独立处理。

LLM增强版: classify_hip_fracture_llm() — 用LLM替代关键词匹配,提高泛化能力
规则版:   classify_hip_fracture() — 原有关键词匹配版本(降级方案)
混合版:   classify_hip_fracture_hybrid() — 优先LLM, 失败降级规则引擎
"""

from __future__ import annotations

from typing import Any

from shared.llm_adapter import call_llm_structured

from .prompts.fracture_classify import (
    OUTPUT_SCHEMA as LLM_OUTPUT_SCHEMA,
)
from .prompts.fracture_classify import (
    SYSTEM_PROMPT as LLM_SYSTEM_PROMPT,
)
from .prompts.fracture_classify import (
    build_prompt as _build_llm_prompt,
)

# 股骨颈骨折 Garden 分型（从高到低排序，避免子串误匹配）
GARDEN_CLASSIFICATION: list[dict[str, Any]] = [
    {"type": "Garden IV", "description": "完全骨折伴完全移位", "stability": "不稳定", "treatment": "关节置换术"},
    {"type": "Garden III", "description": "完全骨折伴部分移位", "stability": "不稳定", "treatment": "内固定/关节置换"},
    {"type": "Garden II", "description": "完全骨折但无移位", "stability": "稳定", "treatment": "内固定术"},
    {"type": "Garden I", "description": "不完全骨折或外展嵌插骨折", "stability": "稳定", "treatment": "可考虑保守治疗或内固定"},
]

# 股骨转子间骨折 Evans 分型
EVANS_CLASSIFICATION: list[dict[str, Any]] = [
    {"type": "Evans I", "subtypes": "IA(无移位)/IB(有移位但后内侧皮质完整)/IC(后内侧皮质断裂)/ID(转子下延伸)", "stability": "IA稳定/IB-D不稳定", "treatment": "PFNA/InterTAN"},
    {"type": "Evans II", "description": "逆斜型骨折", "stability": "不稳定", "treatment": "PFNA/InterTAN(注意防内翻)"},
    {"type": "Evans III", "description": "转子下延伸型骨折", "stability": "极不稳定", "treatment": "长PFNA/钢板"},
]

# AO/OTA 分型(髋部)
AO_OTA_HIP: list[dict[str, Any]] = [
    {"code": "31-A", "description": "股骨转子间骨折", "subtypes": "A1(简单)/A2(多块)/A3(逆斜)"},
    {"code": "31-B", "description": "股骨颈骨折", "subtypes": "B1(头下型轻移位)/B2(经颈型)/B3(头下型明显移位)"},
    {"code": "31-C", "description": "股骨头骨折", "subtypes": "C1(劈裂)/C2(伴凹陷)/C3(伴颈骨折)"},
]

# 术后关键词 — 命中任一即判定为术后数据，分型由 Stage 9 处理
_POSTOP_KEYWORDS: list[str] = [
    "术后", "内固定术后", "关节置换术后", "PFNA术后", "InterTAN术后",
    "THA术后", "HA术后", "钢板内固定术后", "空心钉术后", "骨水泥",
    "假体", "翻修", "愈合", "骨痂", "内固定物", "螺钉位置",
    "骨折愈合", "骨折线模糊", "内固定位置良好", "假体位置",
]


# ASSET:skill-hip-fracture-classify
def classify_hip_fracture(
    diagnosis: str = "",
    exam_result: str = "",
    patient_data: dict | None = None,
    phase: str = "preop",
) -> dict[str, Any]:
    """Classify hip fracture — 术前-only 分型.

    核心原则：分型仅从术前数据判断。术后数据由 Stage 9 处理。

    Args:
        diagnosis: 临床诊断文本
        exam_result: 影像学描述文本
        patient_data: 可选患者元数据 dict（兼容旧调用）
        phase: "preop"(术前) | "postop"(术后)，默认 preop

    Returns:
        分型结果 dict。若 phase="postop" 或检测到术后关键词，
        返回 redirect_to_stage_9 标记。
    """
    text = f"{diagnosis} {exam_result}"

    # ── 术后阶段检测 ──
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
            "message": "术后评估由 Stage 9（术后影像评估）独立处理，请切换到 Stage 9 进行评估。",
        }

    # ── 术前分型 ──
    return _classify_preop(text)


def _is_postop(text: str) -> bool:
    """检测文本是否包含术后关键词."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in _POSTOP_KEYWORDS)


def _classify_preop(text: str) -> dict[str, Any]:
    """纯术前分型核心逻辑."""
    # Determine side
    side = "不确定"
    if "左" in text and "右" in text:
        side = "双侧"
    elif "左" in text:
        side = "左侧"
    elif "右" in text:
        side = "右侧"

    # Extract fracture location
    fracture_type = "不确定"
    if any(kw in text for kw in ["股骨颈", "股骨颈骨折", "femoral neck"]):
        fracture_type = "股骨颈骨折"
    elif any(kw in text for kw in ["转子间", "粗隆间", "转子间骨折", "intertrochanteric"]):
        fracture_type = "股骨转子间骨折"
    elif any(kw in text for kw in ["转子下", "粗隆下", "转子下骨折", "subtrochanteric"]):
        fracture_type = "股骨转子下骨折"
    elif any(kw in text for kw in ["髋部", "髋部骨折", "hip fracture"]):
        fracture_type = "髋部骨折(具体部位待影像确认)"

    classification_system, classification_type, stability, surgery_recommendation = \
        _match_classification(fracture_type, text)

    details_parts = []
    for kw in ["骨折", "骨皮质", "骨折线", "错位", "成角", "压缩", "粉碎"]:
        if kw in text:
            idx = text.find(kw)
            details_parts.append(text[max(0, idx - 10):idx + len(kw) + 20])

    return {
        "fracture_type": fracture_type,
        "side": side,
        "classification_system": classification_system,
        "classification_type": classification_type or "待影像确认分型",
        "stability": stability,
        "surgery_recommendation": surgery_recommendation or "根据分型及患者全身状况综合决定",
        "details": ";".join(details_parts[:3]) if details_parts else "",
        "phase": "preop",
    }


def _match_classification(
    fracture_type: str, text: str,
) -> tuple[str, str, str, str]:
    """匹配分型系统与结果."""
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
        for e in EVANS_CLASSIFICATION:
            if e["type"].lower() in text.lower():
                return "Evans 分型", e["type"], e["stability"], e["treatment"]
        if "稳定" in text or "无移位" in text:
            return "Evans 分型", "Evans IA(推测)", "稳定", "PFNA/InterTAN"
        return "Evans 分型", "Evans 不稳定型(推测)", "不稳定", "PFNA/InterTAN"

    return "", "", "N/A", ""


def print_fracture_classification(result: dict[str, Any]) -> None:
    """Pretty-print the fracture classification result."""
    if result.get("redirect_to_stage_9"):
        print("===== 术后评估 ===== ")
        print(result.get("message", "术后评估由 Stage 9 处理"))
        return

    phase_label = "术前" if result.get("phase") == "preop" else "术后"
    print(f"===== 骨折分型判断 ({phase_label}) =====")
    print(f"骨折类型: {result['fracture_type']}")
    print(f"侧别: {result['side']}")
    print()
    print(f"分型系统: {result['classification_system']}")
    print(f"分型结果: {result['classification_type']}")
    print(f"稳定性: {result['stability']}")
    print()
    print(f"手术推荐: {result['surgery_recommendation']}")
    if result.get("details"):
        print(f"影像依据: {result['details']}")
    if result.get("guideline_ref"):
        print(f"指南引用: {result['guideline_ref']}")
    if result.get("confidence"):
        print(f"置信度: {result['confidence']}")


# ════════════════════════════════════════════════════════════
# LLM增强版 — 术前-only
# ════════════════════════════════════════════════════════════

def classify_hip_fracture_llm(
    diagnosis: str = "",
    exam_result: str = "",
    patient: dict | None = None,
    phase: str = "preop",
) -> dict[str, Any]:
    """LLM增强版骨折分型 — 术前-only，语义理解替代关键词匹配.

    Args:
        diagnosis: 临床诊断文本
        exam_result: 影像学描述文本
        patient: 患者信息 dict(含 age, gender, past_history 等)
        phase: "preop"(术前) | "postop"(术后)

    Returns:
        同 classify_hip_fracture() 格式,增加 guideline_ref 和 confidence
    """
    text = f"{diagnosis} {exam_result}"
    if patient is None:
        patient = {}

    # ── 术后阶段检测 ──
    if phase == "postop" or _is_postop(text):
        return {
            "fracture_type": "术后评估",
            "side": "",
            "classification_system": "",
            "classification_type": "",
            "stability": "N/A",
            "surgery_recommendation": "",
            "guideline_ref": "",
            "confidence": "N/A",
            "llm_generated": False,
            "phase": "postop",
            "redirect_to_stage_9": True,
            "message": "术后评估由 Stage 9（术后影像评估）独立处理。",
        }

    prompt = _build_llm_prompt(
        diagnosis=diagnosis,
        exam_result=exam_result,
        age=patient.get("age"),
        gender=patient.get("gender"),
        past_history=patient.get("past_history", ""),
    )

    llm_result = call_llm_structured(
        prompt=prompt,
        agent="orthopedic-surgery",
        system_prompt=LLM_SYSTEM_PROMPT,
        output_schema=LLM_OUTPUT_SCHEMA,
        temperature=0.1,
    )

    if "data" in llm_result:
        data = llm_result["data"]
        return {
            "fracture_type": data.get("fracture_type", "不确定"),
            "side": data.get("side", "不确定"),
            "classification_system": data.get("classification_system", ""),
            "classification_type": data.get("classification_type", "待影像确认分型"),
            "stability": data.get("stability", "N/A"),
            "surgery_recommendation": data.get("surgery_recommendation", ""),
            "guideline_ref": data.get("guideline_ref", ""),
            "confidence": data.get("confidence", "中"),
            "llm_generated": True,
            "phase": "preop",
        }

    # LLM 失败 → 降级到规则引擎
    rule_result = classify_hip_fracture(diagnosis, exam_result, phase="preop")
    rule_result["llm_generated"] = False
    rule_result["llm_error"] = llm_result.get("error", "unknown")
    return rule_result


def classify_hip_fracture_hybrid(
    diagnosis: str = "",
    exam_result: str = "",
    patient: dict | None = None,
    use_llm: bool = True,
    phase: str = "preop",
) -> dict[str, Any]:
    """Hybrid 骨折分型 — 优先 LLM,失败降级到规则引擎. 术前-only.

    Args:
        use_llm: True=先用LLM, False=直接用规则引擎
        phase: "preop"(术前) | "postop"(术后)
    """
    if use_llm:
        return classify_hip_fracture_llm(diagnosis, exam_result, patient, phase=phase)
    return classify_hip_fracture(diagnosis, exam_result, phase=phase)
