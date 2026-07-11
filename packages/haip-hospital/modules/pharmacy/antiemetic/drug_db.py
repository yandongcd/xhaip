"""
止吐药数据库 (drug_db)

扩展药剂科现有 drug_db.py，提供围术期止吐药专用查询接口
"""


# 21 种止吐药核心元数据（精简版，完整数据在 knowledge/guideline_sources/drug_db_antiemetic.yaml）
ANTIEMETIC_DRUGS = [
    # 5-HT3 受体拮抗剂 (第一代)
    {
        "id": "ondansetron", "name": "昂丹司琼", "class": "5-HT3受体拮抗剂",
        "generation": 1, "half_life_h": 4, "adult_dose": "4mg IV", "pediatric_dose": "0.05-0.1mg/kg IV",
        "timing": "手术结束前", "route": ["IV", "PO"],
        "contraindications": ["QTc延长谨慎重复"], "evidence": "R11.1",
    },
    {
        "id": "granisetron", "name": "格拉司琼", "class": "5-HT3受体拮抗剂",
        "generation": 1, "half_life_h": 5, "adult_dose": "1mg IV", "pediatric_dose": "0.04mg/kg IV",
        "timing": "手术结束前", "route": ["IV", "PO"],
        "contraindications": ["QTc延长谨慎"], "evidence": "R11.1",
    },
    {
        "id": "tropisetron", "name": "托烷司琼", "class": "5-HT3受体拮抗剂",
        "generation": 1, "half_life_h": 10, "adult_dose": "5mg IV",
        "timing": "手术结束前30min", "route": ["IV", "PO"],
        "contraindications": ["QTc延长谨慎"], "evidence": "R11.1",
        "note": "结构最接近5-HT，更具特异性",
    },
    {
        "id": "dolasetron", "name": "多拉司琼", "class": "5-HT3受体拮抗剂",
        "generation": 1, "half_life_h": 7, "adult_dose": "12.5mg IV",
        "timing": "手术结束前", "route": ["IV", "PO"],
        "contraindications": ["QTc延长谨慎"], "evidence": "R11.1",
    },
    # 5-HT3 受体拮抗剂 (第二代)
    {
        "id": "palonosetron", "name": "帕洛诺司琼", "class": "5-HT3受体拮抗剂",
        "generation": 2, "half_life_h": 40, "adult_dose": "0.075mg IV",
        "timing": "麻醉诱导前", "route": ["IV"],
        "contraindications": ["QTc延长谨慎"], "evidence": "R11.3",
        "note": "长效40h，代谢不受肝肾影响",
    },
    {
        "id": "ramosetron", "name": "雷莫司琼", "class": "5-HT3受体拮抗剂",
        "generation": 2, "half_life_h": 7, "adult_dose": "0.3mg IV",
        "timing": "手术结束前", "route": ["IV"],
        "contraindications": ["QTc延长谨慎"], "evidence": "R11.1",
    },
    # 皮质类固醇
    {
        "id": "dexamethasone", "name": "地塞米松", "class": "皮质类固醇",
        "half_life_h": 36, "adult_dose": "4-8mg IV", "pediatric_dose": "0.15mg/kg (≥3岁)",
        "timing": "麻醉诱导后", "route": ["IV"],
        "contraindications": ["糖尿病监测血糖", "高血压SBP>160谨慎", "儿童<3岁禁忌"],
        "evidence": "R12.1",
    },
    # NK-1 受体拮抗剂
    {
        "id": "fosaprepitant", "name": "福沙匹坦", "class": "NK-1受体拮抗剂",
        "half_life_h": 9, "adult_dose": "150mg IV",
        "timing": "麻醉诱导前", "route": ["IV"],
        "contraindications": ["肝功能严重不全谨慎"], "evidence": "R13",
        "note": "单药预防POV效果最佳",
    },
    {
        "id": "aprepitant", "name": "阿瑞匹坦", "class": "NK-1受体拮抗剂",
        "half_life_h": 9, "adult_dose": "40mg PO",
        "timing": "术前1-3h", "route": ["PO"],
        "contraindications": ["肝功能严重不全谨慎"], "evidence": "R13",
    },
    # 多巴胺受体拮抗剂
    {
        "id": "amisulpride", "name": "氨磺必利", "class": "多巴胺受体拮抗剂",
        "half_life_h": 12, "adult_dose": "5mg IV",
        "timing": "麻醉诱导时", "route": ["IV"],
        "contraindications": ["帕金森病", "锥体外系疾病", "严重肝病"],
        "evidence": "R14.1",
    },
    {
        "id": "droperidol", "name": "氟哌利多", "class": "多巴胺受体拮抗剂",
        "half_life_h": 2.5, "adult_dose": "0.625mg IV",
        "timing": "手术结束前", "route": ["IV"],
        "contraindications": ["QTc延长", "低钾", "低镁", "帕金森病", "重症肌无力"],
        "evidence": "R14.3",
    },
    {
        "id": "metoclopramide", "name": "甲氧氯普胺", "class": "多巴胺受体拮抗剂",
        "half_life_h": 5, "adult_dose": "10mg IV",
        "timing": "手术结束前", "route": ["IV", "PO"],
        "contraindications": ["癫痫", "帕金森病", "eGFR<30减半"],
        "evidence": "R14",
        "note": "10mg止吐功效不明确",
    },
    # 抗胆碱能药
    {
        "id": "penehyclidine", "name": "戊乙奎醚", "class": "抗胆碱能药",
        "half_life_h": 10, "adult_dose": "0.01mg/kg (最大0.5mg)",
        "timing": "麻醉诱导后", "route": ["IV"],
        "contraindications": ["青光眼", "前列腺增生", "年龄≥65岁", "谵妄病史"],
        "evidence": "R15",
    },
    # 抗组胺药
    {
        "id": "dimenhydrinate", "name": "茶苯海明", "class": "抗组胺药",
        "half_life_h": 5, "adult_dose": "50mg IV/PO",
        "timing": "手术结束前", "route": ["IV", "PO"],
        "contraindications": ["闭角型青光眼", "癫痫", "重症肌无力"],
        "evidence": "R16",
        "note": "剖宫产患者推荐",
    },
]


def search_drug(keyword: str = "", drug_class: str = "", **kwargs) -> dict:
    """查询止吐药品

    Args:
        keyword: 药品名称关键词（支持中英文）
        drug_class: 药物类别

    Returns:
        {results: [...]}
    """
    results = []
    keyword_lower = keyword.lower() if keyword else ""

    for drug in ANTIEMETIC_DRUGS:
        name_match = keyword_lower in drug["name"].lower() or keyword_lower in drug.get("id", "")
        class_match = not drug_class or drug_class in drug.get("class", "")

        if name_match and class_match:
            results.append(drug)

    if not keyword_lower and not drug_class:
        results = ANTIEMETIC_DRUGS

    return {
        "results": results,
        "total": len(results),
        "drug_classes": list(set(d["class"] for d in results)),
        "status": "ok",
    }


def get_drug_profile(drug_name: str = "", **kwargs) -> dict:
    """获取单个药品完整资料"""
    for drug in ANTIEMETIC_DRUGS:
        if drug_name in (drug["name"], drug["id"]):
            return {"drug": drug, "status": "ok"}

    return {"drug": None, "status": "not_found", "message": f"未找到药品: {drug_name}"}


def list_drug_classes(**kwargs) -> dict:
    """列出所有止吐药类别"""
    classes = sorted(set(d["class"] for d in ANTIEMETIC_DRUGS))
    return {
        "classes": classes,
        "total": len(classes),
        "total_drugs": len(ANTIEMETIC_DRUGS),
        "status": "ok",
    }
