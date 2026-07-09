"""TOGAF 10 Metamodel — 10 entity types + 13 relationship types.

The single source of truth for all TOGAF ABBs (Architecture Building Blocks).
Every Agent, tool, data entity, and organizational unit in xhaip maps to
one of these entity types.

Entity Types (4A layers):
  Business:    Organization, Actor, Role, BusinessService, BusinessProcess
  Data:        DataEntity
  Application: ApplicationComponent, ApplicationService
  Technology:  TechnologyComponent, TechnologyService

Relationship Types:
  Composition: has, employs, contains, composed_of
  Assignment:  plays, participates_in, executes
  Realization: supports, stores, runs_on, deployed_on
  Interaction: communicates_via, accesses
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EntityType:
    id: str
    name: str
    layer: str  # Business | Data | Application | Technology
    description: str


@dataclass
class RelationshipType:
    id: str
    name: str
    category: str  # Composition | Assignment | Realization | Interaction
    source_types: list[str]
    target_types: list[str]
    description: str


# ── 10 Entity Types ──

ENTITY_TYPES: dict[str, EntityType] = {
    "Organization": EntityType(
        id="Organization",
        name="组织",
        layer="Business",
        description="具有共同目标的人群集合体（医院、科室、团队）",
    ),
    "Actor": EntityType(
        id="Actor",
        name="行动者",
        layer="Business",
        description="执行任务的人或系统（医生、护士、药师）",
    ),
    "Role": EntityType(
        id="Role",
        name="角色",
        layer="Business",
        description="行动者在组织中承担的职责（主治医师、护士长）",
    ),
    "BusinessService": EntityType(
        id="BusinessService",
        name="业务服务",
        layer="Business",
        description="向患者或内部客户提供的业务功能（门诊挂号、处方审核）",
    ),
    "BusinessProcess": EntityType(
        id="BusinessProcess",
        name="业务流程",
        layer="Business",
        description="为达成业务目标而执行的一组活动序列（骨折分型流程、TPN配置流程）",
    ),
    "DataEntity": EntityType(
        id="DataEntity",
        name="数据实体",
        layer="Data",
        description="业务过程中使用或产生的数据结构（患者信息、检验报告、处方）",
    ),
    "ApplicationComponent": EntityType(
        id="ApplicationComponent",
        name="应用组件",
        layer="Application",
        description="封装的应用功能模块（骨外科Agent、药剂科Agent）",
    ),
    "ApplicationService": EntityType(
        id="ApplicationService",
        name="应用服务",
        layer="Application",
        description="应用组件对外暴露的服务接口（心脏风险评估、麻醉评估）",
    ),
    "TechnologyComponent": EntityType(
        id="TechnologyComponent",
        name="技术组件",
        layer="Technology",
        description="支撑应用运行的技术基础设施（Python Runtime、SQLite、HTTP Server）",
    ),
    "TechnologyService": EntityType(
        id="TechnologyService",
        name="技术服务",
        layer="Technology",
        description="技术组件提供的基础能力（REST API、数据库查询、MCP协议）",
    ),
}

# ── 13 Relationship Types ──

RELATIONSHIP_TYPES: dict[str, RelationshipType] = {
    "has": RelationshipType(
        id="has",
        name="拥有",
        category="Composition",
        source_types=["Organization"],
        target_types=["Organization", "Actor"],
        description="组织包含子组织或行动者（南方医院 → 骨外科 → 主治医师）",
    ),
    "employs": RelationshipType(
        id="employs",
        name="雇佣",
        category="Composition",
        source_types=["Organization"],
        target_types=["Actor"],
        description="组织雇佣行动者（医院雇佣医生）",
    ),
    "plays": RelationshipType(
        id="plays",
        name="承担",
        category="Assignment",
        source_types=["Actor"],
        target_types=["Role"],
        description="行动者承担特定角色（张医生承担主治医师角色）",
    ),
    "participates_in": RelationshipType(
        id="participates_in",
        name="参与",
        category="Assignment",
        source_types=["Actor", "Role"],
        target_types=["BusinessProcess"],
        description="行动者或角色参与业务流程（主治医师参与骨折分型流程）",
    ),
    "executes": RelationshipType(
        id="executes",
        name="执行",
        category="Assignment",
        source_types=["ApplicationComponent"],
        target_types=["BusinessProcess"],
        description="应用组件执行业务流程（骨外科Agent执行骨折分型）",
    ),
    "supports": RelationshipType(
        id="supports",
        name="支撑",
        category="Realization",
        source_types=["ApplicationComponent", "ApplicationService"],
        target_types=["BusinessService", "BusinessProcess"],
        description="应用支撑业务（心脏风险评估服务支撑MDT会诊）",
    ),
    "stores": RelationshipType(
        id="stores",
        name="存储",
        category="Realization",
        source_types=["ApplicationComponent", "DataEntity"],
        target_types=["DataEntity"],
        description="数据实体存储关系（患者数据中心存储患者信息）",
    ),
    "runs_on": RelationshipType(
        id="runs_on",
        name="运行于",
        category="Realization",
        source_types=["ApplicationComponent"],
        target_types=["TechnologyComponent"],
        description="应用组件运行在技术组件上（Agent运行于Python Runtime）",
    ),
    "deployed_on": RelationshipType(
        id="deployed_on",
        name="部署于",
        category="Realization",
        source_types=["ApplicationService"],
        target_types=["TechnologyService"],
        description="应用服务部署在技术服务上（REST API部署于HTTP Server:8765）",
    ),
    "communicates_via": RelationshipType(
        id="communicates_via",
        name="通信通过",
        category="Interaction",
        source_types=["ApplicationComponent"],
        target_types=["ApplicationComponent", "TechnologyService"],
        description="应用组件间通信（骨外科Agent ← A2A → 心脏风险评估Agent）",
    ),
    "accesses": RelationshipType(
        id="accesses",
        name="访问",
        category="Interaction",
        source_types=["ApplicationComponent", "Actor"],
        target_types=["DataEntity", "ApplicationService"],
        description="访问数据或服务（主治医师访问患者检验报告）",
    ),
    "contains": RelationshipType(
        id="contains",
        name="包含",
        category="Composition",
        source_types=["Organization", "BusinessProcess"],
        target_types=["Organization", "BusinessProcess"],
        description="层级包含关系（创伤骨科诊疗流程包含骨折分型子流程）",
    ),
    "composed_of": RelationshipType(
        id="composed_of",
        name="组成",
        category="Composition",
        source_types=["ApplicationComponent", "DataEntity"],
        target_types=["ApplicationComponent", "DataEntity"],
        description="组件化组成关系（HAIP平台由14个Agent组成）",
    ),
}


def list_entity_types() -> list[dict]:
    """列出全部实体类型。"""
    return [
        {"id": e.id, "name": e.name, "layer": e.layer, "description": e.description}
        for e in ENTITY_TYPES.values()
    ]


def list_relationship_types() -> list[dict]:
    """列出全部关系类型。"""
    return [
        {"id": r.id, "name": r.name, "category": r.category,
         "source": r.source_types, "target": r.target_types,
         "description": r.description}
        for r in RELATIONSHIP_TYPES.values()
    ]


def get_entity_type(type_id: str) -> EntityType | None:
    return ENTITY_TYPES.get(type_id)


def get_relationship_type(rel_id: str) -> RelationshipType | None:
    return RELATIONSHIP_TYPES.get(rel_id)
