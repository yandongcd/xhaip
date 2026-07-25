"""Update remaining specialty agents with clinical workflows."""
import pathlib

import yaml

YAML_DIR = pathlib.Path(r"D:\dst\projects\xhaip\packages\haip-hospital\agents\definitions")

# === Outpatient/Specialty clinical workflow (ENT, Ophthalmology, etc.) ===
OUTPATIENT_STAGES = [
    {"order": 1, "id": "reception", "label": "接诊登记", "desc": "主诉采集、现病史、既往史、专科体格检查",
     "role_ids": ["attending", "resident"]},
    {"order": 2, "id": "exam", "label": "专科检查", "desc": "专科仪器检查、功能评估、影像学检查",
     "role_ids": ["attending", "technician"]},
    {"order": 3, "id": "diagnosis", "label": "诊断与分级", "desc": "明确诊断、疾病分型分级、鉴别诊断",
     "role_ids": ["attending"]},
    {"order": 4, "id": "treatment", "label": "治疗方案", "desc": "药物治疗/手术方案/物理治疗、健康教育",
     "role_ids": ["attending", "head"]},
    {"order": 5, "id": "followup", "label": "复查随访", "desc": "定期复查、疗效评估、长期管理",
     "role_ids": ["attending", "resident"]},
]

OUTPATIENT_ROLES = [
    {"id": "attending", "label": "主治医师", "default": True},
    {"id": "resident", "label": "住院医师"},
    {"id": "technician", "label": "技师"},
    {"id": "head", "label": "科主任"},
]

# === Rehabilitation workflow ===
REHAB_STAGES = [
    {"order": 1, "id": "initial-eval", "label": "初次评估", "desc": "功能评估、ADL评估、康复目标设定、康复方案制定",
     "role_ids": ["attending", "therapist"]},
    {"order": 2, "id": "treatment", "label": "康复治疗", "desc": "物理治疗/作业治疗/言语治疗/心理康复",
     "role_ids": ["therapist", "nurse"]},
    {"order": 3, "id": "progress", "label": "进展评估", "desc": "功能改善评分、方案调整、并发症预防",
     "role_ids": ["attending", "therapist"]},
    {"order": 4, "id": "discharge", "label": "出院计划", "desc": "家庭康复指导、辅助器具配置、社区康复衔接",
     "role_ids": ["attending", "therapist", "nurse"]},
]

REHAB_ROLES = [
    {"id": "attending", "label": "康复医师", "default": True},
    {"id": "therapist", "label": "治疗师"},
    {"id": "nurse", "label": "康复护士"},
]

# === Transplant workflow ===
TRANSPLANT_STAGES = [
    {"order": 1, "id": "donor-match", "label": "供体匹配", "desc": "HLA配型、交叉配型、供体评估、伦理审批",
     "role_ids": ["attending", "coordinator"]},
    {"order": 2, "id": "pre-transplant", "label": "移植前准备", "desc": "受体评估、感染筛查、免疫抑制方案制定",
     "role_ids": ["attending", "immunologist"]},
    {"order": 3, "id": "transplant", "label": "移植手术", "desc": "器官获取、植入、血管吻合、术中免疫抑制",
     "role_ids": ["attending", "surgeon", "anesthesiologist"]},
    {"order": 4, "id": "post-transplant", "label": "术后管理", "desc": "排斥监测、免疫抑制剂调整、感染防控、肾功能监测",
     "role_ids": ["attending", "immunologist", "head_nurse"]},
    {"order": 5, "id": "long-term", "label": "长期随访", "desc": "定期复查、药物浓度监测、慢性排斥筛查",
     "role_ids": ["attending", "coordinator"]},
]

TRANSPLANT_ROLES = [
    {"id": "attending", "label": "移植医师", "default": True},
    {"id": "surgeon", "label": "手术医师"},
    {"id": "immunologist", "label": "免疫医师"},
    {"id": "anesthesiologist", "label": "麻醉医师"},
    {"id": "coordinator", "label": "移植协调员"},
    {"id": "head_nurse", "label": "护士长"},
]

# === Interventional workflow ===
INTERVENTIONAL_STAGES = [
    {"order": 1, "id": "pre-procedure", "label": "术前评估", "desc": "适应证评估、凝血功能、过敏史筛查、知情同意",
     "role_ids": ["attending", "resident"]},
    {"order": 2, "id": "procedure", "label": "介入操作", "desc": "导管操作、造影、栓塞/支架置入、术中监测",
     "role_ids": ["attending", "technician", "anesthesiologist"]},
    {"order": 3, "id": "post-procedure", "label": "术后观察", "desc": "穿刺点管理、并发症监测、生命体征",
     "role_ids": ["attending", "head_nurse"]},
    {"order": 4, "id": "followup", "label": "随访评估", "desc": "影像复查、疗效评估、再狭窄监测",
     "role_ids": ["attending"]},
]

INTERVENTIONAL_ROLES = [
    {"id": "attending", "label": "介入医师", "default": True},
    {"id": "resident", "label": "住院医师"},
    {"id": "technician", "label": "导管技师"},
    {"id": "anesthesiologist", "label": "麻醉医师"},
    {"id": "head_nurse", "label": "护士长"},
]

# Updated department map
UPDATES = {
    "ophthalmology": ("outpatient", OUTPATIENT_STAGES, OUTPATIENT_ROLES),
    "ent": ("outpatient", OUTPATIENT_STAGES, OUTPATIENT_ROLES),
    "rehabilitation": ("rehab", REHAB_STAGES, REHAB_ROLES),
    "renal-transplant": ("transplant", TRANSPLANT_STAGES, TRANSPLANT_ROLES),
    "interventional-therapy": ("interventional", INTERVENTIONAL_STAGES, INTERVENTIONAL_ROLES),
}

for agent_name, (template, stages, roles) in UPDATES.items():
    yf = YAML_DIR / f"{agent_name}.yaml"
    if not yf.exists():
        continue
    with open(yf, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["stages"] = stages
    data["ui"]["roles"] = roles

    dept = data.get("department", data["name"])
    data["prompt"]["system"] = f"你是南方医院{dept}AI助手，负责{dept}常见疾病的诊疗评估和管理。请基于最新临床指南给出专业建议。"

    with open(yf, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200)
    print(f"  Updated: {agent_name} → {template} ({len(stages)} stages, {len(roles)} roles)")

print("Done")
