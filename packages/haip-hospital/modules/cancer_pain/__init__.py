"""癌性疼痛管理 — WHO 三阶梯 + 阿片转换 + 安全审查 + 安宁疗护.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="cancer-pain", department="疼痛科")
_GUIDELINES = [
    "WHO Analgesic Ladder 镇痛三阶梯 (2018)",
    "NCCN Adult Cancer Pain Guidelines (2024)",
    "EAPC 欧洲姑息治疗学会阿片类药物指南",
    "中国癌症疼痛诊疗规范 (2023)",
    "NMPA 麻醉药品/精神药品管理规范",
]
_agent.rule_engine.load_all()

OPIOID_DRUGS = ["吗啡", "羟考酮", "芬太尼", "曲马多", "哌替啶", "美沙酮"]
BENZO_DRUGS = ["地西泮", "阿普唑仑", "劳拉西泮", "咪达唑仑", "氯硝西泮"]
NSAID_DRUGS = ["布洛芬", "双氯芬酸", "塞来昔布", "吲哚美辛", "萘普生", "洛索洛芬", "氟比洛芬"]


def assess(vas_score: int = 0, current_opioid_mg: float = 0.0, nrs_score: int = 0,
           **kwargs: Any) -> dict:
    """WHO 三阶梯镇痛评估 — 含阿片转换."""
    nrs = nrs_score if nrs_score > 0 else max(0, min(10, round(vas_score / 10)))
    meq = current_opioid_mg

    if nrs <= 3:
        step, desc, recs = 1, "第一阶梯 (轻度)", ["对乙酰氨基酚", "NSAIDs", "辅助药(加巴喷丁)"]
    elif nrs <= 6:
        step, desc, recs = 2, "第二阶梯 (中度)", ["曲马多 50-100mg q6h prn", "羟考酮低剂量起始", "NSAIDs+辅助药"]
    else:
        step, desc, recs = 3, "第三阶梯 (重度)", [
            "吗啡/羟考酮按时给药", "即释吗啡解救剂量",
            "芬太尼透皮贴(无法口服)", "PCA 评估",
        ]

    conversions: list[dict] = []
    bd_mg = 0.0
    if meq > 0:
        conversions.append({"from": f"口服吗啡 {meq}mg/day", "to": f"口服羟考酮 {round(meq/1.5, 1)}mg/day"})
        conversions.append({"from": f"口服吗啡 {meq}mg/day", "to": f"芬太尼透皮贴 {round(meq/2, 1)}mcg/h"})
        bd_mg = round(meq * 0.1, 1)

    overdose = meq > 120
    bd_rec = f"即释吗啡 {bd_mg}mg q2-4h prn (24h总量的10%)" if bd_mg > 0 else "N/A"

    return {
        "status": "ok",
        "who_step": step, "step_description": desc,
        "vas_score": vas_score, "current_opioid_mg": meq,
        "overdose_risk": overdose,
        "conversions": conversions,
        "breakthrough_dose_mg": bd_mg,
        "breakthrough_recommendation": bd_rec,
        "recommendations": recs,
        "summary": f"WHO Step {step} NRS={nrs} MEQ={meq}mg/day" + (" OVERLIMIT" if overdose else ""),
    }


def safety(daily_me_mg: float = 0.0, concurrent_meds: list | None = None,
           medications: list | None = None,
           **kwargs: Any) -> dict:
    """阿片安全审查 — 超量检测 + DDI + 重复用药."""
    meq = daily_me_mg
    meds = concurrent_meds or medications or []
    meds_str = " ".join(str(m) for m in meds).lower()

    classes: set[str] = set()
    if any(k in meds_str for k in OPIOID_DRUGS):
        classes.add("opioid")
    if any(k in meds_str for k in BENZO_DRUGS):
        classes.add("benzo")
    if any(k in meds_str for k in NSAID_DRUGS):
        classes.add("nsaid")
    if "华法林" in meds_str:
        classes.add("warfarin")
    if "曲马多" in meds_str:
        classes.add("tramadol")
    if "ssri" in meds_str:
        classes.add("ssri")
    if "acei" in meds_str:
        classes.add("acei")

    warnings: list[dict] = []
    ddi_pairs = [
        (["opioid", "benzo"], "呼吸抑制", "critical", "禁忌"),
        (["tramadol", "ssri"], "5-HT综合征", "severe", "严重"),
        (["warfarin", "nsaid"], "消化道出血", "severe", "严重"),
        (["nsaid", "acei"], "肾功能损伤", "high", "严重"),
    ]
    for pair, risk, sev, _act in ddi_pairs:
        if all(k in classes for k in pair):
            warnings.append({"drugs": "+".join(pair), "risk": risk, "severity": sev,
                           "action": "禁止联合" if sev == "critical" else "避免联合"})

    overdose = meq > 120
    if overdose:
        warnings.append({"drugs": "阿片类药物", "risk": f"日剂量 {meq}mg > 120mg 安全上限", "severity": "severe",
                        "action": "暂停处方，药剂科审核，纳洛酮备药"})
    elif meq > 96:
        warnings.append({"drugs": "阿片类药物", "risk": f"日剂量 {meq}mg 接近120mg上限(80%)", "severity": "moderate",
                        "action": "严密监测，考虑非阿片辅助"})

    opioid_meds = [m for m in (meds or []) if any(k in str(m) for k in ["吗啡", "羟考酮", "芬太尼"])]
    duplicate = len(opioid_meds) > 1

    sedatives = {"diazepam", "lorazepam", "midazolam", "clonazepam", "alprazolam"}
    ddi_detected = any(
        (isinstance(m, str) and (m.lower() in sedatives or "zolam" in m.lower() or "pam" in m.lower()))
        for m in meds
    )

    return {
        "status": "ok",
        "overdose_risk": overdose, "ddi_detected": ddi_detected or len(warnings) > 0,
        "duplicate_detected": duplicate,
        "daily_me_mg": meq, "warnings": warnings,
        "summary": f"阿片安全: 日剂量={meq}mg MEQ" + (f" WARN:{len(warnings)}" if warnings else " PASS"),
    }


def palliative(cancer_stage: str = "", ecog: int = 0,
               prognosis_months: int = 0, life_expectancy_months: int = 0,
               uncontrolled_pain: bool = False, current_treatment: str = "",
               **kwargs: Any) -> dict:
    """安宁疗护转介评估."""
    stage = str(cancer_stage)
    le = prognosis_months or life_expectancy_months
    tx = str(current_treatment)

    refer, reasons = False, []
    if "IV" in stage:
        if ecog >= 3:
            refer = True
            reasons.append(f"Stage IV + ECOG={ecog}")
        if le <= 6 and le > 0:
            refer = True
            reasons.append(f"预估生存≤{le}月")
        if uncontrolled_pain:
            refer = True
            reasons.append("顽固性癌痛")
        if "对症" in tx or "姑息" in tx:
            refer = True
            reasons.append("已转对症支持")
    elif cancer_stage in ("III",) and (ecog >= 3 or le <= 6):
        refer = True
        reasons.append(f"Stage III + ECOG={ecog}")

    if le > 0:
        care_level = "临终关怀" if le <= 3 else ("安宁疗护" if le <= 12 else ("姑息治疗" if refer else "常规治疗"))
    else:
        care_level = "姑息治疗" if refer else "常规治疗"

    recs = ["安宁疗护团队转介", "疼痛+姑息联合管理", "症状控制优先",
            "心理社会+家属哀伤辅导", "ACP 讨论"] if refer else ["继续抗肿瘤治疗", "定期疼痛再评估"]

    return {
        "status": "ok",
        "refer_recommended": refer, "care_level": care_level,
        "reasons": reasons, "cancer_stage": cancer_stage,
        "ecog": ecog, "prognosis_months": le,
        "recommendations": recs,
        "summary": f"安宁疗护: {'推荐' if refer else '不推荐'} — {care_level}",
    }
