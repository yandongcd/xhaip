"""EA Visual Template v1: Roadmap Timeline → TOGAF Transition Architecture (Phase F)."""

from __future__ import annotations

from haip.togaf.templates._base import wrap_html

DEFAULT_DATA: list[dict] = [
    {
        "phase": "Phase 1 · Q3 2026",
        "title": "基础框架搭建",
        "status": "success",
        "items": ["Rules Agent 上线", "TOGAF 元模型 v1", "医疗数据模型标准化"],
    },
    {
        "phase": "Phase 2 · Q4 2026",
        "title": "Agent 扩展",
        "status": "info",
        "items": ["33 科室 Agent 上线", "MCP 容器化部署", "Nexent 集成测试"],
    },
    {
        "phase": "Phase 3 · Q1 2027",
        "title": "智能化升级",
        "status": "warning",
        "items": ["AI 辅助诊断", "实时数据接入", "全院指标面板"],
    },
    {
        "phase": "Phase 4 · Q2 2027",
        "title": "生态扩展",
        "status": "danger",
        "items": ["多院区部署", "外部系统互联", "区域医疗协同"],
    },
]


def render(
    data: list[dict] | None = None,
    theme: dict[str, str] | None = None,
    *,
    full_page: bool = True,
    title: str = "架构路线图",
) -> str:
    """Render an architecture roadmap timeline as HTML.

    Args:
        data: List of phase dicts with keys: phase (label), title, status (badge color),
              items (list of task strings).
        theme: CSS variable overrides.
        full_page: If True, wrap in full HTML page; if False, return fragment only.
        title: Page/element title.

    Returns:
        HTML string (full page or fragment).
    """
    phases = data or DEFAULT_DATA

    rows = ""
    for p in phases:
        items_html = "".join(f"<li>{item}</li>" for item in p.get("items", []))
        rows += (
            '<div style="display:flex;align-items:flex-start;gap:12px;'
            'padding:12px 0;border-bottom:1px solid var(--card-border)">'
            f'<div style="min-width:120px;font-size:var(--font-size-sm);'
            f'color:var(--text-muted);padding-top:2px">{p["phase"]}</div>'
            f'<div style="flex:1">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
            f'<span class="lx-badge {p["status"]}">{p["title"]}</span>'
            f'</div>'
            f'<ul style="padding-left:18px;font-size:var(--font-size)">{items_html}</ul>'
            f'</div></div>'
        )

    body = f"""
<div class="lx-card">
  <div class="lx-card-title">{title}</div>
  {rows}
</div>
<div class="lx-footer">TOGAF Phase F · 迁移规划 · v1</div>
"""
    if full_page:
        return wrap_html("架构路线图", body, theme)
    return body
