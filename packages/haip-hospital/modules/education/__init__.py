"""教育技能 Agent — 病例教学 + 决策复盘 + 指南速查 + 学习路径.

风险缓解 (Risk #5): 所有教学案例均为合成病例，不包含真实患者数据。
"""

from __future__ import annotations

from typing import Any

SYNTHETIC_CASES = {
    "femoral_neck": {
        "basic": {
            "case_id": "EDU-FN-001",
            "title": "股骨颈骨折 Garden III 型 — 基础案例",
            "patient": {"age": 72, "gender": "女", "synthetic": True},
            "history": "跌倒后右髋疼痛 3h，高血压病史 5 年 (口服硝苯地平控制良好)",
            "xray": "右股骨颈骨折，Garden III 型，移位明显",
            "labs": {"Hb": 11.2, "Cr": 82, "INR": 1.1, "cTnI": 0.02},
            "teaching_points": [
                "Garden 分型 I-IV 的影像学鉴别要点",
                "Garden III/IV 型应选择关节置换而非内固定",
                "72岁 + Garden III → THA 优于 HA (活动量大，预期寿命>5年)",
            ],
            "evidence_refs": [
                "# NICE NG37 §1.5: 移位型股骨颈骨折推荐 THA",
                "# AAOS 2022: 老年移位型股骨颈骨折 — THA vs HA 证据",
            ],
        },
    },
    "intertrochanteric": {
        "basic": {
            "case_id": "EDU-IT-001",
            "title": "股骨转子间骨折 Evans ID 型 — 基础案例",
            "patient": {"age": 81, "gender": "男", "synthetic": True},
            "history": "跌倒后左髋疼痛 5h，房颤病史 (华法林 3mg qd)",
            "xray": "左股骨转子间骨折，Evans ID 型，不稳定",
            "labs": {"Hb": 9.8, "INR": 2.4, "Cr": 105},
            "teaching_points": [
                "Evans 分型 ID 型提示不稳定 — PFNA 为首选",
                "INR 2.4 → 需维生素 K 拮抗 → 延迟手术 vs 紧急拮抗",
                "PFNA 螺旋刀片抗旋转优势 vs DHS 滑动加压",
            ],
            "evidence_refs": [
                "# 国家卫健委 2022: §5.2 转子间骨折内固定选择",
                "# AAOS 2022: Cephalomedullary nail vs sliding hip screw",
            ],
        },
    },
}

GUIDELINE_QUICK_REFS = {
    "nhsa_2022": {
        "early_surgery": "力争入院 48h 内完成手术 (§4.1)",
        "dvt_prevention": "低分子肝素/利伐沙班，术后 6-12h 启动 (§6.1)",
        "pain_management": "多模式镇痛，NSAIDs 慎用于 CKD/消化道出血 (§6.3)",
        "osteoporosis": "术后即启动抗骨质疏松治疗，钙剂+VitD 基础 (§7)",
    },
    "nice_ng37": {
        "timing": "手术应在入院当天或次日进行 (1.1)",
        "tha_vs_ha": "能独立行走、无认知障碍者推荐 THA (1.5)",
        "multidisciplinary": "骨科老年医学协作管理 (1.2)",
    },
    "aaos_2022": {
        "preop_traction": "不推荐术前常规皮牵引 (中等证据)",
        "regional_anesthesia": "区域麻醉可能优于全麻 (有限证据)",
    },
}

LEARNING_PATHS = {
    "resident": {
        "name": "住院医师阶段",
        "duration": "6-12 月",
        "milestones": [
            "掌握 Garden/Evans/AO 骨折分型",
            "独立完成 11 项术前检查清单",
            "理解 T2 8因素时机决策逻辑",
            "掌握 Harris 髋关节评分方法",
        ],
    },
    "attending": {
        "name": "主治医师阶段",
        "duration": "12-24 月",
        "milestones": [
            "独立制定手术方案 (THA/HA/PFNA/DHS)",
            "MDT 会诊主导能力",
            "并发症预测与风险管理",
            "质控审计与流程优化",
        ],
    },
    "specialist": {
        "name": "专家阶段",
        "duration": "持续",
        "milestones": [
            "复杂/翻修手术决策",
            "科室质量管理体系建设",
            "青年医师带教与案例库维护",
            "指南解读与本地化适配",
        ],
    },
}


def case_teaching(*, fracture_type: str = "femoral_neck",
                  difficulty: str = "basic", **kwargs: Any) -> dict[str, Any]:
    """典型病例教学 — 所有病例为合成数据，非真实患者.

    Args:
        fracture_type: 骨折类型 (femoral_neck / intertrochanteric)
        difficulty: 难度 (basic / advanced)
    """
    case_data = SYNTHETIC_CASES.get(fracture_type, {}).get(difficulty)
    if not case_data:
        return {
            "available_types": list(SYNTHETIC_CASES.keys()),
            "available_difficulties": ["basic"],
            "error": f"未找到 fracture_type={fracture_type} difficulty={difficulty} 的教学病例",
        }

    return {
        **case_data,
        "disclaimer": "本病例为合成教学数据，不包含真实患者信息，仅供教学参考",
        "data_source": "synthetic",
    }


def decision_review(*, case_id: str, ai_recommendation: dict | None = None,
                    actual_decision: dict | None = None, **kwargs: Any) -> dict[str, Any]:
    """决策复盘 — 智能体推荐 vs 实际临床决策对比.

    Args:
        case_id: 病例 ID
        ai_recommendation: 智能体推荐方案
        actual_decision: 实际临床决策
    """
    ai = ai_recommendation or {}
    actual = actual_decision or {}

    comparison = {"case_id": case_id, "alignment": [], "divergence": []}

    ai_surgery = ai.get("recommended_surgery", "")
    actual_surgery = actual.get("surgery", "")
    if ai_surgery and actual_surgery:
        if ai_surgery == actual_surgery:
            comparison["alignment"].append(f"手术方案一致: {ai_surgery}")
        else:
            comparison["divergence"].append({
                "item": "手术方案",
                "ai": ai_surgery,
                "actual": actual_surgery,
                "analysis": "需回顾分歧原因 — 是否存在 AI 未考虑的临床因素"
            })

    ai_timing = ai.get("timing", "")
    actual_timing = actual.get("timing", "")
    if ai_timing and actual_timing:
        if ai_timing == actual_timing:
            comparison["alignment"].append(f"手术时机一致: {ai_timing}")
        else:
            comparison["divergence"].append({
                "item": "手术时机",
                "ai": ai_timing,
                "actual": actual_timing,
            })

    comparison["total_checks"] = len(comparison["alignment"]) + len(comparison["divergence"])
    comparison["alignment_rate"] = (len(comparison["alignment"]) / max(comparison["total_checks"], 1)) * 100
    comparison["disclaimer"] = "决策复盘为教学工具，不代表对临床决策的评判"

    return comparison


def guideline_quick_ref(*, guideline: str = "nhsa_2022",
                         topic: str = "", **kwargs: Any) -> dict[str, Any]:
    """指南速查 — 核心要点卡片.

    Args:
        guideline: 指南标识 (nhsa_2022 / nice_ng37 / aaos_2022)
        topic: 查询主题（可选，为空返回全部）
    """
    ref = GUIDELINE_QUICK_REFS.get(guideline, {})
    if topic:
        filtered = {k: v for k, v in ref.items() if topic in k}
        return {"guideline": guideline, "topic_filter": topic, "items": filtered}

    return {
        "guideline": guideline,
        "full_name": {"nhsa_2022": "国家卫健委 2022 老年髋部骨折诊疗与管理指南",
                       "nice_ng37": "NICE NG37 Hip Fracture Management",
                       "aaos_2022": "AAOS 2022 Management of Hip Fractures in the Elderly"}.get(guideline),
        "items": ref,
    }


def learning_path(*, role: str = "resident", department: str = "骨外科",
                   **kwargs: Any) -> dict[str, Any]:
    """学习路径规划.

    Args:
        role: 角色 (resident / attending / specialist)
        department: 科室
    """
    path = LEARNING_PATHS.get(role, {})
    return {
        "role": role,
        "department": department,
        "path": path,
        "note": "学习路径基于骨外科住培教学大纲和专科医师培训标准",
    }
