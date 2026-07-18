"""TOGAF Architecture Governance handlers — bridge to haip-core/togaf/.

Mapping:
  metamodel_list   → haip.togaf.metamodel (entity types + relationship types)
  architecture_build → haip.togaf.builder (4A architecture generation)
  layout_graph     → haip.togaf.layout (force-directed layout)
  audit_environment → haip.togaf.audit (auto-discovery + stats)
  template_render  → haip.togaf.dashboard (EA dashboard rendering)
  template_list    → synthetic: lists available EA template types
"""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════
# 1. metamodel_list — TOGAF 10 Metamodel
# ═══════════════════════════════════════════════════════════

def metamodel_list(entity_type: str = "", **kwargs: Any) -> dict[str, Any]:
    """List TOGAF 10 metamodel entity types (10) and relationship types (13).

    Args:
        entity_type: Filter by entity type ID (e.g. 'Organization', 'ApplicationComponent').
                     Empty string returns both entity types and relationship types.

    Returns:
        {
            "entity_types": [...],       # 10 entity types across 4A layers
            "relationship_types": [...],  # 13 relationship types
            "filtered": {...},            # optional: single entity/relationship detail
        }
    """
    from haip.togaf.metamodel import (
        list_entity_types,
        list_relationship_types,
        get_entity_type,
        get_relationship_type,
    )

    entities = list_entity_types()
    relationships = list_relationship_types()

    result: dict[str, Any] = {
        "status": "ok",
        "entity_types": entities,
        "relationship_types": relationships,
        "summary": {
            "entity_type_count": len(entities),
            "relationship_type_count": len(relationships),
            "layers": sorted(set(e["layer"] for e in entities)),
            "categories": sorted(set(r["category"] for r in relationships)),
        },
    }

    if entity_type:
        et = get_entity_type(entity_type)
        rt = get_relationship_type(entity_type)
        if et:
            result["filtered"] = {
                "id": et.id, "name": et.name, "layer": et.layer,
                "description": et.description,
            }
        elif rt:
            result["filtered"] = {
                "id": rt.id, "name": rt.name, "category": rt.category,
                "source_types": rt.source_types, "target_types": rt.target_types,
                "description": rt.description,
            }
        else:
            result["filtered"] = None

    return result


# ═══════════════════════════════════════════════════════════
# 2. architecture_build — 4A Architecture Generation
# ═══════════════════════════════════════════════════════════

def architecture_build(department: str = "", **kwargs: Any) -> dict[str, Any]:
    """Build TOGAF 4A architecture for a department.

    Generates:
      BA (Business): ValueStreams → BusinessProcesses → BusinessServices
      DA (Data): DataEntities (patients, labs, records)
      AA (Application): ApplicationComponents (agents) + ApplicationServices (tools)
      TA (Technology): TechnologyComponents + TechnologyServices

    Args:
        department: Department key ('orthopedic') or Chinese name ('呼吸内科').

    Returns:
        4A architecture dict with nodes, edges, and summary.
    """
    from haip.togaf.builder import build_to_dict

    if not department:
        return {"status": "error", "message": "department is required"}

    result = build_to_dict(department)
    if result is None:
        return {
            "status": "error",
            "message": f"Department '{department}' not found in TOGAF domain registry.",
        }
    result["status"] = "ok"
    return result


# ═══════════════════════════════════════════════════════════
# 3. layout_graph — Force-Directed Graph Layout
# ═══════════════════════════════════════════════════════════

def layout_graph(
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    width: int = 1200,
    height: int = 800,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compute force-directed layout coordinates for a graph.

    Algorithm: Coulomb repulsion + Hooke attraction + center gravity + collision repair.

    Args:
        nodes: [{id, x?, y?, w?, h?}] — node data dicts.
        edges: [{source, target}] — edge data dicts.
        width: Canvas width in pixels (default 1200).
        height: Canvas height in pixels (default 800).

    Returns:
        {status, nodes: [{id, x, y}], node_count, edge_count, canvas}
    """
    from haip.togaf.layout import compute_layout

    nodes = nodes or []
    edges = edges or []

    if not nodes:
        return {"status": "ok", "nodes": [], "node_count": 0, "edge_count": 0}

    positioned = compute_layout(nodes, edges, width=width, height=height)

    return {
        "status": "ok",
        "nodes": positioned,
        "node_count": len(positioned),
        "edge_count": len(edges),
        "canvas": {"width": width, "height": height},
    }


# ═══════════════════════════════════════════════════════════
# 4. audit_environment — Auto-Discovery
# ═══════════════════════════════════════════════════════════

def audit_environment(**kwargs: Any) -> dict[str, Any]:
    """Auto-scan deployed environment to build TOGAF architecture landscape.

    Discovers:
      - Organization (南方医院)
      - Agents from YAML definitions (agents/definitions/*.yaml)
      - Agents from in-memory registry (haip.agent.list_all())
      - Knowledge / data entities (knowledge/ directory)
      - Technology components (Python runtime, OS, YAML store)
      - Relationships between all entities

    Returns:
        {status, landscape, stats, edges_total, nodes_total, registry_size, yaml_count}
    """
    from haip.togaf.audit import audit_environment as _audit

    result = _audit()
    result["status"] = "ok"
    return result


# ═══════════════════════════════════════════════════════════
# 5. template_render — Render EA Visualization Template
# ═══════════════════════════════════════════════════════════

_AVAILABLE_TEMPLATES = {
    "capability_heatmap": {
        "id": "capability_heatmap",
        "name": "能力成熟度热力图",
        "description": "39 科室 × L0-L3 成熟度评分热力图 (分组 + 明细表)",
        "version": "2.0.0",
        "output_format": "html",
    },
    "stakeholder_map": {
        "id": "stakeholder_map",
        "name": "利益相关者地图",
        "description": "170+ 角色 × 科室的利益相关者关系图谱",
        "version": "1.0.0",
        "output_format": "json",
    },
    "roadmap": {
        "id": "roadmap",
        "name": "架构路线图",
        "description": "基于 T0-T3 阶段的架构演进路线图 (当前 → 目标)",
        "version": "1.0.0",
        "output_format": "json",
    },
    "app_landscape": {
        "id": "app_landscape",
        "name": "应用组合景观",
        "description": "52 Agent + 17 检测器的应用组合全景视图",
        "version": "1.0.0",
        "output_format": "json",
    },
    "value_stream": {
        "id": "value_stream",
        "name": "价值流视图",
        "description": "科室价值流阶段 (分诊→诊断→决策→治疗→康复) 的端到端流程",
        "version": "1.0.0",
        "output_format": "json",
    },
}


def template_render(name: str = "", theme: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Render an EA visualization template.

    Currently supported templates:
      - capability_heatmap: Full HTML dashboard with maturity heatmap + detail table.
        Calls haip.togaf.dashboard.render_dashboard().

    Args:
        name: Template ID (e.g. 'capability_heatmap', 'stakeholder_map').
        theme: Optional theme overrides dict (colors, fonts).

    Returns:
        {status, template, format, html} or {status, template, format, data}
    """
    if name not in _AVAILABLE_TEMPLATES:
        return {
            "status": "error",
            "message": f"Unknown template '{name}'. Available: {list(_AVAILABLE_TEMPLATES.keys())}",
        }

    tmpl = _AVAILABLE_TEMPLATES[name]

    if name == "capability_heatmap":
        try:
            from haip.togaf.dashboard import render_dashboard
            html = render_dashboard()
            return {
                "status": "ok",
                "template": tmpl,
                "format": "html",
                "html": html,
            }
        except Exception as e:
            return {"status": "error", "template": tmpl, "message": str(e)}

    # JSON/HTML templates with real rendering via template modules
    if name == "stakeholder_map":
        try:
            from haip.togaf.templates.stakeholder_map import render, DEFAULT_DATA
            html = render(DEFAULT_DATA, theme=theme, full_page=True)
            return {"status": "ok", "template": tmpl, "format": "html", "html": html}
        except Exception as e:
            return {"status": "error", "template": tmpl, "message": str(e)}

    if name == "roadmap":
        try:
            from haip.togaf.templates.roadmap import render, DEFAULT_DATA
            html = render(DEFAULT_DATA, theme=theme, full_page=True)
            return {"status": "ok", "template": tmpl, "format": "html", "html": html}
        except Exception as e:
            return {"status": "error", "template": tmpl, "message": str(e)}

    if name == "app_landscape":
        try:
            from haip.togaf.templates.app_landscape import render, DEFAULT_DATA
            html = render(DEFAULT_DATA, theme=theme, full_page=True)
            return {"status": "ok", "template": tmpl, "format": "html", "html": html}
        except Exception as e:
            return {"status": "error", "template": tmpl, "message": str(e)}

    if name == "value_stream":
        try:
            from haip.togaf.templates.value_stream_map import render, DEFAULT_DATA
            html = render(DEFAULT_DATA, theme=theme, full_page=True)
            return {"status": "ok", "template": tmpl, "format": "html", "html": html}
        except Exception as e:
            return {"status": "error", "template": tmpl, "message": str(e)}

    return {
        "status": "ok",
        "template": tmpl,
        "format": tmpl["output_format"],
        "data": tmpl,
    }


# ═══════════════════════════════════════════════════════════
# 6. template_list — List All Available Templates
# ═══════════════════════════════════════════════════════════

def template_list(**kwargs: Any) -> dict[str, Any]:
    """List all available EA visualization templates.

    Returns:
        {status, templates: [...], total}
    """
    templates = [
        {"id": v["id"], "name": v["name"], "description": v["description"],
         "version": v["version"], "output_format": v["output_format"]}
        for v in _AVAILABLE_TEMPLATES.values()
    ]
    return {
        "status": "ok",
        "templates": templates,
        "total": len(templates),
    }
