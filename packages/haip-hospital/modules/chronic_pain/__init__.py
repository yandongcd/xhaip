"""慢性疼痛综合评估 — 生物心理社会模型 + 阶梯治疗 + 量表评估.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="chronic-pain", department="疼痛科")
_GUIDELINES = [
    "WHO Analgesic Ladder 镇痛三阶梯",
    "IASP 慢性疼痛分类 (ICD-11)",
    "生物心理社会模型 (BPS Model)",
    "中国慢性疼痛管理指南",
    "NICE CG173 神经病理性疼痛管理",
]
_agent.rule_engine.load_all()


def assess(pain_duration_months: int = 0, vas_score: int = 0, nrs_score: int = 0,
           diagnosis: str = "", phq9_score: int = 0, gad7_score: int = 0,
           odi_score: int = 0, past_history: str = "", medications: str = "",
           **kwargs: Any) -> dict:
    """慢性疼痛生物心理社会评估."""
    is_chronic = pain_duration_months >= 3
    nrs = nrs_score if nrs_score > 0 else max(0, min(10, round(vas_score / 10)))

    bio = {
        "diagnosis": diagnosis, "duration_months": pain_duration_months,
        "pain_nrs": nrs, "past_history": past_history, "medications": medications,
    }

    if phq9_score <= 4:
        dep = "无抑郁"
    elif phq9_score <= 9:
        dep = "轻度抑郁"
    elif phq9_score <= 14:
        dep = "中度抑郁"
    elif phq9_score <= 19:
        dep = "中重度抑郁"
    else:
        dep = "重度抑郁"

    if gad7_score <= 4:
        anx = "正常"
    elif gad7_score <= 9:
        anx = "轻度焦虑"
    elif gad7_score <= 14:
        anx = "中度焦虑"
    else:
        anx = "重度焦虑"

    psycho = {
        "phq9_score": phq9_score, "gad7_score": gad7_score,
        "depression_level": dep, "anxiety_level": anx,
        "needs_psychology_consult": phq9_score >= 10 or gad7_score >= 10,
    }

    if odi_score <= 20:
        func = "轻度功能障碍"
        work = "轻度影响"
        daily = "基本自理"
    elif odi_score <= 40:
        func = "中度功能障碍"
        work = "中度影响"
        daily = "部分受限"
    elif odi_score <= 60:
        func = "重度功能障碍"
        work = "严重影响"
        daily = "严重受限"
    else:
        func = "严重功能障碍"
        work = "严重影响"
        daily = "严重受限"

    social = {"odi_score": odi_score, "functional_level": func,
              "work_impact": work, "daily_activity_impact": daily}

    return {
        "status": "ok",
        "is_chronic": is_chronic,
        "pain_duration_months": pain_duration_months,
        "vas_score": vas_score,
        "bio": bio, "psycho": psycho, "social": social,
        "summary": f"慢性疼痛 NRS={nrs}, ODI={odi_score}%, PHQ-9={phq9_score}, GAD-7={gad7_score}",
    }


def assess_scales(odi_responses: list | None = None, ndi_responses: list | None = None,
                  dn4_responses: dict | None = None, phq9_score: int = 0, gad7_score: int = 0,
                  **kwargs: Any) -> dict:
    """多维度疼痛量表评估 — ODI/NDI/DN4/PHQ-9/GAD-7."""
    r: dict[str, Any] = {"status": "ok"}

    if odi_responses:
        raw = sum(odi_responses)
        pct = min(raw * 2, 100)
        lvl = "轻度功能障碍" if pct <= 20 else ("中度功能障碍" if pct <= 40 else (
            "重度功能障碍" if pct <= 60 else ("严重功能障碍" if pct <= 80 else "卧床/夸大症状")))
        r["odi"] = {"score": raw, "percentage": pct, "level": lvl}

    if ndi_responses:
        raw = sum(ndi_responses)
        pct = round(min(raw / (len(ndi_responses) * 5) * 100 if ndi_responses else 0, 100), 1)
        lvl = "无残疾" if pct <= 8 else ("轻度残疾" if pct <= 28 else (
            "中度残疾" if pct <= 48 else ("重度残疾" if pct <= 68 else "完全残疾")))
        r["ndi"] = {"score": raw, "percentage": pct, "level": lvl}

    if dn4_responses:
        score = sum(1 for v in dn4_responses.values() if v)
        r["dn4"] = {"score": score, "is_positive": score >= 4}

    for k, thresholds in [
        ("phq9", [(4, "无抑郁"), (9, "轻度抑郁"), (14, "中度抑郁"), (19, "中重度抑郁"), (999, "重度抑郁")]),
        ("gad7", [(4, "正常"), (9, "轻度焦虑"), (14, "中度焦虑"), (999, "重度焦虑")]),
    ]:
        score = phq9_score if k == "phq9" else gad7_score
        if score is not None:
            for th, lab in thresholds:
                if score <= th:
                    r[k] = {"score": score, "level": lab}
                    break

    data_sources = list(r.keys())
    data_sources.remove("status")
    parts = []
    if "odi" in r:
        parts.append(f"ODI={r['odi']['percentage']}% ({r['odi']['level']})")
    if "phq9" in r:
        parts.append(f"PHQ-9={r['phq9']['score']} ({r['phq9']['level']})")
    if "gad7" in r:
        parts.append(f"GAD-7={r['gad7']['score']} ({r['gad7']['level']})")
    r["summary"] = "; ".join(parts) or "无有效量表数据"
    r["scales"] = data_sources
    return r


def care(vas_score: int = 0, odi_score: int = 0, nrs_score: int = 0,
         duration_months: int = 0, conservative_failed: bool = False,
         intervention_failed: bool = False, failed_prev: bool = False,
         **kwargs: Any) -> dict:
    """阶梯治疗推荐 — 第一/二/三阶梯."""
    nrs = nrs_score if nrs_score > 0 else max(0, min(10, round(vas_score / 10)))

    if ((nrs >= 7 and odi_score >= 45) or (conservative_failed and intervention_failed)) and duration_months >= 6:
        step, name, recs = 3, "第三阶梯 — 手术治疗", [
            "脊柱外科手术评估", "椎间孔镜/脊柱内镜",
            "SCS 试验评估", "IDDS — 顽固性疼痛",
        ]
    elif (nrs >= 5 and odi_score >= 25) or (conservative_failed and duration_months >= 3):
        step, name, recs = 2, "第二阶梯 — 微创介入治疗", [
            "神经阻滞治疗", "脉冲射频/射频热凝",
            "椎间孔镜评估", "运动康复+药物联合",
        ]
    else:
        step, name, recs = 1, "第一阶梯 — 保守治疗", [
            "NSAIDs+肌松药", "抗神经病理药物(加巴喷丁/普瑞巴林/度洛西汀)",
            "物理治疗(PT)", "CBT — 心理共病", "针灸/推拿", "生活方式指导",
        ]

    return {
        "status": "ok",
        "step": step, "step_name": name,
        "vas_score": vas_score, "odi_score": odi_score,
        "recommendations": recs,
        "summary": f"阶梯治疗推荐: {name}",
    }
