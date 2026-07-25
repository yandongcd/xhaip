"""Update all agent YAMLs with proper clinical workflow stages and role assignments."""
import pathlib
import yaml

YAML_DIR = pathlib.Path(r"D:\dst\projects\xhaip\packages\haip-hospital\agents\definitions")

# === Clinical workflow templates by department category ===

SURGICAL_STAGES = [
    {"order": 1, "id": "preop-eval", "label": "术前评估", "desc": "GCS/ASA评分、影像学评估、凝血功能、心肺功能筛查、麻醉评估",
     "role_ids": ["attending", "resident", "anesthesiologist"]},
    {"order": 2, "id": "preop-prep", "label": "术前准备", "desc": "备血交叉配血、预防性抗生素、深静脉穿刺、导尿、备皮",
     "role_ids": ["attending", "resident", "head_nurse"]},
    {"order": 3, "id": "surgery", "label": "手术执行", "desc": "术中监测、出血量评估、冰冻病理、器械清点",
     "role_ids": ["attending", "surgeon", "anesthesiologist", "instrument_nurse"]},
    {"order": 4, "id": "postop-icu", "label": "术后监护", "desc": "ICU监测、GCS追踪、ICP管理、引流管管理、电解质平衡",
     "role_ids": ["attending", "icu_doctor", "head_nurse"]},
    {"order": 5, "id": "ward-care", "label": "病房管理", "desc": "切口护理、活动指导、营养支持、VTE预防、疼痛管理",
     "role_ids": ["attending", "resident", "head_nurse"]},
    {"order": 6, "id": "followup", "label": "随访康复", "desc": "神经功能评分、康复计划制定、术后1/3/6月随访、影像复查",
     "role_ids": ["attending", "rehab_therapist", "head_nurse"]},
]

SURGICAL_ROLES = [
    {"id": "attending", "label": "主治医师", "default": True},
    {"id": "resident", "label": "住院医师"},
    {"id": "surgeon", "label": "手术医师"},
    {"id": "anesthesiologist", "label": "麻醉医师"},
    {"id": "icu_doctor", "label": "ICU医师"},
    {"id": "head_nurse", "label": "护士长"},
    {"id": "instrument_nurse", "label": "器械护士"},
    {"id": "rehab_therapist", "label": "康复师"},
]

MEDICAL_STAGES = [
    {"order": 1, "id": "reception", "label": "接诊登记", "desc": "主诉采集、现病史、既往史、过敏史、体格检查",
     "role_ids": ["attending", "resident", "head_nurse"]},
    {"order": 2, "id": "exam", "label": "辅助检查", "desc": "实验室检查、影像学检查、心电图、专科检查",
     "role_ids": ["attending", "resident"]},
    {"order": 3, "id": "diagnosis", "label": "诊断与分型", "desc": "明确诊断、疾病分型分期、鉴别诊断、合并症评估",
     "role_ids": ["attending"]},
    {"order": 4, "id": "treatment-plan", "label": "治疗方案", "desc": "制定个体化治疗方案、用药方案、非药物治疗、健康教育",
     "role_ids": ["attending", "head"]},
    {"order": 5, "id": "execution", "label": "治疗执行", "desc": "执行治疗方案、用药管理、病情监测、并发症预防",
     "role_ids": ["attending", "resident", "head_nurse"]},
    {"order": 6, "id": "followup", "label": "随访管理", "desc": "慢病随访、用药依从性、复查检验、生活方式指导",
     "role_ids": ["attending", "head_nurse"]},
]

MEDICAL_ROLES = [
    {"id": "attending", "label": "主治医师", "default": True},
    {"id": "resident", "label": "住院医师"},
    {"id": "head_nurse", "label": "护士长"},
    {"id": "head", "label": "科主任"},
]

EMERGENCY_STAGES = [
    {"order": 1, "id": "triage", "label": "急诊分诊", "desc": "生命体征、GCS评分、创伤评分、分诊级别判定（Ⅰ-Ⅳ级）",
     "role_ids": ["attending", "triage_nurse"]},
    {"order": 2, "id": "rescue", "label": "紧急救治", "desc": "ABC评估、气道管理、循环支持、止血、建立静脉通路",
     "role_ids": ["attending", "emergency_doctor", "head_nurse"]},
    {"order": 3, "id": "exam-diagnosis", "label": "快速诊断", "desc": "床旁超声、急诊CT、血气分析、心电图、心肌标志物",
     "role_ids": ["attending", "emergency_doctor"]},
    {"order": 4, "id": "treatment", "label": "急诊处置", "desc": "药物抢救、清创缝合、骨折固定、急诊手术准备",
     "role_ids": ["attending", "emergency_doctor", "head_nurse"]},
    {"order": 5, "id": "disposition", "label": "分流决策", "desc": "收入院/留观/转ICU/离院评估、交接记录",
     "role_ids": ["attending"]},
]

EMERGENCY_ROLES = [
    {"id": "attending", "label": "主治医师", "default": True},
    {"id": "emergency_doctor", "label": "急诊医师"},
    {"id": "triage_nurse", "label": "分诊护士"},
    {"id": "head_nurse", "label": "护士长"},
]

MATERNITY_STAGES = [
    {"order": 1, "id": "antenatal", "label": "产前检查", "desc": "孕周评估、胎心监测、B超检查、宫高腹围、合并症筛查",
     "role_ids": ["attending", "midwife"]},
    {"order": 2, "id": "labor", "label": "产程管理", "desc": "产程图记录、胎心监护、宫缩监测、镇痛管理",
     "role_ids": ["attending", "midwife", "anesthesiologist"]},
    {"order": 3, "id": "delivery", "label": "分娩接生", "desc": "会阴保护、新生儿处理、Apgar评分、胎盘娩出",
     "role_ids": ["attending", "midwife", "neonatologist"]},
    {"order": 4, "id": "postpartum", "label": "产后监护", "desc": "产后出血监测、子宫复旧、泌乳指导、新生儿护理",
     "role_ids": ["attending", "midwife", "head_nurse"]},
    {"order": 5, "id": "neonatal", "label": "新生儿管理", "desc": "新生儿筛查、喂养指导、黄疸监测、预防接种",
     "role_ids": ["neonatologist", "head_nurse"]},
    {"order": 6, "id": "followup", "label": "产后随访", "desc": "42天产后复查、盆底康复、计划生育指导",
     "role_ids": ["attending", "midwife"]},
]

# === Department-to-template mapping ===

DEPARTMENT_MAP = {
    "orthopedic-surgery": "surgical",
    "cardio-surgery": "surgical",
    "neurosurgery": "surgical",
    "general-surgery": "surgical",
    "hepatobiliary-surgery": "surgical",
    "thoracic-surgery": "surgical",
    "vascular-surgery": "surgical",
    "spine-surgery": "surgical",
    "joint-surgery": "surgical",
    "breast-center": "surgical",
    "burns-plastic": "surgical",
    "cosmetic-surgery": "surgical",
    "cardiology": "medical",
    "respiratory": "medical",
    "gastroenterology": "medical",
    "nephrology": "medical",
    "endocrinology": "medical",
    "hematology": "medical",
    "oncology": "medical",
    "rheumatology": "medical",
    "geriatrics": "medical",
    "infectious-disease": "medical",
    "stomatology": "medical",
    "dermatology": "medical",
    "psychiatry": "medical",
    "tcm": "medical",
    "health-management": "medical",
    "emergency": "emergency",
    "icu": "emergency",
    "obgyn": "maternity",
    "neonatology": "maternity",
}

# Only process agents that don't already have custom stages (like pharmacy, medical-record, etc.)
SKIP_AGENTS = {"pharmacy", "medical-record", "metrics", "togaf", "mdt", "pain-hub",
               "cardio-risk", "anesthesia-risk", "pediatrics", "pain-management",
               "acute-pain", "cancer-pain", "chronic-pain", "interventional-pain",
               "pain-rehab", "antiemetic", "dietitian", "education", "lab-critical-value",
               "nurse-general", "medical-docs", "huigiao", "renal-transplant",
               "interventional-therapy", "ophthalmology", "ent", "rehabilitation", "portal"}


def update_yaml(filepath, template):
    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data["name"] in SKIP_AGENTS:
        return False

    if template == "surgical":
        stages = SURGICAL_STAGES
        roles = SURGICAL_ROLES
    elif template == "medical":
        stages = MEDICAL_STAGES
        roles = MEDICAL_ROLES
    elif template == "emergency":
        stages = EMERGENCY_STAGES
        roles = EMERGENCY_ROLES
    elif template == "maternity":
        stages = MATERNITY_STAGES
        roles = [{"id":"attending","label":"主治医师","default":True},{"id":"midwife","label":"助产士"},{"id":"anesthesiologist","label":"麻醉医师"},{"id":"neonatologist","label":"新生儿医师"},{"id":"head_nurse","label":"护士长"}]
    else:
        return False

    data["stages"] = stages
    data["ui"]["roles"] = roles

    # Update prompt to be more specific
    dept = data.get("department", data["name"])
    data["prompt"]["system"] = f"你是南方医院{dept}AI助手，负责{dept}常见疾病的诊疗评估和管理。请基于最新临床指南（2025-2026）给出专业建议，包括诊断标准、治疗方案、风险评估和随访计划。"

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200)
    return True


if __name__ == "__main__":
    updated = 0
    for yf in sorted(YAML_DIR.glob("*.yaml")):
        agent_name = yf.stem
        template = DEPARTMENT_MAP.get(agent_name)
        if not template:
            continue
        if update_yaml(yf, template):
            updated += 1
            print(f"  Updated: {agent_name} → {template}")

    print(f"\nTotal updated: {updated}")
