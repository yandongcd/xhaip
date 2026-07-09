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
    "capability_heatmap": """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>业务能力热力图 · EA Templates</title></head>
<body style="font-family:sans-serif;padding:2rem">
<h1>业务能力热力图</h1><p>TOGAF Phase B — 能力成熟度 / 关键性 / 覆盖率矩阵（占位模板，完整 HTML 见 templates/）</p>
</body></html>""",
    "stakeholder_map": """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>干系人地图 · EA Templates</title></head>
<body style="font-family:sans-serif;padding:2rem">
<h1>干系人地图</h1><p>TOGAF Phase A — 权力·兴趣四象限矩阵（占位模板，完整 HTML 见 templates/）</p>
</body></html>""",
    "roadmap": """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>架构路线图 · EA Templates</title></head>
<body style="font-family:sans-serif;padding:2rem">
<h1>架构路线图</h1><p>TOGAF Phase F — 四阶段迁移时间线（占位模板，完整 HTML 见 templates/）</p>
</body></html>""",
    "app_landscape": """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>应用全景图 · EA Templates</title></head>
<body style="font-family:sans-serif;padding:2rem">
<h1>应用全景图</h1><p>TOGAF Phase C — 应用组合状态与技术栈（占位模板，完整 HTML 见 templates/）</p>
</body></html>""",
    "value_stream": """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>价值流图 · EA Templates</title></head>
<body style="font-family:sans-serif;padding:2rem">
<h1>价值流图</h1><p>TOGAF Phase B — 端到端价值流阶段（占位模板，完整 HTML 见 templates/）</p>
</body></html>""",
}

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
    """Render an EA visualisation template by name."""
    try:
        html = _TEMPLATE_HTML.get(name)
        if html is None:
            available = ", ".join(_TEMPLATE_HTML.keys())
            return {
                "status": "error",
                "error": f"Template '{name}' not found. Available: {available}",
            }

        # Apply theme as CSS variables override inline if provided
        if theme:
            css_vars = ";".join(f"{k}:{v}" for k, v in theme.items())
            html = html.replace("</head>", f"<style>:root{{{css_vars}}}</style></head>")

        return {"status": "ok", "result": html}
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
