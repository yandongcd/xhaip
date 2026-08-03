"""VTE小南·静脉血栓栓塞症全周期管理 — Caprini/Wells 风险分层 + 抗凝方案 + 随访管理.

Guidelines: 中华医学会 DVT/PTE 指南, ESC/ESVS 2021, ACCP-10, 院内VTE防治临床路径
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="vte-management", department="血管外科")
_GUIDELINES = [
    "中华医学会《深静脉血栓形成的诊断和治疗指南》",
    "中华医学会《肺血栓栓塞症诊治与预防指南》",
    "ESC/ESVS 2021 静脉血栓栓塞症管理指南",
    "ACCP-10 抗栓治疗与血栓预防临床实践指南",
    "院内VTE防治临床路径",
]
_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def _get_patient(kwargs: dict, agent: KnowledgeAgent = _agent):
    return agent.get_patient_from_kwargs(kwargs)


# ── Caprini / Wells / Padua 风险评分 ──

def _caprini_risk(surgery_type: str = "", age: int = 0, bmi: float = 0.0,
                  has_cancer: bool = False, has_vte_history: bool = False,
                  bed_rest_days: int = 0, laparoscopic: bool = False) -> dict:
    """Caprini 外科 VTE 风险评估模型 (2005/2010修订)."""
    score = 0
    factors: list[str] = []
    # Each risk factor = 1 point
    _one_point = {
        "age_41_60": age >= 41 and age <= 60,
        "minor_surgery": surgery_type == "minor",
        "bmi_25": bmi > 25,
        "leg_swelling": False,
        "varicose_veins": False,
        "pregnancy": False,
        "ocp": False,
        "sepsis": False,
        "pneumonia": False,
        "abnormal_pft": False,
        "ami": False,
        "chf": False,
        "ibd": False,
        "bed_rest": False,
    }
    for k, v in _one_point.items():
        if v:
            score += 1
            factors.append(k)

    # Start with known high-value items
    score = 0
    factors = []

    if age >= 41 and age <= 60:
        score += 1
        factors.append("年龄41-60岁")
    if age >= 61 and age <= 74:
        score += 2
        factors.append("年龄61-74岁")
    if age >= 75:
        score += 3
        factors.append("年龄≥75岁")

    if bmi > 25:
        score += 1
        factors.append(f"BMI={bmi:.0f}")

    if surgery_type in ("major", "orthopedic", "abdominal", "pelvic"):
        score += 2
        factors.append(f"大手术({surgery_type})")

    if has_cancer:
        score += 2
        factors.append("活动性恶性肿瘤")

    if has_vte_history:
        score += 3
        factors.append("VTE病史")

    if bed_rest_days >= 3:
        score += 1
        factors.append("卧床≥3天")

    if laparoscopic and surgery_type == "abdominal":
        score += 1
        factors.append("腹腔镜手术")

    # Risk stratification
    if score <= 1:
        level = "极低危"
        level_en = "very_low"
        prophylaxis = ["早期下床活动", "无需药物预防"]
    elif score == 2:
        level = "低危"
        level_en = "low"
        prophylaxis = ["IPC 间歇充气加压装置", "或 GCS 弹力袜"]
    elif score <= 4:
        level = "中危"
        level_en = "moderate"
        prophylaxis = ["LMWH 低分子肝素", "或 IPC + GCS", "或 NOAC (利伐沙班/阿哌沙班)"]
    else:
        level = "高危"
        level_en = "high"
        prophylaxis = ["LMWH + IPC 联合预防", "或 NOAC", "延长预防至术后28-35天"]

    return {
        "model": "Caprini",
        "score": score,
        "risk_level": level,
        "risk_level_en": level_en,
        "factors": factors,
        "prophylaxis": prophylaxis,
    }


def _wells_score(dvt_symptoms: list | None = None, pe_symptoms: list | None = None,
                 heart_rate: int = 0, hemoptysis: bool = False,
                 has_cancer: bool = False, alternative_diagnosis: bool = True,
                 scenario: str = "dvt") -> dict:
    """Wells 临床概率评分 (DVT / PE)."""
    dvt_symptoms = dvt_symptoms or []
    pe_symptoms = pe_symptoms or []
    score = 0
    factors = []

    if scenario == "dvt":
        if "active_cancer" in dvt_symptoms or has_cancer:
            score += 1; factors.append("活动性肿瘤")
        if "paralysis" in dvt_symptoms:
            score += 1; factors.append("瘫痪/下肢石膏固定")
        if "bed_rest_3d" in dvt_symptoms:
            score += 1; factors.append("卧床≥3天/大手术4周内")
        if "tenderness" in dvt_symptoms:
            score += 1; factors.append("沿深静脉走行局部压痛")
        if "leg_swelling" in dvt_symptoms:
            score += 1; factors.append("全腿肿胀")
        if "calf_swelling_3cm" in dvt_symptoms:
            score += 1; factors.append("小腿肿胀>3cm")
        if "pitting_edema" in dvt_symptoms:
            score += 1; factors.append("凹陷性水肿")
        if "collateral_veins" in dvt_symptoms:
            score += 1; factors.append("浅表侧支静脉")
        if "previous_dvt" in dvt_symptoms:
            score += 1; factors.append("DVT病史")
        if alternative_diagnosis:
            score -= 2; factors.append("有其他诊断可能")

        if score <= 0:
            probability = "低临床概率 (3%)"
            action = "D-二聚体检测，若阴性可排除DVT"
        elif score <= 2:
            probability = "中临床概率 (17%)"
            action = "D-二聚体检测 + 必要时超声"
        else:
            probability = "高临床概率 (75%)"
            action = "直接行下肢静脉超声检查"
    else:
        # Wells PE score
        if "clinical_dvt" in pe_symptoms:
            score += 3; factors.append("DVT临床症状")
        if heart_rate > 100:
            score += 1.5; factors.append(f"心率>100次/分({heart_rate})")
        if "immobilization" in pe_symptoms:
            score += 1.5; factors.append("制动/手术4周内")
        if "previous_pe_dvt" in pe_symptoms:
            score += 1.5; factors.append("PE/DVT病史")
        if hemoptysis:
            score += 1; factors.append("咯血")
        if has_cancer:
            score += 1; factors.append("活动性肿瘤")
        if not alternative_diagnosis:
            score += 3; factors.append("无其他合理诊断")

        if score <= 4:
            probability = "低临床概率"
            action = "D-二聚体检测，若阴性可排除PE"
        else:
            probability = "高临床概率"
            action = "直接行CTPA检查"

    return {
        "model": f"Wells ({scenario.upper()})",
        "score": score,
        "probability": probability,
        "recommended_action": action,
        "factors": factors,
    }


# ── Handler Functions ──

def assess_risk(patient_id: str = "", scenario: str = "surgery",
                symptoms: list | None = None, **kwargs: Any) -> dict:
    """VTE风险分层评估."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    age = int(p.get("age", 50) or 50)
    bmi = float(p.get("bmi", 24) or 24)
    dx = p.get("diagnosis", "")
    surgery_type = kwargs.get("surgery_type", "")
    labs = p.get("lab_results", {})
    ddimer = float(labs.get("D-dimer", 0.5) or 0.5)
    has_cancer = "癌" in dx or "肿瘤" in dx or "malignant" in dx.lower()
    has_vte = "血栓" in dx or "栓塞" in dx or "VTE" in dx.upper()

    if scenario in ("surgery", "caprini", "外科"):
        risk = _caprini_risk(
            surgery_type=surgery_type,
            age=age, bmi=bmi,
            has_cancer=has_cancer,
            has_vte_history=has_vte,
        )
    elif scenario in ("medical", "wells", "内科"):
        risk = _wells_score(
            dvt_symptoms=symptoms or [],
            has_cancer=has_cancer,
            scenario="dvt",
        )
    else:
        risk = _wells_score(
            dvt_symptoms=symptoms or [],
            has_cancer=has_cancer,
            scenario="dvt",
        )

    guides = _agent.search_guidelines("VTE") or _GUIDELINES
    rules = _agent.search_rules("血栓|抗凝")

    return _agent.clinical_result(
        summary=f"VTE风险分层 — {risk.get('risk_level', risk.get('probability', 'N/A'))}",
        patient=p, stage="S1",
        findings=[
            f"D-二聚体: {ddimer} mg/L {'(升高)' if ddimer > 0.5 else '(正常)'}",
            f"风险模型: {risk.get('model', 'N/A')} 评分={risk.get('score', 'N/A')}",
            *risk.get("factors", []),
        ],
        recommendations=risk.get("prophylaxis", [risk.get("recommended_action", "")]),
        guidelines=guides, rules=rules,
        guideline_refs=_GUIDELINES,
    )


def anticoagulation(patient_id: str = "", drug: str = "", inr: float = 0.0,
                    creatinine: float = 0.0, weight_kg: float = 0.0,
                    **kwargs: Any) -> dict:
    """抗凝方案决策引擎."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    age = int(p.get("age", 50) or 50)
    crcl = _calc_crcl(creatinine, age, weight_kg, p.get("gender", "M"))

    if not drug:
        drug = kwargs.get("drug_name", "warfarin")

    result = _anticoagulation_plan(drug, inr, crcl, age, weight_kg)

    guides = _agent.search_guidelines("抗凝") or _GUIDELINES
    rules = _agent.search_rules("抗凝|INR")

    return _agent.clinical_result(
        summary=f"抗凝方案 — {drug} | {result.get('note', '')}",
        patient=p, stage="S3",
        findings=[
            f"INR: {inr} {'(目标2.0-3.0)' if drug == 'warfarin' else ''}",
            f"CrCl: {crcl} mL/min",
            f"方案: {result.get('regimen', 'N/A')}",
        ],
        recommendations=[result.get("note", ""),
                        f"监测: {result.get('monitoring', '')}"],
        guidelines=guides, rules=rules,
        guideline_refs=_GUIDELINES,
    )


def _calc_crcl(creatinine: float, age: int, weight: float, gender: str) -> float:
    """Cockcroft-Gault CrCl estimation."""
    if creatinine <= 0:
        creatinine = 1.0
    if weight <= 0:
        weight = 70.0
    crcl = ((140 - age) * weight) / (72 * creatinine)
    if gender.upper() == "F":
        crcl *= 0.85
    return round(crcl, 1)


def _anticoagulation_plan(drug: str, inr: float, crcl: float, age: int, weight: float) -> dict:
    """抗凝方案推荐引擎."""
    drug_lower = drug.lower()

    if drug_lower in ("warfarin", "华法林"):
        if inr < 1.5:
            adjustment = "增加华法林剂量(建议增加10-20%), 可考虑低分子肝素桥接"
            monitoring = "3-7天后复查INR"
        elif inr < 2.0:
            adjustment = "轻微增加剂量(建议增加5-10%)"
            monitoring = "1周后复查INR"
        elif inr <= 3.0:
            adjustment = "INR在目标范围, 维持当前剂量"
            monitoring = "2-4周后复查INR"
        elif inr <= 4.0:
            adjustment = "INR偏高, 建议减量或暂停1次, 次日复查INR"
            monitoring = "次日复查INR"
        else:
            adjustment = "INR>4.0 高危! 暂停华法林, 口服维生素K 1-2.5mg, 每日复查INR"
            monitoring = "每日复查INR直至<3.0"
        return {
            "drug": "Warfarin",
            "inr_target": "2.0-3.0",
            "adjustment": adjustment,
            "monitoring": monitoring,
            "note": f"华法林 {'维持' if 2.0 <= inr <= 3.0 else '调整'}方案 | CrCl={crcl}",
            "regimen": f"华法林 {'维持' if 2.0 <= inr <= 3.0 else '调整'}方案",
        }

    elif drug_lower in ("rivaroxaban", "利伐沙班"):
        if crcl < 15:
            return {"drug": "Rivaroxaban", "warning": "CrCl<15 避免使用利伐沙班",
                    "monitoring": "建议改用华法林或阿哌沙班",
                    "note": "CrCl<15 禁忌", "regimen": "禁忌"}
        elif crcl < 50:
            dose = "15mg qd"
            note = "CrCl 15-50: 减量至15mg qd"
        else:
            dose = "20mg qd (急性期前21天: 15mg bid)"
            note = "肾功能正常标准剂量"
        return {"drug": "Rivaroxaban", "dose": dose, "note": note, "regimen": dose,
                "monitoring": "每3-6个月评估肾功能"}

    elif drug_lower in ("dabigatran", "达比加群"):
        if crcl < 30:
            return {"drug": "Dabigatran", "warning": "CrCl<30 禁用达比加群",
                    "monitoring": "建议改用华法林",
                    "note": "CrCl<30 禁用", "regimen": "禁忌"}
        dose = "150mg bid (或110mg bid 年龄≥80/出血风险高)"
        return {"drug": "Dabigatran", "dose": dose, "note": "达比加群标准剂量 | 不可嚼碎",
                "regimen": dose, "monitoring": "每6-12个月评估肾功能"}

    elif drug_lower in ("enoxaparin", "低分子肝素", "lmwh"):
        if crcl < 30:
            dose = f"{weight * 1:.0f}mg qd (治疗剂量减至 qd)"
        else:
            dose = f"{weight * 1:.0f}mg q12h (或 {weight * 1.5:.0f}mg qd)"
        return {"drug": "Enoxaparin (LMWH)", "dose": dose,
                "note": "LMWH 皮下注射 | 治疗≥5天 | 监测血小板q3d",
                "regimen": dose, "monitoring": "血小板计数 q3d (HIT风险)"}

    return {"drug": drug, "note": "未识别的抗凝药物, 请咨询临床药师",
            "regimen": "待确认", "monitoring": "待定"}


def monitor(patient_id: str = "", symptoms: list | None = None,
            leg_circumference_cm: float = 0.0, leg_circumference_prev: float = 0.0,
            chest_pain: bool = False, dyspnea: bool = False,
            bleeding: str = "", **kwargs: Any) -> dict:
    """症状监测与三色风险预警."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    symptoms = symptoms or []
    alerts = []
    risk = "low"
    actions = []

    leg_change = abs(leg_circumference_cm - leg_circumference_prev) if leg_circumference_prev > 0 else 0

    # HIGH risk triggers
    if chest_pain or dyspnea:
        risk = "high"
        alerts.append("胸痛/呼吸困难 — 需排除PE!")
        actions = ["立即联系血管外科住院总", "建议急诊CTPA", "创建预警工单"]
    elif "大出血" in str(symptoms) or "黑便" in bleeding or "血尿" in bleeding:
        risk = "high"
        alerts.append("活动性出血征象!")
        actions = ["暂停抗凝", "查血常规+凝血功能", "立即联系主管医生"]
    elif leg_change > 2.0:
        risk = "medium"
        alerts.append(f"腿围增加{leg_change:.1f}cm — 需警惕血栓进展")
        actions = ["抬高患肢", "24h内复查血管超声", "标记护士关注"]
    elif "腿肿" in str(symptoms) or "腿痛" in str(symptoms):
        risk = "medium"
        alerts.append("患者报告下肢症状 — 需评估血栓进展")
        actions = ["建议复查D-二聚体", "必要时血管超声"]
    else:
        risk = "low"
        actions = ["继续当前管理方案", "保持规律服药"]

    return _agent.clinical_result(
        summary=f"VTE症状监测 — {risk.upper()}风险",
        patient=p, stage="S5",
        findings=[
            f"风险等级: {risk.upper()}",
            f"腿围变化: {leg_change:.1f}cm (当前{leg_circumference_cm:.1f}cm)",
            f"胸痛: {'是' if chest_pain else '否'} | 呼吸困难: {'是' if dyspnea else '否'}",
            f"出血征象: {bleeding or '无'}",
        ],
        recommendations=actions,
        alerts=alerts,
        guideline_refs=_GUIDELINES,
    )


def followup(patient_id: str = "", discharge_date: str = "",
             drug: str = "warfarin", **kwargs: Any) -> dict:
    """出院后30天随访计划."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    plan = []
    if drug.lower() in ("warfarin", "华法林"):
        plan = [
            {"day": 3, "action": "INR复查", "note": "首次出院后INR监测，调整华法林剂量"},
            {"day": 7, "action": "INR复查 + 症状随访", "note": "评估INR是否达标(2.0-3.0)"},
            {"day": 14, "action": "INR复查 + 抗凝评估", "note": "INR稳定者进入每月监测"},
            {"day": 21, "action": "症状随访", "note": "评估用药依从性及不良反应"},
            {"day": 30, "action": "INR复查 + 综合评估", "note": "长期抗凝方案评估(3/6/12个月疗程)"},
        ]
    else:
        plan = [
            {"day": 3, "action": "症状随访 + 用药确认", "note": "确认规律服药，评估不良反应"},
            {"day": 7, "action": "症状随访", "note": "评估腿肿、疼痛改善"},
            {"day": 14, "action": "肾功能复查", "note": "NOAC需监测肾功能(CrCl)"},
            {"day": 21, "action": "症状随访", "note": "评估用药依从性"},
            {"day": 30, "action": "综合评估 + 抗凝疗程决策", "note": "决定继续/停药/转换抗凝方案"},
        ]

    return _agent.clinical_result(
        summary=f"VTE出院后30天随访计划 — {len(plan)}个节点",
        patient=p, stage="S6",
        findings=[f"抗凝药物: {drug}"] + [f"D{p['day']}: {p['action']} — {p['note']}" for p in plan],
        recommendations=[
            "登记VTE全周期管理队列",
            "设置自动用药提醒",
            "告知紧急情况联系方式",
        ],
        guideline_refs=_GUIDELINES,
    )


def reminder(patient_id: str = "", drug_name: str = "", **kwargs: Any) -> dict:
    """抗凝药物提醒."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    drug_lower = drug_name.lower()
    reminders = []
    if drug_lower in ("warfarin", "华法林"):
        reminders = [
            "每天固定时间服用(建议晚餐后)",
            "勿漏服: 如漏服≤8h可补服, >8h跳过次日正常",
            "定期监测INR: 初期每3-7天, 稳定后每2-4周",
            "避免大量摄入富含维生素K食物(菠菜/西兰花/动物肝脏)",
            "就医/手术前告知医生正在服用华法林",
        ]
    elif drug_lower in ("rivaroxaban", "利伐沙班"):
        reminders = [
            "与餐同服(提高生物利用度)",
            "每天固定时间服用",
            "勿擅自停药: VTE复发风险高",
            "如漏服≤12h可补服, >12h跳过下次正常",
        ]
    elif drug_lower in ("dabigatran", "达比加群"):
        reminders = [
            "整粒吞服不可嚼碎/打开胶囊",
            "每天固定时间服用(早晚各一次)",
            "如漏服≤6h可补服, >6h跳过",
        ]
    else:
        reminders = [
            "请遵医嘱规律服药",
            "勿擅自停药或调整剂量",
            "如有出血/黑便/血尿立即就医",
        ]

    return _agent.clinical_result(
        summary=f"VTE用药提醒 — {drug_name}",
        patient=p, stage="S6",
        findings=reminders[:3],
        recommendations=[
            "设置每日服药提醒(建议时间: 20:00)",
            "未确认服药: 间隔2h重复提醒, 连续3次未响应触发护士关注",
        ],
        alerts=[],
        guideline_refs=_GUIDELINES,
    )


def bridging(patient_id: str = "", surgery_date: str = "",
             drug: str = "warfarin", surgery_bleeding_risk: str = "standard",
             **kwargs: Any) -> dict:
    """围术期抗凝桥接方案."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    drug_lower = drug.lower()

    if drug_lower in ("warfarin", "华法林"):
        stop_before = 5
        restart_after = "术后12-24h (确认止血后)"
        bridge = True
        plan = [
            f"术前{stop_before}天: 停用华法林",
            f"术前{stop_before-2}天: 开始LMWH治疗剂量桥接",
            "术前24h: 最后一次LMWH (半量)",
            f"术后: {restart_after} 恢复华法林 + LMWH桥接",
            "INR达标(≥2.0 连续2天)后停用LMWH",
        ]
    else:
        # NOACs
        if surgery_bleeding_risk == "high":
            stop_before = 3
        else:
            stop_before = 1 if drug_lower in ("rivaroxaban", "利伐沙班", "apixaban", "阿哌沙班") else 2
        restart_after = "术后6-8h (低出血风险) 或 术后48-72h (高出血风险)"
        plan = [
            f"术前{stop_before}天: 停用{drug}",
            "无需LMWH桥接 (NOAC半衰期短)",
            f"术后: {restart_after} 恢复{drug}",
        ]

    return _agent.clinical_result(
        summary=f"围术期抗凝桥接方案 — {drug}",
        patient=p, stage="S4",
        findings=plan,
        recommendations=[
            "术前评估: CrCl + 凝血功能 + 血小板",
            "术后监测: 出血征象 + 伤口引流 + INR (华法林)",
            "高危患者: 术后24h内开始VTE物理预防(IPC)",
        ],
        guideline_refs=_GUIDELINES,
    )
