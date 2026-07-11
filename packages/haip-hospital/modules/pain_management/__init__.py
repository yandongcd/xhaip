"""疼痛管理技能 Agent — VAS 评估 + 多模式镇痛 + 无痛化质控 + PCA 配置.

风险缓解 (Risk #3): 麻醉 Agent 为强制 A2A 依赖，术中镇痛策略由麻醉主导。
风险缓解 (Risk #4): VAS 评分标注 input_required: true，必须由护理人员输入。
风险缓解 (Risk #6): 无痛化质控指标标注 ±2 分评估容差。
"""

from __future__ import annotations

from typing import Any

PAIN_MEDICATIONS = {
    "nsaids": [
        {"name": "塞来昔布", "dose": "200mg bid", "contraindications": ["CKD 3期", "消化道出血"], "level": 2},
        {"name": "帕瑞昔布", "dose": "40mg iv bid", "contraindications": ["CKD 3期", "消化道出血"], "level": 2},
        {"name": "氟比洛芬酯", "dose": "50mg iv tid", "contraindications": ["CKD 3期"], "level": 2},
    ],
    "weak_opioids": [
        {"name": "曲马多", "dose": "50-100mg q6h", "contraindications": ["癫痫"], "level": 3},
        {"name": "可待因", "dose": "30-60mg q6h", "contraindications": ["呼吸抑制"], "level": 3},
    ],
    "strong_opioids": [
        {"name": "吗啡", "dose": "5-10mg iv q4h", "contraindications": ["呼吸抑制", "颅内压增高"], "level": 4},
        {"name": "羟考酮", "dose": "5-10mg po q4h", "contraindications": ["呼吸抑制"], "level": 4},
    ],
    "local_anesthetics": [
        {"name": "罗哌卡因 0.2%", "dose": "持续神经阻滞", "contraindications": ["局麻药过敏"], "level": 3},
        {"name": "布比卡因 0.125%", "dose": "硬膜外", "contraindications": ["凝血障碍", "脊柱畸形"], "level": 3},
    ],
    "nerve_blocks": [
        {"name": "髂筋膜间隙阻滞 (FICB)", "target": "髋部骨折术前镇痛", "level": 2},
        {"name": "腰丛神经阻滞", "target": "髋关节手术", "level": 3},
    ],
}

PAIN_PATHWAYS = {
    "mild": {"vas_range": "1-3", "strategy": "NSAIDs ± 非药物干预", "reassess": "q8h"},
    "moderate": {"vas_range": "4-6", "strategy": "弱阿片 ± NSAIDs ± 局麻", "reassess": "q4h"},
    "severe": {"vas_range": "7-10", "strategy": "强阿片 + 局麻/神经阻滞 + NSAIDs", "reassess": "q2h"},
}

PAIN_FREE_WARD_TARGETS = {
    "vas_under_3_ratio": {"target": ">=85%", "tolerance": "±2分评估容差"},
    "breakthrough_pain_rate": {"target": "<15%", "unit": "次/24h"},
    "rescue_medication_rate": {"target": "<10%", "unit": "次/周"},
    "patient_satisfaction": {"target": ">=90%", "unit": "满意度评分"},
}

EVIDENCE_REFS = [
    "# WHO 疼痛阶梯治疗原则 (2020)",
    "# ERAS 加速康复外科指南 §5 围术期疼痛管理",
    "# 国家卫健委 2022 老年髋部骨折指南 §6.3 疼痛管理",
    "# PROSPECT 工作组: 髋部骨折手术镇痛循证建议 (2023)",
]


def assess_pain(*, patient_id: str, vas_score: float | None = None,
                nurse_id: str = "", assessment_time: str = "", **kwargs: Any) -> dict[str, Any]:
    """疼痛评估 — VAS 值必须由护理人员输入，不接受空值.

    Args:
        patient_id: 患者 ID
        vas_score: VAS 评分 (0-10)，必须由护理人员输入
        nurse_id: 评估护士 ID
        assessment_time: 评估时间
    """
    if vas_score is None:
        return {
            "patient_id": patient_id,
            "error": "VAS 评分未输入 — 疼痛评估需要护理人员床旁评估后输入分值",
            "requires_input": True,
            "recommendation": "请护士完成 VAS 床旁评估后重新调用，输入 vas_score (0-10)",
        }

    if not 0 <= vas_score <= 10:
        return {
            "patient_id": patient_id,
            "error": f"VAS 评分 {vas_score} 超出有效范围 (0-10)",
            "requires_input": True,
        }

    if vas_score <= 3:
        severity = "轻度"
        pathway = PAIN_PATHWAYS["mild"]
    elif vas_score <= 6:
        severity = "中度"
        pathway = PAIN_PATHWAYS["moderate"]
    else:
        severity = "重度"
        pathway = PAIN_PATHWAYS["severe"]

    return {
        "patient_id": patient_id,
        "vas_score": vas_score,
        "severity": severity,
        "pathway": pathway,
        "nurse_id": nurse_id,
        "assessment_time": assessment_time,
        "evidence_refs": EVIDENCE_REFS[:2],
    }


def multimodal_analgesia(*, patient_id: str, vas_score: float,
                         allergies: list[str] | None = None,
                         renal_function: str = "normal",
                         liver_function: str = "normal", **kwargs: Any) -> dict[str, Any]:
    """多模式镇痛阶梯方案推荐.

    Args:
        patient_id: 患者 ID
        vas_score: VAS 评分
        allergies: 过敏史
        renal_function: 肾功能 (normal/mild_moderate/severe/透析)
        liver_function: 肝功能 (normal/mild/severe)
    """
    allergies = allergies or []
    contraindications = set()

    if renal_function in ("severe", "透析", "CKD3", "CKD4", "CKD5"):
        contraindications.add("nsaids")
    if liver_function == "severe":
        contraindications.add("nsaids")
    if any("阿片" in a or "opioid" in a.lower() for a in allergies):
        contraindications.add("opioids")

    plan = {"patient_id": patient_id, "vas_score": vas_score, "layers": [], "warnings": []}

    if vas_score <= 3:
        if "nsaids" not in contraindications:
            plan["layers"].append({"layer": 1, "type": "非甾体抗炎药", "medications": PAIN_MEDICATIONS["nsaids"][:2]})
        plan["layers"].append({"layer": 2, "type": "非药物干预", "items": ["冰敷", "抬高患肢", "心理疏导"]})
    elif vas_score <= 6:
        if "nsaids" not in contraindications:
            plan["layers"].append({"layer": 1, "type": "非甾体抗炎药基础", "medications": PAIN_MEDICATIONS["nsaids"][:1]})
        plan["layers"].append({"layer": 2, "type": "弱阿片类药物", "medications": PAIN_MEDICATIONS["weak_opioids"][:1]})
        plan["layers"].append({"layer": 3, "type": "局麻辅助", "items": [PAIN_MEDICATIONS["nerve_blocks"][0]["name"]]})
    else:
        if "nsaids" not in contraindications:
            plan["layers"].append({"layer": 1, "type": "非甾体抗炎药", "medications": PAIN_MEDICATIONS["nsaids"][:1]})
        plan["layers"].append({"layer": 2, "type": "区域阻滞", "items": [PAIN_MEDICATIONS["nerve_blocks"][0]["name"],
                                PAIN_MEDICATIONS["nerve_blocks"][1]["name"]]})
        plan["layers"].append({"layer": 3, "type": "强阿片类药物", "medications": PAIN_MEDICATIONS["strong_opioids"][:1]})

    if renal_function in ("severe", "透析", "CKD3"):
        plan["warnings"].append("肾功能不全 — 禁用 NSAIDs，优先选择对乙酰氨基酚 + 区域阻滞")
    if "nsaids" in contraindications:
        plan["warnings"].append("NSAIDs 禁忌 — 已从方案中排除")
    if vas_score >= 7:
        plan["warnings"].append("重度疼痛 — 建议麻醉科会诊，考虑 PCA 镇痛泵")

    plan["evidence_refs"] = EVIDENCE_REFS

    return plan


def pain_free_ward_metrics(*, ward_id: str = "", period: str = "monthly",
                            **kwargs: Any) -> dict[str, Any]:
    """无痛化病房质控指标.

    Args:
        ward_id: 病区 ID
        period: 统计周期 (daily/weekly/monthly)
    """
    return {
        "ward_id": ward_id,
        "period": period,
        "targets": PAIN_FREE_WARD_TARGETS,
        "assessment_tolerance": "VAS 评估基于护士床旁评估，不同评估者间可能存在 ±2 分的评估差异",
        "note": "数据来源: 护士床旁 VAS 评估记录，非智能体自行评估",
        "evidence_refs": EVIDENCE_REFS,
    }


def pca_config(*, patient_id: str, age: int, weight: float, procedure: str,
               allergies: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
    """术后 PCA 镇痛泵配置建议.

    Args:
        patient_id: 患者 ID
        age: 年龄
        weight: 体重 (kg)
        procedure: 手术方式 (THA/HA/PFNA/DHS)
        allergies: 过敏史
    """
    config = {
        "patient_id": patient_id,
        "mode": "PCIA" if procedure in ("THA", "HA") else "PCEA" if procedure == "PFNA" else "PCIA",
        "drug": "舒芬太尼 100μg + 昂丹司琼 8mg / 100ml NS" if age < 75 else "舒芬太尼 50μg + 昂丹司琼 8mg / 100ml NS",
        "basal_rate": "1 ml/h" if weight >= 50 else "0.5 ml/h",
        "bolus_dose": "2 ml" if weight >= 50 else "1 ml",
        "lockout_interval": "15 min",
        "max_dose_4h": "舒芬太尼 ≤30μg",
        "monitoring": ["SpO2 q4h", "RR q4h", "镇静评分 (Ramsay) q4h", "恶心呕吐评分 q8h"],
        "contraindications": [],
    }

    if age >= 80:
        config["warnings"] = ["高龄患者 — 阿片剂量减半，加强呼吸监测"]
        config["monitoring"].append("EtCO2 监测 (推荐)")

    if any("吗啡" in a or "morphine" in a.lower() for a in (allergies or [])):
        config["contraindications"].append("吗啡过敏 — 改用舒芬太尼或瑞芬太尼")

    config["evidence_refs"] = EVIDENCE_REFS[:3]

    return config
