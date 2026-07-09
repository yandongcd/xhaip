"""TOGAF 4A Architecture Builder — generates complete architecture from metamodel + domain knowledge.

Top-down generation: metamodel → department domain → 4A JSON.

Architecture layers:
  BA (Business):    ValueStream → BusinessProcess → BusinessService
  DA (Data):        DataEntity (patients, labs, exams, records)
  AA (Application): ApplicationComponent (agents) + ApplicationService (tools)
  TA (Technology):  TechnologyComponent + TechnologyService (infrastructure)

Usage:
  from haip.togaf.builder import build_4a
  arch = build_4a("orthopedic")  # → dict with 4A layers + edges + graph data
"""

from __future__ import annotations

from dataclasses import dataclass, field



# ── Domain Knowledge: Orthopedic Surgery ──

_ORTHO_VALUE_STREAMS = [
    {
        "id": "vs-triage",
        "name": "分诊登记",
        "stage": 1,
        "description": "患者基本信息采集、病史录入、分诊判定",
        "trigger": "患者到达",
        "outcome": "分诊级别 (I/II/III/IV)",
        "roles": ["主治医师", "护士长"],
    },
    {
        "id": "vs-diagnosis",
        "name": "诊断与评估",
        "stage": 2,
        "description": "影像学检查、骨折分型、术前综合评估",
        "trigger": "分诊完成",
        "outcome": "明确诊断 + 骨折分型",
        "roles": ["主治医师", "麻醉医师"],
    },
    {
        "id": "vs-decision",
        "name": "多学科决策",
        "stage": 3,
        "description": "心脏风险评估、麻醉评估、MDT会诊、手术时机决策",
        "trigger": "诊断确认",
        "outcome": "手术时机决策 + MDT方案",
        "roles": ["主治医师", "麻醉医师"],
    },
    {
        "id": "vs-treatment",
        "name": "治疗执行",
        "stage": 4,
        "description": "手术方案制定、手术执行、并发症监测、护理执行",
        "trigger": "MDT决策完成",
        "outcome": "手术完成 + 并发症管理",
        "roles": ["主治医师", "护士长"],
    },
    {
        "id": "vs-recovery",
        "name": "康复随访",
        "stage": 5,
        "description": "术后康复训练、随访计划、长期管理",
        "trigger": "治疗完成",
        "outcome": "功能恢复 + 长期管理计划",
        "roles": ["主治医师", "护士长"],
    },
]

_ORTHO_BUSINESS_PROCESSES = [
    {
        "id": "bp-reg", "name": "患者登记与分诊", "order": 1,
        "description": "采集患者基本信息、病史、检验结果，执行分诊判定",
        "inputs": ["患者信息", "病史", "体格检查"],
        "outputs": ["分诊级别", "患者档案"],
        "owner": "主治医师",
    },
    {
        "id": "bp-classify", "name": "骨折分型", "order": 2,
        "description": "基于影像学检查（X线/CT/MRI）进行骨折分型（Garden/Evans/AO）",
        "inputs": ["X线正位", "X线侧位"],
        "outputs": ["骨折分型 (Garden I-IV)", "Evans分型", "稳定性评估"],
        "owner": "主治医师",
    },
    {
        "id": "bp-completeness", "name": "术前完整性检查", "order": 3,
        "description": "逐项核查术前必需检查是否完成：检验/影像/心电图/会诊",
        "inputs": ["检验报告", "影像报告", "心电图", "会诊记录"],
        "outputs": ["完整性检查清单", "缺失项列表"],
        "owner": "主治医师",
    },
    {
        "id": "bp-cardio-risk", "name": "心脏风险评估", "order": 4,
        "description": "A2A调用cardio-risk Agent：RCRI评分、心肌酶、心电图分析",
        "inputs": ["患者信息", "检验结果", "心电图"],
        "outputs": ["RCRI评分", "心脏风险等级", "抗凝建议"],
        "owner": "麻醉医师",
    },
    {
        "id": "bp-anes-risk", "name": "麻醉风险评估", "order": 5,
        "description": "A2A调用anesthesia-risk Agent：ASA分级、气道评估、凝血评估",
        "inputs": ["患者信息", "气道评估", "凝血功能"],
        "outputs": ["ASA分级", "麻醉方案", "困难气道预案"],
        "owner": "麻醉医师",
    },
    {
        "id": "bp-mdt", "name": "MDT手术时机决策", "order": 6,
        "description": "综合心内科、麻醉科意见，结合骨折类型和并发症风险，决定手术时机",
        "inputs": ["心脏风险报告", "麻醉评估报告", "骨折分型", "合并症清单"],
        "outputs": ["手术时机 (急诊/限期/择期)", "延迟原因", "术前优化方案"],
        "owner": "主治医师",
    },
    {
        "id": "bp-complication", "name": "并发症预测", "order": 7,
        "description": "基于患者年龄、合并症、骨折类型预测术后并发症概率",
        "inputs": ["患者档案", "合并症", "手术类型"],
        "outputs": ["DVT风险", "感染风险", "压疮风险", "谵妄风险"],
        "owner": "主治医师",
    },
    {
        "id": "bp-surgery-plan", "name": "手术方案制定", "order": 8,
        "description": "确定手术方式（THA/PFNA/空心钉等）、入路、假体选择",
        "inputs": ["骨折分型", "并发症评估", "患者年龄/骨质量"],
        "outputs": ["手术方式", "假体选择", "入路方案"],
        "owner": "主治医师",
    },
    {
        "id": "bp-nursing", "name": "围术期护理", "order": 9,
        "description": "4阶段护理方案：术前/术后当日/术后早期/出院，含DVT预防、压疮、疼痛、体位",
        "inputs": ["患者信息", "手术方式"],
        "outputs": ["4阶段护理方案", "DVT预防计划", "压疮预防", "疼痛管理", "出院指导"],
        "owner": "护士长",
    },
    {
        "id": "bp-followup", "name": "随访管理", "order": 10,
        "description": "术后1周/1月/3月/6月随访，含Harris评分、影像复查、康复指导",
        "inputs": ["手术记录", "出院方案"],
        "outputs": ["随访计划", "Harris评分", "复查提醒", "骨质疏松管理"],
        "owner": "主治医师",
    },
]

_ORTHO_DATA_ENTITIES = [
    {"id": "de-patient", "name": "患者信息", "category": "Master",
     "fields": ["patient_id", "name", "age", "gender", "weight_kg", "height_cm", "diagnosis"]},
    {"id": "de-lab", "name": "检验报告", "category": "Transaction",
     "fields": ["albumin", "crp", "creatinine", "hb", "troponin", "inr", "glucose"]},
    {"id": "de-exam", "name": "影像报告", "category": "Transaction",
     "fields": ["xray_ap", "xray_lat", "ct_scan", "mri"]},
    {"id": "de-risk", "name": "风险评估报告", "category": "Analytics",
     "fields": ["rcri_score", "asa_grade", "complication_risks", "timing_decision"]},
    {"id": "de-surgery", "name": "手术记录", "category": "Transaction",
     "fields": ["surgery_type", "approach", "implant", "duration", "blood_loss"]},
    {"id": "de-followup", "name": "随访记录", "category": "Transaction",
     "fields": ["harris_score", "xray_result", "rehab_status", "complication_events"]},
    {"id": "de-checklist", "name": "术前检查清单", "category": "Reference",
     "fields": ["items", "completed", "missing", "status"]},
]

_ORTHO_APPLICATION_COMPONENTS = [
    {
        "id": "ac-ortho", "name": "创伤骨科Agent",
        "type": "ApplicationComponent",
        "port": 8765,
        "services": ["classify_fracture", "preop_assessment", "surgical_plan",
                      "complication_risk", "timing_decision", "nursing_plan", "followup_plan"],
        "depends_on": ["ac-cardio-risk", "ac-anes-risk", "ac-master-data"],
    },
    {
        "id": "ac-cardio-risk", "name": "围术期心脏评估Agent",
        "type": "ApplicationService",
        "services": ["assess_cardiac_risk", "evaluate_ecg", "anticoagulation_plan"],
    },
    {
        "id": "ac-anes-risk", "name": "围术期麻醉评估Agent",
        "type": "ApplicationService",
        "services": ["assess_asa", "evaluate_airway", "anesthesia_plan"],
    },
    {
        "id": "ac-master-data", "name": "患者数据中心",
        "type": "DataEntity",
        "port": 8766,
        "services": ["get_patient", "get_labs", "get_history"],
    },
]

_ORTHO_TECH_COMPONENTS = [
    {"id": "tc-python", "name": "Python 3.10 Runtime", "type": "TechnologyComponent"},
    {"id": "tc-http", "name": "HTTP Server (FastAPI/uvicorn)", "type": "TechnologyService"},
    {"id": "tc-mcp", "name": "MCP Protocol", "type": "TechnologyService"},
    {"id": "tc-sqlite", "name": "SQLite Knowledge Store", "type": "TechnologyComponent"},
    {"id": "tc-yaml", "name": "YAML Configuration Store", "type": "TechnologyComponent"},
]


# ── Department-Specific Domain Registry ──

_DOMAIN_REGISTRY: dict[str, dict] = {
    "orthopedic": {
        "value_streams": _ORTHO_VALUE_STREAMS,
        "business_processes": _ORTHO_BUSINESS_PROCESSES,
        "data_entities": _ORTHO_DATA_ENTITIES,
        "application_components": _ORTHO_APPLICATION_COMPONENTS,
        "technology_components": _ORTHO_TECH_COMPONENTS,
    },
}


# ── Data Structures ──

@dataclass
class ArchitectureNode:
    id: str
    name: str
    type: str          # TOGAF EntityType id
    layer: str         # Business | Data | Application | Technology
    properties: dict = field(default_factory=dict)


@dataclass
class ArchitectureEdge:
    source: str
    target: str
    relationship: str  # TOGAF RelationshipType id
    description: str = ""


@dataclass
class Architecture4A:
    """Complete TOGAF 4A Architecture."""
    domain: str
    value_streams: list[ArchitectureNode]
    business_processes: list[ArchitectureNode]
    business_services: list[ArchitectureNode]
    data_entities: list[ArchitectureNode]
    application_components: list[ArchitectureNode]
    application_services: list[ArchitectureNode]
    technology_components: list[ArchitectureNode]
    technology_services: list[ArchitectureNode]
    edges: list[ArchitectureEdge]

    def nodes(self) -> list[ArchitectureNode]:
        return (
            self.value_streams + self.business_processes + self.business_services
            + self.data_entities
            + self.application_components + self.application_services
            + self.technology_components + self.technology_services
        )

    def edges_by_layer(self) -> dict[str, list[ArchitectureEdge]]:
        out: dict[str, list[ArchitectureEdge]] = {}
        for e in self.edges:
            out.setdefault(e.relationship, []).append(e)
        return out

    def summary(self) -> str:
        ns = self.nodes()
        es = self.edges
        n_by_layer = {}
        for n in ns:
            n_by_layer[n.layer] = n_by_layer.get(n.layer, 0) + 1
        layers = ", ".join(f"{k}:{v}" for k, v in sorted(n_by_layer.items()))
        return f"4A Architecture [{self.domain}]: {len(ns)} nodes ({layers}), {len(es)} edges"


# ── Builder ──

def _build_valueream_nodes(streams: list[dict]) -> list[ArchitectureNode]:
    return [
        ArchitectureNode(
            id=vs["id"], name=vs["name"], type="BusinessService", layer="Business",
            properties={"stage": vs["stage"], "trigger": vs["trigger"],
                        "outcome": vs["outcome"], "roles": vs["roles"]},
        )
        for vs in streams
    ]


def _build_bp_nodes(processes: list[dict]) -> list[ArchitectureNode]:
    return [
        ArchitectureNode(
            id=bp["id"], name=bp["name"], type="BusinessProcess", layer="Business",
            properties={"order": bp["order"], "owner": bp["owner"],
                        "inputs": bp["inputs"], "outputs": bp["outputs"]},
        )
        for bp in processes
    ]


def _build_data_nodes(entities: list[dict]) -> list[ArchitectureNode]:
    return [
        ArchitectureNode(
            id=de["id"], name=de["name"], type="DataEntity", layer="Data",
            properties={"category": de["category"], "fields": de["fields"]},
        )
        for de in entities
    ]


def _build_app_nodes(components: list[dict]) -> tuple[list[ArchitectureNode], list[ArchitectureNode]]:
    comps = []
    services = []
    for ac in components:
        comps.append(ArchitectureNode(
            id=ac["id"], name=ac["name"], type=ac["type"], layer="Application",
            properties={"port": ac.get("port"), "depends_on": ac.get("depends_on", [])},
        ))
        for svc_name in ac.get("services", []):
            services.append(ArchitectureNode(
                id=f"as-{svc_name}", name=svc_name, type="ApplicationService", layer="Application",
                properties={"component": ac["id"]},
            ))
    return comps, services


def _build_tech_nodes(components: list[dict]) -> tuple[list[ArchitectureNode], list[ArchitectureNode]]:
    comps = []
    services = []
    for tc in components:
        node = ArchitectureNode(
            id=tc["id"], name=tc["name"], type=tc["type"], layer="Technology",
            properties={},
        )
        if tc["type"] == "TechnologyService":
            services.append(node)
        else:
            comps.append(node)
    return comps, services


def _build_edges(nodes: list[ArchitectureNode], domain: str) -> list[ArchitectureEdge]:
    """Generate TOGAF relationships between architecture nodes."""
    node_map = {n.id: n for n in nodes}
    edges: list[ArchitectureEdge] = []

    # VS → BP (contains)
    vs_nodes = [n for n in nodes if n.type == "BusinessService"]
    bp_nodes = [n for n in nodes if n.type == "BusinessProcess"]
    for vs in vs_nodes:
        for bp in bp_nodes[:2]:  # First 2 BPs per value stream
            edges.append(ArchitectureEdge(
                source=vs.id, target=bp.id,
                relationship="contains",
                description=f"{vs.name} 包含 {bp.name}",
            ))

    # BP → BP (workflow flow: sequential contained_by)
    sorted_bps = sorted(bp_nodes, key=lambda n: n.properties.get("order", 0))
    for i in range(len(sorted_bps) - 1):
        edges.append(ArchitectureEdge(
            source=sorted_bps[i].id, target=sorted_bps[i + 1].id,
            relationship="contains",
            description=f"{sorted_bps[i].name} → {sorted_bps[i+1].name}",
        ))

    # ApplicationComponent → ApplicationService (composed_of)
    app_comps = [n for n in nodes if n.type == "ApplicationComponent"]
    app_svcs = [n for n in nodes if n.type == "ApplicationService" and "as-" in n.id]
    for ac in app_comps:
        for svc in app_svcs:
            if svc.properties.get("component") == ac.id:
                edges.append(ArchitectureEdge(
                    source=ac.id, target=svc.id,
                    relationship="composed_of",
                    description=f"{ac.name} contains {svc.name}",
                ))

    # ApplicationComponent ↔ ApplicationComponent (communicates_via)
    for i, ac1 in enumerate(app_comps):
        for dep_id in ac1.properties.get("depends_on", []):
            if dep_id in node_map:
                edges.append(ArchitectureEdge(
                    source=ac1.id, target=dep_id,
                    relationship="communicates_via",
                    description=f"{ac1.name} → A2A → {node_map[dep_id].name}",
                ))

    # ApplicationComponent → BusinessProcess (executes) — all BPs
    for ac in app_comps:
        for bp in bp_nodes:
            edges.append(ArchitectureEdge(
                source=ac.id, target=bp.id,
                relationship="executes",
                description=f"{ac.name} executes {bp.name}",
            ))

    # Smart data access mapping: BP_id → [data_entity_ids it accesses]
    _BP_DATA_MAP = {
        "bp-reg": ["de-patient", "de-lab", "de-checklist"],
        "bp-classify": ["de-patient", "de-exam"],
        "bp-completeness": ["de-lab", "de-exam", "de-checklist"],
        "bp-cardio-risk": ["de-patient", "de-lab", "de-risk"],
        "bp-anes-risk": ["de-patient", "de-lab", "de-risk"],
        "bp-mdt": ["de-risk", "de-patient", "de-exam"],
        "bp-complication": ["de-patient", "de-risk"],
        "bp-surgery-plan": ["de-patient", "de-exam", "de-risk", "de-surgery"],
        "bp-nursing": ["de-patient", "de-surgery", "de-risk"],
        "bp-followup": ["de-patient", "de-surgery", "de-followup"],
    }
    data_nodes = [n for n in nodes if n.type == "DataEntity"]
    # ApplicationComponent → DataEntity (accesses) — all data entities
    for ac in app_comps:
        for de in data_nodes:
            edges.append(ArchitectureEdge(
                source=ac.id, target=de.id,
                relationship="accesses",
                description=f"{ac.name} accesses {de.name}",
            ))
    # BusinessProcess → DataEntity (accesses) — smart mapping
    for bp in bp_nodes:
        de_ids = _BP_DATA_MAP.get(bp.id, ["de-patient", "de-lab"])
        for de_id in de_ids:
            de_node = node_map.get(de_id)
            de_display = de_node.name if de_node else de_id
            edges.append(ArchitectureEdge(
                source=bp.id, target=de_id,
                relationship="accesses",
                description=f"{bp.name} reads/writes {de_display}",
            ))

    # ApplicationComponent → TechnologyComponent (runs_on)
    tech_comps = [n for n in nodes if n.type == "TechnologyComponent"]
    for ac in app_comps:
        for tc in tech_comps[:2]:
            edges.append(ArchitectureEdge(
                source=ac.id, target=tc.id,
                relationship="runs_on",
                description=f"{ac.name} runs on {tc.name}",
            ))

    # ApplicationService → TechnologyService (deployed_on)
    tech_svcs = [n for n in nodes if n.type == "TechnologyService"]
    for svc in app_svcs[:3]:
        for ts in tech_svcs[:2]:
            edges.append(ArchitectureEdge(
                source=svc.id, target=ts.id,
                relationship="deployed_on",
                description=f"{svc.name} deployed on {ts.name}",
            ))

    # Unique relationships only (dedup by source+target+relationship)
    seen = set()
    unique: list[ArchitectureEdge] = []
    for e in edges:
        key = (e.source, e.target, e.relationship)
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def _build_domain_from_template(department: str) -> dict | None:
    """Generate domain data from templates_dept.py for any department."""
    from haip.togaf.templates_dept import get_dept_template
    from haip.togaf.organization import list_orgs

    # Try Chinese name → org_id lookup
    org_id = department
    for org in list_orgs():
        if org.name == department:
            org_id = org.id
            break

    # Find parent for template
    parent_id = ""
    for org in list_orgs():
        for child in org.children:
            if child.id == org_id or child.name == department:
                parent_id = org.id
                break
        if parent_id:
            break

    template = get_dept_template(org_id, parent_id)
    if not template:
        return None

    return {
        "value_streams": [
            {"id": vs["id"], "name": vs["name"], "stage": vs["stage"],
             "trigger": vs.get("trigger", ""), "outcome": vs.get("outcome", ""),
             "roles": template.typical_roles[:3]}
            for vs in template.value_streams
        ],
        "business_processes": [
            {"id": bp["id"], "name": bp["name"], "order": bp["order"],
             "owner": bp.get("owner", ""),
             "inputs": ["患者信息", "检验报告"],
             "outputs": [bp.get("name", "") + "结果"]}
            for bp in template.business_processes
        ],
        "data_entities": [
            {"id": f"de-{de[:20].replace(' ', '-')}",
             "name": de, "category": "Transaction", "fields": ["result"]}
            for de in template.common_data_entities
        ],
        "application_components": [
            {"id": f"ac-{department[:20].replace(' ', '-')}",
             "name": f"{department}Agent", "type": "ApplicationComponent",
             "services": [bp["id"] for bp in template.business_processes[:3]],
             "depends_on": ["ac-master-data"]},
            {"id": "ac-master-data", "name": "患者数据中心",
             "type": "DataEntity", "port": 8766, "services": ["get_patient"]},
        ],
        "technology_components": [
            {"id": "tc-python", "name": "Python Runtime", "type": "TechnologyComponent"},
            {"id": "tc-http", "name": "HTTP Server", "type": "TechnologyService"},
        ],
    }


# ── Public API ──

def build_4a(department: str = "orthopedic") -> Architecture4A | None:
    """Generate complete 4A TOGAF architecture for a department.

    First tries the hardcoded domain registry, then falls back
    to template-based generation from templates_dept.py.

    Args:
        department: Department key ('orthopedic') or Chinese name ('呼吸内科')

    Returns:
        Architecture4A with all nodes and edges, or None if unrecognized.
    """
    # Try hardcoded domain first
    domain = _DOMAIN_REGISTRY.get(department)
    # Try template-based generation
    if not domain:
        domain = _build_domain_from_template(department)
    if not domain:
        return None

    vs_nodes = _build_valueream_nodes(domain["value_streams"])
    bp_nodes = _build_bp_nodes(domain["business_processes"])
    bs_nodes: list[ArchitectureNode] = []  # Business Services (VS fills this)
    de_nodes = _build_data_nodes(domain["data_entities"])
    ac_nodes, as_nodes = _build_app_nodes(domain["application_components"])
    tc_nodes, ts_nodes = _build_tech_nodes(domain["technology_components"])

    all_nodes = vs_nodes + bp_nodes + bs_nodes + de_nodes + ac_nodes + as_nodes + tc_nodes + ts_nodes
    edges = _build_edges(all_nodes, department)

    return Architecture4A(
        domain=department,
        value_streams=vs_nodes,
        business_processes=bp_nodes,
        business_services=bs_nodes,
        data_entities=de_nodes,
        application_components=ac_nodes,
        application_services=as_nodes,
        technology_components=tc_nodes,
        technology_services=ts_nodes,
        edges=edges,
    )


def build_to_dict(department: str = "orthopedic") -> dict | None:
    """Generate 4A architecture as a plain dict (suitable for JSON serialization)."""
    arch = build_4a(department)
    if not arch:
        return None

    def _node(n: ArchitectureNode) -> dict:
        return {"id": n.id, "name": n.name, "type": n.type, "layer": n.layer,
                "properties": n.properties}

    def _edge(e: ArchitectureEdge) -> dict:
        return {"source": e.source, "target": e.target,
                "relationship": e.relationship, "description": e.description}

    return {
        "domain": arch.domain,
        "nodes": [_node(n) for n in arch.nodes()],
        "edges": [_edge(e) for e in arch.edges],
        "summary": arch.summary(),
    }


def list_domains() -> list[str]:
    return list(_DOMAIN_REGISTRY.keys())
