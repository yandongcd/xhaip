"""Patient Data Generator — Auto-generate digital patients for all departments.

Maps department types to common diseases and lab patterns.
Extends existing patients.json with department-specific patients.
"""

from __future__ import annotations

import json
import random

random.seed(42)

# 科室 → 常见诊断列表
_DIAGNOSES: dict[str, list[str]] = {
    "respiratory": ["COPD急性加重", "支气管哮喘", "社区获得性肺炎", "肺栓塞", "间质性肺炎", "慢性咳嗽"],
    "gastroenterology": ["胃食管反流病", "慢性胃炎", "肝硬化", "胰腺炎", "结直肠息肉", "消化道出血"],
    "nephrology": ["慢性肾脏病3期", "肾病综合征", "IgA肾病", "急性肾损伤", "糖尿病肾病", "肾性贫血"],
    "hematology": ["缺铁性贫血", "急性白血病", "淋巴瘤", "多发性骨髓瘤", "骨髓增生异常综合征", "血小板减少"],
    "endocrinology": ["2型糖尿病", "甲状腺功能亢进", "甲状腺结节", "骨质疏松症", "高脂血症", "肥胖症"],
    "rheumatology": ["类风湿关节炎", "系统性红斑狼疮", "强直性脊柱炎", "干燥综合征", "痛风"],
    "infectious_disease": ["病毒性肝炎", "肺结核", "感染性腹泻", "脓毒症", "HIV/AIDS"],
    "oncology": ["肺癌", "胃癌", "肝癌", "乳腺癌", "结直肠癌", "食管癌"],
    "tcm": ["中风后遗症", "慢性胃炎", "失眠", "更年期综合征", "颈肩腰腿痛", "亚健康状态"],
    "geriatrics": ["老年衰弱综合征", "老年高血压", "老年认知障碍", "老年营养不良", "多重用药"],
    "general_surgery": ["急性阑尾炎", "胆囊结石", "腹股沟疝", "肠梗阻", "甲状腺肿瘤", "胃溃疡穿孔"],
    "hepatobiliary_surgery": ["肝细胞癌", "肝内胆管结石", "胆囊癌", "胰腺导管癌", "门静脉高压"],
    "neurosurgery": ["脑胶质瘤", "颅脑损伤", "高血压脑出血", "脑动脉瘤", "椎管内肿瘤"],
    "thoracic_surgery": ["肺结节", "食管癌", "纵隔肿瘤", "胸腺瘤", "气胸"],
    "vascular_surgery": ["下肢动脉硬化闭塞症", "腹主动脉瘤", "深静脉血栓", "颈动脉狭窄", "下肢静脉曲张"],
    "renal_transplant": ["终末期肾病", "移植肾功能延迟恢复", "移植肾排斥反应"],
    "breast_center": ["乳腺纤维腺瘤", "乳腺导管癌", "乳腺炎", "乳腺增生"],
    "burns_plastic": ["面部烧伤", "手部烧伤", "瘢痕挛缩", "皮肤软组织缺损"],
    "interventional_therapy": ["肝癌介入", "子宫肌瘤栓塞", "胆道梗阻", "咯血栓塞"],
    "obgyn": ["异位妊娠", "子宫肌瘤", "卵巢囊肿", "宫颈上皮内瘤变", "盆腔炎", "产前保健"],
    "neonatology": ["新生儿黄疸", "早产儿", "新生儿肺炎", "新生儿窒息", "低出生体重"],
    "ophthalmology": ["白内障", "青光眼", "糖尿病视网膜病变", "黄斑变性", "屈光不正"],
    "ent": ["慢性鼻窦炎", "过敏性鼻炎", "声带息肉", "中耳炎", "扁桃体肥大"],
    "stomatology": ["龋齿", "牙髓炎", "口腔溃疡", "牙周炎", "颌面部骨折"],
    "emergency": ["急性心肌梗死", "急性脑卒中", "多发伤", "过敏性休克", "中毒"],
    "icu": ["脓毒性休克", "ARDS", "多器官功能衰竭", "重症胰腺炎", "心脏骤停后综合征"],
    "dermatology": ["银屑病", "湿疹", "带状疱疹", "荨麻疹", "皮肤肿瘤"],
    "psychiatry": ["抑郁症", "焦虑障碍", "双相情感障碍", "精神分裂症", "睡眠障碍"],
    "rehabilitation": ["脑卒中康复", "骨折术后康复", "脊髓损伤康复", "心肺康复", "吞咽障碍"],
    "pain_management": ["腰椎间盘突出症", "带状疱疹后神经痛", "胰腺癌疼痛", "三叉神经痛", "纤维肌痛"],
    "health_mgmt": ["年度体检", "高血压随访", "糖尿病复查", "肿瘤筛查", "疫苗接种"],
}

# 通用检验指标模板
_LAB_TEMPLATES: dict[str, list[str]] = {
    "respiratory": ["WBC", "CRP", "PCT", "血气pH", "PaO2", "PaCO2", "FEV1"],
    "gastroenterology": ["ALT", "AST", "TBIL", "AMY", "LPS", "HBsAg", "HP抗体"],
    "nephrology": ["BUN", "Cr", "eGFR", "尿蛋白", "K+", "P", "Ca2+"],
    "hematology": ["Hb", "WBC", "PLT", "PT", "APTT", "铁蛋白", "叶酸"],
    "endocrinology": ["FPG", "HbA1c", "TSH", "FT3", "FT4", "TG", "LDL", "骨密度T值"],
    "general_surgery": ["WBC", "CRP", "Hb", "PT", "APTT", "ALT", "Cr"],
    "neurosurgery": ["CT", "MRI", "GCS评分", "ICP", "凝血功能"],
    "obgyn": ["hCG", "CA125", "HPV", "TCT", "Hb", "超声"],
    "emergency": ["Troponin", "D-Dimer", "血气", "乳酸", "GLU", "Cr"],
}


def _random_lab(diagnosis: str, dept_keys: list[str]) -> dict:
    """Generate realistic lab values based on diagnosis and department."""
    labs = {}
    for key in dept_keys:
        if "Hb" in key or "hb" in key.lower():
            labs[key] = round(random.uniform(80, 160), 1)
        elif "WBC" in key or "wbc" in key.lower():
            labs[key] = round(random.uniform(3.5, 18.0), 1)
        elif "CRP" in key or "crp" in key.lower():
            labs[key] = round(random.uniform(5, 200), 1)
        elif "Cr" in key or "BUN" in key:
            labs[key] = round(random.uniform(60, 300), 1)
        elif "ALT" in key:
            labs[key] = round(random.uniform(20, 200), 1)
        elif "GLU" in key or "FPG" in key:
            labs[key] = round(random.uniform(4.0, 15.0), 1)
        elif "K+" in key:
            labs[key] = round(random.uniform(3.0, 6.0), 1)
        elif key == "HbA1c":
            labs[key] = round(random.uniform(5.0, 12.0), 1)
        elif key == "TSH":
            labs[key] = round(random.uniform(0.1, 20.0), 2)
        elif key == "Troponin":
            labs[key] = round(random.uniform(0.01, 5.0), 3)
        elif key == "D-Dimer":
            labs[key] = round(random.uniform(0.2, 5.0), 2)
        else:
            labs[key] = round(random.uniform(1, 100), 1)
    return labs


def generate_patients(output_path: str = "") -> list[dict]:
    """Generate 5-8 patients per department with realistic data."""
    from haip.togaf.organization import list_orgs
    import yaml

    all_orgs = list_orgs()
    clinical = [o for o in all_orgs if o.type == "clinical" and o.parent]

    # Read existing patients to avoid duplicates
    from haip.patients import PATIENTS_FILE
    patients_file = PATIENTS_FILE
    existing_patients: list[dict] = []
    existing_ids: set[str] = set()
    existing_depts: set[str] = set()
    if patients_file.exists():
        with open(patients_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            existing = data.get("patients", [])
            for p in existing:
                existing_ids.add(p["patient_id"])
                dept = p.get("department", "")
                if dept:
                    existing_depts.add(dept)
            existing_patients = list(existing)

    new_patients: list[dict] = []
    pid_counter = 200  # Start after existing P001-P100

    for org in clinical:
        dept_name = org.name
        # Skip if already has patients
        if dept_name in existing_depts or org.id in existing_depts:
            continue

        diag_list = _DIAGNOSES.get(org.id, _DIAGNOSES.get(org.parent if hasattr(org, 'parent') else "", []))
        if not diag_list:
            diag_list = [f"{dept_name}常见病", f"{dept_name}待查"]

        labs_keys = _LAB_TEMPLATES.get(org.id, _LAB_TEMPLATES.get(org.parent if hasattr(org, 'parent') else "", ["Hb", "WBC", "Cr"]))
        if not labs_keys:
            labs_keys = ["Hb", "WBC", "Cr", "ALT", "GLU"]

        agent_name = _dept_to_agent(org.name)
        num_patients = min(8, max(4, len(diag_list)))

        for i in range(num_patients):
            pid_counter += 1
            diagnosis = diag_list[i % len(diag_list)]
            age = random.randint(18, 85)
            gender = random.choice(["M", "F"])
            weight = round(random.uniform(45, 95), 1)
            height = round(random.uniform(150, 185), 1)

            patient = {
                "patient_id": f"P{pid_counter}",
                "name": f"{random.choice('李王张刘陈杨赵黄周吴徐孙马胡朱郭何罗林')}*",
                "age": age,
                "gender": gender,
                "weight_kg": weight,
                "height_cm": height,
                "department": dept_name,
                "diagnosis": diagnosis,
                "scenario": f"{dept_name}诊疗",
                "lab_results": _random_lab(diagnosis, labs_keys),
                "compatible_agents": [agent_name, "medical-record"],
                "urgency": random.choice(["normal", "normal", "normal", "high"]),
            }
            new_patients.append(patient)

    # Merge with existing
    all_patients = existing_patients + new_patients
    result = {"total": len(all_patients), "patients": all_patients}

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return new_patients


def _dept_to_agent(org_name: str) -> str:
    known = {
        "呼吸内科": "respiratory", "消化内科": "gastroenterology", "肾内科": "nephrology",
        "血液内科": "hematology", "内分泌科": "endocrinology", "风湿免疫科": "rheumatology",
        "感染内科": "infectious-disease", "肿瘤科": "oncology", "中医科": "tcm",
        "老年病科": "geriatrics", "普通外科": "general-surgery", "肝胆外科": "hepatobiliary-surgery",
        "神经外科": "neurosurgery", "胸外科": "thoracic-surgery", "血管外科": "vascular-surgery",
        "肾移植科": "renal-transplant", "乳腺中心": "breast-center", "烧伤整形科": "burns-plastic",
        "介入治疗科": "interventional-therapy", "妇产科": "obgyn", "新生儿科": "neonatology",
        "眼科": "ophthalmology", "耳鼻喉科": "ent", "口腔科": "stomatology",
        "急诊科": "emergency", "重症医学科": "icu", "皮肤科": "dermatology",
        "精神心理科": "psychiatry", "康复医学科": "rehabilitation", "健康管理科": "health-management",
        "惠侨医疗中心": "huigiao", "整形美容科": "cosmetic-surgery",
    }
    return known.get(org_name, org_name.replace(" ", "-").lower())
