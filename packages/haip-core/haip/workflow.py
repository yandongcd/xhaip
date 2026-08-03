"""临床工作流定义 — 科室 × 角色 × 阶段 × 工具。

每个 Agent 的工作流基于国家诊疗规范定义:
  骨科: 国家卫健委2022《老年髋部骨折诊疗与管理指南》§1-§7
  药剂科: ESPEN/CSPEN 肠外肠内营养指南
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════
# 骨科工作流 — 基于国家卫健委2022 §1-§7
# ═══════════════════════════════════════════════════════════════

ORTHO_WORKFLOW = {
    "agent": "orthopedic-surgery",
    "cn_name": "创伤骨科 — 老年髋部骨折围术期管理",
    "guideline": "国家卫健委2022《老年髋部骨折诊疗与管理指南》",
    "stages": [
        {
            "id": "triage",
            "order": 1, "label": "① 急诊分诊",
            "description": "11项检查清单, 绿色通道判定 (≥75岁+髋部骨折)",
            "tool": "checklist",
            "roles": ["attending", "head_nurse"],
            "key_output": "triage_level",
            "guideline_ref": "卫健委2022 §2",
        },
        {
            "id": "classify",
            "order": 2, "label": "② 骨折分型",
            "description": "Garden/Evans/AO 分型评估",
            "tool": "classify_fracture",
            "roles": ["attending", "surgeon"],
            "key_output": "classification",
            "guideline_ref": "卫健委2022 §3",
        },
        {
            "id": "preop",
            "order": 3, "label": "③ 术前评估",
            "description": "合并症/药物/营养/认知 + 14项检查完备性",
            "tool": "preop_assessment",
            "roles": ["attending", "surgeon", "anesthesiologist"],
            "key_output": "cleared",
            "guideline_ref": "卫健委2022 §3",
        },
        {
            "id": "timing",
            "order": 4, "label": "④ 手术时机",
            "description": "T2 8因素层次决策 (高危→择期 / 中危→限期 / 无→48h急诊)",
            "tool": "timing_decision",
            "roles": ["attending", "surgeon", "anesthesiologist"],
            "key_output": "urgency",
            "guideline_ref": "卫健委2022 §4",
        },
        {
            "id": "complication",
            "order": 5, "label": "⑤ 并发症预测",
            "description": "DVT/感染/心脏/跌倒-谵妄 4维风险评估",
            "tool": "complication_risk",
            "roles": ["attending", "surgeon"],
            "key_output": "overall_risk",
            "guideline_ref": "卫健委2022 §6",
        },
        {
            "id": "surgery",
            "order": 6, "label": "⑥ 手术方案",
            "description": "THA/HA/PFNA/DHS 手术方式推荐",
            "tool": "surgical_plan",
            "roles": ["attending", "surgeon"],
            "key_output": "procedure",
            "guideline_ref": "卫健委2022 §5",
        },
        {
            "id": "nursing",
            "order": 7, "label": "⑦ 围术期护理",
            "description": "4阶段25项护理计划 (术前/D0/D1-3/恢复期)",
            "tool": "nursing_plan",
            "roles": ["head_nurse", "attending"],
            "key_output": "plan",
            "guideline_ref": "卫健委2022 §6",
        },
        {
            "id": "rehab",
            "order": 8, "label": "⑧ 术后康复",
            "description": "4阶段康复跟踪 + Harris 髋关节评分",
            "tool": "rehab_track",
            "roles": ["attending", "head_nurse"],
            "key_output": "harris_score",
            "guideline_ref": "卫健委2022 §7",
        },
        {
            "id": "followup",
            "order": 9, "label": "⑨ 随访计划",
            "description": "1/3/6/12月随访 + 6个红旗症状 + 骨质疏松管理",
            "tool": "followup_plan",
            "roles": ["attending", "head_nurse"],
            "key_output": "schedule",
            "guideline_ref": "卫健委2022 §7",
        },
        {
            "id": "quality",
            "order": 10, "label": "⑩ 质控审计",
            "description": "6阶段18检查点合规评分",
            "tool": "quality_audit",
            "roles": ["attending"],
            "key_output": "total_score",
            "guideline_ref": "卫健委2022 全文",
        },
    ],
    "roles": {
        "attending": {"name": "主治医师", "icon": "🩺", "stages": "all", "desc": "全流程管理: 分诊→随访→质控"},
        "surgeon": {"name": "主刀医生", "icon": "🔪", "stages": [2,3,4,5,6], "desc": "手术相关: 分型→手术方案"},
        "anesthesiologist": {"name": "麻醉科医生", "icon": "💉", "stages": [3,4], "desc": "术前评估+手术时机"},
        "head_nurse": {"name": "护士长", "icon": "🏥", "stages": [1,7,8,9], "desc": "护理相关: 分诊+护理+康复+随访"},
    },
}


# ═══════════════════════════════════════════════════════════════
# 药剂科工作流 — 基于 ESPEN/CSPEN 指南
# ═══════════════════════════════════════════════════════════════

PHARMACY_WORKFLOW = {
    "agent": "pharmacy",
    "cn_name": "药剂科 — 营养支持与处方审核",
    "guideline": "ESPEN 2023 / CSPEN 肠外肠内营养指南",
    "stages": [
        {"id": "assess", "order": 1, "label": "① NRS2002 营养评估",
         "description": "营养风险筛查 (NRS2002) + 再喂养+电解质+肝功",
         "tool": "nutrition_assess", "roles": ["pharmacist", "clinical_pharmacist"],
         "key_output": "risk_level", "guideline_ref": "ESPEN §3"},
        {"id": "route", "order": 2, "label": "② 营养途径推荐",
         "description": "EN (肠内) vs PN (肠外) 途径选择",
         "tool": "nutrition_route", "roles": ["clinical_pharmacist", "dietitian"],
         "key_output": "recommended_route", "guideline_ref": "ESPEN §4"},
        {"id": "tpn", "order": 3, "label": "③ TPN 配比计算",
         "description": "氨基酸/脂肪乳/葡萄糖/电解质/渗透压",
         "tool": "calculate_tpn", "roles": ["clinical_pharmacist", "iv_compounding_pharmacist"],
         "key_output": "energy_kcal", "guideline_ref": "CSPEN 肠外营养"},
        {"id": "review", "order": 4, "label": "④ 处方审核 (17规则)",
         "description": "抗凝4+抗生素3+电解质3+镇痛3+心血管4 完整规则库",
         "tool": "review_rx", "roles": ["review_pharmacist", "pharmacist"],
         "key_output": "risk_level", "guideline_ref": "中国药典2020"},
        {"id": "drugs", "order": 5, "label": "⑤ 药品查询",
         "description": "通用名/商品名/规格/医保类别",
         "tool": "drug_search", "roles": ["all"],
         "key_output": "results", "guideline_ref": "—"},
    ],
    "roles": {
        "pharmacist": {"name": "药师", "icon": "💊", "stages": "all", "desc": "全流程: 评估→处方审核→发药"},
        "clinical_pharmacist": {"name": "临床药师", "icon": "🔬", "stages": [1,2,3], "desc": "营养评估+TPN计算"},
        "review_pharmacist": {"name": "审方药师", "icon": "📋", "stages": [4], "desc": "处方审核"},
        "iv_compounding_pharmacist": {"name": "静配药师", "icon": "💉", "stages": [3], "desc": "TPN配置"},
        "dietitian": {"name": "营养师", "icon": "🥗", "stages": [2], "desc": "营养途径推荐"},
    },
}


# ═══════════════════════════════════════════════════════════════
# 工作流注册表
# ═══════════════════════════════════════════════════════════════

WORKFLOWS: dict[str, dict] = {
    "orthopedic-surgery": ORTHO_WORKFLOW,
    "pharmacy": PHARMACY_WORKFLOW,
}


def get_workflow(agent_name: str) -> dict | None:
    return WORKFLOWS.get(agent_name)


def get_visible_stages(agent_name: str, role: str) -> list[dict]:
    """返回指定角色可见的工作流阶段列表。"""
    wf = WORKFLOWS.get(agent_name)
    if not wf:
        return []
    stages = wf["stages"]
    if role == "all" or role not in wf["roles"]:
        return stages  # 未知角色或 all = 全量
    role_config = wf["roles"][role]
    role_stages = role_config["stages"]
    if role_stages == "all":
        return stages
    # role_stages = [1,2,3,4,5,6] (stage order numbers)
    stage_order = set(role_stages)
    return [s for s in stages if s["order"] in stage_order]
