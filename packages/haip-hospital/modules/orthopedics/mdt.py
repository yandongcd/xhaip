"""MDT 多学科会诊技能 Agent — 聚合多方评估，输出结构化 MDT 纪要.

作为技能 Agent，可被骨外科、心内科、麻醉科等任意科室 Agent 调用。
支持降级模式：部分参与智能体不可用时标注"待补充"，不中断 MDT 流程。

风险缓解 (Risk #1): 输出标注"AI 辅助建议，需人工确认" + 签名字段。
风险缓解 (Risk #9): 降级模式，任一 Agent 失败不阻塞整个 MDT。
"""

from __future__ import annotations

from typing import Any

MDT_TEMPLATE = {
    "mdt_id": "",
    "patient_id": "",
    "timestamp": "",
    "chief_complaint": "",
    "participants": [],
    "diagnosis": {"primary": "", "secondary": [], "icd_code": ""},
    "risk_assessment": {"overall": "", "cardiac": "", "anesthesia": "", "orthopedic": ""},
    "treatment_plan": {"recommended": "", "alternatives": [], "rationale": ""},
    "controversies": [],
    "assignments": {"surgeon": "", "anesthesiologist": "", "consultant": "", "nurse": ""},
    "timeline": {"target_surgery_window": "", "preop_deadline": ""},
    "disclaimer": "本 MDT 纪要由 AI 辅助生成，需经多学科团队人工审核确认后方可作为临床决策依据。",
    "signatures": {"chair": "", "surgeon": "", "anesthesiologist": "", "timestamp": ""},
    "status": "draft",
    "_mode": "ai_assisted",
}

ROLE_RECOMMENDATIONS = {
    "cardio-risk": ["心内科评估", "ECG 复核", "心酶动态监测", "抗血小板调整"],
    "anesthesia-risk": ["ASA 分级", "气道评估", "抗凝管理", "麻醉方案"],
    "pain-management": ["VAS 基线评分", "术前镇痛策略", "术后 PCA 配置"],
    "education": [],
}

EVIDENCE_REFS = {
    "mdt": [
        "# NHSA 2022: 老年髋部骨折诊疗与管理指南 §4.2 多学科协作",
        "# NICE NG37 §1.2: Multidisciplinary management",
        "# AAOS 2022: Management of Hip Fractures in the Elderly §III",
    ]
}


def mdt_aggregate(*, patient_id: str, cardio_eval: dict | None = None,
                  anesthesia_eval: dict | None = None, orthopedic_eval: dict | None = None,
                  pain_eval: dict | None = None, chief_complaint: str = "",
                  participants: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
    """聚合多方评估结果，生成结构化 MDT 纪要.

    Args:
        patient_id: 患者 ID
        cardio_eval: 心内科评估结果（可选，缺失时标注 degradation）
        anesthesia_eval: 麻醉科评估结果（可选）
        orthopedic_eval: 骨科评估结果（可选）
        pain_eval: 疼痛评估结果（可选）
        chief_complaint: 主诉
        participants: 参与会诊的 Agent 列表

    Returns:
        MDT 纪要以 dict 返回，含 diagnosis/risk_assessment/treatment_plan/controversies/assignments
    """
    from datetime import datetime
    import copy

    mdt = copy.deepcopy(MDT_TEMPLATE)
    mdt["mdt_id"] = f"MDT-{patient_id}-{datetime.now().strftime('%Y%m%d%H%M')}"
    mdt["patient_id"] = patient_id
    mdt["timestamp"] = datetime.now().isoformat()
    mdt["chief_complaint"] = chief_complaint
    mdt["participants"] = participants or ["cardiologist", "anesthesiologist", "orthopedist"]
    degradation = []

    if orthopedic_eval and isinstance(orthopedic_eval, dict):
        mdt["diagnosis"]["primary"] = orthopedic_eval.get("diagnosis", "")
        mdt["diagnosis"]["icd_code"] = orthopedic_eval.get("icd_code", "")
        mdt["treatment_plan"]["recommended"] = orthopedic_eval.get("recommended_surgery", "")
        mdt["treatment_plan"]["alternatives"] = orthopedic_eval.get("alternatives", [])
        mdt["treatment_plan"]["rationale"] = orthopedic_eval.get("rationale", "")
        mdt["risk_assessment"]["orthopedic"] = orthopedic_eval.get("risk_level", "未评估")
    else:
        degradation.append("orthopedic")

    if cardio_eval and isinstance(cardio_eval, dict):
        mdt["risk_assessment"]["cardiac"] = cardio_eval.get("risk_level", "未评估")
        if cardio_eval.get("recommendations"):
            mdt["controversies"].extend(cardio_eval["recommendations"])
        if cardio_eval.get("contraindications"):
            mdt["controversies"].append({"source": "心内科", "issue": "禁忌症",
                                          "detail": str(cardio_eval["contraindications"])})
    else:
        degradation.append("cardiology")

    if anesthesia_eval and isinstance(anesthesia_eval, dict):
        mdt["risk_assessment"]["anesthesia"] = anesthesia_eval.get("asa_grade", "未评估")
        mdt["assignments"]["anesthesiologist"] = anesthesia_eval.get("recommended_plan", "")
        if anesthesia_eval.get("special_considerations"):
            mdt["controversies"].append({"source": "麻醉科", "issue": "特殊注意事项",
                                          "detail": str(anesthesia_eval["special_considerations"])})
    else:
        degradation.append("anesthesia")

    if pain_eval and isinstance(pain_eval, dict):
        mdt["risk_assessment"]["pain_baseline"] = pain_eval.get("vas_score", "未评估")
        mdt["controversies"].append({"source": "疼痛管理", "issue": "镇痛策略",
                                      "detail": pain_eval.get("analgesia_plan", "未指定")})

    mdt["risk_assessment"]["overall"] = _derive_overall_risk(mdt["risk_assessment"])

    if degradation:
        mdt["_degraded"] = True
        mdt["_degraded_agents"] = degradation
        mdt["_degradation_note"] = f"以下 Agent 不可用或返回空: {', '.join(degradation)}，相关评估标注为'待补充'"
        for field in degradation:
            if field == "orthopedic" and not mdt["risk_assessment"]["orthopedic"]:
                mdt["risk_assessment"]["orthopedic"] = "待补充 (Agent 不可用)"
            elif field == "cardiology" and not mdt["risk_assessment"]["cardiac"]:
                mdt["risk_assessment"]["cardiac"] = "待补充 (Agent 不可用)"
            elif field == "anesthesia" and not mdt["risk_assessment"]["anesthesia"]:
                mdt["risk_assessment"]["anesthesia"] = "待补充 (Agent 不可用)"

    mdt["evidence_refs"] = EVIDENCE_REFS["mdt"]

    return mdt


def mdt_summary(mdt_result: dict, **kwargs: Any) -> dict[str, Any]:
    """将 MDT 聚合结果格式化为可展示的摘要（适合 UI 渲染和 API 输出）.

    Args:
        mdt_result: mdt_aggregate() 的返回结果

    Returns:
        结构化摘要，含 markdown_text 和结构化字段
    """
    r = mdt_result
    lines = [
        "# MDT 多学科会诊纪要",
        f"**会诊编号**: {r.get('mdt_id', '')}",
        f"**患者 ID**: {r.get('patient_id', '')}",
        f"**时间**: {r.get('timestamp', '')}",
        "",
        "## 诊断",
        f"- 主诊断: {r.get('diagnosis', {}).get('primary', '未指定')}",
        f"- ICD 编码: {r.get('diagnosis', {}).get('icd_code', '')}",
        "",
        "## 风险评估",
    ]
    risk = r.get("risk_assessment", {})
    for key, val in risk.items():
        if key != "overall":
            lines.append(f"- {key}: {val}")
    lines.append(f"- **综合风险**: {risk.get('overall', '未评估')}")

    lines.extend(["", "## 治疗方案"])
    plan = r.get("treatment_plan", {})
    lines.append(f"- 推荐方案: {plan.get('recommended', '未指定')}")
    if plan.get("alternatives"):
        lines.append(f"- 备选方案: {', '.join(plan['alternatives'])}")
    lines.append(f"- 依据: {plan.get('rationale', '')}")

    if r.get("controversies"):
        lines.extend(["", "## 争议与待确认事项"])
        for c in r["controversies"]:
            if isinstance(c, dict):
                lines.append(f"- [{c.get('source', '')}] {c.get('issue', '')}: {c.get('detail', '')}")
            else:
                lines.append(f"- {c}")

    lines.extend(["", "## 责任分配"])
    assign = r.get("assignments", {})
    for role, person in assign.items():
        if person:
            lines.append(f"- {role}: {person}")

    lines.extend(["", "## 证据来源"])
    for ref in r.get("evidence_refs", []):
        lines.append(f"- {ref}")

    if r.get("_degraded"):
        lines.extend(["", f"> ⚠ {r.get('_degradation_note', '')}"])

    lines.extend(["", f"> {r.get('disclaimer', '')}"])

    return {
        "mdt_id": r.get("mdt_id"),
        "patient_id": r.get("patient_id"),
        "summary_markdown": "\n".join(lines),
        "diagnosis": r.get("diagnosis"),
        "risk_overall": risk.get("overall"),
        "treatment": plan.get("recommended"),
        "controversies_count": len(r.get("controversies", [])),
        "degraded": r.get("_degraded", False),
        "status": r.get("status", "draft"),
    }


def _derive_overall_risk(risk: dict) -> str:
    """根据各维度风险推导综合风险等级."""
    high_count = sum(1 for k, v in risk.items()
                     if k != "overall" and isinstance(v, str) and "高" in v)
    if high_count >= 2:
        return "高风险 — 建议 48h 内手术，加强围术期监护"
    if high_count == 1:
        return "中高风险 — 建议限期手术，针对性处理高风险维度"
    return "低中风险 — 择期手术，常规准备"
