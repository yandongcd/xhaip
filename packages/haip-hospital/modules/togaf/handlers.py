"""TOGAF Agent MCP Handlers — bridge between A2A dispatch and haip.togaf core.

Each handler accepts **kwargs for flexible parameter passing, delegates to the
corresponding haip.togaf function, and returns a standardised {"status": ..., ...}
response dict.
"""

from __future__ import annotations

from typing import Any


# ── metamodel_list ────────────────────────────────────────────────────────────

def metamodel_list(entity_type: str = "", **kwargs: Any) -> dict[str, Any]:
    """List TOGAF 10 entity types and relationship types."""
    try:
        from haip.togaf.metamodel import list_entity_types, list_relationship_types

        entities = list_entity_types()
        if entity_type:
            entities = [e for e in entities if e["id"] == entity_type]

        return {
            "status": "ok",
            "result": {
                "entity_types": entities,
                "relationship_types": list_relationship_types(),
            },
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── architecture_build ────────────────────────────────────────────────────────

def architecture_build(department: str = "", dept: str = "", **kwargs: Any) -> dict[str, Any]:
    """Build a TOGAF 4A architecture instance for a department."""
    try:
        from haip.togaf.builder import build_to_dict

        target = department or dept or "orthopedic"
        result = build_to_dict(target)
        if result is None:
            return {
                "status": "error",
                "error": f"Unknown department: {target}",
            }
        return {"status": "ok", "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── layout_graph ──────────────────────────────────────────────────────────────

def layout_graph(
    nodes: list[dict] | None = None,
    edges: list[dict] | None = None,
    width: int = 1200,
    height: int = 800,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compute force-directed layout coordinates for a graph."""
    try:
        from haip.togaf.layout import compute_layout

        if not nodes:
            return {"status": "error", "error": "nodes is required"}
        if not edges:
            edges = []

        result = compute_layout(nodes, edges, width=width, height=height)
        return {"status": "ok", "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── audit_environment ─────────────────────────────────────────────────────────

def audit_environment(**kwargs: Any) -> dict[str, Any]:
    """Scan and discover the current deployment environment architecture."""
    try:
        from haip.togaf.audit import audit_environment as _audit

        result = _audit()
        return {"status": "ok", "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── template_render ───────────────────────────────────────────────────────────

_TEMPLATE_HTML: dict[str, str] = {
    # Templates now rendered dynamically by _render_template_real()
}
_TEMPLATE_CACHE: dict[str, str] = {}


def _render_template_real(name: str, dept: str = "orthopedic") -> str:
    """Render EA template with real builder data."""
    if name in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[name]

    from haip.togaf.builder import build_to_dict

    arch_data = build_to_dict(dept)
    if not arch_data:
        return f"<html><body><h1>Error</h1><p>No architecture data for {dept}</p></body></html>"

    nodes = arch_data.get("nodes", [])

    if name == "capability_heatmap":
        from haip.togaf.templates.capability_heatmap import render as render_heatmap, DEFAULT_DATA
        capabilities = [
            {"capability": n["name"], "maturity": min(5, 3 + n.get("properties", {}).get("stage", 0)),
             "criticality": 4 if n["layer"] == "Business" else 3, "coverage": 0.75}
            for n in nodes if n["layer"] in ("Business", "Application")
        ]
        html = render_heatmap(capabilities or DEFAULT_DATA)
    elif name == "app_landscape":
        from haip.togaf.templates.app_landscape import render as render_app, DEFAULT_DATA
        apps = [
            {"name": n["name"], "type": n["type"], "status": "active",
             "version": "1.0", "owner": n.get("properties", {}).get("owner", dept)}
            for n in nodes if n["layer"] == "Application"
        ]
        html = render_app(apps or DEFAULT_DATA)
    elif name == "value_stream":
        from haip.togaf.templates.value_stream_map import render as render_vs, DEFAULT_DATA
        stages = [{"name": n["name"], "order": n.get("properties", {}).get("stage", 0)}
                  for n in nodes if n["type"] == "BusinessService"]
        html = render_vs(stages or DEFAULT_DATA)
    else:
        html = ea_templates.render_template(name, arch_data)

    _TEMPLATE_CACHE[name] = html
    return html

_TEMPLATE_META: dict[str, dict[str, str]] = {
    "capability_heatmap": {
        "name": "业务能力热力图",
        "description": "TOGAF Phase B — 能力成熟度 / 关键性 / 覆盖率矩阵",
    },
    "stakeholder_map": {
        "name": "干系人地图",
        "description": "TOGAF Phase A — 权力·兴趣四象限矩阵",
    },
    "roadmap": {
        "name": "架构路线图",
        "description": "TOGAF Phase F — 四阶段迁移时间线",
    },
    "app_landscape": {
        "name": "应用全景图",
        "description": "TOGAF Phase C — 应用组合状态与技术栈",
    },
    "value_stream": {
        "name": "价值流图",
        "description": "TOGAF Phase B — 端到端价值流阶段",
    },
}


def template_render(name: str = "", theme: dict[str, str] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Render an EA visualisation template with real data."""
    try:
        dept = kwargs.get("department", kwargs.get("dept", "orthopedic"))
        html = _TEMPLATE_HTML.get(name)
        if html is None:
            # Generate from real templates + builder data
            try:
                html = _render_template_real(name, dept)
            except Exception:
                available = list(_TEMPLATE_META.keys())
                return {"status": "error",
                        "error": f"Unknown template: {name}. Available: {', '.join(available)}"}
        return {"status": "ok", "result": {"template": name, "html": html[:5000], "rendered": True}}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── template_list ─────────────────────────────────────────────────────────────

def template_list(**kwargs: Any) -> dict[str, Any]:
    """List all available EA visualisation templates."""
    try:
        templates = [
            {"id": tid, "name": meta["name"], "description": meta["description"]}
            for tid, meta in _TEMPLATE_META.items()
        ]
        return {"status": "ok", "result": {"templates": templates}}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
