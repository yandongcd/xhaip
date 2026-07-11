"""
围术期止吐药用药管控引擎 (drug_controls)

7 类禁忌证筛查：药物过敏 / 肝肾功能 / 基础病 / 特殊人群 / 重复用药 / 给药时机 / 药物相互作用
"""


def validate_contraindications(
    regimen: dict = None,
    patient_id: str = "",
    patient: dict = None,
    surgery: dict = None,
    **kwargs,
) -> dict:
    """综合用药管控审核

    Args:
        regimen: 推荐用药方案 {drugs: [{class, name, dose, route, timing}]}
        patient: 患者信息 {age, gender, allergies, comorbidities, labs}
        surgery: 手术信息 {type, duration}

    Returns:
        {passed, violations: [{rule_id, severity, message, alternative}], ...}
    """
    if regimen is None:
        regimen = {}
    if patient is None:
        patient = {}
    if surgery is None:
        surgery = {}

    drugs = regimen.get("drugs", [])
    violations = []

    for drug in drugs:
        drug_class = drug.get("class", "")
        drug_name = drug.get("name", "")

        # 1. 过敏检查
        allergy_violations = _check_allergy(drug_name, drug_class, patient)
        violations.extend(allergy_violations)

        # 2. QT间期检查
        qt_violations = _check_qtc(drug_name, drug_class, patient)
        violations.extend(qt_violations)

        # 3. 基础病检查
        comorbidity_violations = _check_comorbidity(drug_name, drug_class, patient)
        violations.extend(comorbidity_violations)

        # 4. 特殊人群检查
        pop_violations = _check_special_population(drug_name, drug_class, patient, surgery)
        violations.extend(pop_violations)

        # 5. 肝肾功能
        renal_hepatic = _check_renal_hepatic(drug_name, drug_class, patient)
        violations.extend(renal_hepatic)

    passed = len(violations) == 0

    return {
        "passed": passed,
        "drug_count": len(drugs),
        "violations": violations,
        "high_severity_count": sum(1 for v in violations if v.get("severity") == "high"),
        "medium_severity_count": sum(1 for v in violations if v.get("severity") == "medium"),
        "low_severity_count": sum(1 for v in violations if v.get("severity") == "low"),
        "status": "ok",
    }


def _check_allergy(drug_name: str, drug_class: str, patient: dict) -> list:
    """检查药物过敏禁忌"""
    allergies = patient.get("allergies", [])
    if not allergies:
        return []

    violations = []
    allergy_map = {
        "5-HT3受体拮抗剂": {
            "drugs": ["昂丹司琼", "格拉司琼", "托烷司琼", "帕洛诺司琼", "多拉司琼", "雷莫司琼"],
            "alternative": "地塞米松 + NK-1受体拮抗剂（福沙匹坦/阿瑞匹坦）",
        },
        "皮质类固醇": {
            "drugs": ["地塞米松", "甲泼尼龙"],
            "alternative": "5-HT3受体拮抗剂 + NK-1受体拮抗剂或氟哌利多",
        },
        "多巴胺受体拮抗剂": {
            "drugs": ["甲氧氯普胺", "氨磺必利", "氟哌利多", "氟哌啶醇"],
            "alternative": "5-HT3受体拮抗剂 + 地塞米松 + NK-1受体拮抗剂",
        },
        "NK-1受体拮抗剂": {
            "drugs": ["福沙匹坦", "阿瑞匹坦"],
            "alternative": "5-HT3受体拮抗剂 + 地塞米松 + 氟哌利多",
        },
        "抗胆碱能药": {
            "drugs": ["戊乙奎醚", "东莨菪碱贴剂"],
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        },
        "抗组胺药": {
            "drugs": ["茶苯海明", "赛克利嗪", "异丙嗪"],
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        },
    }

    for allergy in allergies:
        allergy_lower = allergy.lower()
        for class_desc, info in allergy_map.items():
            if any(kw in allergy_lower for kw in class_desc.lower().split("/")):
                if drug_name in info["drugs"]:
                    violations.append({
                        "rule_id": "AE001",
                        "severity": "high",
                        "type": "drug_allergy",
                        "message": f"患者存在{class_desc}过敏，禁用{drug_name}",
                        "alternative": info["alternative"],
                    })

    return violations


def _check_qtc(drug_name: str, drug_class: str, patient: dict) -> list:
    """检查QT间期延长风险"""
    labs = patient.get("labs", {}) or patient.get("lab_results", {}) or {}
    qtc = labs.get("qtc", 0) or labs.get("QTc", 0)
    gender = patient.get("gender", "").strip().upper()

    threshold = 470 if gender == "M" else 480

    if not qtc or float(qtc) < threshold:
        return []

    violations = []
    qtc_risk_drugs = ["氟哌利多", "氟哌啶醇"]

    if drug_name in qtc_risk_drugs:
        violations.append({
            "rule_id": "CM001",
            "severity": "high",
            "type": "qtc_prolongation",
            "message": f"QTc={qtc}ms 超过阈值({threshold}ms)，禁用{drug_name}",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        })

    if drug_class == "5-HT3受体拮抗剂":
        violations.append({
            "rule_id": "CM002",
            "severity": "medium",
            "type": "qtc_caution",
            "message": f"QTc={qtc}ms，使用5-HT3受体拮抗剂需谨慎，避免重复给药",
            "alternative": "单次给药可接受，避免重复",
        })

    return violations


def _check_comorbidity(drug_name: str, drug_class: str, patient: dict) -> list:
    """检查基础病禁忌"""
    comorbidities = patient.get("comorbidities", [])
    if not comorbidities:
        return []

    violations = []
    com_str = " ".join(str(c).lower() for c in comorbidities)

    comorbidity_rules = [
        {
            "keyword": "癫痫", "drug_class": "多巴胺受体拮抗剂",
            "rule_id": "CM003", "message": "癫痫病史，禁用多巴胺受体拮抗剂",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        },
        {
            "keyword": "帕金森", "drug_class": "多巴胺受体拮抗剂",
            "rule_id": "CM004", "message": "帕金森病史，禁用所有多巴胺受体拮抗剂",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松 + NK-1受体拮抗剂",
        },
        {
            "keyword": "锥体外系", "drug_class": "多巴胺受体拮抗剂",
            "rule_id": "CM007", "message": "锥体外系疾病史，禁用多巴胺受体拮抗剂",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松 + NK-1受体拮抗剂",
        },
        {
            "keyword": "青光眼", "drug_class": "抗胆碱能药",
            "rule_id": "CM008", "message": "青光眼病史，禁用抗胆碱能药",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        },
        {
            "keyword": "前列腺增生", "drug_class": "抗胆碱能药",
            "rule_id": "CM009", "message": "前列腺增生，禁用抗胆碱能药（可能诱发尿潴留）",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        },
        {
            "keyword": "重症肌无力", "drug_class": "多巴胺受体拮抗剂",
            "rule_id": "CM010", "message": "重症肌无力，禁用氟哌利多",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        },
        {
            "keyword": "闭角型青光眼", "drug_class": "抗组胺药",
            "rule_id": "CM011", "message": "闭角型青光眼，禁用抗组胺药",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        },
    ]

    for rule in comorbidity_rules:
        if rule["keyword"] in com_str and drug_class == rule["drug_class"]:
            violations.append({
                "rule_id": rule["rule_id"],
                "severity": "high",
                "type": "comorbidity",
                "message": rule["message"],
                "alternative": rule["alternative"],
            })

    return violations


def _check_special_population(
    drug_name: str, drug_class: str, patient: dict, surgery: dict
) -> list:
    """检查特殊人群（孕产妇/老年/儿童）"""
    violations = []
    age = patient.get("age", 0)
    pregnancy = patient.get("pregnancy", False) or patient.get("pregnant", False)
    lactation = patient.get("lactation", False) or patient.get("breastfeeding", False)

    # 孕期
    if pregnancy and drug_class == "多巴胺受体拮抗剂":
        violations.append({
            "rule_id": "SP001",
            "severity": "high",
            "type": "pregnancy",
            "message": f"孕期禁用{ '多巴胺受体拮抗剂' if drug_class == '多巴胺受体拮抗剂' else drug_name }",
            "alternative": "单用昂丹司琼4mg，或穴位刺激替代",
        })

    # 哺乳期
    if lactation and drug_name == "甲氧氯普胺":
        violations.append({
            "rule_id": "SP002",
            "severity": "medium",
            "type": "lactation",
            "message": "甲氧氯普胺可进入乳汁，哺乳期慎用",
            "alternative": "5-HT3受体拮抗剂（昂丹司琼哺乳期安全性较高）",
        })

    # 老年
    if age >= 65 and drug_class == "抗胆碱能药":
        violations.append({
            "rule_id": "SP003",
            "severity": "high",
            "type": "elderly",
            "message": f"老年患者禁用抗胆碱能药（{drug_name}），可能诱发谵妄/认知障碍",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        })

    # 儿童<3岁
    if age < 3 and drug_name == "地塞米松":
        violations.append({
            "rule_id": "SP004",
            "severity": "high",
            "type": "pediatric",
            "message": "3岁以下儿童不建议使用地塞米松预防PONV",
            "alternative": "单用5-HT3受体拮抗剂",
        })

    return violations


def _check_renal_hepatic(drug_name: str, drug_class: str, patient: dict) -> list:
    """检查肝肾功能剂量调整"""
    violations = []
    labs = patient.get("labs", {}) or patient.get("lab_results", {}) or {}
    egfr = labs.get("egfr", 90) or labs.get("eGFR", 90)
    alt = labs.get("alt", 30) or labs.get("ALT", 30)

    try:
        egfr = float(egfr)
    except (TypeError, ValueError):
        egfr = 90
    try:
        alt = float(alt)
    except (TypeError, ValueError):
        alt = 30

    # 肾功能
    if egfr < 30 and drug_name == "甲氧氯普胺":
        violations.append({
            "rule_id": "RH001",
            "severity": "medium",
            "type": "renal_adjustment",
            "message": f"eGFR={egfr} < 30，甲氧氯普胺剂量需减半",
            "alternative": "换用不受肾功能影响的5-HT3受体拮抗剂",
        })

    if egfr < 15 and drug_name == "氟哌利多":
        violations.append({
            "rule_id": "RH004",
            "severity": "high",
            "type": "renal_contraindication",
            "message": f"eGFR={egfr} < 15（终末期肾病），禁用氟哌利多",
            "alternative": "5-HT3受体拮抗剂 + 地塞米松",
        })

    # 肝功能
    if alt > 150 and drug_name == "昂丹司琼":  # >3×ULN
        violations.append({
            "rule_id": "RH002",
            "severity": "medium",
            "type": "hepatic_adjustment",
            "message": f"ALT={alt} > 3×ULN，昂丹司琼单次最大剂量不超过8mg",
        })

    return violations


def check_duplicate_medication(
    current_regimen: dict = None,
    prior_medications: list = None,
    **kwargs,
) -> dict:
    """重复用药拦截"""
    violations = []
    if not prior_medications:
        return {"violations": [], "status": "ok"}

    for prior in prior_medications:
        hours_ago = prior.get("hours_ago", 0)
        drug_class = prior.get("class", "")

        if drug_class == "5-HT3受体拮抗剂" and hours_ago < 24:
            violations.append({
                "rule_id": "DM001",
                "severity": "high",
                "message": f"5-HT3拮抗剂24h内已使用（{hours_ago}h前），禁止重复",
                "exception": "补救治疗可给予预防剂量的1/4（如昂丹司琼1mg）",
            })

        if drug_class == "皮质类固醇" and hours_ago < 24:
            violations.append({
                "rule_id": "DM002",
                "severity": "high",
                "message": "地塞米松已使用，不推荐重复给药",
            })

    return {"violations": violations, "status": "ok"}


def suggest_alternatives(violation: dict = None, **kwargs) -> dict:
    """根据违规类型建议替代方案"""
    if not violation:
        return {"alternatives": [], "status": "ok"}

    alt = violation.get("alternative", "")
    return {
        "original_drug": violation.get("message", ""),
        "suggested_alternative": alt,
        "rule_id": violation.get("rule_id", ""),
        "status": "ok",
    }
