"""
非药物止吐干预推荐 (nondrug_guide)

基于 2025 版中国《术后恶心呕吐诊疗指南》§4 §5
涵盖：穴位刺激 / 耳穴刺激 / 术前碳水化合物 / 咀嚼口香糖 /
       音乐疗法 / 正向心理引导 / 头高位 / 生姜 / 芳香疗法
"""


def recommend_acupoint(
    risk_level: str = "", drug_contraindications: bool = False, **kwargs
) -> dict:
    """穴位刺激推荐 (TEAS/电针)"""
    if risk_level in ("medium", "high") or drug_contraindications:
        return {
            "acupoint_recommended": True,
            "method": "TEAS（经皮穴位电刺激）",
            "acupoints": ["合谷(LI4)", "内关(PC6)", "足三里(ST36)"],
            "mechanism": "调节神经递质（5-HT3/β-内啡肽），平衡自主神经系统",
            "evidence": "可显著降低全身麻醉术后PONV发生率和止吐药需求",
            "strength": "weak",
            "evidence_quality": "very_low",
            "guideline_ref": "R17.1",
            "status": "ok",
        }

    return {
        "acupoint_recommended": False,
        "message": "低风险且无用药顾虑者，穴位刺激非必需",
        "status": "ok",
    }


def recommend_auricular(
    risk_level: str = "", surgery_type: str = "", **kwargs
) -> dict:
    """耳穴刺激推荐"""
    recommended = risk_level in ("low", "medium", "high")

    result = {
        "auricular_recommended": recommended,
        "auricular_points": ["神门", "胃", "交感"],
        "mechanism": "激活迷走神经-脑干通路，调节β-内啡肽/5-HT水平",
        "note": "对降低POV发生率效果无统计学意义，但对降低恶心有效",
        "strength": "weak",
        "evidence_quality": "very_low",
        "guideline_ref": "R18",
        "status": "ok",
    }

    if surgery_type in ("laparoscopic", "gynecological"):
        result["enhanced"] = True
        result["note"] += "；腹腔镜/妇科手术联合药物效果更佳"

    return result


def recommend_preop_carbs(
    patient: dict = None, surgery_type: str = "", **kwargs
) -> dict:
    """术前碳水化合物推荐"""
    if patient is None:
        patient = {}

    diabetic = patient.get("diabetic", False) or "糖尿病" in str(
        patient.get("comorbidities", [])
    )
    bmi = patient.get("bmi", 22)
    age = patient.get("age", 35)

    if diabetic or bmi >= 30:
        return {
            "carbs_recommended": False,
            "message": "糖尿病患者/肥胖患者不建议常规使用术前碳水化合物",
            "guideline_ref": "R19",
            "status": "ok",
        }

    if age >= 65:
        dose = "200ml"
    elif age < 18:
        dose = "5ml/kg"
    else:
        dose = "≤400ml"

    return {
        "carbs_recommended": True,
        "timing": "术前2h",
        "dosage": dose,
        "evidence": "可显著降低腹腔镜胆囊切除术患者PON和POV发生率",
        "note": "胃排空时间约1.0-1.5h，不增加反流误吸风险",
        "strength": "weak",
        "evidence_quality": "very_low",
        "guideline_ref": "R19",
        "status": "ok",
    }


def recommend_lifestyle(
    patient: dict = None, postoperative: bool = False, **kwargs
) -> dict:
    """综合生活方式干预推荐"""
    if patient is None:
        patient = {}

    interventions = []

    # 咀嚼口香糖
    if postoperative:
        unable = patient.get("altered_consciousness", False) or patient.get("npo", False)
        if not unable:
            interventions.append({
                "type": "咀嚼口香糖",
                "timing": "术后",
                "evidence": "激活口腔-迷走神经反射，降低POV发生率",
                "strength": "weak",
                "evidence_quality": "moderate",
                "guideline_ref": "R20.1",
                "note": "意识清醒/可咀嚼/非禁食/非肠梗阻者适用",
            })

    # 音乐疗法
    if postoperative:
        interventions.append({
            "type": "音乐疗法",
            "timing": "术后",
            "evidence": "降低β-内啡肽水平，调节杏仁核和海马活动",
            "effect_size": "小到中等（Hedges' g）",
            "strength": "weak",
            "evidence_quality": "very_low",
            "guideline_ref": "R20.2",
        })

    # 头高位
    stable = patient.get("hemodynamically_stable", True)
    interventions.append({
        "type": "头高位体位",
        "timing": "术前/术后",
        "contraindicated": not stable,
        "evidence": "头高位可降低PONV发生率",
        "strength": "weak",
        "evidence_quality": "low",
        "guideline_ref": "R20.4",
    })

    # 正向心理引导
    interventions.append({
        "type": "正向心理引导",
        "timing": "术前",
        "evidence": "避免负面心理暗示降低PONV风险",
        "strength": "weak",
        "evidence_quality": "low",
        "guideline_ref": "R20.3",
    })

    # 生姜
    anticoagulated = "抗凝" in str(patient.get("medications", [])) or patient.get(
        "anticoagulated", False
    )
    interventions.append({
        "type": "生姜",
        "timing": "术后",
        "contraindicated": anticoagulated,
        "evidence": "调节5-HT3/NK-1受体，仅对呕吐有效",
        "note": "抗凝患者慎用",
        "guideline_ref": "§5",
    })

    return {
        "interventions": interventions,
        "total": len(interventions),
        "active_count": sum(1 for i in interventions if not i.get("contraindicated", False)),
        "status": "ok",
    }


def recommend_aromatherapy(**kwargs) -> dict:
    """芳香疗法推荐"""
    return {
        "aromatherapy_recommended": True,
        "note": "仅减轻恶心程度，对PONV总体发生率无明显作用",
        "mechanism": "精油挥发性成分通过嗅觉受体激活边缘系统抑制呕吐中枢",
        "evidence": "减少止吐药补救治疗几率（证据质量低）",
        "guideline_ref": "§5",
        "status": "ok",
    }
