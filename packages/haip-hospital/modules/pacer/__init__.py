"""PACER v2.0 — 腹部手术并发症智能识别: Clavien-Dindo I-V + 器官特异性评分 + ACS-NSQIP风险.

Guidelines: Clavien-Dindo 2009, ACS-NSQIP, ISGPS/ISGLS, NICE CG74
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="pacer", department="普通外科")
_GUIDELINES = [
    "Clavien-Dindo 手术并发症分级 (2009修订)",
    "中国胃肠肿瘤外科术后并发症诊断登记规范 (2018)",
    "胰腺术后外科常见并发症防治指南 — ISGPF/ISGPS (2022)",
    "ACS-NSQIP 手术风险计算器 (2023)",
    "NICE CG74 手术部位感染预防 (2020)",
]
_agent.rule_engine.load_all()


def _pick(labs: dict | None, *keys: str):
    """取首个存在的检验值 — 大小写/连字符-下划线容错."""
    if not labs:
        return None
    for k in keys:
        if k in labs:
            return labs[k]
    norm: dict = {}
    for k, v in labs.items():
        norm[str(k).lower().replace("-", "_")] = v
    for k in keys:
        nk = str(k).lower().replace("-", "_")
        if nk in norm:
            return norm[nk]
    return None


_CLAVIEN_DINDO = {
    "I": "偏离正常恢复, 无需药物/手术/内镜/介入干预 (允许: 止吐/退热/止痛/利尿/电解质/理疗, 床旁切口敞开)",
    "II": "需药物治疗: 输血/TPN/抗生素/抗凝(不包括Grade I允许的药物)",
    "IIIa": "需有创干预(不需全麻): 局麻下引流/穿刺/内镜止血",
    "IIIb": "需有创干预(需全麻): 再次手术探查/全麻下止血/吻合口重建",
    "IVa": "危及生命的并发症需ICU管理 — 单器官功能障碍(呼吸/循环/肾 单一器官衰竭需ICU)",
    "IVb": "危及生命的并发症需ICU管理 — 多器官功能障碍(MODS)",
    "V": "患者死亡",
}

# Organ-specific complication criteria
_COMPLICATION_CRITERIA = {
    "anastomotic_leak": {
        "name": "吻合口漏", "grades": ["II", "IIIb"],
        "criteria": [
            "引流液淀粉酶/胆红素升高 >3x血清值",
            "CT: 吻合口周围液体积聚/游离气体",
            "口服亚甲蓝>引流液染色",
            "腹痛+发热+WBC↑+引流液性状改变(粪性/肠液性)",
        ],
        "management": {
            "II": "禁食+TPN+广谱抗生素+引流管冲洗+生长抑素",
            "IIIb": "急诊手术: 腹腔冲洗+引流+吻合口修补±近端造口",
        },
    },
    "pancreatic_fistula": {
        "name": "胰瘘 (ISGPF)", "grades": ["I", "II", "IIIb"],
        "criteria": [
            "引流液淀粉酶 >3x血清淀粉酶上限 POD≥3",
            "分级: BL(生化漏) — 无临床影响, B级 — 需要治疗干预, C级 — 需再次手术/器官衰竭/死亡",
        ],
        "management": {
            "II": "禁食+TPN+生长抑素(奥曲肽)+引流管持续+抗生素",
            "IIIb": "再次手术: 腹腔引流+胰肠吻合加固±残胰切除",
        },
    },
    "surgical_site_infection": {
        "name": "手术部位感染 (SSI)", "grades": ["I", "II", "IIIa"],
        "criteria": [
            "切口红肿/疼痛/渗液/脓液 (POD 3-14)",
            "浅部SSI: 仅皮肤/皮下组织", "深部SSI: 筋膜/肌层受累",
            "器官/腔隙SSI: 腹腔内脓肿",
        ],
        "management": {
            "I": "切口敞开引流+换药+理疗", "II": "抗生素+切口引流",
            "IIIa": "CT引导下穿刺引流(腹腔脓肿)",
        },
    },
    "postoperative_ileus": {
        "name": "术后肠梗阻 (POI)", "grades": ["I", "II"],
        "criteria": [
            "腹胀+恶心呕吐+>3天无排气排便",
            "腹部平片: 肠管扩张+气液平", "鼻胃管引流>500mL/24h",
        ],
        "management": {
            "I": "禁食+胃肠减压+维持水电解质平衡+早期下床活动",
            "II": "TPN+促动力药(甲氧氯普胺/红霉素)+纠正电解质",
        },
    },
    "postoperative_hemorrhage": {
        "name": "术后出血", "grades": ["II", "IIIb", "IVa"],
        "criteria": [
            "引流量突然增多(>200mL/h 鲜红)", "Hb下降>2g/dL/24h", "血流动力学不稳定(SBP<90/HR>110)",
        ],
        "management": {
            "II": "输血+纠正凝血异常(FFP/凝血酶原复合物)+停抗凝",
            "IIIb": "急诊手术探查止血", "IVa": "ICU+大量输血方案(MTP)+血管活性药物",
        },
    },
    "dvt_pe": {
        "name": "深静脉血栓/肺栓塞 (DVT/PE)", "grades": ["II", "IVa", "V"],
        "criteria": [
            "下肢不对称肿胀+小腿疼痛 (DVT)", "突发胸痛+呼吸困难+咯血+SpO2↓ (PE)",
            "D-二聚体升高+超声/CTA确诊",
        ],
        "management": {
            "II": "抗凝治疗 (LMWH→NOAC/华法林)",
            "IVa": "大面积PE→溶栓(rt-PA)或导管取栓+ICU",
        },
    },
    "respiratory_complication": {
        "name": "呼吸系统并发症", "grades": ["I", "II", "IVa"],
        "criteria": [
            "肺炎: 发热+咳嗽+痰+胸片浸润 (POD 2-7)", "肺不张: 呼吸音↓+X线膨胀不全",
            "呼吸衰竭: SpO2<90%+PaO2<60 (需机械通气)",
        ],
        "management": {
            "I": "深呼吸+诱发性肺量计+早期活动+体位引流",
            "II": "抗生素(肺炎)+雾化吸入+胸部理疗",
            "IVa": "ICU+机械通气(无创/有创)",
        },
    },
    "cardiac_complication": {
        "name": "心血管系统并发症", "grades": ["II", "IVa"],
        "criteria": [
            "心律失常(AF常见): 新发房颤/心动过速 POD 2-5",
            "心肌损伤: 肌钙蛋白升高(>0.04 ng/mL) ± ECG改变",
            "心衰: 肺水肿/下肢水肿+BNP升高",
        ],
        "management": {
            "II": "β-阻滞剂/胺碘酮+控制液体入量+纠正电解质",
            "IVa": "ICU+血管活性药+机械通气",
        },
    },
    "acute_kidney_injury": {
        "name": "急性肾损伤 (AKI)", "grades": ["I", "II", "IVa"],
        "criteria": [
            "SCr升高>26.5 μmol/L (48h内) 或 ≥1.5x基线", "尿量<0.5 mL/kg/h >6h",
            "KDIGO 1 → 2 → 3 进展",
        ],
        "management": {
            "I": "停肾毒性药物+优化容量(补液/利尿)+纠正电解质",
            "II": "液体管理+利尿剂+ICU会诊", "IVa": "RRT(血液透析/CRRT)",
        },
    },
}


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ Handler Functions ═══════


def complication_scan(patient_id: str = "", postop_day: int = 1,
                      vital_signs: dict | None = None,
                      drainage_ml: float = 0.0, drainage_color: str = "",
                      **kwargs: Any) -> dict:
    """术后全面并发症扫描 — 10器官系统 x Clavien-Dindo I-V."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    vital_signs = vital_signs or {}
    labs = p.get("lab_results", {}) or {}
    wbc = float(labs.get("wbc", 7) or 7)
    crp = float(labs.get("crp", 20) or 20)
    hb = float(labs.get("hb", 120) or 120)
    cr = float(labs.get("creatinine", 80) or 80)
    amylase = float(_pick(labs, "amylase", "Amylase") or 50)
    troponin = float(_pick(labs, "troponin", "Troponin", "cTnI", "hsTnI") or 0.01)
    albumin = float(labs.get("albumin", 35) or 35)
    plt = float(labs.get("platelet", 200) or 200)
    inr = float(labs.get("INR", 1.0) or 1.0)
    temp = float(vital_signs.get("temperature", 37.0) or 37.0)
    hr = int(vital_signs.get("heart_rate", 80) or 80)
    sbp = int(vital_signs.get("sbp", 120) or 120)
    rr = int(vital_signs.get("respiratory_rate", 16) or 16)
    spo2 = int(vital_signs.get("spo2", 98) or 98)

    findings: list[dict] = []
    overall_grade = "I"
    alerts: list[str] = []

    # 1. Anastomotic leak / Pancreatic fistula
    if crp > 150 and wbc > 12 and postop_day >= 3:
        if amylase > 200:
            findings.append({
                "complication": _COMPLICATION_CRITERIA["pancreatic_fistula"],
                "grade": "II",
                "evidence": [f"血清淀粉酶={amylase} (>3xULN对照; 引流液标准)", f"CRP={crp} (>150)", f"WBC={wbc} (>12)"],
            })
            overall_grade = max_grade(overall_grade, "II")
        else:
            findings.append({
                "complication": _COMPLICATION_CRITERIA["anastomotic_leak"],
                "grade": "II",
                "evidence": [f"CRP={crp} (>150 POD≥3 — 漏高危)", f"WBC={wbc} (>12)", f"POD={postop_day} (典型时间窗 3-7天)"],
            })
            alerts.append("吻合口漏高危 — 建议急诊腹部CT(口服造影剂) + 引流液淀粉酶/胆红素测定")
            overall_grade = max_grade(overall_grade, "II")

    # 2. SSI
    if temp > 38 and wbc > 12 and postop_day >= 3 and postop_day <= 14:
        findings.append({
            "complication": _COMPLICATION_CRITERIA["surgical_site_infection"],
            "grade": "II",
            "evidence": [f"体温={temp}C (>38)", f"WBC={wbc} (>12)", f"POD={postop_day}"],
        })
        alerts.append("手术部位感染 — 检查切口(红肿/渗液/波动感)")
        overall_grade = max_grade(overall_grade, "II")

    # 3. Hemorrhage — 血流动力学不稳定 (SBP<90+HR>110) 独立触发, 不依赖 Hb 数据
    hemodynamically_unstable = sbp < 90 and hr > 110
    if hb < 80 or (hb < 100 and sbp < 90) or hemodynamically_unstable:
        grade = "II" if hb >= 80 or sbp >= 90 else "IIIb"
        if hemodynamically_unstable:
            grade = "IVa"
            alerts.append("术后出血+血流动力学不稳定 — 立即启动MTP!")
        findings.append({
            "complication": _COMPLICATION_CRITERIA["postoperative_hemorrhage"],
            "grade": grade,
            "evidence": [f"Hb={hb} (<80)", f"SBP={sbp}/{hr}", f"引流{drainage_ml}mL {'鲜红' if '红' in drainage_color or 'blood' in drainage_color.lower() else '—'}"],
        })
        overall_grade = max_grade(overall_grade, grade)

    # 4. AKI
    if cr > 180:
        findings.append({
            "complication": _COMPLICATION_CRITERIA["acute_kidney_injury"],
            "grade": "II" if cr < 354 else "IVa",
            "evidence": [f"Cr={cr} (>180)", "尿量? (需<0.5mL/kg/h → AKI)"],
        })
        overall_grade = max_grade(overall_grade, "II")

    # 5. Respiratory
    if spo2 < 92 or rr > 25:
        findings.append({
            "complication": _COMPLICATION_CRITERIA["respiratory_complication"],
            "grade": "IVa" if spo2 < 90 else "I",
            "evidence": [f"SpO2={spo2}% (<92)", f"RR={rr} (>25)"],
        })
        alerts.append(f"SpO2={spo2}% — {'需ICU+机械通气' if spo2 < 90 else '加强呼吸锻炼+胸部理疗'}")

    # 6. Cardiac
    if troponin > 0.04 or hr > 130:
        findings.append({
            "complication": _COMPLICATION_CRITERIA["cardiac_complication"],
            "grade": "IVa" if troponin > 0.4 else "II",
            "evidence": [f"cTnI={troponin} ng/mL" if troponin > 0.04 else f"HR={hr} (>130)"],
        })

    # 7. Ileus
    if postop_day >= 3 and not kwargs.get("flatus_passed", True):
        findings.append({
            "complication": _COMPLICATION_CRITERIA["postoperative_ileus"],
            "grade": "I",
            "evidence": [f"POD{postop_day} — 未排气/排便"],
        })

    # 8. Nutritional
    if albumin < 25 and postop_day >= 5:
        findings.append({
            "complication": {"name": "严重低蛋白血症/营养不良"},
            "grade": "II",
            "evidence": [f"Alb={albumin} (<25)", f"POD={postop_day} — 营养状态恶化"],
        })
        alerts.append("Alb<25 — 需TPN/EN营养支持")

    # 9. Coagulopathy
    if inr > 1.5 and plt < 100:
        findings.append({
            "complication": {"name": "凝血功能障碍/DIC待排除"},
            "grade": "II",
            "evidence": [f"INR={inr} (>1.5)", f"PLT={plt} (<100)"],
        })

    # Normal course
    if not findings:
        findings.append({"complication": {"name": "术后恢复顺利"}, "grade": "I",
                         "evidence": ["生命体征平稳", "检验指标正常", f"POD={postop_day} — 按计划恢复"]})

    # Determine final grade
    grade_counts = {}
    for f in findings:
        g = f.get("grade", "I")
        grade_counts[g] = grade_counts.get(g, 0) + 1
    overall_grade = max(grade_counts.keys(), key=lambda g: _grade_order(g))

    return {
        "status": "ok",
        "patient_id": patient_id, "postop_day": postop_day,
        "overall_grade": overall_grade,
        "grade_description": _CLAVIEN_DINDO.get(overall_grade, ""),
        "findings": [{"name": f["complication"]["name"], "grade": f["grade"],
                      "evidence": f["evidence"]} for f in findings],
        "alerts": alerts, "total_complications": len(findings),
        "summary": f"POD{postop_day} — Clavien-Dindo Grade {overall_grade} | {len(findings)}项发现",
    }


def _grade_order(grade: str) -> int:
    """Clavien-Dindo ordering: I < II < IIIa < IIIb < IVa < IVb < V."""
    order = {"I": 1, "II": 2, "IIIa": 3, "IIIb": 4, "IVa": 5, "IVb": 6, "V": 7}
    return order.get(grade, 0)


def max_grade(a: str, b: str) -> str:
    return a if _grade_order(a) >= _grade_order(b) else b


def risk_predict(patient_id: str = "", surgery_type: str = "",
                 surgery_duration: float = 120.0, blood_loss: float = 200.0,
                 asa_class: int = 2, age: int = 50,
                 emergency: bool = False, contaminated: str = "clean",
                 albumin_preop: float = 35.0, diabetes: bool = False,
                 smoking: bool = False, copd: bool = False,
                 **kwargs: Any) -> dict:
    """术后并发症风险预测 — ACS-NSQIP因素 + 手术因素."""
    p, err = _get_patient({"patient_id": patient_id})

    score = 0
    factors: list[str] = []

    # ASA
    if asa_class >= 4:
        score += 4; factors.append(f"ASA {asa_class} — 严重系统性疾病")
    elif asa_class >= 3:
        score += 2; factors.append(f"ASA {asa_class} — 中度系统性疾病")
    elif asa_class >= 2:
        score += 1

    # Age
    if age >= 80:
        score += 3; factors.append("年龄≥80岁")
    elif age >= 65:
        score += 1; factors.append("年龄≥65岁")

    # Emergency surgery
    if emergency:
        score += 3; factors.append("急诊手术 — 并发症风险显著增高")

    # Surgery duration
    if surgery_duration > 240:
        score += 3; factors.append(f"手术时长>4h ({surgery_duration}min)")
    elif surgery_duration > 180:
        score += 2; factors.append(f"手术时长>3h ({surgery_duration}min)")

    # Blood loss
    if blood_loss > 1000:
        score += 4; factors.append(f"大出血>1000mL ({blood_loss}mL)")
    elif blood_loss > 500:
        score += 2; factors.append(f"出血>500mL ({blood_loss}mL)")

    # Contamination
    if contaminated in ("contaminated", "dirty", "污染", "感染"):
        score += 3; factors.append(f"{contaminated}手术 — SSI风险5-10x")

    # Albumin (nutritional)
    if albumin_preop < 30:
        score += 2; factors.append(f"Alb<30 ({albumin_preop}) — 营养不良")
    elif albumin_preop < 35:
        score += 1; factors.append(f"Alb<35 ({albumin_preop}) — 营养边缘")

    # Comorbidities
    if diabetes:
        score += 1; factors.append("糖尿病")
    if smoking:
        score += 1; factors.append("吸烟史")
    if copd:
        score += 2; factors.append("COPD")

    # Risk tier
    if score >= 10:
        risk = "极高危"
        morbitity_risk = "并发症风险>50%, 死亡率>5%"
        prophylaxis = ["术前优化(营养支持2-4周)", "MDT讨论手术方案", "ICU术后预留", "预防性抗生素+LMWH+DVT预防", "术前肺康复(若COPD)"]
    elif score >= 7:
        risk = "高危"
        morbitity_risk = "并发症风险30-50%, 死亡率2-5%"
        prophylaxis = ["术前营养优化", "预防性抗生素+LMWH", "术后ICU监测 24-48h"]
    elif score >= 4:
        risk = "中危"
        morbitity_risk = "并发症风险10-30%"
        prophylaxis = ["标准预防: 抗生素+LMWH+早期活动"]
    else:
        risk = "低危"
        morbitity_risk = "并发症风险<10%"
        prophylaxis = ["常规预防+ERAS方案"]

    return {
        "status": "ok",
        "patient_id": patient_id,
        "risk_level": risk, "risk_score": score,
        "morbidity_estimate": morbitity_risk,
        "factors": factors,
        "prophylaxis": prophylaxis,
        "summary": f"术后并发症风险 — {risk} (评分{score}) | {morbitity_risk}",
    }


def escalation(patient_id: str = "", complication_grade: str = "I",
               complication_type: str = "", **kwargs: Any) -> dict:
    """并发症分级升级 + MDT触发 + 急诊手术决策."""
    p, err = _get_patient({"patient_id": patient_id})

    grade = complication_grade
    actions: list[str] = []
    needs_mdt = False
    needs_surgery = False
    needs_icu = False
    urgency = "routine"

    if grade in ("I", "II"):
        urgency = "routine"
        actions = ["常规处理: 按并发症类型针对治疗 + 密切临床观察(12-24h)", "记录并发症入病历+Clavien-Dindo分级登记"]

    elif grade == "IIIa":
        urgency = "urgent — 24h内"
        needs_mdt = True
        actions = [
            "无需全麻的介入: 局麻下穿刺引流/内镜止血/介入栓塞",
            "启动MDT讨论(外科+介入+ICU)",
            "取得患者/家属知情同意",
        ]

    elif grade == "IIIb":
        urgency = "emergent — 6h内"
        needs_surgery = True; needs_mdt = True
        actions = [
            "需全麻的再次手术/介入",
            "🔴 立即通知外科主治+手术室备台+麻醉科",
            "急诊手术方案: 剖腹探查±吻合口重建±造口±腹腔引流",
            "术前准备: 备血+凝血纠正+广谱抗生素+ICU沟通",
        ]

    elif grade in ("IVa", "IVb"):
        urgency = "emergent — 即刻"
        needs_surgery = True; needs_mdt = True; needs_icu = True
        actions = [
            "🔴 立即转入ICU!",
            "多学科紧急MDT(外科+ICU+麻醉+介入)",
            "器官支持: 机械通气/血管活性药/RRT",
            "生命体征稳定后急诊手术(若外科病因可逆)",
        ]

    elif grade == "V":
        urgency = "critical"
        actions = ["患者死亡 — 进行死亡病例讨论(M&M Conference)", "完成并发症登记+不良事件上报"]

    # Complication-specific management
    if complication_type:
        for key, info in _COMPLICATION_CRITERIA.items():
            if info["name"] in complication_type or key in complication_type.lower():
                mgmt = info.get("management", {})
                if grade in mgmt:
                    actions.append(f"{info['name']}特异处理: {mgmt[grade]}")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "grade": grade, "urgency": urgency,
        "needs_mdt": needs_mdt, "needs_emergency_surgery": needs_surgery, "needs_icu": needs_icu,
        "actions": actions,
        "summary": f"并发症升级 — Grade {grade} | {urgency} | {'急诊手术!' if needs_surgery else 'MDT' if needs_mdt else '常规'}",
    }
