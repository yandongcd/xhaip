"""EA Visual Templates — versioned template library for TOGAF architecture visualization.

Templates live in this directory, versioned as sub-modules.
Each template provides a render(data, theme) → str function.

Usage:
    from haip.togaf.templates import render_template, list_templates
    html = render_template("capability_heatmap", data=[...], theme={"--primary": "#2e86c1"})
"""

from __future__ import annotations

import importlib

TEMPLATE_MANIFEST: dict[str, dict] = {
    "capability_heatmap": {
        "name": "业务能力热力图",
        "description": "TOGAF Phase B — 能力成熟度/关键性/覆盖率矩阵",
        "version": "v1",
    },
    "stakeholder_map": {
        "name": "干系人地图",
        "description": "TOGAF Phase A — 权力·兴趣四象限矩阵",
        "version": "v1",
    },
    "roadmap": {
        "name": "架构路线图",
        "description": "TOGAF Phase F — 四阶段迁移时间线",
        "version": "v1",
    },
    "app_landscape": {
        "name": "应用全景图",
        "description": "TOGAF Phase C — 应用组合状态与技术栈",
        "version": "v1",
    },
    "value_stream_map": {
        "name": "价值流图",
        "description": "TOGAF Phase B — 端到端价值流阶段",
        "version": "v1",
    },
}


def list_templates() -> list[dict]:
    """List all available templates."""
    return [
        {
            "id": template_id,
            "name": meta["name"],
            "description": meta["description"],
            "version": meta["version"],
        }
        for template_id, meta in TEMPLATE_MANIFEST.items()
    ]


def render_template(
    name: str,
    data: list[dict] | dict | None = None,
    theme: dict[str, str] | None = None,
    *,
    full_page: bool = True,
) -> str:
    """Render a template by name.

    Args:
        name: Template ID (e.g. "capability_heatmap").
        data: Domain-specific data for the template.
        theme: Dict of CSS variable overrides.
        full_page: If True, return full HTML page; if False, return fragment.

    Returns:
        Rendered HTML string.

    Raises:
        ValueError: If template name is not found.
    """
    meta = TEMPLATE_MANIFEST.get(name)
    if not meta:
        available = ", ".join(TEMPLATE_MANIFEST.keys())
        raise ValueError(f"Template '{name}' not found. Available: {available}")

    module_path = f"haip.togaf.templates.{name}"
    mod = importlib.import_module(module_path)
    return mod.render(data=data, theme=theme, full_page=full_page)
