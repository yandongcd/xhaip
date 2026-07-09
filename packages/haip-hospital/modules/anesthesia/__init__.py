"""麻醉评估 — ASA分级 + 困难气道 + 抗凝管理 + 麻醉方案.

业务流来源:
  - ASA体格状态分级系统
  - 困难气道管理指南 (ASA 2022)
  - ACCP 围术期抗栓治疗指南
"""

from __future__ import annotations

from typing import Any

# ASA 分级标准
ASA_CRITERIA = {
    1: "健康患者, 无系统性疾病",
    2: "轻度系统性疾病, 无功能受限 (如控制良好的高血压/糖尿病)",
    3: "重度系统性疾病, 功能受限但非失能 (如控制不佳的糖尿病/稳定心绞痛)",
    4: "重度系统性疾病, 持续威胁生命 (如不稳定心绞痛/失代偿心衰)",
    5: "濒死患者, 无论手术与否均难以存活 24h",
    6: "脑死亡患者, 器官捐献",
}

# Mallampati 分级
MALLAMPATI = {
    1: "可见软腭/咽腭弓/悬雍垂 — 插管容易",
    2: "可见软腭/咽腭弓/部分悬雍垂 — 插管可能容易",
    3: "仅见软腭/悬雍垂基部 — 插管可能困难",
    4: "不可见软腭 — 插管困难",
}


def evaluate(
    patient_id: str = "", conditions: list[str] | None = None,
    functional_status: str = "", **kwargs: Any,
) -> dict[str, Any]:
    """ASA 体格状态分级。"""
    conditions = conditions or []
    asa = 1
    if conditions:
        asa = 2
    if len(conditions) >= 2 or "uncontrolled" in functional_status.lower():
        asa = 3
    if any(k in " ".join(conditions).lower() for k in [
        "unstable angina", "失代偿心衰", "respiratory failure", "sepsis",
    ]):
        asa = 4

    risk = "low" if asa <= 2 else "moderate" if asa == 3 else "high"
    return {
        "patient_id": patient_id, "asa_class": asa,
        "asa_description": ASA_CRITERIA.get(asa, ""),
        "risk": risk, "conditions": conditions,
        "functional_status": functional_status,
        "suitable_for_surgery": asa <= 4,
        "recommendations": (
            ["常规麻醉"] if asa <= 2
            else ["术前优化 + 术中加强监测"] if asa == 3
            else ["MDT评估 + ICU备床 + 有创监测"]
        ),
    }


def evaluate_aw(
    patient_id: str = "", mallampati: int = 1,
    thyromental: float = 6.5, neck_mobility: str = "normal",
    **kwargs: Any,
) -> dict[str, Any]:
    """困难气道评估: Mallampati + 甲颌距 + 颈活动度。"""
    difficult = mallampati >= 4 or thyromental < 6.0 or neck_mobility == "limited"
    return {
        "patient_id": patient_id, "mallampati": mallampati,
        "mallampati_desc": MALLAMPATI.get(mallampati, ""),
        "thyromental_distance_cm": thyromental,
        "neck_mobility": neck_mobility,
        "difficult_airway": difficult,
        "plan": (
            "备困难气道车 + 纤支镜 + 清醒插管预案" if difficult
            else "常规快速序贯诱导"
        ),
    }


def anticoag_assess(
    patient_id: str = "", meds: list[str] | None = None,
    inr: float = 1.0, **kwargs: Any,
) -> dict[str, Any]:
    """围术期抗凝管理评估。

    参考: ACCP 围术期抗栓指南
    """
    meds = [m.lower() for m in (meds or [])]
    actions: list[str] = []
    bridge_needed = False

    if "warfarin" in " ".join(meds):
        if inr > 1.5:
            actions.append("华法林: 停药 5 天, 目标 INR < 1.5")
            bridge_needed = True
        else:
            actions.append("华法林: INR 已达标, 可手术")
    if any(m in " ".join(meds) for m in ["clopidogrel", "ticagrelor"]):
        actions.append("P2Y12 抑制剂: 停药 5-7 天")
        bridge_needed = True
    if "aspirin" in " ".join(meds):
        actions.append("阿司匹林: 风险获益评估, 一般不建议停用")
    if any(m in " ".join(meds) for m in ["rivaroxaban", "apixaban", "edoxaban"]):
        actions.append("NOAC: 停药 48-72h (根据肾功能调整)")

    if bridge_needed:
        actions.append("桥接方案: LMWH (依诺肝素 1mg/kg bid), 术前 24h 停用")

    return {
        "patient_id": patient_id, "inr": inr, "medications": meds,
        "bridge_needed": bridge_needed, "actions": actions,
        "evidence": ["ACCP 围术期抗栓指南"],
    }


def recommend(
    patient_id: str = "", surgery_type: str = "",
    asa_class: int = 1, age: int = 40, **kwargs: Any,
) -> dict[str, Any]:
    """麻醉方案推荐。"""
    plan_type = "全麻"
    if "lower" in surgery_type.lower() or "下肢" in surgery_type:
        plan_type = "腰麻" if asa_class <= 2 else "腰麻+镇静" if asa_class == 3 else "全麻"

    induction = ("propofol 1.5-2mg/kg + rocuronium 0.6mg/kg" if "全麻" in plan_type
                 else "bupivacaine 0.5% 2-3ml 蛛网膜下腔")

    return {
        "patient_id": patient_id, "plan": plan_type,
        "induction": induction,
        "monitoring": ["ECG", "SpO2", "NIBP", "ETCO2"] if "全麻" in plan_type else ["ECG", "SpO2", "NIBP"],
        "special_considerations": (
            ["高龄: 减少诱导剂量 20-30%", "脆弱心功能: 避免心肌抑制药物"] if age >= 70
            else []
        ),
    }
