"""Secondary HTN v2.0 — 继发性高血压六大病因 + ARR解读 + 肾上腺静脉采血 + 治疗分层.

Guidelines: 中国继发性高血压筛查专家共识(2023), ESH 2023, Endocrine Society PA指南 2016, JCS 2021
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="hypertension-screening", department="内分泌代谢科")
_GUIDELINES = [
    "中国继发性高血压筛查专家共识 (2023)",
    "ESH 高血压管理指南 (2023)",
    "Endocrine Society 原发性醛固酮增多症管理指南 (2016)",
    "中国嗜铬细胞瘤和副神经节瘤诊断治疗专家共识 (2020)",
    "JCS 2021 继发性高血压筛查路径",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ Secondary HTN Pattern Detection ═══════

_HIGH_RISK_PATTERNS = {
    "早发高血压": {"criteria": "年龄<40岁新发高血压 (血压≥140/90)", "suspect": "继发性高血压(肾血管/内分泌/肾脏)", "weight": 3},
    "难治性高血压": {"criteria": "≥3种药物(含利尿剂)仍不达标, 或≥4种药物才达标", "suspect": "原醛症/肾动脉狭窄/OSA", "weight": 3},
    "低血钾": {"criteria": "自发或利尿剂诱导的低钾血症 (K<3.5 mmol/L)", "suspect": "原发性醛固酮增多症(PA)", "weight": 4},
    "肾上腺占位": {"criteria": "影像学(CT/MRI)发现肾上腺意外瘤 ≥1cm", "suspect": "原醛/嗜铬细胞瘤/库欣/肾上腺皮质癌", "weight": 4},
    "阵发性三联征": {"criteria": "阵发性高血压+头痛+心悸+大汗", "suspect": "嗜铬细胞瘤", "weight": 5},
    "肾功能恶化_ACEi": {"criteria": "使用ACEI/ARB后SCr升高>30% 或 急性肾损伤", "suspect": "双侧肾动脉狭窄", "weight": 4},
    "低肾素高血压": {"criteria": "PRA<1.0 ng/mL/h + 高血压", "suspect": "原醛症/Liddle综合征/盐皮质激素过多", "weight": 3},
    "向心性肥胖特征": {"criteria": "满月脸/水牛背/紫纹/糖皮质激素用药史", "suspect": "库欣综合征", "weight": 4},
    "睡眠呼吸暂停": {"criteria": "打鼾+白天嗜睡+肥胖+顽固性HTN", "suspect": "OSA继发性高血压", "weight": 2},
    "肾脏结构异常": {"criteria": "肾脏超声异常(萎缩/囊肿/肾实质病变)", "suspect": "肾实质性高血压(CKD)", "weight": 3},
    "药物相关": {"criteria": "NSAIDs/激素/口服避孕药/甘草/环孢素/促红细胞生成素用药史", "suspect": "药物诱发高血压", "weight": 2},
    "妊娠相关": {"criteria": "妊娠20周后新发高血压+蛋白尿", "suspect": "子痫前期", "weight": 4},
    "下肢血压差": {"criteria": "上肢高血压+下肢血压低/股动脉搏动弱", "suspect": "主动脉缩窄", "weight": 4},
}

_ETIOLOGY_WORKUP = {
    "PA": {
        "name": "原发性醛固酮增多症",
        "screening": "ARR (醛固酮/肾素比值): 立位2h后 ALD>10-15 ng/dL + PRA<1.0 → ARR>20-30 → 阳性",
        "prep": "停螺内酯/依普利酮≥4周, 停ACEi/ARB/β-blocker≥2周 (可换用维拉帕米+多沙唑嗪)",
        "confirmatory": ["生理盐水负荷试验 (输注2L NS后ALD>10 ng/dL → 确诊)",
                        "卡托普利试验 (25-50mg po, 2h后ALD>12 ng/dL → 确诊)", "氟氢可的松抑制试验"],
        "subtype": ["肾上腺CT (薄层 2-3mm) — 鉴别腺瘤vs增生",
                   "AVS (肾上腺静脉采血) — 金标准区分单侧vs双侧, 适合手术者",
                   "AVS判定: 患侧/对侧 ALD/Cortisol梯度≥4:1 → 优势侧"],
        "treatment": ["单侧腺瘤 → 腹腔镜肾上腺切除术", "双侧增生 → 盐皮质激素受体拮抗剂 (螺内酯/依普利酮)"],
        "target_organs": ["低钾血症", "代谢综合征", "心血管重塑", "心房颤动"],
    },
    "PHEO": {
        "name": "嗜铬细胞瘤/副神经节瘤",
        "screening": "血浆游离甲氧基肾上腺素(MN) + 甲氧基去甲肾上腺素(NMN) 或 24h尿 MN+NMN",
        "screening_positive": "MN或NMN > 正常上限3倍 → 直接确诊 | 1-3倍 → 加做可乐定抑制试验",
        "imaging": ["腹部CT(薄层) — 肾上腺占位>3cm", "MRI — 与CT互补, 嗜铬细胞瘤T2高信号", "MIBG/PET-CT — 定位副神经节瘤/多发/转移"],
        "pre_surgery_prep": ["α-阻滞剂(酚苄明/多沙唑嗪) ≥7-14天 — 必须! (防止术中高血压危象)",
                             "高盐饮食/充分水化 (抵消α阻滞后的血管床扩张/低血压)",
                             "β-阻滞剂 (仅用于α阻滞后仍有反射性心动过速, 绝对不能先用β! → 可诱发高血压危象)"],
        "treatment": ["腹腔镜肾上腺切除术", "术后24-48h严密监护 (低血糖/低血压风险)"],
        "genetic": ["RET/MEN2, VHL, NF1, SDHx — 30%为遗传性 → 建议基因检测"],
    },
    "RAS": {
        "name": "肾动脉狭窄",
        "screening": "肾动脉超声(Doppler) — 首选无创筛查 (PSV>180cm/s, RAR>3.5 → 狭窄>60%)",
        "imaging": ["CTA — 金标准 (注意造影剂肾病风险!)", "MRA — 无辐射/无碘造影剂 (GFR<30禁用钆!)", "DSA — 确诊+可同时介入治疗"],
        "clinical_clues": ["ACEI/ARB后SCr升高>30% (高特异性!)",
                          "腹部血管杂音(上腹部/腰部收缩期)", "不对称肾萎缩 (>1.5cm差别)",
                          "肺水肿Flash (反复发作的急性肺水肿)"],
        "treatment": ["动脉粥样硬化性RAS→ 优化药物治疗(抗血小板+他汀+控制血压)", "Fibromuscular dysplasia → 球囊血管成形术(年轻女性)",
                     "支架植入: 难治性HTN+进行性肾功能恶化+反复肺水肿"],
    },
    "CUSHING": {
        "name": "库欣综合征",
        "screening": ["1mg地塞米松抑制试验 (DST): 午夜1mg DEX, 次晨8am 皮质醇>1.8 μg/dL → 阳性",
                      "24h尿游离皮质醇(UFC) > 正常上限", "深夜唾液皮质醇 > 正常上限 2次"],
        "imaging": ["肾上腺CT — 腺瘤/增生/癌", "垂体MRI — 鞍区占位 (库欣病)"],
        "treatment": ["库欣病(垂体) → 经蝶手术", "肾上腺腺瘤 → 腹腔镜切除", "异位ACTH → 查找原发肿瘤"],
    },
}


# ═══════ ARR Interpretation ═══════

def _interpret_arr(aldosterone: float, renin_pra: float, renin_drc: float | None,
                   post_captopril_ald: float | None, potassium: float) -> dict:
    """ARR (醛固酮/肾素比值) 综合解读."""

    pra_or_drc = ""
    arr = 0.0
    if renin_pra > 0:
        arr = aldosterone / renin_pra
        pra_or_drc = f"PRA={renin_pra:.2f}"
    elif renin_drc and renin_drc > 0:
        arr = aldosterone / (renin_drc / 12)  # approximate conversion DRC→PRA
        pra_or_drc = f"DRC={renin_drc:.1f} mU/L"

    # PA screening interpretation
    pa_suspected = False
    pa_confidence = ""
    if renin_pra > 0:
        if arr > 30 and aldosterone > 15:
            pa_suspected = True
            pa_confidence = "高度提示原醛症 (ARR>30且ALD>15 ng/dL)"
        elif arr > 20 and aldosterone > 10:
            pa_suspected = True
            pa_confidence = "提示原醛症可能 (ARR>20且ALD>10 ng/dL)"
    elif renin_drc and renin_drc > 0:
        if arr > 3.7 and aldosterone > 10:
            pa_suspected = True
            pa_confidence = "高度提示原醛症 (DRC法 ARR>3.7)"

    # Medication interference warnings
    interferences = []
    if renin_pra < 1.0:
        interferences.append("肾素抑制: PRA很低 — β-blocker/NSAIDs可降低PRA致假阳性ARR")
    if potassium < 3.5:
        interferences.append(f"低钾血症(K={potassium})可抑制醛固酮分泌 → 假阴性! 需先纠正K至≥4.0再检测")

    return {
        "arr": round(arr, 1), "aldosterone": aldosterone, "renin": pra_or_drc,
        "pa_suspected": pa_suspected, "pa_confidence": pa_confidence,
        "medication_interferences": interferences,
        "next_step": ("卡托普利确证试验 或 生理盐水负荷试验" if pa_suspected
                       else "复查ARR(纠正K+停干扰药物后)" if renin_pra < 1 and aldosterone > 10
                       else "原醛症筛查阴性, 评估其他继发原因"),
    }


# ═══════ Handler Functions ═══════


def high_risk_pattern(patient_id: str = "", **kwargs: Any) -> dict:
    """继发性高血压高危特征识别 — 13种模式 + 病因指向."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    age = p.get("age", 50)
    dx = str(p.get("diagnosis", "")).lower()
    labs = p.get("lab_results", {}) or {}
    potassium = float(labs.get("k", 4.0) or labs.get("potassium", 4.0) or 4.0)
    creatinine = float(labs.get("creatinine", 1.0) or labs.get("cr", 1.0) or 1.0)
    renin_pra = float(labs.get("renin_pra", 5.0) or 5.0)
    meds = kwargs.get("medications", [])

    matched = []
    total_score = 0
    etiology_hints: dict[str, int] = {}

    # Age < 40
    if age < 40:
        matched.append({"pattern": _HIGH_RISK_PATTERNS["早发高血压"], "matched": True})
        total_score += 3

    # Resistant HTN
    if any(kw in dx for kw in ["难治", "refractory", "resistant", "顽固"]):
        matched.append({"pattern": _HIGH_RISK_PATTERNS["难治性高血压"], "matched": True})
        total_score += 3
        etiology_hints["RAS"] = etiology_hints.get("RAS", 0) + 2
        etiology_hints["PA"] = etiology_hints.get("PA", 0) + 2
        etiology_hints["OSA"] = etiology_hints.get("OSA", 0) + 1

    # Low potassium → PA
    if potassium < 3.5:
        matched.append({"pattern": _HIGH_RISK_PATTERNS["低血钾"], "matched": True})
        total_score += 4
        etiology_hints["PA"] = etiology_hints.get("PA", 0) + 4

    # Adrenal incidentaloma
    if kwargs.get("adrenal_incidentaloma", False) or "肾上腺占位" in dx or "adrenal" in dx:
        matched.append({"pattern": _HIGH_RISK_PATTERNS["肾上腺占位"], "matched": True})
        total_score += 4
        etiology_hints["PHEO"] = etiology_hints.get("PHEO", 0) + 2
        etiology_hints["PA"] = etiology_hints.get("PA", 0) + 2
        etiology_hints["CUSHING"] = etiology_hints.get("CUSHING", 0) + 1

    # Paroxysmal triad → PHEO
    symptoms = kwargs.get("symptoms", "").lower() + " " + dx
    if all(kw in symptoms for kw in ["头痛", "心悸"]) and ("出汗" in symptoms or "阵发" in symptoms or "flush" in symptoms):
        matched.append({"pattern": _HIGH_RISK_PATTERNS["阵发性三联征"], "matched": True})
        total_score += 5
        etiology_hints["PHEO"] = etiology_hints.get("PHEO", 0) + 5

    # ACEi/ARB worsening
    if "ACEi加" in dx or "ARB加" in dx or "creatinine rise" in dx.lower():
        matched.append({"pattern": _HIGH_RISK_PATTERNS["肾功能恶化_ACEi"], "matched": True})
        total_score += 4
        etiology_hints["RAS"] = etiology_hints.get("RAS", 0) + 4

    # Low renin
    if renin_pra < 1.0:
        matched.append({"pattern": _HIGH_RISK_PATTERNS["低肾素高血压"], "matched": True})
        total_score += 3
        etiology_hints["PA"] = etiology_hints.get("PA", 0) + 3

    # Cushingoid features
    if any(kw in symptoms for kw in ["满月脸", "水牛背", "紫纹", "centripetal", "向心性", "cushingoid"]):
        matched.append({"pattern": _HIGH_RISK_PATTERNS["向心性肥胖特征"], "matched": True})
        total_score += 4
        etiology_hints["CUSHING"] = etiology_hints.get("CUSHING", 0) + 4

    # Drug-induced
    offending_meds = ["nsaids", "nsaid", "steroid", "激素", "ocp", "避孕药", "环孢素", "epo"]
    if any(any(om in str(m).lower() for om in offending_meds) for m in meds):
        matched.append({"pattern": _HIGH_RISK_PATTERNS["药物相关"], "matched": True})
        total_score += 2
        etiology_hints["DRUG"] = etiology_hints.get("DRUG", 0) + 2

    # Risk level
    if total_score >= 8:
        level = "极高危"
        urgency = "紧急 — 2周内完成筛查"
    elif total_score >= 5:
        level = "高危"
        urgency = "优先 — 1个月内完成筛查"
    elif total_score >= 3:
        level = "中危"
        urgency = "常规 — 3个月内完成筛查"
    else:
        level = "低危"
        urgency = "原发性高血压可能性大, 常规随访"

    # Top etiology suspects
    top_etiology = sorted(etiology_hints.items(), key=lambda x: -x[1])[:3]
    top_etiology_names = [f"{_ETIOLOGY_WORKUP[e]['name']} (得分{score})"
                         for e, score in top_etiology if e in _ETIOLOGY_WORKUP]

    return {
        "status": "ok",
        "patient_id": patient_id,
        "risk_level": level,
        "total_score": total_score,
        "urgency": urgency,
        "matched_patterns": [m["pattern"]["criteria"] for m in matched],
        "primary_etiology_suspects": top_etiology_names,
        "etiology_scores": {_ETIOLOGY_WORKUP.get(e, {}).get("name", e): s
                           for e, s in sorted(etiology_hints.items(), key=lambda x: -x[1])},
        "summary": f"继发性高血压筛查 — {level} (得分{total_score}) | 转诊{urgency}",
        "recommendation": ("高度怀疑继发性高血压 — 立即启动病因筛查 (ARR+MNs+肾动脉+DST)"
                          if total_score >= 5 else "原发性高血压可能性大, 优化药物治疗后若仍不达标再筛查"),
    }


def screening_recommend(patient_id: str = "", risk_pattern: dict | None = None,
                        **kwargs: Any) -> dict:
    """病因导向的筛查检查推荐 — PA/PHEO/RAS/Cushing 四条路径."""
    p, err = _get_patient({"patient_id": patient_id})
    risk_pattern = risk_pattern or {}

    tests = ["基础: 电解质(K/Na)+肾功能(Cr/eGFR)+尿常规+肾脏超声"]
    specific_tests: list[dict] = []
    etiology = risk_pattern.get("etiology_scores", {})

    # PA path
    if "原醛" in str(etiology) or "PA" in str(etiology):
        pa_workup = _ETIOLOGY_WORKUP["PA"]
        specific_tests.append({
            "etiology": "原发性醛固酮增多症",
            "screening": pa_workup["screening"],
            "preparation": pa_workup["prep"],
            "confirmatory": pa_workup["confirmatory"],
            "note": "ARR是最关键的一线筛查! 正常值不能排除PA (部分PA醛固酮不高)",
        })

    # PHEO path
    if "嗜铬" in str(etiology) or "PHEO" in str(etiology):
        pheo = _ETIOLOGY_WORKUP["PHEO"]
        specific_tests.append({
            "etiology": "嗜铬细胞瘤",
            "screening": pheo["screening"],
            "positive_threshold": pheo["screening_positive"],
            "note": "假阳性: 急性疾病/药物(TCAs/β-blocker)/心衰 → 注意排除干扰",
        })

    # RAS path
    if "肾动脉" in str(etiology) or "RAS" in str(etiology):
        ras = _ETIOLOGY_WORKUP["RAS"]
        specific_tests.append({
            "etiology": "肾动脉狭窄",
            "screening": ras["screening"],
            "imaging": ras["imaging"],
            "note": "CTA: 注意造影剂肾病风险 (eGFR<30慎用), MRA: eGFR<30禁用钆对比剂",
        })

    # Cushing path
    if "库欣" in str(etiology) or "CUSHING" in str(etiology):
        cush = _ETIOLOGY_WORKUP["CUSHING"]
        specific_tests.append({
            "etiology": "库欣综合征",
            "screening": cush["screening"],
            "note": "1mg DST最常用, 注意假阳性(肥胖/抑郁/慢性病/口服雌激素)和假阴性(周期性库欣)",
        })

    return {
        "status": "ok",
        "patient_id": patient_id,
        "basic_tests": tests,
        "etiology_specific_tests": specific_tests,
        "total_pathways": len(specific_tests),
        "summary": f"建议{len(tests)}基础检查 + {len(specific_tests)}条病因路径",
    }


def referral_decision(patient_id: str = "", screening_results: dict | None = None,
                      facility_level: str = "primary",
                      **kwargs: Any) -> dict:
    """转诊决策 — 基于筛查结果的分级转诊 + 病因导向治疗."""
    p, err = _get_patient({"patient_id": patient_id})
    screening_results = screening_results or {}

    score = screening_results.get("total_score", 0)
    etiology = screening_results.get("etiology_scores", {})

    referral = ""
    urgency = ""
    rationale = ""

    if score >= 8:
        referral = "紧急转诊 — 内分泌科/高血压专科 (住院筛查)"
        urgency = "紧急 — 1周内安排"
        rationale = "≥8分 — 继发性高血压高危, 部分病因为可治愈性(手术/介入)"
    elif score >= 5:
        referral = "优先转诊 — 内分泌科高血压专科门诊"
        urgency = "优先 — 2-4周内就诊"
        rationale = "5-7分 — 继发性高血压中危, 建议专科评估"
    elif score >= 3:
        if facility_level == "primary":
            referral = "转诊 — 县级医院内科/内分泌科"
            urgency = "常规 — 1-3月内"
            rationale = "3-4分 — 基层难以完成专科检查, 建议上级医院评估"
        else:
            referral = "门诊随访 — 优化药物治疗, 3月后评估"
            urgency = "常规"
            rationale = "3-4分 — 二级医院可先行ARR+MNs筛查"
    else:
        referral = "社区/基层管理 — 优化降压方案"
        urgency = "常规 — 6-12月随访"
        rationale = "0-2分 — 原发性高血压可能性大"

    # Specific treatment hints
    treatment_hints = []
    if "原醛" in str(etiology):
        treatment_hints.append("若确诊单侧PA → 腹腔镜肾上腺切除术 (可治愈性高血压)")
        treatment_hints.append("双侧PA → 螺内酯/依普利酮 长期口服")
    if "嗜铬" in str(etiology):
        treatment_hints.append("若确诊嗜铬细胞瘤 → 术前α阻滞 ≥7-14天 → 腹腔镜切除")
    if "肾动脉" in str(etiology):
        treatment_hints.append("若确诊RAS → FMD(年轻女性)→球囊成形术 vs AS→优化药物±支架")
    if "库欣" in str(etiology):
        treatment_hints.append("若确诊库欣综合征 → 病因导向手术(肾上腺/垂体/异位)")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "facility_level": facility_level,
        "risk_score": score,
        "referral_decision": referral,
        "urgency": urgency,
        "rationale": rationale,
        "treatment_hints": treatment_hints,
        "pre_referral_prep": [
            "停用干扰ARR药物≥2-4周 (换用维拉帕米+多沙唑嗪)",
            "纠正低钾血症 (K≥4.0 mmol/L)",
            "完善基础检查: 电解质/肾功能/肾脏超声",
        ] if score >= 5 else [],
        "summary": f"转诊决策 — {referral[:40]} | {urgency}",
    }
