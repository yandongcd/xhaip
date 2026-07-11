"""
麻醉管理止吐优化建议 (anesthesia_guide)

基于 2025 版中国《术后恶心呕吐诊疗指南》§2
涵盖：TIVA/PNB/硬膜外/右美托咪定/阿片节律/液体治疗/肌松拮抗剂
"""


def recommend_tiva(risk_level: str = "", surgery_type: str = "", **kwargs) -> dict:
    """丙泊酚 TIVA 推荐"""
    if risk_level == "high":
        recommendation = "strong"
        message = "强烈推荐使用丙泊酚TIVA替代吸入麻醉（降低约39%PONV发生率）"
    elif risk_level == "medium":
        recommendation = "prefer"
        message = "建议优先使用丙泊酚TIVA"
    else:
        recommendation = "consider"
        message = "可考虑丙泊酚TIVA，风险低时不强制"

    return {
        "tiva_recommended": risk_level in ("medium", "high"),
        "recommendation_level": recommendation,
        "message": message,
        "evidence": "与吸入麻醉相比可降低约39%PONV发生率",
        "guideline_ref": "R8",
        "status": "ok",
    }


def recommend_pnb(surgery_type: str = "", patient: dict = None, **kwargs) -> dict:
    """外周神经阻滞类型推荐"""
    if patient is None:
        patient = {}

    pnb_map = {
        "breast": {
            "pnb": "SAPB（前锯肌平面阻滞）/ RIB（菱形肌肋间阻滞）",
            "guideline_ref": "R3",
        },
        "hip": {
            "pnb": "股神经阻滞 / 髂筋膜间隙阻滞",
            "guideline_ref": "R3",
        },
        "knee": {
            "pnb": "股神经阻滞 / 坐骨神经阻滞 / 腰丛阻滞",
            "guideline_ref": "R3",
        },
        "craniotomy": {
            "pnb": "SNB（头皮神经阻滞）",
            "guideline_ref": "R3",
        },
        "spine": {
            "pnb": "ESPB（竖脊肌平面阻滞）/ TLIP（胸腰筋膜平面阻滞）",
            "guideline_ref": "R3",
        },
        "laparoscopic": {
            "pnb": "TAP（腹横肌平面阻滞）— 减重手术有效",
            "guideline_ref": "R3",
        },
    }

    # Fuzzy match surgery type
    matched_pnb = None
    for key, info in pnb_map.items():
        if key in surgery_type.lower():
            matched_pnb = info
            break

    if not matched_pnb:
        return {
            "pnb_recommended": False,
            "message": "未匹配到适合该手术的PNB方案",
            "status": "ok",
        }

    # Check contraindications
    contraindicated = any(
        kw in str(patient.get("comorbidities", [])).lower()
        for kw in ["凝血", "感染", "过敏"]
    )

    return {
        "pnb_recommended": not contraindicated,
        "pnb_type": matched_pnb["pnb"],
        "contraindicated": contraindicated,
        "contraindication_reason": "存在禁忌证" if contraindicated else None,
        "guideline_ref": matched_pnb["guideline_ref"],
        "status": "ok",
    }


def recommend_epidural(
    surgery_category: str = "", patient: dict = None, **kwargs
) -> dict:
    """椎管内麻醉评估"""
    if patient is None:
        patient = {}

    age = patient.get("age", 35)

    contra = any(
        kw in str(patient.get("comorbidities", [])).lower()
        for kw in ["凝血", "脊柱畸形", "血流动力学不稳定"]
    )

    if contra:
        return {
            "epidural_recommended": False,
            "message": "存在硬膜外麻醉禁忌证",
            "guideline_ref": "R4",
            "status": "ok",
        }

    if surgery_category in ("major_non_cardiac", "abdominal", "thoracic"):
        return {
            "epidural_recommended": True,
            "message": "建议全身麻醉联合硬膜外麻醉，减少阿片类药物用量",
            "evidence": "联合硬膜外可降低PONV发生率",
            "guideline_ref": "R4",
            "status": "ok",
        }

    if age <= 7 and surgery_category == "laparoscopic":
        return {
            "epidural_recommended": True,
            "type": "骶管阻滞",
            "message": "≤7岁小儿腹腔镜可考虑骶管阻滞",
            "note": "尚无高质量多中心RCT，需谨慎评估风险",
            "guideline_ref": "R4",
            "status": "ok",
        }

    return {
        "epidural_recommended": False,
        "message": "该手术类型硬膜外获益不明确",
        "guideline_ref": "R4",
        "status": "ok",
    }


def recommend_dexmedetomidine(
    patient: dict = None, surgery_type: str = "", **kwargs
) -> dict:
    """右美托咪定推荐"""
    if patient is None:
        patient = {}

    hr = patient.get("hr", 70)
    is_hypovolemic = patient.get("hypovolemic", False)
    heart_block = "传导阻滞" in str(patient.get("comorbidities", []))

    if hr < 50 or is_hypovolemic or heart_block:
        return {
            "dexmedetomidine_recommended": False,
            "message": "存在右美托咪定禁忌证",
            "contraindication": "心动过缓/低血容量/心脏传导阻滞",
            "guideline_ref": "R6",
            "status": "ok",
        }

    return {
        "dexmedetomidine_recommended": True,
        "usage": "术中镇静 + 术后PCIA",
        "mechanism": "减少阿片需求 + 激活蓝斑α2受体减少交感活性",
        "supported_surgeries": ["鼻内镜", "胸科", "小儿斜视", "脊柱"],
        "evidence": "多项SR显示显著降低PONV发生率",
        "guideline_ref": "R6",
        "status": "ok",
    }


def recommend_opioid_sparing(
    pain_level: str = "",
    opioid_used: bool = False,
    patient: dict = None,
    **kwargs,
) -> dict:
    """阿片节律策略"""
    if patient is None:
        patient = {}

    recommendations = []

    if opioid_used:
        recommendations.append({
            "strategy": "纳洛酮",
            "condition": "阿片过量/过度镇静时",
            "dose": "低剂量（0.25μg/kg/h或更低）",
            "evidence": "降低PON发生率，减少止吐药补救需求",
            "guideline_ref": "R7",
        })

    if pain_level in ("mild", "moderate", "轻", "中"):
        contraindicated = any(
            kw in str(patient.get("comorbidities", [])).lower()
            for kw in ["胃溃疡", "肾功能", "出血"]
        )
        if not contraindicated:
            recommendations.append({
                "strategy": "布洛芬替代",
                "condition": "轻中度疼痛",
                "evidence": "网状Meta分析显示显著降低PONV",
                "note": "对乙酰氨基酚/酮咯酸的有效性在不同研究中相悖",
                "guideline_ref": "R5",
            })

    return {
        "strategies": recommendations,
        "total": len(recommendations),
        "status": "ok",
    }


def recommend_fluid_therapy(
    surgery_duration_min: int = 0, risk_level: str = "", **kwargs
) -> dict:
    """液体治疗策略"""
    base = {
        "fluid_recommended": True,
        "message": "建议围术期维持适当液体平衡，补充晶体液10-30ml/kg",
        "evidence": "与限制性输液相比降低PONV发生率",
        "guideline_ref": "R10.1",
    }

    if surgery_duration_min > 180:
        base["colloid_recommended"] = True
        base["fluid_type"] = "胶体液优先"
        base["message"] += "；预计>3h手术建议使用适量胶体液维持血容量"
        base["guideline_ref"] = "R10.1, R10.2"
        base["note"] = "麻醉时间<3h者胶体与晶体无显著差异"
    else:
        base["colloid_recommended"] = False
        base["fluid_type"] = "晶体液即可"

    base["status"] = "ok"
    return base


def recommend_muscle_relaxant(
    reversal_needed: bool = False,
    risk_level: str = "",
    sugammadex_contraindicated: bool = False,
    **kwargs,
) -> dict:
    """肌松拮抗剂选择"""
    if not reversal_needed:
        return {"status": "ok", "message": "无需肌松拮抗"}

    if not sugammadex_contraindicated:
        return {
            "recommended": "舒更葡糖钠",
            "alternative": "新斯的明",
            "reason": "新斯的明的拟胆碱作用可能导致PONV，舒更葡糖钠PONV风险更低",
            "guideline_ref": "R1",
            "status": "ok",
        }

    return {
        "recommended": "新斯的明",
        "warning": "使用新斯的明可能增加PONV风险" if risk_level in ("medium", "high") else None,
        "note": "建议加强止吐预防" if risk_level in ("medium", "high") else None,
        "guideline_ref": "R1",
        "status": "ok",
    }
