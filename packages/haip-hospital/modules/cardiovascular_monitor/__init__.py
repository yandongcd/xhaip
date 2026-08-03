"""心脑血管疾病智能监测与随访平台 — 事件识别 + 风险分层 + 随访 + 公卫上报.

双路径: 事件路径(ICD-10→检验→排除→确认) + 风险路径(因素→评分→分层).
"""
from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="cardiovascular-monitor", department="公共卫生科")
_GUIDELINES = [
    "中国心血管病一级预防指南 (2023)",
    "中国高血压防治指南 (2024年修订版)",
    "中国2型糖尿病防治指南 (2024年版)",
    "中国血脂管理指南 (2023)",
    "国家慢性病防控规范 — 心脑血管事件报告",
    "ACC/AHA 心血管疾病一级预防指南 (2019)",
]
_agent.rule_engine.load_all()

# ICD-10 → CVD event mapping
CVD_ICD_CODES = {
    "AMI": ["I21", "I22"], "STEMI": ["I21.0", "I21.1", "I21.2", "I21.3"],
    "NSTEMI": ["I21.4"], "UA": ["I20.0"], "stroke_ischemic": ["I63"],
    "stroke_hemorrhagic": ["I61", "I62"], "TIA": ["G45"],
    "HF": ["I50"], "AF": ["I48"],
}

# CVD risk factors
RISK_FACTORS = {
    "hypertension": {"label": "高血压", "weight": 2, "threshold": "SBP≥140 or DBP≥90"},
    "diabetes": {"label": "糖尿病", "weight": 2, "threshold": "HbA1c≥6.5% or FPG≥7.0"},
    "dyslipidemia": {"label": "血脂异常", "weight": 1, "threshold": "LDL-C≥3.4 or TC≥5.2"},
    "smoking": {"label": "吸烟", "weight": 2, "threshold": "当前吸烟或戒烟<1年"},
    "obesity": {"label": "肥胖", "weight": 1, "threshold": "BMI≥28"},
    "family_history": {"label": "早发CVD家族史", "weight": 1, "threshold": "一级亲属男<55/女<65"},
    "ckd": {"label": "慢性肾脏病", "weight": 2, "threshold": "eGFR<60 or 蛋白尿"},
}

FOLLOWUP_TEMPLATES = {
    "AMI": {"频率": "1/3/6/12月(首年), 此后每6月", "检查": "ECG+心脏超声+LDL-C+HbA1c+肾功能", "目标": "LDL-C<1.4, BP<130/80, 双抗≥12月"},
    "stroke": {"频率": "1/3/6/12月(首年), 此后每6月", "检查": "NIHSS+mRS+颈动脉超声+LDL-C+HbA1c", "目标": "LDL-C<1.8, BP<140/90, 抗血小板/抗凝"},
    "HF": {"频率": "1/3/6/12月", "检查": "NT-proBNP+心脏超声+肾功能+电解质+K+", "目标": "NT-proBNP下降>30%, 体重稳定, GDMT达标"},
    "general": {"频率": "每3-6月", "检查": "BP+LDL-C+HbA1c+肾功能", "目标": "BP<140/90, LDL-C<2.6, HbA1c<7.0%"},
}


def event_identify(**kwargs) -> dict:
    """心脑血管事件识别 — ICD-10 + 证据链."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid) or {}

    dx = str(p.get("diagnosis", "")).lower()
    labs = p.get("lab_results", {}) or {}

    events = []
    # Check diagnosis keywords
    if any(kw in dx for kw in ["心梗", "心肌梗死", "心肌梗塞", "mi", "ami"]):
        events.append({"event": "急性心肌梗死(AMI)", "type": "arteriosclerotic", "severity": "high"})
    if any(kw in dx for kw in ["脑梗", "脑卒中", "卒中", "中风", "stroke", "脑出血"]):
        events.append({"event": "脑卒中(Stroke)", "type": "cerebrovascular", "severity": "high"})
    if any(kw in dx for kw in ["心衰", "心力衰竭", "heart failure", "hf"]):
        events.append({"event": "心力衰竭(HF)", "type": "cardiac", "severity": "medium"})
    if any(kw in dx for kw in ["房颤", "af", "atrial fibrillation"]):
        events.append({"event": "心房颤动(AF)", "type": "arrhythmia", "severity": "medium"})

    # Lab evidence
    troponin = float(labs.get("troponin", 0) or 0)
    if troponin > 0.5 and not events:
        events.append({"event": "疑似心肌损伤(troponin升高)", "type": "cardiac", "severity": "pending"})

    return {
        "status": "ok",
        "patient_id": pid,
        "events": events,
        "event_count": len(events),
        "needs_reporting": len(events) > 0,
        "action": "需填报心脑血管事件报告卡" if events else "无急性CVD事件",
    }


def risk_stratify(**kwargs) -> dict:
    """CVD风险分层."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid) or {}
    age = p.get("age", 0)
    dx = str(p.get("diagnosis", "")).lower()
    labs = p.get("lab_results", {}) or {}

    score = 0
    matched = []

    for key, info in RISK_FACTORS.items():
        if key == "hypertension" and any(kw in dx for kw in ["高血压", "hypertension"]) or key == "diabetes" and any(kw in dx for kw in ["糖尿病", "diabetes"]) or key == "dyslipidemia" and any(kw in dx for kw in ["高脂", "dyslipidemia"]) or key == "ckd" and any(kw in dx for kw in ["肾病", "kidney", "CKD", "renal"]) or key == "obesity" and p.get("bmi", 0) and float(str(p.get("bmi", 0))) >= 28:
            matched.append(info["label"]); score += info["weight"]

    if age >= 55:
        matched.append(f"年龄≥55 ({age}岁)"); score += 1

    level = "低危"
    if score >= 6:
        level = "高危"
    elif score >= 3:
        level = "中危"

    return {
        "status": "ok",
        "score": score, "level": level,
        "factors": matched,
        "summary": f"CVD风险分层 — {level} (评分{score})",
        "recommendations": [
            "高危: 每3月随访+LDL-C+BP+血糖三重达标",
            "中危: 每6月随访+生活方式干预",
            "低危: 每年健康体检+保持健康生活方式",
        ],
    }


def followup_plan(**kwargs) -> dict:
    """个体化随访计划."""
    pid = kwargs.get("patient_id", "")
    risk_level = kwargs.get("risk_level", "中危")
    event_type = kwargs.get("event_type", "general")

    template = FOLLOWUP_TEMPLATES.get(event_type, FOLLOWUP_TEMPLATES["general"])
    freq = {"高危": "每3月", "中危": "每6月", "低危": "每年"}

    schedule = [
        {"节点": "出院后1周", "方式": "电话随访", "内容": "用药依从性+症状评估+血压监测"},
        {"节点": f"{freq.get(risk_level, '每6月')}随访", "方式": "门诊/社区",
         "内容": f"{template['检查']} + 生活方式评估"},
        {"节点": "年度评估", "方式": "门诊", "内容": "心脏超声+颈动脉超声+综合风险评估"},
    ]

    return {
        "status": "ok",
        "summary": f"随访计划 — {event_type} {risk_level}",
        "schedule": schedule,
        "targets": template.get("目标", ""),
    }


def public_health_report(**kwargs) -> dict:
    """公卫上报 — 心脑血管事件报告卡."""
    pid = kwargs.get("patient_id", "")
    event_type = kwargs.get("event_type", "")
    event_date = kwargs.get("event_date", "")

    report_card = {
        "报告卡类型": "心脑血管事件报告卡",
        "患者ID": pid,
        "事件类型": event_type,
        "事件日期": event_date,
        "填报日期": "2026-07-26",
        "ICD-10编码": CVD_ICD_CODES.get(event_type, [""])[0] if event_type in CVD_ICD_CODES else "",
        "报告单位": "南方医科大学南方医院",
        "报告人": "__________",
    }

    return {
        "status": "ok",
        "summary": f"公卫报告卡 — {event_type}",
        "report_card": report_card,
        "deadline": "事件发生后24h内上报",
        "channel": "中国疾控中心 — 慢性病监测系统",
    }
