"""创伤骨科 — T2 时机引擎 + 并发症预测 + 护理计划 + 随访 + 分型 + 手术方案.

业务流来源:
  - 国家卫健委 2022 版《老年髋部骨折诊疗与管理指南》(65 条规则)
  - NICE NG37 (25 条) / AAOS 2022 (20 条) / CSCO 2018/2020 (22 条)
  - 南方医院 T2 层次调整 (5 项差异)

设计方法论:
  - 5 层证据链: 国标 PDF → 指南 YAML → 规则 YAML → BP YAML → Python 模块
  - T2 8 因素层次决策: 高危(心脏/肺/脑) → 中危(抗凝/贫血/肾/感染/血糖) → 无 → 48h
"""

from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="orthopedic-surgery", department="创伤骨科")
_GUIDELINES = [
    "国家卫健委《老年髋部骨折诊疗与管理指南(2022年版)》",
    "NICE NG37 髋部骨折管理 (2023)",
    "AAOS 老年髋部骨折循证临床实践指南 (2022)",
    "CSCO 股骨颈骨折诊疗指南 (2018)",
    "CSCO 转子间骨折诊疗指南 (2020)",
    "ACCP 抗栓治疗与血栓预防指南 (2021)",
    "Caprini 静脉血栓栓塞症风险评估模型",
]
_agent.rule_engine.load_all()

# Re-export clinical functions
from .clinical import analyze_xray, harris_score, parse_clinical_text  # noqa: F401

# Re-export extended module functions
from .extended import (  # noqa: F401
    checklist,
    completeness,
    osteoporosis_mgmt,
    quality_audit,
    rehab_track,
)
from .his_adapter import query_imaging, query_labs, query_patient  # noqa: F401
from .idata_adapter import list_categories, search_knowledge  # noqa: F401

# Re-export new modules (v1.1: MDT + HIS Mock + iData Mock)
from .mdt import audit_stage, mdt_aggregate, mdt_summary  # noqa: F401

EVIDENCE_REFS = {
    "general": [
        "# 国家卫健委 2022 版《老年髋部骨折诊疗与管理指南》(65 条规则)",
        "# NICE NG37: Hip Fracture Management (2023 update)",
        "# AAOS 2022: Management of Hip Fractures in the Elderly",
        "# CSCO 2018/2020 骨与软组织肿瘤诊疗指南 (22 条)",
    ],
    "timing": [
        "# 国家卫健委 2022 §4.1: 力争入院 48h 内完成手术",
        "# NICE NG37 §1.1: Surgery on day of or day after admission",
        "# 南方医院 T2 层次调整 (5 项差异)",
    ],
    "surgery": [
        "# NICE NG37 §1.5: 移位型股骨颈骨折推荐 THA",
        "# AAOS 2022 §III: Cephalomedullary nail vs sliding hip screw",
        "# 国家卫健委 2022 §5.2: 转子间骨折内固定选择",
    ],
}

DISCLAIMER = ("本建议由 AI 辅助生成，需经临床医师审核确认后方可作为诊疗依据。"
              "不构成独立医疗决策。")


# ═══════════════════════════════════════════════════════════
# 1. T2 手术时机决策引擎 (timing_engine v3.0)
# ═══════════════════════════════════════════════════════════

TIMING_FACTORS = {
    "cardiac": {
        "weight": "high",
        "label": "心脏因素",
        "criteria": {
            "troponin_high": "cTnI > 0.04 or cTnT > 0.1",
            "ckmb_high": "CK-MB > 25",
            "ecg_high_risk": "ST elevation / ST depression / VT / VF / 3° AVB",
        },
    },
    "pulmonary": {
        "weight": "high",
        "label": "肺部因素",
        "criteria": {
            "acute": "急性肺炎 / 肺栓塞 / 哮喘急性发作 / COPD 加重 / 呼衰",
        },
    },
    "cerebral": {
        "weight": "high",
        "label": "脑血管因素",
        "criteria": {
            "acute": "急性卒中 / 脑梗 / TIA / 脑出血 (1 月内)",
        },
    },
    "anticoagulation": {
        "weight": "medium",
        "label": "抗凝管理",
        "criteria": {
            "severe": "华法林 + INR > 1.5",
            "moderate": "NOAC 使用 / 抗血小板 / PT > 14",
        },
    },
    "anemia": {
        "weight": "medium",
        "label": "贫血",
        "criteria": {
            "severe": "Hb < 80",
            "moderate": "Hb < 100 + 心脏病史",
        },
    },
    "renal": {
        "weight": "medium",
        "label": "肾功能",
        "criteria": {
            "severe": "eGFR < 30",
            "moderate": "eGFR < 60 or Cr > 133",
        },
    },
    "infection": {
        "weight": "medium",
        "label": "感染/炎症",
        "criteria": {
            "severe": "WBC > 12 or CRP > 100",
            "moderate": "NEUT > 8",
        },
    },
    "glucose": {
        "weight": "medium",
        "label": "血糖",
        "criteria": {
            "severe": "空腹血糖 > 13.9 or DKA or HHS",
            "moderate": "HbA1c > 9.0",
        },
    },
}


def evaluate_timing(
    patient_id: str = "",
    labs: dict[str, float] | None = None,
    ecg_findings: str = "",
    conditions: list[str] | None = None,
    meds: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """T2 层次决策: 8 因素评估 → 手术时机分级。

    参考: 国家卫健委 2022 §4 + NICE NG37 + 南方医院 T2 调整

    Returns:
        urgency: "emergency" (< 48h) | "urgent" (3-7d) | "elective" (MDT 延迟)
        delay_factors: 触发延迟的具体因素
        recommendation: 临床建议
    """
    labs = labs or {}
    conditions = [c.lower() for c in (conditions or [])]
    meds = [m.lower() for m in (meds or [])]

    high_triggers: list[str] = []
    medium_triggers: list[str] = []

    # ── 高危因素 ──
    troponin = labs.get("troponin", labs.get("cTnI", 0))
    ckmb = labs.get("ckmb", labs.get("CK-MB", 0))
    if troponin > 0.04 or ckmb > 25:
        high_triggers.append("cardiac_troponin")
    if any(p in ecg_findings.upper() for p in ["ST ELEVATION", "ST DEPRESSION", "VT", "VF", "3° AVB"]):
        high_triggers.append("cardiac_ecg")

    pulm_keywords = ["肺炎", "肺栓塞", "哮喘发作", "copd加重", "呼衰", "pneumonia", "pe"]
    if any(k in " ".join(conditions) for k in pulm_keywords):
        high_triggers.append("pulmonary")

    neuro_keywords = ["卒中", "脑梗", "tia", "脑出血", "cerebral"]
    if any(k in " ".join(conditions) for k in neuro_keywords):
        high_triggers.append("cerebral")

    # ── 中危因素 ──
    inr = labs.get("inr", 1.0)
    if "warfarin" in " ".join(meds) and inr > 1.5:
        medium_triggers.append("anticoag_severe")
    elif any(m in " ".join(meds) for m in ["rivaroxaban", "apixaban", "clopidogrel", "ticagrelor"]):
        medium_triggers.append("anticoag_moderate")

    hb = labs.get("hb", labs.get("hemoglobin", 150))
    has_cardiac = any(c in " ".join(conditions) for c in ["冠心病", "心衰", "心律失常", "cad", "chf"])
    if hb < 80:
        medium_triggers.append("anemia_severe")
    elif hb < 100 and has_cardiac:
        medium_triggers.append("anemia_moderate")

    egfr = labs.get("egfr", labs.get("eGFR", 90))
    cr = labs.get("creatinine", labs.get("Cr", 80))
    if egfr < 30:
        medium_triggers.append("renal_severe")
    elif egfr < 60 or cr > 133:
        medium_triggers.append("renal_moderate")

    wbc = labs.get("wbc", labs.get("WBC", 7))
    crp = labs.get("crp", labs.get("CRP", 5))
    if wbc > 12 or crp > 100:
        medium_triggers.append("infection_severe")

    glucose = labs.get("glucose", labs.get("Glu", 5))
    if glucose > 13.9:
        medium_triggers.append("glucose_severe")

    # ── 决策 ──
    if high_triggers:
        urgency = "elective"
        recommendation = "存在高危延迟因素，建议 MDT 会诊后择期手术"
    elif medium_triggers:
        urgency = "urgent"
        recommendation = "存在可控延迟因素，建议 3-7 天内限期手术"
    else:
        urgency = "emergency"
        recommendation = "无延迟因素，建议 48h 内急诊手术 (NICE NG37 推荐)"

    return {
        "patient_id": patient_id,
        "urgency": urgency,
        "sla": {"emergency": "<48h", "urgent": "3-7d", "elective": "MDT 确定"}[urgency],
        "high_triggers": high_triggers,
        "medium_triggers": medium_triggers,
        "total_factors": len(high_triggers) + len(medium_triggers),
        "recommendation": recommendation,
        "evidence": ["国家卫健委 2022 §4", "NICE NG37", "南方医院 T2 调整"],
    }


# ═══════════════════════════════════════════════════════════
# 2. 并发症风险预测
# ═══════════════════════════════════════════════════════════

def predict_complications(
    patient_id: str = "",
    age: int = 0,
    labs: dict[str, float] | None = None,
    conditions: list[str] | None = None,
    procedure: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """4 维度并发症风险: DVT / 感染 / 心脏 / 跌倒-谵妄。

    参考: DVT共识 2024 / RCRI / Morse跌倒评估
    """
    labs = labs or {}
    conditions = [c.lower() for c in (conditions or [])]

    # ── DVT/PE 风险 (Caprini 简化) ──
    dvt_score = 1  # base: 大手术
    if age >= 75:
        dvt_score += 2
    if age >= 60:
        dvt_score += 1
    if labs.get("bmi", 22) > 30:
        dvt_score += 1
    if any(c in " ".join(conditions) for c in ["卧床", "瘫痪", "immobil"]):
        dvt_score += 1
    if any(c in " ".join(conditions) for c in ["dvt史", "pe史", "血栓"]):
        dvt_score += 3
    dvt_risk = "high" if dvt_score >= 5 else "moderate" if dvt_score >= 3 else "low"

    # ── 感染风险 ──
    infection_score = 0
    wbc = labs.get("wbc", 7)
    crp = labs.get("crp", 5)
    if wbc > 12:
        infection_score += 2
    if crp > 100:
        infection_score += 2
    if any(c in " ".join(conditions) for c in ["糖尿病", "dm", "diabetes"]):
        infection_score += 1
    if labs.get("albumin", 40) < 30:
        infection_score += 1
    infection_risk = "high" if infection_score >= 4 else "moderate" if infection_score >= 2 else "low"

    # ── 心脏风险 (简化 RCRI) ──
    cardiac_score = 1  # base: 骨科大手术
    if any(c in " ".join(conditions) for c in ["冠心病", "心梗史", "心衰", "cad", "mi", "chf"]):
        cardiac_score += 1
    cr = labs.get("creatinine", 80)
    if cr > 177:
        cardiac_score += 1
    if any(c in " ".join(conditions) for c in ["糖尿病", "dm"]):
        cardiac_score += 1
    cardiac_risk = "high" if cardiac_score >= 3 else "moderate" if cardiac_score >= 2 else "low"

    # ── 跌倒/谵妄风险 ──
    fall_score = 0
    if age >= 80:
        fall_score += 2
    if age >= 70:
        fall_score += 1
    if any(c in " ".join(conditions) for c in ["痴呆", "认知", "dementia"]):
        fall_score += 2
    if any(c in " ".join(conditions) for c in ["镇静", "sedative", "催眠"]):
        fall_score += 1
    fall_risk = "high" if fall_score >= 4 else "moderate" if fall_score >= 2 else "low"

    risks = {"dvt": dvt_risk, "infection": infection_risk, "cardiac": cardiac_risk, "fall_delirium": fall_risk}
    overall = "high" if "high" in risks.values() else "moderate" if "moderate" in risks.values() else "low"

    prevention: list[str] = []
    if dvt_risk in ("high", "moderate"):
        prevention.append("LMWH + IPC + GCS + 踝泵")
    if infection_risk in ("high", "moderate"):
        prevention.append("围术期抗生素 + 血糖控制")
    if cardiac_risk in ("high",):
        prevention.append("心内科会诊 + 术中监测")
    if fall_risk in ("high", "moderate"):
        prevention.append("防跌倒宣教 + 床栏 + 呼叫铃")

    return {
        "patient_id": patient_id,
        "overall_risk": overall,
        "risks": risks,
        "scores": {"dvt": dvt_score, "infection": infection_score, "cardiac": cardiac_score, "fall": fall_score},
        "prevention": prevention,
        "evidence": ["Caprini DVT 评分", "RCRI 心脏风险指数", "Morse 跌倒评估", "DVT共识 2024"],
    }


# ═══════════════════════════════════════════════════════════
# 3. 围术期护理计划 (4 阶段 25 项)
# ═══════════════════════════════════════════════════════════

def nursing_plan(
    patient_id: str = "",
    age: int = 0,
    conditions: list[str] | None = None,
    procedure: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """4 阶段护理计划: 术前 → 术后当日 → 早期(1-3d) → 恢复期(4d-出院)

    参考: 国家卫健委 2022 §6 + DVT共识 2024 + 衰弱护理共识 2023
    """
    conditions = [c.lower() for c in (conditions or [])]

    plan = {
        "stage_1_preop": {
            "label": "术前护理 (入院-术前)",
            "items": [
                "健康宣教: 手术流程 + 疼痛管理 + 康复预期",
                "皮肤准备: 术区清洁 + 全身皮肤评估",
                "禁食指导: 术前 6h 禁食 / 2h 禁水",
                "VTE 风险评估 (Caprini) + 基础预防教育",
                "谵妄风险评估 (CAM) + 环境优化",
            ],
        },
        "stage_2_day0": {
            "label": "术后当日 (D0)",
            "items": [
                "生命体征: q1h×4 → q4h",
                "体位: 患肢外展中立位, 抬高 15-30°",
                "伤口观察: 渗血/肿胀/皮温",
                "疼痛评估: VAS q4h, 目标 ≤ 3",
                "DVT 物理预防: IPC 2×/天 + GCS + 踝泵 20 次/h",
                "压疮预防: Braden 评分, q2h 翻身",
            ],
        },
        "stage_3_early": {
            "label": "术后早期 (D1-D3)",
            "items": [
                "饮食: 逐步过渡普食, 高蛋白",
                "功能锻炼: 踝泵 + 股四头肌等长收缩 + CPM",
                "导管管理: 引流管/尿管评估拔除时机",
                "排便管理: 预防便秘",
                "心理护理: 焦虑/抑郁筛查",
            ],
        },
        "stage_4_recovery": {
            "label": "恢复期 (D4-出院)",
            "items": [
                "下床活动: 助行器辅助, 渐进负重",
                "防跌倒教育: 环境安全 + 起床三步法",
                "出院指导: 伤口护理 + 用药 + 复查时间",
                "照顾者培训: 翻身/转移/如厕",
                "DVT 药物预防: LMWH 2-5 周",
            ],
        },
    }

    # 患者特异性高亮
    highlights: list[str] = []
    if age >= 80:
        highlights.append("高龄患者: 加强谵妄监测 + 防跌倒")
    if any(c in " ".join(conditions) for c in ["糖尿病", "dm"]):
        highlights.append("糖尿病患者: 血糖监测, 围术期目标 6-10 mmol/L")
    if any(c in " ".join(conditions) for c in ["高血压", "htn"]):
        highlights.append("高血压患者: 术前控制 < 160/100, 术后继续口服降压药")
    if any(c in " ".join(conditions) for c in ["copd", "哮喘"]):
        highlights.append("肺部疾病: 呼吸训练 + 雾化 + 体位引流")
    if any(c in " ".join(conditions) for c in ["痴呆", "认知"]):
        highlights.append("认知障碍: 定向力支持 + 家属陪伴 + 减少约束")

    return {
        "patient_id": patient_id,
        "plan": plan,
        "highlights": highlights,
        "evidence": ["国家卫健委 2022 §6", "DVT共识 2024", "衰弱护理共识 2023"],
    }


# ═══════════════════════════════════════════════════════════
# 4. 随访计划 (1/3/6/12 月)
# ═══════════════════════════════════════════════════════════

def followup_plan(
    patient_id: str = "",
    procedure: str = "",
    discharge_date: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """4 个时间点随访 + 6 个红旗症状 + 骨质疏松管理。

    参考: 国家卫健委 2022 §7 + NICE NG37 + APTA 2021
    """
    return {
        "patient_id": patient_id,
        "schedule": [
            {
                "month": 1, "label": "术后 1 个月",
                "tasks": ["伤口愈合评估", "VAS 疼痛评分", "X光复查", "拆线 (如未拆)", "Harris 评分"],
            },
            {
                "month": 3, "label": "术后 3 个月",
                "tasks": ["Harris 评分", "X光 (骨愈合评估)", "功能恢复评估", "骨质疏松治疗启动/调整",
                         "跌倒风险评估"],
            },
            {
                "month": 6, "label": "术后 6 个月",
                "tasks": ["功能评估", "X光复查", "骨密度 DXA (首次或复查)", "用药依从性评估"],
            },
            {
                "month": 12, "label": "术后 12 个月",
                "tasks": ["终期功能评估", "X光确认", "骨密度 DXA 复查", "二次骨折风险评估",
                         "转入社区长期管理评估"],
            },
        ],
        "red_flags": [
            "伤口感染 (红肿/渗液/发热 >38.5°C)",
            "胸痛/呼吸困难 (疑似 PE 或 MI)",
            "下肢肿胀/疼痛 (疑似 DVT)",
            "跌倒/再次受伤",
            "非计划疼痛加重 (VAS > 4)",
            "假体脱位感/异响",
        ],
        "osteoporosis_management": {
            "calcium": "1000-1200 mg/d",
            "vitamin_d": "800-1200 IU/d",
            "medications": ["双膦酸盐 (阿仑膦酸钠 70mg/wk)", "地舒单抗 60mg q6mo (备选)",
                           "特立帕肽 20μg/d (严重骨质疏松)"],
            "bmd_monitoring": "基线 DXA → 1 年复查 → 每 1-2 年",
        },
        "evidence": ["国家卫健委 2022 §7", "NICE NG37", "APTA 2021"],
    }


# ═══════════════════════════════════════════════════════════
# 5. 原有函数 (分型 + 方案) — 保留并增强
# ═══════════════════════════════════════════════════════════

def assess(patient_id: str = "", xray_findings: dict | None = None, **kwargs):
    """骨折分型: Garden/Evans/AO。"""
    findings = xray_findings or {}
    location = findings.get("location", "")
    ftype = findings.get("type", "unknown")

    if "femoral_neck" in location or "股骨颈" in location:
        classification = f"Garden {ftype}"
        severity = "high" if any(x in ftype for x in ["III", "IV"]) else "moderate"
    elif "intertroch" in location or "转子间" in location:
        classification = f"Evans {ftype}"
        severity = "high" if not findings.get("stable", True) else "moderate"
    else:
        classification = "AO classification"
        severity = "moderate"

    return {
        "patient_id": patient_id, "fracture_type": ftype, "location": location,
        "classification": classification, "severity": severity,
        "stability": "stable" if severity == "moderate" else "unstable",
    }


def plan(patient_id: str = "", fracture_type: str = "", age: int = 0, **kwargs):
    """手术方案: 股骨颈≥75→THA, <65→CCS/DHS, 转子间→PFNA。"""
    ft = fracture_type.lower()
    if "femoral" in ft or "股骨颈" in ft:
        procedure = "THA (全髋关节置换)" if age >= 75 else "CCS/DHS (空心钉/动力髋)"
        approach = "后外侧 Moore" if age >= 75 else "微创"
    elif "intertroch" in ft or "转子间" in ft:
        procedure = "PFNA (股骨近端防旋髓内钉) — 金标准"
        approach = "微创髓内"
    else:
        procedure = "待定 — 需明确分型"
        approach = "待定"

    return {
        "patient_id": patient_id, "procedure": procedure, "approach": approach,
        "anesthesia": "腰麻 (ASA≤2) / 全麻 (ASA≥3)",
        "guideline_ref": ["国家卫健委 2022 §5", "AAOS 2022", "CSCO 股骨颈 2018 / 转子间 2020"],
    }


def recommend_surgery(
    patient_id: str = "",
    diagnosis: str = "",
    fracture_type: str = "",
    fracture_stability: str = "",
    age: int = 0,
    **kwargs,
) -> dict[str, Any]:
    """年龄驱动决策树: 个性化手术方案推荐 (纯规则版).

    根据骨折类型 + 年龄 + 稳定性推荐手术方案、入路、植入物。
    不依赖 LLM，纯 Python 决策树，作为 LLM 降级方案。

    Args:
        patient_id: 患者 ID。
        diagnosis: 诊断文本 (用于关键词匹配)。
        fracture_type: 骨折类型 (如 "股骨颈骨折")。
        fracture_stability: 稳定性 ("稳定"/"不稳定")。
        age: 患者年龄。

    Returns:
        {recommended_surgery, alternative_surgery, surgical_approach,
         implant_choice, anesthesia_recommendation, key_considerations,
         guideline_ref, reasoning}
    """
    combined = (fracture_type + " " + diagnosis).lower()

    # ── 股骨颈骨折 ──
    if "股骨颈" in combined or "femoral neck" in combined:
        if age >= 75:
            return {
                "recommended_surgery": "人工全髋关节置换术(THA)",
                "alternative_surgery": "人工股骨头置换术(HA,若预期寿命较短)",
                "surgical_approach": "后外侧入路或直接前入路(DAA)",
                "implant_choice": "生物型假体(骨质量尚可)/骨水泥型假体(骨质疏松严重)",
                "anesthesia_recommendation": "全身麻醉或腰硬联合麻醉",
                "key_considerations": ["高龄患者注意围术期管理", "抗凝药物桥接", "预防DVT"],
                "guideline_ref": "AAOS 2022: 老年移位股骨颈骨折行关节置换",
                "reasoning": f"患者{age}岁,股骨颈骨折,关节置换可早期负重,降低并发症",
            }
        elif age < 65:
            return {
                "recommended_surgery": "闭合/切开复位内固定术(空心螺钉/动力髋螺钉)",
                "alternative_surgery": "若复位不满意则考虑THA",
                "surgical_approach": "经皮微创或前外侧入路",
                "implant_choice": "3枚空心螺钉(稳定型)/DHS(不稳定型)",
                "anesthesia_recommendation": "腰麻或全麻",
                "key_considerations": ["尽量保留自身股骨头", "术后避免早期完全负重",
                                       "监测股骨头坏死风险"],
                "guideline_ref": "中国成人股骨颈骨折诊治指南(2018)",
                "reasoning": f"患者{age}岁相对年轻,内固定可保留自身关节",
            }
        else:
            return {
                "recommended_surgery": "THA 或 内固定(空心螺钉/DHS)",
                "alternative_surgery": "HA (若功能需求低)",
                "surgical_approach": "根据骨质量和功能需求选择",
                "implant_choice": "根据分型决定",
                "anesthesia_recommendation": "全麻或腰硬联合",
                "key_considerations": ["需综合功能需求和骨质量决策", "术前评估并存症"],
                "guideline_ref": "NICE NG37 + 国家卫健委 2022",
                "reasoning": f"患者{age}岁(65-74),手术方案需个体化决策",
            }

    # ── 转子间骨折 ──
    if "转子间" in combined or "intertroch" in combined:
        return {
            "recommended_surgery": "股骨近端防旋髓内钉(PFNA)",
            "alternative_surgery": "InterTAN髓内钉/动力髋螺钉(DHS,稳定型)",
            "surgical_approach": "微创小切口",
            "implant_choice": "PFNA(首选)/InterTAN(反转子间骨折)",
            "anesthesia_recommendation": "全身麻醉或腰硬联合麻醉",
            "key_considerations": ["恢复颈干角和解剖力线", "避免内翻畸形", "尖顶距控制<25mm"],
            "guideline_ref": "老年股骨转子间骨折诊疗指南(2020)",
            "reasoning": "PFNA是转子间骨折金标准,微创,固定牢固",
        }

    # ── 转子下骨折 ──
    if "转子下" in combined or "subtroch" in combined:
        return {
            "recommended_surgery": "长PFNA或股骨近端锁定钢板",
            "alternative_surgery": "逆行髓内钉",
            "surgical_approach": "微创髓内入路",
            "implant_choice": "长PFNA(首选)",
            "anesthesia_recommendation": "全身麻醉",
            "key_considerations": ["注意复位力线", "避免内翻", "长髓内钉跨过骨折端"],
            "guideline_ref": "NICE NG37",
            "reasoning": "转子下骨折需长髓内钉跨过骨折端提供稳定固定",
        }

    return {
        "recommended_surgery": "需进一步明确骨折类型和患者状况",
        "alternative_surgery": "",
        "surgical_approach": "",
        "implant_choice": "",
        "anesthesia_recommendation": "",
        "key_considerations": ["请完善影像学检查明确骨折分型"],
        "guideline_ref": "",
        "reasoning": "信息不足以做出明确手术推荐",
    }


def evaluate(patient_id: str = "", **kwargs):
    return {"patient_id": patient_id, "cleared_for_surgery": True,
            "risk_factors": [], "required_consults": ["cardio", "anesthesia"]}


def predict(patient_id: str = "", **kwargs):
    return predict_complications(patient_id=patient_id, **kwargs)


def decide(patient_id: str = "", is_emergency: bool = False, **kwargs):
    if is_emergency:
        return {"patient_id": patient_id, "timing": "immediate", "sla": "即刻"}
    return evaluate_timing(patient_id=patient_id, **kwargs)
