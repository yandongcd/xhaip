"""TOGAF Agent YAML Generator — Auto-generate agent definitions from TOGAF templates.

Input:  department org_id
Output: complete YAML agent definition with stages, roles, tools, guard
"""

from __future__ import annotations

from pathlib import Path
import yaml

from haip.togaf.organization import ROLE_BY_ORG, list_roles, list_orgs
from haip.togaf.templates_dept import get_dept_template, get_guideline_info


# Tool name generators per template type
_TOOL_NAMES_BY_TYPE: dict[str, list[dict]] = {
    "surgery": [
        {"name": "preop_assess", "desc": "术前评估", "handler": "{module}.preop"},
        {"name": "surgical_plan", "desc": "手术方案", "handler": "{module}.plan"},
        {"name": "risk_assess", "desc": "风险评估", "handler": "{module}.risk"},
        {"name": "followup_plan", "desc": "术后随访", "handler": "{module}.followup"},
    ],
    "internal_medicine": [
        {"name": "diagnose", "desc": "诊断评估", "handler": "{module}.diagnose"},
        {"name": "treatment_plan", "desc": "治疗方案", "handler": "{module}.plan"},
        {"name": "followup_mgmt", "desc": "慢病随访", "handler": "{module}.followup"},
    ],
    "obgyn_pediatrics": [
        {"name": "assess", "desc": "专项评估", "handler": "{module}.assess"},
        {"name": "treatment_plan", "desc": "治疗方案", "handler": "{module}.plan"},
        {"name": "followup_mgmt", "desc": "随访保健", "handler": "{module}.followup"},
    ],
    "ent_oph": [
        {"name": "exam", "desc": "专科检查", "handler": "{module}.exam"},
        {"name": "diagnose", "desc": "诊断定级", "handler": "{module}.diagnose"},
        {"name": "treatment", "desc": "治疗执行", "handler": "{module}.treat"},
    ],
    "emergency_critical": [
        {"name": "triage", "desc": "急诊分诊", "handler": "{module}.triage"},
        {"name": "rescue", "desc": "急救处置", "handler": "{module}.rescue"},
        {"name": "monitor", "desc": "监护管理", "handler": "{module}.monitor"},
    ],
    "other_clinical": [
        {"name": "assess", "desc": "接诊评估", "handler": "{module}.assess"},
        {"name": "diagnose", "desc": "诊断确认", "handler": "{module}.diagnose"},
        {"name": "treat", "desc": "治疗管理", "handler": "{module}.treat"},
    ],
}

_GUARD_TRIGGERS_BY_TYPE: dict[str, list[str]] = {
    "surgery": ["手术决策"],
    "internal_medicine": [],
    "obgyn_pediatrics": ["药物交互"],
    "ent_oph": [],
    "emergency_critical": ["手术决策"],
    "other_clinical": [],
}


def generate_agent_yaml(org_id: str, output_dir: str = "") -> str | None:
    """Generate a complete YAML agent definition for a department.

    Args:
        org_id: Department org_id (e.g. 'respiratory', 'neurosurgery')
        output_dir: If provided, write YAML to this directory

    Returns:
        YAML string or None if department has no template.
    """
    # Find org info
    all_orgs = list_orgs()
    org = next((o for o in all_orgs if o.id == org_id), None)
    if not org:
        return None

    # Find parent for template
    parent_id = ""
    for o in all_orgs:
        if o.parent:
            if any(c.id == org_id for c in o.children):
                parent_id = o.id
                break
    if not parent_id and org.parent:
        parent_id = org.parent

    template = get_dept_template(org_id, parent_id)
    if not template:
        return None

    # Agent name: org name → pinyin-ish module name
    agent_name = _org_to_agent_name(org.name)
    module_name = _org_to_module_name(org.name)
    cn_name = f"{org.name}智能体"

    # Port assignment
    port = _assign_port(org_id)

    # Role IDs
    role_defs = list_roles(org_id=org_id)
    ui_roles = []
    for r in role_defs[:4]:  # Max 4 UI roles
        role_id = r.id.replace(org_id.replace("-", "").replace("_", ""), "")
        if role_id.startswith("_"):
            role_id = role_id[1:]
        ui_roles.append({
            "id": role_id,
            "label": r.level,
            "default": r.level == "主治医师",
        })

    # Stages from template BPs
    stages_yaml = ""
    for bp in template.business_processes:
        dept_roles = " / ".join(r.level for r in role_defs[:3])
        role_ids_list = [r["id"] for r in ui_roles[:3]]
        stages_yaml += f"""  - order: {bp['order']}
    id: {bp['id']}
    label: {bp['name']}
    desc: "{bp['name']}流程"
    role: "{dept_roles}"
    role_ids: [{', '.join(repr(rid) for rid in role_ids_list)}]
"""

    # Tools — use BP IDs as tool names (matching handler functions)
    tools_yaml = ""
    for bp in template.business_processes:
        tool_name = bp['id'].replace('-', '_')
        handler = f"{module_name}.{tool_name}"
        tools_yaml += f"""  - name: {tool_name}
    description: {bp['name']}
    handler: {handler}
    input: {{patient_id: str}}

"""

    # Guard
    guard_triggers = _GUARD_TRIGGERS_BY_TYPE.get(parent_id, [])
    guard_yaml = ""
    if guard_triggers:
        trigger_list = ", ".join(repr(t) for t in guard_triggers)
        guard_yaml = f"""guard:
  triggers: [{trigger_list}]
"""

    yaml_content = f"""name: {agent_name}
cn_name: {cn_name}
version: "1.0.0"
type: business
department: {org.name}
port: {port}
aliases: [{org.name}, {agent_name}]

prompt:
  system: |
    你是南方医院{org.name}AI助手，负责{org.name}常见疾病的诊疗评估和管理。
    请基于相关临床指南给出专业建议。
  temperature: 0.3

tools:
{tools_yaml}{guard_yaml}
ui:
  template: chat-with-role-switcher
  roles:
"""
    for r in ui_roles:
        default_str = ", default: true" if r.get("default") else ""
        yaml_content += f"    - {{id: {r['id']}, label: {r['label']}{default_str}}}\n"

    yaml_content += f"""
stages:
{stages_yaml}"""

    # Write to file
    if output_dir:
        out_path = Path(output_dir) / f"{agent_name}.yaml"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(yaml_content, encoding="utf-8")

    return yaml_content


def _org_to_agent_name(org_name: str) -> str:
    """Convert Chinese dept name to agent kebab-case name."""
    known = {
        "心血管内科": "cardiology", "消化内科": "gastroenterology",
        "呼吸内科": "respiratory", "肾内科": "nephrology",
        "血液内科": "hematology", "内分泌科": "endocrinology",
        "风湿免疫科": "rheumatology", "感染内科": "infectious-disease",
        "肿瘤科": "oncology", "中医科": "tcm", "老年病科": "geriatrics",
        "普通外科": "general-surgery", "肝胆外科": "hepatobiliary-surgery",
        "神经外科": "neurosurgery", "胸外科": "thoracic-surgery",
        "介入治疗科": "interventional-therapy", "乳腺中心": "breast-center",
        "烧伤整形科": "burns-plastic", "整形美容科": "cosmetic-surgery",
        "血管外科": "vascular-surgery", "肾移植科": "renal-transplant",
        "妇产科": "obgyn", "新生儿科": "neonatology",
        "眼科": "ophthalmology", "耳鼻喉科": "ent", "口腔科": "stomatology",
        "急诊科": "emergency", "重症医学科": "icu",
        "健康管理科": "health-management", "惠侨医疗中心": "huigiao",
        "皮肤科": "dermatology", "精神心理科": "psychiatry",
        "康复医学科": "rehabilitation",
    }
    return known.get(org_name, org_name.replace(" ", "-").lower())


def _org_to_module_name(org_name: str) -> str:
    """Map to Python module name for handlers."""
    agent_name = _org_to_agent_name(org_name)
    return agent_name.replace("-", "_")


def _assign_port(org_id: str) -> int:
    """Assign unique port for new agent."""
    port_map = {
        "respiratory": 8781, "gastroenterology": 8782, "nephrology": 8783,
        "hematology": 8784, "endocrinology": 8785, "rheumatology": 8786,
        "infectious_disease": 8787, "oncology": 8788, "tcm": 8789,
        "geriatrics": 8790, "general_surgery": 8791, "hepatobiliary_surgery": 8792,
        "neurosurgery": 8793, "thoracic_surgery": 8794, "vascular_surgery": 8795,
        "renal_transplant": 8796, "breast_center": 8797, "burns_plastic": 8798,
        "cosmetic_surgery": 8799, "interventional_therapy": 8802,
        "obgyn": 8803, "neonatology": 8804,
        "ophthalmology": 8805, "ent": 8806, "stomatology": 8807,
        "emergency": 8808, "icu": 8809, "dermatology": 8810,
        "psychiatry": 8811, "rehabilitation": 8812, "health_mgmt": 8813,
        "huigiao": 8814,
    }
    return port_map.get(org_id, 8900)


def generate_all_missing(output_dir: str, dry_run: bool = False) -> list[str]:
    """Generate agents for all departments without one."""
    agent_registry = {}
    try:
        from haip.agent import _registry as _agent_registry, load_from_dir
        if not _agent_registry:
            load_from_dir("")
        agent_registry = _agent_registry
    except Exception:
        pass

    # Map org name → agent name
    agents_registered = {a.cn_name: a.name for a in agent_registry.values()}

    all_orgs = list_orgs()
    clinical = [o for o in all_orgs if o.type == "clinical" and o.parent]
    generated: list[str] = []

    dept_name_to_agent = {
        "创伤骨科": "orthopedic-surgery", "脊柱骨科": "orthopedic-surgery",
        "关节骨科": "orthopedic-surgery", "心血管外科": "cardio-surgery",
        "儿科": "pediatrics", "疼痛科": "pain-hub",
        "心血管内科": "cardiology",
    }

    for org in sorted(clinical, key=lambda o: o.name):
        # Check if already has agent
        if dept_name_to_agent.get(org.name, "") in agent_registry:
            continue

        if not dry_run:
            generate_agent_yaml(org.id, output_dir)
        generated.append(org.name)

    return generated
