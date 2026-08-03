"""住院患者跌倒防护智能体 — Morse + Hendrich II + 个性化方案."""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="fall-prevention", department="护理部")
_GUIDELINES = [
    "Morse Fall Scale (Morse et al., 1989)",
    "Hendrich II Fall Risk Model (2003)",
    "中国医院协会《患者安全目标》— 防范与减少患者跌倒/坠床",
    "NICE CG161 老年人跌倒预防 (2013, updated 2019)",
    "南方医院跌倒防护SOP (T2)",
]
_agent.rule_engine.load_all()

# Morse Fall Scale
MORSE_ITEMS = [
    ("跌倒史", [("无", 0), ("有", 25)]),
    ("二次诊断", [("无", 0), ("≥2个", 15)]),
    ("行走辅助", [("无/卧床/护士帮助", 0), ("拐杖/助行器", 15), ("扶家具行走", 30)]),
    ("静脉输液", [("无", 0), ("有", 20)]),
    ("步态", [("正常/卧床/轮椅", 0), ("虚弱", 10), ("不正常", 20)]),
    ("精神状态", [("认知自身能力", 0), ("高估/遗忘自身限制", 15)]),
]

# High-risk semantic factors (from A34 needs document)
HIGH_RISK_FACTORS = [
    "步态不稳", "行走困难", "体力虚弱", "肌力下降",
    "视力障碍", "视力模糊", "依从性差", "不配合",
    "术后麻醉未醒", "麻醉恢复期", "跌倒史",
    "Hb<90", "白蛋白<30", "电解质异常",
]


def morse_assess(**kwargs) -> dict:
    """Morse 跌倒风险评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _agent.clinical_result("Patient not found", None)

    age = p.get("age", 0)

    # Score based on patient data
    score = 0
    factors = []

    if age >= 65:
        score += 15
        factors.append("年龄≥65 (+15)")

    dx = str(p.get("diagnosis", "")).lower()
    if "跌倒" in dx or "fall" in dx:
        score += 25
        factors.append("跌倒史 (+25)")

    # Multiple diagnoses implies secondary diagnosis
    score += 15
    factors.append("合并多种诊断 (+15)")

    if age >= 75:
        score += 15
        factors.append("高龄≥75 — 步态虚弱 (+15)")

    # Post-op anesthesia risk
    meds = str(p.get("medications", "")).lower()
    if any(kw in meds for kw in ["镇静", "安眠", "sedative", "麻醉"]):
        score += 20
        factors.append("使用镇静/麻醉药物 (+20)")

    level = "低危"
    if score >= 45:
        level = "高危"
    elif score >= 25:
        level = "中危"

    guides = _agent.search_guidelines("跌倒评估") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"Morse跌倒评估 — {level} (评分{score})",
        patient=p,
        guidelines=guides,
        findings=[{
            "Morse评分": score,
            "风险等级": level,
            "评分因素": factors,
            "解读": "0-24低危 / 25-44中危 / ≥45高危",
        }],
        recommendations=[
            "高危(≥45): 床头高危标识 + 床栏+呼叫铃 + 每班评估 + 家属教育",
            "中危(25-44): 床栏+防滑鞋+环境安全+定时巡视",
            "低危(<25): 常规安全指导+环境安全检查",
        ],
    )


def prevention_plan(**kwargs) -> dict:
    """个性化跌倒防护方案."""
    pid = kwargs.get("patient_id", "")
    morse_score = int(kwargs.get("morse_score", 0) or 0)
    risk_level = kwargs.get("risk_level", "低危")

    p = _agent.get_patient(pid) or {}
    age = p.get("age", 0)

    plan = {
        "environment": [
            "床栏拉起(双侧)",
            "床头呼叫铃置于伸手可及处",
            "病床降至最低位置",
            "清除地面障碍物/保持干燥",
            "夜间保留地灯",
        ],
        "behavior": [
            "下床活动前先坐起2分钟(预防体位性低血压)",
            "穿防滑鞋/勿穿拖鞋行走",
            "如厕/洗漱需家属或护士陪同",
            "头晕/乏力时立即呼叫帮助",
        ],
        "medication": [
            "评估镇静/安眠/降压/降糖/利尿剂使用 → 注意体位性低血压风险",
            "避免夜间使用利尿剂",
        ] if age >= 65 else [],
        "monitoring": [
            "每班评估跌倒风险(Morse评分)",
            "高危患者: 每2小时巡视一次",
        ] if risk_level == "高危" else ["每班巡视+评估"],
    }

    if risk_level == "高危":
        plan["environment"].append("⚠️ 床头高危跌倒警示标识(红色)")
        plan["environment"].append("必要时使用约束带(需家属签署知情同意)")
        plan["monitoring"].append("交班重点: 标注高危跌倒+防护措施完成情况")

    return {
        "status": "ok",
        "summary": f"跌倒防护方案 — {risk_level} (Morse {morse_score})",
        "risk_level": risk_level,
        "plan": plan,
        "disclaimer": "本方案为AI辅助生成，须经责任护士确认后执行",
    }


def postop_check(**kwargs) -> dict:
    """术后麻醉恢复期跌倒风险评估."""
    pid = kwargs.get("patient_id", "")
    surgery_date = kwargs.get("surgery_date", "")
    anesthesia_type = kwargs.get("anesthesia_type", "")

    p = _agent.get_patient(pid) or {}

    risk = "中危"
    alerts = []

    if anesthesia_type in ("全麻", "腰麻", "硬膜外", "general", "spinal", "epidural"):
        risk = "高危"
        alerts.append("🔴 麻醉药物残留效应 — 术后24h内极度高危")
        alerts.append("术后24h内: 必须有人陪护下床")

    if any(kw in anesthesia_type.lower() for kw in ["opioid", "阿片", "sedative", "镇静"]):
        alerts.append("⚠️ 阿片/镇静药物 — 增加跌倒风险")

    return {
        "status": "ok",
        "summary": f"术后跌倒评估 — {risk} ({anesthesia_type or '未指定麻醉方式'})",
        "risk": risk,
        "alerts": alerts,
        "recommendations": [
            "术后首次下床须在护士/家属搀扶下进行",
            "评估下肢肌力(坐-站测试)后再允许独立行走",
            "术后24h内: 床旁便器 → 避免走到卫生间",
            "条件允许: 术后4-6h开始渐进式离床活动",
        ],
    }
