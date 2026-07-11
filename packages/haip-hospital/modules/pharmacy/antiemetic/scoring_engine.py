"""
围术期 PONV 风险评分引擎 (scoring_engine)

基于 2025 版中国《术后恶心呕吐诊疗指南》
- calculate_apfel_score: 成人 Apfel 简化评分 (4因子)
- calculate_povoc_score: 儿童 POVOC 评分 (4因子)
- calculate_pdnv_score: 出院后 PDNV 评分 (5因子)
- classify_risk_level: 风险等级分类
"""


def calculate_apfel_score(
    gender: str = "",
    smoking: str = "",
    ponv_history: str = "",
    motion_sickness: str = "",
    opioid_planned: str = "",
    **kwargs,
) -> dict:
    """成人 Apfel 简化评分 (0-4分)

    Args:
        gender: 性别 (男/女 F/M)
        smoking: 吸烟 (否=非吸烟)
        ponv_history: PONV 病史 (有/无)
        motion_sickness: 晕动病史 (有/无)
        opioid_planned: 计划术后阿片类药物 (是/否)

    Returns:
        {score, risk_level, probability, factors, recommendation_id}
    """
    score = 0
    factors = []

    gender_val = gender.strip().upper() if gender else ""
    if gender_val in ("F", "女", "女性"):
        score += 1
        factors.append("女性")

    smoking_val = smoking.strip() if smoking else ""
    if smoking_val in ("否", "无", "不吸烟", "非吸烟", "N", "No"):
        score += 1
        factors.append("非吸烟")

    ponv_val = ponv_history.strip() if ponv_history else ""
    motion_val = motion_sickness.strip() if motion_sickness else ""
    if ponv_val in ("有", "是", "Y", "Yes") or motion_val in ("有", "是", "Y", "Yes"):
        score += 1
        factors.append("PONV/晕动病史")

    opioid_val = opioid_planned.strip() if opioid_planned else ""
    if opioid_val in ("是", "有", "Y", "Yes"):
        score += 1
        factors.append("术后阿片类药物")

    probability_map = {0: 10, 1: 21, 2: 39, 3: 61, 4: 79}
    probability = probability_map.get(score, 0)

    if score <= 1:
        risk_level = "low"
    elif score == 2:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "score_type": "apfel",
        "population": "adult",
        "score": score,
        "max_score": 4,
        "risk_level": risk_level,
        "probability_pct": probability,
        "factors": factors,
        "factor_count": len(factors),
        "recommendation_id": "R2.1",
        "guideline": "2025版中国PONV诊疗指南",
    }


def calculate_povoc_score(
    age: int = 0,
    surgery_duration_min: int = 0,
    opioid_used: str = "",
    ponv_history: str = "",
    motion_sickness: str = "",
    **kwargs,
) -> dict:
    """儿童 POVOC 评分 (0-4分)
    2025版指南更新：术中阿片替代"斜视手术"以提升普适性

    Returns:
        {score, risk_level, probability, factors, recommendation_id}
    """
    score = 0
    factors = []

    if age >= 3:
        score += 1
        factors.append("年龄≥3岁")

    if surgery_duration_min >= 30:
        score += 1
        factors.append("手术时间≥30min")

    opioid_val = opioid_used.strip() if opioid_used else ""
    if opioid_val in ("是", "有", "Y", "Yes"):
        score += 1
        factors.append("术中阿片类药物")

    ponv_val = ponv_history.strip() if ponv_history else ""
    motion_val = motion_sickness.strip() if motion_sickness else ""
    if ponv_val in ("有", "是", "Y", "Yes") or motion_val in ("有", "是", "Y", "Yes"):
        score += 1
        factors.append("PONV/晕动病史")

    probability_map = {0: 9, 1: 10, 2: 30, 3: 55, 4: 70}
    probability = probability_map.get(score, 0)

    if score == 0:
        risk_level = "low"
    elif score in (1, 2):
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "score_type": "povoc",
        "population": "pediatric",
        "score": score,
        "max_score": 4,
        "risk_level": risk_level,
        "probability_pct": probability,
        "factors": factors,
        "factor_count": len(factors),
        "recommendation_id": "R2.2",
        "guideline": "2025版中国PONV诊疗指南",
    }


def calculate_pdnv_score(
    gender: str = "",
    age: int = 0,
    ponv_history: str = "",
    pacu_opioid: str = "",
    pacu_nausea: str = "",
    **kwargs,
) -> dict:
    """出院后恶心呕吐 PDNV 评分 (0-5分)

    Returns:
        {score, probability, factors}
    """
    score = 0
    factors = []

    gender_val = gender.strip().upper() if gender else ""
    if gender_val in ("F", "女", "女性"):
        score += 1
        factors.append("女性")

    if age < 50:
        score += 1
        factors.append("年龄<50岁")

    ponv_val = ponv_history.strip() if ponv_history else ""
    if ponv_val in ("有", "是", "Y", "Yes"):
        score += 1
        factors.append("PONV发生史")

    pacu_op_val = pacu_opioid.strip() if pacu_opioid else ""
    if pacu_op_val in ("是", "有", "Y", "Yes"):
        score += 1
        factors.append("PACU使用阿片类药物")

    pacu_na_val = pacu_nausea.strip() if pacu_nausea else ""
    if pacu_na_val in ("是", "有", "Y", "Yes"):
        score += 1
        factors.append("PACU内出现恶心")

    probability_map = {0: 10, 1: 20, 2: 30, 3: 50, 4: 60, 5: 80}
    probability = probability_map.get(score, 0)

    return {
        "score_type": "pdnv",
        "population": "adult_outpatient",
        "score": score,
        "max_score": 5,
        "probability_pct": probability,
        "factors": factors,
        "factor_count": len(factors),
        "guideline": "SAMBA Fourth Consensus + 2025版中国PONV诊疗指南",
    }


def classify_risk_level(score: int, score_type: str = "apfel", **kwargs) -> dict:
    """根据评分和类型返回风险等级"""
    if score_type == "apfel":
        if score <= 1:
            level = "low"
        elif score == 2:
            level = "medium"
        else:
            level = "high"
    elif score_type == "povoc":
        if score == 0:
            level = "low"
        elif score in (1, 2):
            level = "medium"
        else:
            level = "high"
    elif score_type == "pdnv":
        if score <= 1:
            level = "low"
        elif score <= 4:
            level = "medium"
        else:
            level = "high"
    else:
        level = "unknown"

    return {"risk_level": level, "score": score, "score_type": score_type}
