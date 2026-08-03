"""疼痛康复管理 — 运动处方 + 进度追踪 + 心理共病评估.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="pain-rehab", department="疼痛科")
_GUIDELINES = [
    "IASP 慢性疼痛康复指南",
    "ACSM 运动处方指南",
    "中国疼痛康复专家共识",
    "生物心理社会模型 (BPS Model)",
]
_agent.rule_engine.load_all()

from typing import Any

EXERCISES_BY_REGION = {
    "lumbar": ["猫式伸展", "鸟狗式", "桥式运动", "死虫式", "平板支撑(改良)", "麦肯基俯卧撑", "骨盆倾斜"],
    "cervical": ["颈部缩下巴", "颈部侧屈拉伸", "肩胛骨后缩", "颈部旋转拉伸", "上斜方肌拉伸", "姿势力线训练"],
    "knee": ["股四头肌等长收缩", "直腿抬高", "靠墙静蹲", "腘绳肌拉伸", "臀桥", "台阶训练"],
    "shoulder": ["钟摆运动", "爬墙运动", "肩胛稳定性训练", "弹力带外旋", "肩关节活动度训练"],
}


def exercise(pain_location: str = "", odi_score: int = 0,
             pain_region: str = "",
             **kwargs: Any) -> dict:
    """运动处方生成 — 按部位和功能障碍程度."""
    region = pain_region if pain_region else pain_location
    exercises = EXERCISES_BY_REGION.get(region, EXERCISES_BY_REGION.get("lumbar", []))

    intensity = "high" if odi_score <= 20 else ("moderate" if odi_score <= 40 else "low")
    freq = 5 if intensity == "high" else (4 if intensity == "moderate" else 3)
    duration_mins = 30 if intensity == "high" else (20 if intensity == "moderate" else 15)
    num_exercises = min(5 if intensity == "high" else (4 if intensity == "moderate" else 3), len(exercises))
    selected = exercises[:num_exercises]

    precautions: list[str] = []
    if intensity == "low":
        precautions.append("以不引起疼痛加重的范围为限")
    if odi_score >= 50:
        precautions.append("需在物理治疗师指导下进行")
    if odi_score >= 60:
        precautions.append("避免负重运动")
    if region == "lumbar":
        precautions.append("避免弯腰动作")
    elif region == "cervical":
        precautions.append("避免颈部过伸")
    precautions.append("运动前热身5分钟，运动后冷敷(如有急性疼痛)")

    return {
        "status": "ok",
        "exercises": selected,
        "frequency": {"sessions_per_week": freq, "duration_minutes": duration_mins},
        "intensity": intensity,
        "precautions": precautions,
        "pain_location": pain_location,
        "odi_score": odi_score,
        "summary": f"运动处方: {region} — {intensity}强度, {freq}次/周, {duration_mins}分/次, {len(selected)}个动作",
    }


def assess_progress(
    baseline_odi: int = 0, current_odi: int = 0,
    target_odi: int = 20, weeks_in_rehab: int = 4,
    **kwargs: Any,
) -> dict:
    """康复进度追踪 — ODI 改善率对比预期."""
    base = baseline_odi
    curr = current_odi
    pct = round((base - curr) / base * 100, 1) if base > 0 else 0
    expected_pct = weeks_in_rehab * 2.5
    on_track = pct >= expected_pct

    status = "达标" if on_track else "落后"
    if pct >= 50:
        status = "显著改善"
    elif pct <= 0 and weeks_in_rehab >= 4:
        status = "无进展 — 需重新评估治疗方案"

    recs = ["继续当前康复方案"] if on_track else [
        "增加康复频率", "物理治疗师再评估",
        "考虑心理行为治疗(CBT)", "疼痛科药物治疗调整",
    ]

    return {
        "status": "ok",
        "progress": "improving" if on_track else "stalled",
        "baseline_odi": base, "current_odi": curr, "target_odi": target_odi,
        "improvement_pct": pct, "weeks_in_rehab": weeks_in_rehab,
        "on_track": on_track, "status_detail": status,
        "recommendations": recs,
        "summary": f"康复进度: ODI {base}%→{curr}% ({pct}%改善), {'达标' if on_track else '落后'} — {weeks_in_rehab}周",
    }


def comorbid(phq9_score: int = 0, gad7_score: int = 0,
             suicide_ideation: bool = False,
             **kwargs: Any) -> dict:
    """心理共病评估 — PHQ-9 / GAD-7 / 自杀风险."""
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

    needs_psychology = phq9_score >= 10 or gad7_score >= 8 or suicide_ideation
    suicide_risk = phq9_score >= 15 or (phq9_score >= 10 and gad7_score >= 10) or suicide_ideation

    recs: list[str] = []
    if needs_psychology:
        recs.append("心理科/精神科会诊")
    if suicide_risk:
        recs.append("24h监护，禁止单独离院，精神科紧急评估")
    if 5 <= phq9_score <= 14:
        recs.append("CBT (认知行为治疗) 推荐")
    if 5 <= gad7_score <= 14:
        recs.append("放松训练/正念减压 (MBSR)")

    return {
        "status": "ok",
        "phq9_score": phq9_score, "gad7_score": gad7_score,
        "depression_level": dep, "anxiety_level": anx,
        "needs_psychology": needs_psychology,
        "suicide_risk": suicide_risk,
        "recommendations": recs,
        "summary": f"心理共病: {dep} + {anx}" + (" NEED_PSYCH" if needs_psychology else "") + (" SUICIDE_RISK" if suicide_risk else ""),
    }
