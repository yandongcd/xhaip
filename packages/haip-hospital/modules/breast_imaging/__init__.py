"""Breast Imaging v2.0 — BI-RADS v2025 全典 + 密度分层 + 多模态 + 风险模型.

Guidelines: BI-RADS v2025 (ACR), NCCN 2024, 中国乳腺癌筛查指南(2023)
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="breast-imaging", department="影像诊断科")
_GUIDELINES = [
    "BI-RADS v2025 (ACR 乳腺影像报告和数据系统)",
    "NCCN 乳腺癌筛查与诊断指南 (2024)",
    "中国乳腺癌筛查指南 (2023)",
    "ACR 乳腺密度评估 (4分类: a/b/c/d)",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ BI-RADS Complete Lexicon ═══════

_BIRADS_DESCRIPTORS = {
    "mass_shape": {
        "oval": {"score": 0, "desc": "卵圆形 — 良性特征(囊肿/纤维腺瘤)"},
        "round": {"score": 0, "desc": "圆形 — 鉴别: 囊肿vs边界清楚的癌(髓样/黏液癌)"},
        "irregular": {"score": 1, "desc": "分叶状/不规则形 — 恶性风险增高"},
    },
    "mass_margin": {
        "circumscribed": {"score": 0, "desc": "边界清楚 — 良性但与恶性重叠(髓样/黏液癌可清楚)"},
        "microlobulated": {"score": 1, "desc": "微分叶 — 中危征象"},
        "indistinct": {"score": 1, "desc": "模糊 — 被周围组织遮盖"},
        "spiculated": {"score": 3, "desc": "毛刺状 — 高度恶性征象(PPV 70-90%)"},
    },
    "mass_density": {
        "high_density": {"score": 1, "desc": "高密度 — 恶性肿块常为高密度或等密度"},
        "equal_density": {"score": 0, "desc": "等密度 — 注意: 等密度也可能为恶性"},
        "low_density": {"score": -1, "desc": "脂肪密度 — 几乎肯定良性"},
    },
    "calcification_morphology": {
        "benign_typical": {"score": 0, "desc": "典型良性: 皮肤钙化/血管钙化/粗大爆米花状(纤维腺瘤)/棒状(分泌性疾病)/边缘清楚圆形/蛋壳状"},
        "suspicious_amorphous": {"score": 2, "desc": "不定形/模糊 — 可疑形态 (BI-RADS 4B)"},
        "suspicious_coarse_heterogeneous": {"score": 2, "desc": "粗糙不均质 — 可疑形态 (BI-RADS 4B)"},
        "suspicious_fine_pleomorphic": {"score": 3, "desc": "细小多形性 — 高度可疑 (BI-RADS 4C)"},
        "suspicious_fine_linear_branching": {"score": 4, "desc": "细线/分枝状 — 高度恶性(典型DCIS, BI-RADS 5)"},
    },
    "calcification_distribution": {
        "diffuse": {"score": 0, "desc": "弥漫/散在 — 良性分布模式"},
        "regional": {"score": 1, "desc": "区域性 — 覆盖较大范围"},
        "grouped": {"score": 2, "desc": "簇状/成组 — 可疑分布 (DCIS)"},
        "linear": {"score": 3, "desc": "线样 — 显示恶性沿导管分布"},
        "segmental": {"score": 3, "desc": "段性分布 — 高度提示DCIS"},
    },
    "asymmetry": {
        "asymmetry": {"score": 1, "desc": "单纯不对称 — 需加摄点压/超声除外真实病变(developing asymmetry更可疑)"},
        "developing_asymmetry": {"score": 2, "desc": "进展性不对称 — 较前新出现或增大, 需活检(PPV 10-15%)"},
        "global_asymmetry": {"score": 1, "desc": "全局不对称 — 多为正常变异/激素替代"},
    },
    "architectural_distortion": {
        "present_without_trauma": {"score": 3, "desc": "结构扭曲(无手术/外伤史) — 高度可疑征象(PPV 10-30%), DBT优于FFDM"},
        "post_surgical": {"score": 0, "desc": "术后疤痕 — 与既往手术位置一致, 动态观察"},
    },
    "associated_features": {
        "skin_retraction": {"score": 2, "desc": "皮肤凹陷/牵拉 — 恶性征象"},
        "nipple_retraction": {"score": 2, "desc": "乳头回缩 — 需鉴别: 先天vs获得性(恶性)"},
        "skin_thickening": {"score": 2, "desc": "皮肤增厚 — 炎性乳癌/放疗后/淋巴水肿"},
        "axillary_adenopathy": {"score": 2, "desc": "腋窝淋巴结异常 — 应超声评估形态(皮质增厚>3mm=可疑)"},
        "trabecular_thickening": {"score": 2, "desc": "小梁增粗 — 炎性乳癌特征"},
    },
}

# BI-RADS 4 subcategories
_BIRADS4_SUBTYPES = {
    "4A": {"range": (4, 5), "ppv": "2-10%", "desc": "低度可疑 — 恶性可能2-10%", "action": "活检(核心针) → 良性结果可6月随访"},
    "4B": {"range": (5, 8), "ppv": "10-50%", "desc": "中度可疑 — 恶性可能10-50%", "action": "活检(核心针/真空辅助) → 无论结果均需临床-病理一致性评估"},
    "4C": {"range": (8, 11), "ppv": "50-95%", "desc": "高度可疑 — 恶性可能50-95%", "action": "活检 → 高度建议多学科MDT → 即使良性也需重新评估"},
}

# BI-RADS final categories
_BIRADS_MEANING = {
    0: "评估不完整 — 需进一步检查(加摄点压/超声/MRI/与前片对比)",
    1: "阴性 — 恶性可能0% — 正常筛查随访",
    2: "良性发现 — 恶性可能0% — 常规筛查随访",
    3: "可能良性 — 恶性可能<2% — 6个月短期随访(钼靶+超声), 连续2-3年稳定→降为BI-RADS 2",
    4: "可疑恶性 — 恶性可能>2%-<95% — 需活检 (建议注明4A/4B/4C亚型)",
    5: "高度怀疑恶性 — 恶性可能≥95% — 活检确诊+MDT+手术方案",
    6: "已活检证实恶性 — 等待手术/新辅助化疗反应评估",
}

_FOLLOWUP = {
    0: "补充: 加摄点压/放大/超声/MRI/与前片对比",
    1: "常规筛查: 每年钼靶±超声 (年龄>40) 或 每1-2年 (45-69岁)",
    2: "常规筛查: 每年钼靶±超声 (含良性肿块/钙化/淋巴结的定性描述)",
    3: "短期随访: 6月±12月±24月 钼靶+超声 同侧 + 建议连续2-3年稳定→降级",
    4: "活检: 空芯针穿刺(CNB) 或 真空辅助(VABB) → 放置定位夹 → 标本摄片(钙化) → 临床-病理一致性评估",
    5: "活检确诊 → 乳腺外科+肿瘤内科+放疗科 MDT → 手术方案(保乳vs全切+前哨淋巴结)",
    6: "治疗中: 新辅助化疗反应评估(MRI每2周期) → 术后复查(每年钼靶+超声)",
}

_BREAST_DENSITY = {
    "a": {"name": "脂肪型", "risk_modifier": 0, "masking": "无遮蔽 — 钼靶敏感度>95%"},
    "b": {"name": "散在纤维腺体型", "risk_modifier": 0, "masking": "轻度遮蔽 — 钼靶敏感度85-95%"},
    "c": {"name": "不均匀致密型", "risk_modifier": 1, "masking": "中度遮蔽 — 钼靶敏感度70-85%, 加超声MRI"},
    "d": {"name": "极度致密型", "risk_modifier": 2, "masking": "重度遮蔽 — 钼靶敏感度<60%, 强烈建议+超声/MRI"},
}


# ═══════ Handler Functions ═══════


def birads_classify(patient_id: str = "", findings: dict | None = None,
                    modality: str = "FFDM",
                    breast_density: str = "c",
                    menopausal: str = "post",
                    **kwargs: Any) -> dict:
    """BI-RADS v2025 综合分级 — 全典匹配 + 4A/4B/4C亚型 + 密度调整."""
    p, err = _get_patient({"patient_id": patient_id})
    findings = findings or {}

    score = 0
    features: list[str] = []
    birads4_evidence: list[str] = []

    # Mass assessment
    mass_score = 0
    if findings.get("mass"):
        mass_info: dict = findings.get("mass", {}) or {}
        shape = mass_info.get("shape", "")
        margin = mass_info.get("margin", "")
        density = mass_info.get("density", "")

        shape_info = _BIRADS_DESCRIPTORS["mass_shape"].get(shape, {})
        margin_info = _BIRADS_DESCRIPTORS["mass_margin"].get(margin, {})
        density_info = _BIRADS_DESCRIPTORS["mass_density"].get(density, {})

        mass_score = shape_info.get("score", 0) + margin_info.get("score", 0) + density_info.get("score", 0)
        score += mass_score
        features.append(f"肿块: {shape_info.get('desc', shape)} + {margin_info.get('desc', margin)}")
        if "spiculated" in margin.lower():
            birads4_evidence.append("毛刺状肿块 — PPV 70-90%")

    # Calcification assessment
    if findings.get("calcifications"):
        calcs_info: dict = findings.get("calcifications", {}) or {}
        morph = calcs_info.get("morphology", "")
        dist = calcs_info.get("distribution", "")

        morph_info = _BIRADS_DESCRIPTORS["calcification_morphology"].get(morph, {})
        dist_info = _BIRADS_DESCRIPTORS["calcification_distribution"].get(dist, {})

        score += morph_info.get("score", 0) + dist_info.get("score", 0)
        features.append(f"钙化: {morph_info.get('desc', morph)[:50]}")
        if "fine_linear" in morph.lower() or "fine_pleomorphic" in morph.lower():
            birads4_evidence.append(f"{morph_info.get('desc', morph)} — 高度可疑钙化")

    # Asymmetry
    if findings.get("asymmetry"):
        asym_info = _BIRADS_DESCRIPTORS["asymmetry"].get(findings["asymmetry"], {})
        score += asym_info.get("score", 0)
        features.append(f"不对称: {asym_info.get('desc', findings['asymmetry'])[:60]}")

    # Architectural distortion
    if findings.get("architectural_distortion"):
        ad_info = _BIRADS_DESCRIPTORS["architectural_distortion"].get(
            "present_without_trauma" if not findings.get("post_surgical") else "post_surgical", {})
        score += ad_info.get("score", 0)
        features.append(ad_info.get("desc", ""))
        if score >= 3:
            birads4_evidence.append("结构扭曲+毛刺状肿块 → 高度可疑")

    # Associated features
    if findings.get("associated"):
        for feat, present in findings.get("associated", {}).items():
            if present:
                feat_info = _BIRADS_DESCRIPTORS["associated_features"].get(feat, {})
                score += feat_info.get("score", 0)
                features.append(f"伴随征象: {feat}")

    # Density modifier (dense breast may obscure lesions)
    density_info = _BREAST_DENSITY.get(breast_density, _BREAST_DENSITY["c"])
    density_modifier = ""

    # Map score to BI-RADS
    if score <= 0:
        birads = 1
    elif score <= 1:
        birads = 2
    elif score <= 2:
        birads = 3
    elif score <= 7:
        birads = 4
        # Determine 4A/4B/4C
        for subtype, info in _BIRADS4_SUBTYPES.items():
            lo, hi = info["range"]
            if lo <= score < hi:
                birads_detail = f"4 ({subtype}) — {info['desc']}"
                break
        else:
            birads_detail = "4 — 可疑恶性"
    elif score <= 10:
        birads = 5
    else:
        birads = 5

    # BI-RADS 4 detail
    if birads == 4:
        birads_display = birads_detail if 'birads_detail' in dir() else "4"
        for subtype, info in _BIRADS4_SUBTYPES.items():
            lo, hi = info["range"]
            if lo <= score < hi:
                birads_display = f"4{subtype} ({info['ppv']})"
                break
    else:
        birads_display = str(birads)

    # Density recommendation
    if birads <= 2 and breast_density in ("c", "d"):
        density_modifier = f"致密乳腺(ACR {breast_density}) — 钼靶敏感度降低, 建议加做超声/MRI"
        features.append(density_modifier)

    return {
        "status": "ok",
        "patient_id": patient_id,
        "birads": birads,
        "birads_display": birads_display if birads == 4 else str(birads),
        "birads_meaning": _BIRADS_MEANING[birads],
        "raw_score": score,
        "modality": modality,
        "breast_density": f"ACR {breast_density} ({density_info['name']})",
        "features": features,
        "malignancy_evidence": birads4_evidence if birads4_evidence else None,
        "density_masking_warning": density_info["masking"],
        "followup": _FOLLOWUP[birads],
        "summary": f"BI-RADS {birads_display} — {_BIRADS_MEANING[birads][:60]}",
    }


def risk_predict(patient_id: str = "", birads: int = 1,
                 age: int = 45, family_history: str = "none",
                 brca: str = "negative",
                 breast_density: str = "c",
                 menopausal: str = "post",
                 age_menarche: int = 13,
                 age_first_birth: int = 28,
                 breast_biopsies: int = 0,
                 atypical_hyperplasia: bool = False,
                 **kwargs: Any) -> dict:
    """乳腺癌风险预测 — BI-RADS + 密度 + Gail/Tyrer-Cuzick 因素 + BRCA."""
    p, err = _get_patient({"patient_id": patient_id})

    risk_score = 0
    factors: list[str] = []

    # BI-RADS contribution
    if birads >= 5:
        risk_score += 10
        factors.append("BI-RADS 5 — 恶性可能≥95%")
    elif birads == 4:
        risk_score += 6
        factors.append("BI-RADS 4 — 恶性可能2-95%")
    elif birads == 3:
        risk_score += 2
        factors.append("BI-RADS 3 — 恶性可能<2%")

    # Age
    if age >= 55:
        risk_score += 1
        factors.append(f"年龄≥55岁 ({age}) — 乳腺癌发病率随年龄增高")

    # Family history (Tyrer-Cuzick model)
    if family_history == "first_degree":
        risk_score += 2
        factors.append("一级亲属乳腺癌史 — 终生风险增高2-3倍")
    elif family_history == "multiple":
        risk_score += 4
        factors.append("多个亲属乳腺癌/卵巢癌史 — 高度提示遗传性乳腺癌")

    # BRCA
    if brca.lower() == "positive":
        risk_score += 5
        factors.append("BRCA1/2 致病突变 — 终生乳腺癌风险 65-72%")

    # Breast density
    density_info = _BREAST_DENSITY.get(breast_density, _BREAST_DENSITY["c"])
    risk_score += density_info["risk_modifier"]
    if density_info["risk_modifier"] > 0:
        factors.append(f"致密乳腺(ACR {breast_density}) — 独立风险因素")

    # Hormonal factors (Gail model)
    if menopausal == "pre" and age_menarche < 12:
        risk_score += 1
        factors.append("初潮<12岁 — Gail模型风险因素")
    if age_first_birth > 30 or (age_first_birth == 0 and age > 25):
        risk_score += 1
        factors.append("未产/晚产>30岁 — 风险因素")

    # Biopsy history
    if breast_biopsies >= 2:
        risk_score += 1
        factors.append("≥2次乳腺活检史")
    if atypical_hyperplasia:
        risk_score += 3
        factors.append("非典型增生(ADH/ALH) — 相对风险4-5倍")

    # Risk stratification
    if risk_score >= 10:
        risk = "极高危"
        rec = "遗传咨询+乳腺MRI每年+钼靶每年(交替q6m) + 考虑预防性药物(他莫昔芬/雷洛昔芬)"
    elif risk_score >= 6:
        risk = "高危"
        rec = "乳腺MRI每年 + 钼靶+超声每年 + 遗传咨询(BRCA检测)"
    elif risk_score >= 3:
        risk = "中危"
        rec = "钼靶+超声每年(>40岁连续) + 考虑个体化MRI筛查"
    else:
        risk = "一般风险"
        rec = "常规筛查: 钼靶±超声 每1-2年(45-69岁)"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "risk_level": risk,
        "risk_score": risk_score,
        "factors": factors,
        "recommendation": rec,
        "summary": f"5年+终生乳腺癌风险 — {risk} (评分{risk_score}) | {rec[:60]}",
        "guideline_ref": "NCCN 2024 高风险筛查指南 + Tyrer-Cuzick v8",
    }


def followup_recommend(patient_id: str = "", birads: int = 1,
                       breast_density: str = "c",
                       **kwargs: Any) -> dict:
    """BI-RADS导向的个体化随访路径."""
    p, err = _get_patient({"patient_id": patient_id})

    base_rec = _FOLLOWUP.get(birads, "临床评估")

    supplemental = ""
    if breast_density in ("c", "d"):
        if birads <= 2:
            supplemental = "致密乳腺: 强烈建议加做乳腺超声/MRI (钼靶敏感度受限)"
        if birads == 3:
            supplemental = "致密乳腺: 6月随访建议含乳腺超声 + 每1-2年加做MRI"

    # BI-RADS specific checklist
    checklist = []
    if birads == 4:
        checklist = [
            "活检定位夹放置(钙化/超声不可见者: 导丝/定位夹+钼靶确认)",
            "标本摄片(钙化病变)",
            "病理-影像一致性评估(关键!) — 不一致则需再次活检或手术",
            "良性但不一致结果: 真空辅助完整切除或手术活检",
        ]
    elif birads == 5:
        checklist = [
            "活检确诊(核心针)",
            "肿瘤生物标记: ER/PR/HER2/Ki-67 + FISH(若HER2 2+)",
            "腋窝超声+可疑淋巴结穿刺",
            "乳腺MRI: 评价病变范围+对侧乳腺+多灶/多中心",
            "MDT: 乳腺外科+肿瘤内科+放疗科+病理+影像",
            "新辅助化疗评估: 每2周期MRI",
        ]
    elif birads == 3:
        checklist = [
            "6月: 同侧钼靶(点压)+超声",
            "12月: 钼靶+超声 同侧",
            "24月: 钼靶+超声 双侧 → 稳定2-3年→降级BI-RADS 2",
            "随访期间若增大或出现可疑特征 → 立即活检",
        ]

    return {
        "status": "ok",
        "patient_id": patient_id,
        "birads": birads,
        "breast_density": f"ACR {breast_density}",
        "primary_recommendation": base_rec,
        "density_supplement": supplemental if supplemental else None,
        "action_checklist": checklist,
        "next_imaging_interval": _get_imaging_interval(birads, breast_density),
        "summary": f"BI-RADS {birads} → {base_rec[:60]}",
    }


def _get_imaging_interval(birads: int, density: str) -> str:
    """个体化影像随访间隔."""
    if birads >= 5:
        return "治疗中: 每2周期MRI→术后每年钼靶+超声"
    if birads == 4:
        return "活检确诊后按病理结果确定"
    if birads == 3:
        return "6月→12月→24月(同侧) → 稳定后转每年"
    if birads <= 2:
        if density in ("c", "d"):
            return "每年钼靶+超声 + 每1-2年考虑MRI"
        return "每年钼靶 或 每2年钼靶(45-54岁连续, 55+每2年)"
    return "补充检查后确定"
