"""EA Visual Template v1: Application Landscape → TOGAF Application Portfolio (Phase C)."""

from __future__ import annotations

from haip.togaf.templates._base import wrap_html

DEFAULT_DATA: list[dict] = [
    {"name": "患者数据中心", "type": "Master Data", "status": "Active", "health": "success", "tech": "Python 3.12"},
    {"name": "Rules Agent", "type": "Master Data", "status": "Active", "health": "success", "tech": "Python 3.12"},
    {"name": "TOGAF Agent", "type": "Infrastructure", "status": "Active", "health": "info", "tech": "Python 3.12"},
    {"name": "NX Agent", "type": "Infrastructure", "status": "Active", "health": "success", "tech": "Python 3.12"},
    {"name": "创伤骨科 Agent", "type": "Business", "status": "Active", "health": "success", "tech": "Python 3.12"},
    {"name": "药剂科 Agent", "type": "Business", "status": "Active", "health": "success", "tech": "Python 3.12"},
    {"name": "心血管外科 Agent", "type": "Business", "status": "Active", "health": "warning", "tech": "Python 3.12"},
    {"name": "HAIP 门户", "type": "Infrastructure", "status": "Active", "health": "success", "tech": "Python 3.12"},
    {"name": "骨科 AI 辅助诊断", "type": "Business", "status": "Planned", "health": "danger", "tech": "TBD"},
]


def render(
    data: list[dict] | None = None,
    theme: dict[str, str] | None = None,
    *,
    full_page: bool = True,
    title: str = "应用全景图",
) -> str:
    """Render an application landscape portfolio table as HTML.

    Args:
        data: List of app dicts with keys: name, type, status (Active/Planned/Retired),
              health (badge color), tech (technology stack).
        theme: CSS variable overrides.
        full_page: If True, wrap in full HTML page; if False, return fragment only.
        title: Page/element title.

    Returns:
        HTML string (full page or fragment).
    """
    apps = data or DEFAULT_DATA

    rows = ""
    for a in apps:
        rows += (
            f"<tr>"
            f"<td><strong>{a['name']}</strong></td>"
            f"<td><span class=\"lx-badge info\">{a['type']}</span></td>"
            f"<td><span class=\"lx-badge {a['health']}\">{a['status']}</span></td>"
            f"<td style=\"color:var(--text-secondary)\">{a['tech']}</td>"
            f"</tr>"
        )

    body = f"""
<div class="lx-card">
  <div class="lx-card-title">{title}</div>
  <table class="lx-table">
    <thead><tr><th>应用</th><th>类型</th><th>状态</th><th>技术栈</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<div class="lx-footer">TOGAF Phase C · 应用架构 · v1</div>
"""
    if full_page:
        return wrap_html("应用全景图", body, theme)
    return body
