"""
围术期止吐用药方案推荐引擎 (drug_recommend)

基于 2025 版中国《术后恶心呕吐诊疗指南》+ SAMBA 第四版共识
支持成人/儿童 × 低/中/高危 × 首选/备选方案
"""


def recommend_regimen_adult(
    risk_level: str = "",
    risk_score: int = 0,
    patient_id: str = "",
    **kwargs,
) -> dict:
    """成人止吐用药方案推荐

    Args:
        risk_level: 风险等级 (low/medium/high)
        risk_score: Apfel 评分 (0-4)

    Returns:
        {
            regimen: {tier, drugs: [{class, name, dose, route, timing, evidence}], ...},
            alternatives: [...],
            strategy: str,
            guideline_refs: [...]
        }
    """
    regimens = {
        "low": {
            "tier": "单药预防",
            "strategy": "观察为主，可选用单药预防",
            "drugs": [
                {
                    "class": "5-HT3受体拮抗剂",
                    "name": "托烷司琼",
                    "dose": "5mg",
                    "route": "IV",
                    "timing": "手术结束前30min",
                    "evidence": "R11.4",
                    "note": "短效5-HT3拮抗剂，术毕给药",
                }
            ],
            "alternatives": [
                {
                    "class": "5-HT3受体拮抗剂",
                    "name": "昂丹司琼",
                    "dose": "4mg",
                    "route": "IV",
                    "timing": "手术结束前",
                    "evidence": "R11.4",
                }
            ],
        },
        "medium": {
            "tier": "二联用药预防",
            "strategy": "二联用药覆盖不同受体",
            "drugs": [
                {
                    "class": "5-HT3受体拮抗剂",
                    "name": "托烷司琼",
                    "dose": "5mg",
                    "route": "IV",
                    "timing": "手术结束前30min",
                    "evidence": "R11.1",
                },
                {
                    "class": "皮质类固醇",
                    "name": "地塞米松",
                    "dose": "4-8mg",
                    "route": "IV",
                    "timing": "麻醉诱导后",
                    "evidence": "R12.1",
                    "note": "无糖皮质激素禁忌证时使用",
                },
            ],
            "alternatives": [
                {
                    "class": "5-HT3受体拮抗剂",
                    "name": "昂丹司琼",
                    "dose": "4mg",
                    "route": "IV",
                    "timing": "手术结束前",
                    "evidence": "R11.1",
                },
                {
                    "class": "多巴胺受体拮抗剂",
                    "name": "氨磺必利",
                    "dose": "5mg",
                    "route": "IV",
                    "timing": "麻醉诱导时",
                    "evidence": "R14.1",
                    "note": "用于中高风险患者",
                },
            ],
        },
        "high": {
            "tier": "三联用药预防",
            "strategy": "三联用药覆盖5-HT3+激素+多巴胺受体",
            "drugs": [
                {
                    "class": "5-HT3受体拮抗剂",
                    "name": "帕洛诺司琼",
                    "dose": "0.075mg",
                    "route": "IV",
                    "timing": "麻醉诱导前",
                    "evidence": "R11.3",
                    "note": "长效（半衰期40h），覆盖24h高风险期",
                },
                {
                    "class": "皮质类固醇",
                    "name": "地塞米松",
                    "dose": "8mg",
                    "route": "IV",
                    "timing": "麻醉诱导后",
                    "evidence": "R12.1",
                },
                {
                    "class": "多巴胺受体拮抗剂",
                    "name": "氟哌利多",
                    "dose": "0.625mg",
                    "route": "IV",
                    "timing": "手术结束前",
                    "evidence": "R14.3",
                    "contraindications": [
                        "重症肌无力",
                        "锥体外系疾病",
                        "QT间期延长",
                        "电解质紊乱",
                        "帕金森病",
                    ],
                },
            ],
            "alternatives": [
                {
                    "class": "NK-1受体拮抗剂",
                    "name": "福沙匹坦",
                    "dose": "150mg",
                    "route": "IV",
                    "timing": "麻醉诱导前",
                    "evidence": "R13",
                    "note": "单药预防POV效果最佳，成本较高",
                },
                {
                    "class": "皮质类固醇",
                    "name": "地塞米松",
                    "dose": "8mg",
                    "route": "IV",
                    "timing": "麻醉诱导后",
                    "evidence": "R12.1",
                },
            ],
        },
    }

    if risk_level not in regimens:
        risk_level = "medium"  # default

    result = regimens[risk_level]
    result["risk_score"] = risk_score
    result["guideline_refs"] = ["R11", "R12", "R13", "R14", "R21.1", "SAMBA 2020"]
    result["status"] = "ok"

    return result


def recommend_regimen_pediatric(
    risk_level: str = "",
    risk_score: int = 0,
    age: int = 0,
    **kwargs,
) -> dict:
    """儿童止吐用药方案推荐"""
    regimens = {
        "low": {
            "tier": "观察",
            "strategy": "低危儿童无需常规药物预防",
            "drugs": [],
            "alternatives": [],
        },
        "medium": {
            "tier": "二联用药",
            "strategy": "5-HT3拮抗剂 + 地塞米松",
            "drugs": [
                {
                    "class": "5-HT3受体拮抗剂",
                    "name": "昂丹司琼",
                    "dose": "0.05-0.1mg/kg (最大4mg)",
                    "route": "IV",
                    "timing": "手术结束前",
                    "evidence": "R11.1",
                },
            ],
            "alternatives": [],
        },
        "high": {
            "tier": "三联用药",
            "strategy": "5-HT3 + 地塞米松 + 氟哌利多（谨慎）",
            "drugs": [
                {
                    "class": "5-HT3受体拮抗剂",
                    "name": "昂丹司琼",
                    "dose": "0.1mg/kg (最大4mg)",
                    "route": "IV",
                    "timing": "手术结束前",
                    "evidence": "R11.1",
                },
                {
                    "class": "皮质类固醇",
                    "name": "地塞米松",
                    "dose": "0.15mg/kg (最大8mg)",
                    "route": "IV",
                    "timing": "手术开始前",
                    "evidence": "R12.2",
                    "note": "仅适用于≥3岁儿童",
                },
            ],
            "alternatives": [],
        },
    }

    if risk_level not in regimens:
        risk_level = "medium"

    result = regimens[risk_level]
    result["risk_score"] = risk_score
    result["guideline_refs"] = ["R11", "R12.2", "SAMBA 2020"]
    result["status"] = "ok"
    return result


def recommend_timing(drugs: list = None, **kwargs) -> dict:
    """给药时机推荐"""
    if drugs is None:
        drugs = []

    timing_map = {
        "帕洛诺司琼": {
            "timing": "麻醉诱导前",
            "reason": "长效（半衰期40h），覆盖24h高风险期",
            "evidence": "R11.3",
        },
        "昂丹司琼": {
            "timing": "手术结束前",
            "reason": "短效（半衰期3-6h），术毕给药",
            "evidence": "R11.4",
        },
        "托烷司琼": {
            "timing": "手术结束前30min",
            "reason": "短效，术毕给药",
            "evidence": "R11.4",
        },
        "地塞米松": {
            "timing": "麻醉诱导后",
            "reason": "约10min起效，药效持续24h以上",
            "evidence": "R12.1",
        },
        "阿瑞匹坦(口服)": {
            "timing": "术前1-3h",
            "reason": "口服制剂需在麻醉诱导前吸收",
            "evidence": "R13",
        },
        "福沙匹坦": {
            "timing": "麻醉诱导前",
            "reason": "NK-1受体拮抗剂，诱导前给药",
            "evidence": "R13",
        },
        "东莨菪碱贴剂": {
            "timing": "术前晚或术前2-4h",
            "reason": "透皮吸收需提前使用",
            "evidence": "R15",
        },
        "氨磺必利": {
            "timing": "麻醉诱导时",
            "reason": "多巴胺受体拮抗剂",
            "evidence": "R14.1",
        },
    }

    result = []
    for drug_name in drugs:
        timing = timing_map.get(drug_name, {"timing": "手术结束前", "reason": "短效药物常规时机"})
        result.append({"drug": drug_name, **timing})

    return {"timing_plan": result, "status": "ok"}


def recommend_rescue(
    prior_prophylaxis: bool = False,
    hours_since_prophylaxis: float = 0,
    triple_therapy_used: bool = False,
    **kwargs,
) -> dict:
    """补救治疗方案推荐"""
    if not prior_prophylaxis:
        return {
            "scenario": "未接受预防用药",
            "recommendation": {
                "first_line": {
                    "drug": "5-HT3受体拮抗剂（小剂量）",
                    "options": [
                        {"name": "昂丹司琼", "dose": "1mg", "route": "IV"},
                        {"name": "格拉司琼", "dose": "0.1mg", "route": "IV"},
                        {"name": "托烷司琼", "dose": "0.5mg", "route": "IV"},
                    ],
                    "note": "治疗剂量约为预防剂量的1/4",
                },
                "alternatives": [
                    {"name": "地塞米松", "dose": "2-4mg", "route": "IV"},
                    {"name": "氟哌利多", "dose": "0.625mg", "route": "IV"},
                ],
                "pacu_specific": {"name": "丙泊酚", "dose": "20mg", "route": "IV"},
            },
            "guideline_refs": ["R11.2", "SAMBA 2020"],
            "status": "ok",
        }

    if triple_therapy_used and hours_since_prophylaxis < 6:
        return {
            "scenario": "三联疗法预防后6h内仍发生PONV",
            "recommendation": "6h内不重复原三联药物组合，换用其他类型止吐药",
            "note": "考虑非药物干预（穴位刺激/耳穴）",
            "guideline_refs": ["R21.1"],
            "status": "ok",
        }

    if hours_since_prophylaxis < 6:
        return {
            "scenario": "预防用药后6h内发生PONV",
            "recommendation": "换用不同机制的药物，6h内不重复使用原预防药物",
            "note": "地塞米松不推荐重复使用",
            "guideline_refs": ["R11", "R12", "R21.1"],
            "status": "ok",
        }

    return {
        "scenario": "预防用药后超过6h发生PONV",
        "recommendation": "可重复给予5-HT3受体拮抗剂和氟哌利多/氟哌啶醇（剂量同前）",
        "note": "不推荐重复使用地塞米松",
        "guideline_refs": ["R11.2", "R21.1"],
        "status": "ok",
    }
