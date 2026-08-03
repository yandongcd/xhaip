"""antiemetic — Perioperative Antiemetic Management.

Clinical tools:
  - assess: PONV risk assessment (Apfel score)
  - prophylaxis: Prophylactic antiemetic regimen recommendation
  - rescue: Breakthrough PONV rescue management

Guidelines referenced:
  - SAMBA Guidelines for PONV (2020)
  - Fourth Consensus Guidelines for PONV Management (2020)
  - Chinese Expert Consensus on PONV Prevention (中华医学会麻醉学分会)
"""

from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="antiemetic", department="药学部")
_GUIDELINES = [
    "ASER/SAMBA 术后恶心呕吐管理共识 (2020)",
    "中国麻醉学会 术后恶心呕吐诊疗指南 (2025版)",
    "Fourth Consensus Guidelines for PONV Management (2020)",
    "NMPA 止吐药物说明书 (5-HT3/NK1/糖皮质激素/抗组胺类)",
]
_agent.rule_engine.load_all()

APFEL_FACTORS = {
    "female": "女性",
    "nonsmoker": "非吸烟者",
    "ponv_history": "PONV/晕动病史",
    "postop_opioid": "术后阿片类镇痛",
}

RISK_STRATA: dict[int, dict[str, Any]] = {
    0: {"risk": "低危", "incidence": "~10%", "level": 0},
    1: {"risk": "低中危", "incidence": "~20%", "level": 1},
    2: {"risk": "中危", "incidence": "~40%", "level": 2},
    3: {"risk": "高危", "incidence": "~60%", "level": 3},
    4: {"risk": "极高危", "incidence": "~80%", "level": 4},
}

ANTIEMETIC_AGENTS: dict[str, dict[str, Any]] = {
    "5ht3": {
        "class": "5-HT3 受体拮抗剂",
        "drugs": ["昂丹司琼 (4-8mg IV)", "格拉司琼 (1mg IV)", "帕洛诺司琼 (0.075mg IV)"],
        "mechanism": "阻断中枢化学感受器触发区和外周5-HT3受体",
        "timing": "手术结束前 30min",
        "efficacy": "中等 (NNT≈6)",
        "caution": ["QT间期延长", "肝功能不全"],
    },
    "dexamethasone": {
        "class": "糖皮质激素",
        "drugs": ["地塞米松 (4-8mg IV)"],
        "mechanism": "抗炎+抗前列腺素+减少5-HT释放",
        "timing": "麻醉诱导后",
        "efficacy": "强效 (NNT≈4)",
        "caution": ["血糖升高 (糖尿病患者需监测)", "免疫功能抑制"],
    },
    "dopamine_antagonist": {
        "class": "D2 受体拮抗剂",
        "drugs": ["甲氧氯普胺 (10mg IV)", "氟哌利多 (0.625-1.25mg IV)"],
        "mechanism": "阻断中枢D2受体+增强胃肠动力",
        "timing": "麻醉诱导时或术毕",
        "efficacy": "弱-中等",
        "caution": ["锥体外系反应", "QT间期延长 (氟哌利多)"],
    },
    "anticholinergic": {
        "class": "抗胆碱能药",
        "drugs": ["东莨菪碱贴片 (1.5mg 透皮)"],
        "mechanism": "阻断前庭系统和呕吐中枢M1受体",
        "timing": "术前 2-4h 贴片",
        "efficacy": "中等 (对晕动病/PONV史有效)",
        "caution": ["口干", "视物模糊", "尿潴留", "闭角型青光眼"],
    },
    "nk1": {
        "class": "NK-1 受体拮抗剂",
        "drugs": ["阿瑞匹坦 (40mg PO)"],
        "mechanism": "阻断中枢NK-1受体 (substance P)",
        "timing": "术前 1-3h 口服",
        "efficacy": "强效 (NNT≈3)",
        "caution": ["CYP3A4 相互作用 (华法林/口服避孕药)"],
    },
}

RESCUE_AGENTS: dict[str, dict[str, Any]] = {
    "ondansetron": {
        "class": "5-HT3 受体拮抗剂",
        "dose": "昂丹司琼 4mg IV (如已用则换类)",
        "onset": "5-10min",
    },
    "promethazine": {
        "class": "H1 受体拮抗剂",
        "dose": "异丙嗪 12.5-25mg IV",
        "onset": "5-10min",
    },
    "dimenhydrinate": {
        "class": "H1 受体拮抗剂",
        "dose": "茶苯海明 50mg IV",
        "onset": "5-10min",
    },
    "haloperidol": {
        "class": "丁酰苯类 (D2 拮抗剂)",
        "dose": "氟哌啶醇 0.5-1mg IV",
        "onset": "10-15min",
    },
    "propofol": {
        "class": "亚麻醉剂量丙泊酚",
        "dose": "丙泊酚 10-20mg IV (亚麻醉剂量)",
        "onset": "2-3min",
    },
}

HIGH_EMETIC_SURGERIES = [
    "腹腔镜", "胆囊", "胆囊切除术", "妇科", "子宫",
    "斜视", "中耳", "甲状腺", "整形",
]


def assess(
    patient_id: str = "",
    risk_factors: dict[str, bool] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """PONV 风险评估 — Apfel 4因素评分.

    Apfel 评分因素:
      1. 女性
      2. 非吸烟者
      3. PONV/晕动病史
      4. 术后预计使用阿片类镇痛

    Reference: Apfel CC et al, Anesthesiology 2004;101:265-267
    """
    risk_factors = risk_factors or {}

    apfel_score = 0
    factors_present: list[dict[str, Any]] = []

    factor_keys = [
        ("female", "女性"),
        ("nonsmoker", "非吸烟者"),
        ("ponv_history", "PONV/晕动病史"),
        ("postop_opioid", "术后预计使用阿片类"),
    ]

    for key, label in factor_keys:
        present = risk_factors.get(key, False) or kwargs.get(key, False)
        factors_present.append({
            "factor": label,
            "key": key,
            "present": present,
        })
        if present:
            apfel_score += 1

    risk = RISK_STRATA.get(apfel_score, RISK_STRATA[0])

    return {
        "status": "ok",
        "patient_id": patient_id,
        "assessment": (
            f"Apfel 评分 {apfel_score}/4 分，PONV 风险 {risk['risk']} "
            f"(预估发生率 {risk['incidence']})"
        ),
        "apfel_score": apfel_score,
        "risk_level": risk["risk"],
        "predicted_incidence": risk["incidence"],
        "risk_factors": factors_present,
        "guideline_refs": [
            "Apfel CC et al, Anesthesiology 2004;101:265-267",
            "SAMBA Consensus Guidelines for PONV Management (2020)",
            "中华医学会麻醉学分会 PONV 防治专家共识 (2020)",
        ],
    }


def prophylaxis(
    patient_id: str = "",
    apfel_score: int = 0,
    surgery_type: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """预防性止吐方案推荐 (基于风险分层).

    Risk-based prophylaxis:
      Apfel 0 + 非高危手术: 无需常规预防
      Apfel 1: 单一药物 (5-HT3 拮抗剂首选)
      Apfel 2: 二联 (5-HT3 + 地塞米松)
      Apfel 3: 三联 (5-HT3 + 地塞米松 + D2 拮抗剂)
      Apfel 4: 四联 (5-HT3 + 地塞米松 + D2拮抗剂 + NK-1/东莨菪碱)

    Reference: SAMBA Guidelines (2020)
    """
    plan: list[dict[str, Any]] = []

    is_high_emetic = any(s in surgery_type for s in HIGH_EMETIC_SURGERIES)

    if apfel_score == 0 and not is_high_emetic:
        plan.append({
            "step": 1,
            "agent_class": "无",
            "drugs": ["无需常规预防性用药"],
            "note": "Apfel 0 分 + 非高危手术类型，PONV 发生率低",
        })
    elif apfel_score == 1 and not is_high_emetic:
        plan.append({
            "step": 1,
            "agent_class": ANTIEMETIC_AGENTS["5ht3"]["class"],
            "drugs": ANTIEMETIC_AGENTS["5ht3"]["drugs"],
            "note": "单一药物预防 (5-HT3 拮抗剂首选)",
        })
    elif apfel_score >= 2 or is_high_emetic:
        plan.append({
            "step": 1,
            "agent_class": f"{ANTIEMETIC_AGENTS['5ht3']['class']} + {ANTIEMETIC_AGENTS['dexamethasone']['class']}",
            "drugs": [
                ANTIEMETIC_AGENTS["5ht3"]["drugs"][0],
                ANTIEMETIC_AGENTS["dexamethasone"]["drugs"][0],
            ],
            "note": "二联方案：5-HT3 拮抗剂 + 地塞米松 (高证据等级)",
        })

        if apfel_score >= 3:
            plan.append({
                "step": 2,
                "agent_class": ANTIEMETIC_AGENTS["dopamine_antagonist"]["class"],
                "drugs": [ANTIEMETIC_AGENTS["dopamine_antagonist"]["drugs"][0]],
                "note": "高危患者加用 D2 受体拮抗剂 (三联方案)",
            })

        if apfel_score >= 4:
            plan.append({
                "step": 3,
                "agent_class": (
                    f"{ANTIEMETIC_AGENTS['nk1']['class']} 或 "
                    f"{ANTIEMETIC_AGENTS['anticholinergic']['class']}"
                ),
                "drugs": [
                    ANTIEMETIC_AGENTS["nk1"]["drugs"][0],
                    ANTIEMETIC_AGENTS["anticholinergic"]["drugs"][0],
                ],
                "note": "极高危患者考虑四联方案：加用 NK-1 拮抗剂或东莨菪碱贴片",
            })

    non_pharm: list[str] = []
    if apfel_score >= 2:
        non_pharm.append("优先区域麻醉 (避免全麻)，减少挥发性麻醉药使用")
        non_pharm.append("充分补液 (晶体液 15-20ml/kg)")
        non_pharm.append("使用丙泊酚 TIVA (全凭静脉麻醉) 替代吸入麻醉")
        non_pharm.append("术中避免低血压和低血容量")
    if apfel_score >= 1:
        non_pharm.append("尽量减少围术期阿片类药物使用 (多模式镇痛)")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "apfel_score": apfel_score,
        "prophylaxis_plan": plan,
        "non_pharmacologic": non_pharm,
        "surgery_type": surgery_type,
        "high_emetic_surgery": is_high_emetic,
        "guideline_refs": [
            "SAMBA Guidelines: Gan TJ et al, Anesth Analg 2020;131:411-448",
            "Fourth Consensus Guidelines: Anesth Analg 2020",
            "Apfel CC et al, N Engl J Med 2004;350:2441-2451",
        ],
    }


def rescue(
    patient_id: str = "",
    current_regimen: list[str] | None = None,
    severity: str = "moderate",
    **kwargs: Any,
) -> dict[str, Any]:
    """突破性 PONV 抢救方案.

    Rescue principles:
      - Use antiemetic from a different class than prophylaxis
      - If 6h elapsed since initial dose, repeat may be effective
      - Severe/refractory: consider propofol bolus (sub-anesthetic dose)

    Reference: SAMBA Guidelines (2020); Apfel CC et al, Anesth Analg 2012
    """
    current_regimen = [c.lower() for c in (current_regimen or [])]

    rescue_plan: list[dict[str, Any]] = []
    used_classes: set[str] = set()

    for drug in current_regimen:
        if any(k in drug for k in [
            "昂丹司琼", "格拉司琼", "帕洛诺司琼",
            "ondansetron", "granisetron", "palonosetron",
        ]):
            used_classes.add("5-HT3")
        if any(k in drug for k in ["地塞米松", "dexamethasone"]):
            used_classes.add("steroid")
        if any(k in drug for k in [
            "甲氧氯普胺", "氟哌利多", "metoclopramide", "droperidol",
        ]):
            used_classes.add("D2")
        if any(k in drug for k in ["东莨菪碱", "scopolamine"]):
            used_classes.add("anticholinergic")
        if any(k in drug for k in ["阿瑞匹坦", "aprepitant"]):
            used_classes.add("NK1")

    if "H1" not in used_classes:
        rescue_plan.append({
            "step": 1,
            "recommendation": "一线抢救：换用不同机制药物",
            "agent": RESCUE_AGENTS["promethazine"],
            "note": "选择与预防用药不同机制的药物 (首选 H1 受体拮抗剂)",
        })
    elif "5-HT3" not in used_classes:
        rescue_plan.append({
            "step": 1,
            "recommendation": "一线抢救：5-HT3 拮抗剂",
            "agent": RESCUE_AGENTS["ondansetron"],
            "note": "如预防未用 5-HT3，可用昂丹司琼 4mg IV",
        })
    else:
        rescue_plan.append({
            "step": 1,
            "recommendation": "换用剩余可选药物",
            "agent": RESCUE_AGENTS["dimenhydrinate"],
            "note": "H1 受体拮抗剂：茶苯海明 50mg IV",
        })

    if severity == "severe":
        rescue_plan.append({
            "step": 2,
            "recommendation": "重症 PONV：亚麻醉剂量丙泊酚",
            "agent": RESCUE_AGENTS["propofol"],
            "note": "丙泊酚 10-20mg IV 推注，强效止吐，起效快 (2-3min)",
        })
        rescue_plan.append({
            "step": 3,
            "recommendation": "顽固性 PONV：多模式抢救",
            "agent": RESCUE_AGENTS["haloperidol"],
            "note": "氟哌啶醇 0.5-1mg IV (黑框警告：QT间期延长，用药后心电监测)",
        })

    general: list[str] = [
        "确认无胃扩张/机械性肠梗阻 (触诊、听诊)",
        "补充氧气 (SpO2 维持 > 95%)",
        "纠正低血压/低血容量 (晶体液 250-500ml 快速输注)",
        "排除药物因素 (阿片类、挥发性麻醉药)",
        "如 6h 内未用，可重复同一类药一次 (首次剂量)",
    ]

    if severity == "severe":
        general.append("考虑留置胃管减压")
        general.append("监测电解质、血气分析 (排除代谢紊乱)")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "severity": severity,
        "current_regimen": current_regimen,
        "used_classes": list(used_classes),
        "rescue_plan": rescue_plan,
        "general_measures": general,
        "guideline_refs": [
            "SAMBA Guidelines: Gan TJ et al, Anesth Analg 2020;131:411-448",
            "中华医学会麻醉学分会 PONV 防治专家共识 (2020)",
            "Apfel CC et al, Anesth Analg 2012;114:1305-1315 (rescue RCT)",
        ],
    }


# ── v2.0 扩展: 术后监测 + 出院随访 ──


def postop_monitor(
    patient_id: str = "",
    hours_postop: float = 0,
    nausea_severity: str = "none",
    vomiting_episodes: int = 0,
    rescue_given: bool = False,
    **kwargs,
) -> dict[str, Any]:
    """术后24h/48h分层监测 — 基于T0基准的定时评估.

    T0 = 手术结束时间, T0+24h/48h 自动触发评估.
    """
    severity = "none"
    alert = ""

    if vomiting_episodes >= 3:
        severity = "high"
        alert = "🟠 持续呕吐≥3次 → 触发MDT会诊(麻醉+外科+药师)"
    elif vomiting_episodes >= 1 or nausea_severity in ("moderate", "severe"):
        severity = "medium"
        alert = "🟡 有PONV症状 → 启动补救治疗"
    elif nausea_severity == "mild":
        severity = "low"
    else:
        alert = "✅ 无PONV → 继续常规监测"

    if hours_postop < 24:
        next_check = f"T0+24h (约{24 - hours_postop:.0f}h后)"
    else:
        next_check = "T0+48h 最终评估"

    return {
        "status": "ok",
        "hours_postop": hours_postop,
        "severity": severity,
        "nausea": nausea_severity,
        "vomiting": vomiting_episodes,
        "rescue_given": rescue_given,
        "alert": alert,
        "next_check": next_check,
        "recommendations": [
            "PONV已发生 → 选择与预防用药不同机制的补救药物" if severity != "none" else "",
            "持续呕吐+脱水 → 补液+电解质纠正" if severity == "high" else "",
            "记录PONV事件用于质控报表" if severity != "none" else "",
        ],
    }


def discharge_followup(
    patient_id: str = "",
    day_postop: int = 0,
    has_nausea: bool = False,
    has_vomiting: bool = False,
    has_dizziness: bool = False,
    has_constipation: bool = False,
    **kwargs,
) -> dict[str, Any]:
    """出院随访 — D3/D7自动短信/小程序随访问卷."""
    if day_postop <= 0:
        return {"status": "error", "message": "需要指定术后天数(day_postop)"}

    symptoms = []
    if has_nausea:
        symptoms.append("恶心")
    if has_vomiting:
        symptoms.append("呕吐")
    if has_dizziness:
        symptoms.append("头晕")
    if has_constipation:
        symptoms.append("便秘 (阿片/5-HT3相关)")

    needs_contact = bool(symptoms)

    return {
        "status": "ok",
        "day_postop": day_postop,
        "symptoms": symptoms,
        "needs_clinician_contact": needs_contact,
        "message": f"术后D{day_postop}随访 — {'有症状需关注' if needs_contact else '恢复良好'}",
        "actions": [
            f"D{day_postop}自动推送随访问卷(短信/小程序)" if day_postop in (3, 7) else "",
            "持续呕吐 → 药师远程指导或建议返院" if has_vomiting else "",
            "记录止吐药不良反应(头晕/便秘)用于质控" if has_dizziness or has_constipation else "",
        ],
    }
