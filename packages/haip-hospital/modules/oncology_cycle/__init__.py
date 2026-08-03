"""Oncology Cycle v1.0 — 肿瘤周期治疗管理与返院决策辅助 (A76).

一页摘要 + D3/7/10-11/14周期计划 + 骨髓抑制/感染/irAE风险筛查 + 三端输出
Guidelines: CSCO 2024, NCCN, ESMO, CTCAE v5, irAE管理共识
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="oncology-cycle", department="肿瘤科")
_GUIDELINES = [
    "中国临床肿瘤学会 CSCO 指南 (2024)",
    "NCCN 肿瘤临床实践指南",
    "ESMO 肿瘤管理指南",
    "CTCAE v5 不良事件通用术语标准",
    "免疫检查点抑制剂相关不良反应(irAE)管理共识",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ Patient Summary (一页式病情摘要) ═══════

def patient_summary(patient_id: str = "", **kwargs: Any) -> dict:
    """一页式病情摘要 — 诊断/分期/病理/分子检测/治疗线数/疗效评价."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    dx = p.get("diagnosis", "")
    stage = p.get("tumor_stage", "未知")
    path = p.get("pathology", "")
    molecular = p.get("molecular_markers", {})
    treatment_line = kwargs.get("treatment_line", 1)
    current_regimen = kwargs.get("current_regimen", [])
    response = kwargs.get("response_evaluation", "待评估")
    ecog = kwargs.get("ecog", 0)
    labs = p.get("lab_results", {}) or {}

    summary = {
        "diagnosis": dx, "stage": stage, "pathology": path,
        "molecular": molecular,
        "treatment_line": f"第{treatment_line}线治疗",
        "current_regimen": current_regimen,
        "last_response": response,
        "ecog": ecog,
        "key_labs": {
            "WBC": labs.get("wbc", "—"), "Hb": labs.get("hb", "—"), "PLT": labs.get("platelet", "—"),
            "ALT": labs.get("alt", "—"), "Cr": labs.get("creatinine", "—"),
            "CEA": labs.get("cea", "—"), "CRP": labs.get("crp", "—"),
        },
    }

    risk_points = []
    if ecog >= 2:
        risk_points.append("ECOG≥2 — 体能状态差")
    if labs.get("wbc", 4) < 2:
        risk_points.append("WBC<2 — 粒缺风险 (FN高危)")
    if labs.get("alt", 30) > 120:
        risk_points.append("ALT>3xULN — 肝毒性, 化疗需减量/延期")
    if "免疫" in str(current_regimen) or "immuno" in str(current_regimen).lower():
        risk_points.append("免疫治疗中 — 需监测irAE (皮肤/肠/肝/肺/内分泌)")


    return {
        "status": "ok", "patient_id": patient_id,
        "summary": summary,
        "risk_points": risk_points,
        "overview": f"{dx} {stage} | 第{treatment_line}线 {current_regimen[:3] if current_regimen else 'N/A'} | ECOG={ecog} | 疗效={response}",
        "summary_type": "医生端病情摘要",
    }


# ═══════ Cycle Plan (周期计划) ═══════

def cycle_plan(patient_id: str = "", treatment_date: str = "",
               regimen_type: str = "chemotherapy", cycle_number: int = 1,
               cycle_interval_days: int = 21, **kwargs: Any) -> dict:
    """治疗周期与返院计划 — D3-4/D7/D10-11/D14 节点自动生成."""
    p, err = _get_patient({"patient_id": patient_id})

    from datetime import datetime, timedelta, timezone
    try:
        t_date = datetime.strptime(treatment_date, "%Y-%m-%d")
    except ValueError:
        today = datetime.now(tz=timezone.utc)
        t_date = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        treatment_date = t_date.strftime("%Y-%m-%d")

    plan = {
        "treatment_date": treatment_date,
        "cycle_number": cycle_number,
        "regimen_type": regimen_type,
        "next_cycle_date": (t_date + timedelta(days=cycle_interval_days)).strftime("%Y-%m-%d"),
    }

    checks = []

    # D3-4: Nadir WBC
    d34 = t_date + timedelta(days=3)
    checks.append({"day": 3, "date": d34.strftime("%Y-%m-%d"),
                   "label": "D3-4 血常规",
                   "detail": "血常规+粒细胞计数 — 骨髓抑制监测(中性粒细胞最低点通常在化疗后7-10天)",
                   "action": "若G-CSF预防性使用, 于D5-10 qd; 若WBC<2.0或NEUT<1.0 → G-CSF治疗性启用"})

    # D7: Toxicity check
    d7 = t_date + timedelta(days=7)
    checks.append({"day": 7, "date": d7.strftime("%Y-%m-%d"),
                   "label": "D7 综合复查",
                   "detail": "血常规+肝肾功能+电解质 — 化疗毒性高峰评估",
                   "action": "若ALT>3xULN → 化疗减量25%; ALT>5xULN → 暂停化疗至恢复"})

    # D10-11: Recovery
    d10 = t_date + timedelta(days=10)
    checks.append({"day": 10, "date": d10.strftime("%Y-%m-%d"),
                   "label": "D10-11 恢复评估",
                   "detail": "血常规+症状评估(恶心/呕吐/腹泻/口腔黏膜炎/疲劳) — 评估是否恢复至基线",
                   "action": "确认WBC>3.0+PLT>100+症状改善 → 下周期可按时进行; 否则延期1周"})

    # D14: Tumor marker + pre-next-cycle
    d14 = t_date + timedelta(days=14)
    checks.append({"day": 14, "date": d14.strftime("%Y-%m-%d"),
                   "label": "D14 返院前准备",
                   "detail": "血常规+肝肾功能+肿瘤标志物+心电图(若含蒽环类/抗HER2)",
                   "action": "确认检查齐全 → 门诊预约 → 返院(D{cycle_interval_days}天)"})

    # Regimen-specific notes
    regimen_notes = []
    if "顺铂" in str(regimen_type) or "cisplatin" in regimen_type.lower():
        regimen_notes.append("顺铂方案: 水化(D1-3)+利尿+监测电解质(Mg/K) + 耳毒性/肾毒性评估")
    if "紫杉" in str(regimen_type) or "pacli" in regimen_type.lower():
        regimen_notes.append("紫杉类: 预防性抗过敏(地塞米松+Diphen+西咪替丁) + 周围神经毒性评估")
    if "免疫" in str(regimen_type) or "immuno" in regimen_type.lower():
        regimen_notes.append("免疫治疗: 无需常规G-CSF, 监测irAE(D14后任何时间均可出现)")
        plan["irAE_monitoring"] = "皮肤/腹泻/肝ALT/肺/甲功 每周期评估"

    plan["checks"] = checks
    plan["regimen_notes"] = regimen_notes

    return {
        "status": "ok", "patient_id": patient_id,
        "cycle_plan": plan,
        "next_steps": [
            f"D{cycle_interval_days}天 返院: {plan['next_cycle_date']}",
            "返院前1天确认: 血常规+肝肾功能+ECOG+知情同意",
            "若延期≥7天 → 重新评估治疗方案",
        ],
        "summary": f"周期计划 — C{cycle_number} | {treatment_date} → 下次{plan['next_cycle_date']} | {len(checks)}个复查节点",
    }


# ═══════ Risk Screening (检验风险) ═══════

def risk_screening(patient_id: str = "", treatment_type: str = "chemotherapy",
                   **kwargs: Any) -> dict:
    """治疗相关风险初筛 — 骨髓抑制/感染/肝肾/irAE/心脏."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    labs = p.get("lab_results", {}) or {}
    wbc = float(labs.get("wbc", 4) or 4)
    neut = float(labs.get("neutrophil", 2) or 2)
    plt = float(labs.get("platelet", 150) or 150)
    hb = float(labs.get("hb", 120) or 120)
    alt = float(labs.get("alt", 30) or 30)
    cr = float(labs.get("creatinine", 80) or 80)
    crp = float(labs.get("crp", 10) or 10)
    temp = float(kwargs.get("temperature", 37.0) or 37.0)
    symptoms = kwargs.get("symptoms", [])

    risks: list[dict] = []
    alerts: list[str] = []

    # 1. Myelosuppression
    if neut < 0.5:
        risks.append({"risk": "粒缺 4级 (NEUT<0.5)", "grade": "4", "severity": "high",
                      "action": "G-CSF立即启用, 预防性抗生素(左氧氟沙星), 隔离, 每日血常规",
                      "chemotherapy": "暂停化疗至NEUT≥1.5"})
        alerts.append("粒缺4级 — 发热+粒缺是肿瘤急症!")
    elif neut < 1.0:
        risks.append({"risk": "粒缺 3级", "grade": "3", "severity": "medium",
                      "action": "G-CSF, 加强监测(每48h), 下周期考虑G-CSF一级预防"})
    elif wbc < 3.0:
        risks.append({"risk": "白细胞降低", "grade": "1-2", "severity": "low",
                      "action": "观察, G-CSF按需"})

    if plt < 25:
        risks.append({"risk": "血小板减少 4级", "grade": "4", "severity": "high",
                      "action": "血小板输注, 暂停化疗, 排除DIC/HIT"})
        alerts.append("PLT<25 — 自发出血风险!")
    elif plt < 50:
        risks.append({"risk": "血小板减少 3级", "grade": "3", "severity": "medium",
                      "action": "暂停化疗至PLT≥75, 评估出血风险"})

    if hb < 80:
        risks.append({"risk": "贫血 2-3级", "grade": "2-3", "severity": "medium",
                      "action": "EPO ± 补铁, 必要时输注RBC"})

    # 2. Infection / Febrile Neutropenia
    if temp > 38.3 and neut < 1.0:
        risks.append({"risk": "粒缺伴发热 (FN)", "grade": "3-4", "severity": "high",
                      "action": "立即住院! 血培养×2套+PCT+广谱抗生素1h内(头孢吡肟/哌拉西林他唑巴坦/美罗培南), 加G-CSF"})
        alerts.append("FN肿瘤急症 — 立即住院+抗生素!")

    if crp > 100 and temp > 38:
        risks.append({"risk": "感染待排除", "grade": "2-3", "severity": "medium",
                      "action": "血培养+PCT+CRP追踪+胸部CT+必要时抗生素"})

    # 3. Hepatotoxicity
    if alt > 200:
        risks.append({"risk": "肝毒性 3-4级 (ALT>5xULN)", "grade": "3-4", "severity": "high",
                      "action": "立即停药! 查乙肝/丙肝/自身免疫性肝炎/肝转移, 请肝病科会诊",
                      "chemotherapy": "暂停所有化疗至ALT<3xULN"})
        alerts.append("ALT>5xULN — 立即停药+肝病科会诊!")
    elif alt > 120:
        risks.append({"risk": "肝毒性 2级", "grade": "2", "severity": "medium",
                      "action": "减量25%, 护肝(谷胱甘肽/甘草酸), 每周复查ALT"})

    # 4. Nephrotoxicity
    if cr > 180:
        risks.append({"risk": "急性肾损伤", "grade": "2-3", "severity": "medium",
                      "action": "水化+利尿, 停肾毒性药物(NSAIDs/顺铂/抗生素), 请肾内科会诊",
                      "chemotherapy": "暂停顺铂至Cr<150, 卡铂按Calvert公式减量"})

    # 5. irAE (immune-related)
    if "免疫" in treatment_type or "immuno" in treatment_type.lower():
        diarrhea = any(kw in str(symptoms).lower() for kw in ["腹泻", "diarrh", "稀便"])
        rash = any(kw in str(symptoms).lower() for kw in ["皮疹", "rash", "瘙痒"])
        dyspnea = any(kw in str(symptoms).lower() for kw in ["呼吸困难", "dyspnea", "气促", "咳嗽"])
        if diarrhea:
            risks.append({"risk": "irAE 肠炎 (G1-3)", "grade": "1-3", "severity": "medium",
                          "action": "G1: 洛哌丁胺+口服补液; G2: 泼尼松1mg/kg; G3: 住院+甲泼尼龙+GI会诊"})
        if rash:
            risks.append({"risk": "irAE 皮疹 (G1-2)", "grade": "1-2", "severity": "low",
                          "action": "局部激素+抗组胺, 若G3→口服泼尼松+皮肤科会诊"})
        if dyspnea:
            risks.append({"risk": "irAE 肺炎 (G1-3)", "grade": "1-3", "severity": "high",
                          "action": "HRCT+肺功能+泼尼松1-2mg/kg, G3→住院+甲泼尼龙+呼吸科会诊"})
            alerts.append("irAE肺炎高致死率 — 需HRCT+大剂量激素!")

    if not risks:
        risks.append({"risk": "无明显治疗相关风险", "grade": "—", "severity": "low",
                      "action": "按计划进行治疗"})

    return {
        "status": "ok", "patient_id": patient_id,
        "risks": risks, "alerts": alerts,
        "highest_severity": "high" if any(r["severity"] == "high" for r in risks) else (
            "medium" if any(r["severity"] == "medium" for r in risks) else "low"),
        "summary": f"风险初筛 — {len(risks)}项 | 最高级别={max((r['severity'] for r in risks), key=lambda s: {'high':3,'medium':2,'low':1}.get(s,0)) if risks else 'low'}",
    }


# ═══════ Tri-Endpoint Output (三端输出) ═══════

def tri_endpoint(patient_id: str = "", endpoint: str = "doctor",
                 **kwargs: Any) -> dict:
    """医生端/护士端/患者端 三端标准化输出."""
    p, err = _get_patient({"patient_id": patient_id})
    summary_data = kwargs.get("summary", {})
    cycle_data = kwargs.get("cycle_plan", {})
    risk_data = kwargs.get("risks", [])
    treatment_date = kwargs.get("treatment_date", "—")

    if endpoint == "doctor":
        output = {
            "title": "医生端 — 诊疗摘要与风险提示",
            "summary": summary_data.get("overview", ""),
            "key_risks": [r["risk"] for r in risk_data if r["severity"] in ("high", "medium")],
            "next_cycle": cycle_data.get("next_cycle_date", "—"),
            "recommendations": [
                "确认下周期治疗前检查齐全",
                "高风险项需主管医师签字确认",
                "MDT: 疗效评价PD → 重新讨论治疗方案",
            ],
            "disclaimer": "此为AI辅助摘要, 须经主管医师复核确认后纳入病历",
        }
    elif endpoint == "nurse":
        output = {
            "title": "护士端 — 随访清单与电话话术",
            "checklist": [
                f"患者{patient_id}: 下次返院D{cycle_data.get('cycle_interval_days', 21)}天前1天电话确认",
                "确认患者无发热/出血/严重不良反应",
                "提醒携带: 身份证+就诊卡+既往检查报告",
                "核对: 是否有临时用药变化(华法林/降糖药/降压药)",
                "若患者报告不良反应≥G2 → 立即通知主管医生",
            ],
            "phone_script": "您好, 我是南方医院肿瘤科护士。您上次治疗日期是..., 根据计划您需要在...前后返院复查。请问最近有没有发热、出血、严重恶心呕吐或呼吸困难? 记得返院前空腹抽血, 携带所有检查报告。有任何不适随时联系我们。",
            "followup_frequency": "根据风险和周期频率确定",
        }
    else:
        output = {
            "title": "患者端 — 返院提醒与居家注意事项",
            "return_date": cycle_data.get("next_cycle_date", "—"),
            "prepare": [
                "返院前2天: 空腹抽血(血常规+肝肾功能)",
                "返院当天: 携带本人身份证+就诊卡+所有外院检查报告",
                "返院前1天: 确认无发热(体温<37.5), 无腹泻/恶心严重, 无出血",
            ],
            "home_care": [
                "化疗后7-10天: 白细胞最低点 — 少去人多场所, 戴口罩, 勤洗手",
                "饮食: 高蛋白+高热量+易消化 — 少量多餐(每日5-6餐)",
                "口腔护理: 软毛牙刷+盐水漱口 — 若口腔溃疡疼痛 → 告知医生",
                "发热>38.3 → 立即电话联系主管医生/X护士 (夜间急诊!)",
                "每日记录: 体温(早/晚)、饮食量、排便情况、疼痛评分(0-10)",
            ],
            "danger_signs": [
                "发热>38.3 (粒缺伴发热 — 肿瘤急症!)",
                "持续腹泻>6次/天或血便",
                "呼吸困难/胸痛",
                "黑便/呕血/瘀斑(出血征象)",
            ],
            "disclaimer": "此为AI辅助生成的居家指导, 具体请遵医嘱。紧急情况立即拨打医院电话或到急诊就诊。",
        }

    return {
        "status": "ok", "patient_id": patient_id,
        "endpoint": endpoint, "output": output,
        "summary": f"三端输出 — {endpoint}端 | {output['title']}",
    }
