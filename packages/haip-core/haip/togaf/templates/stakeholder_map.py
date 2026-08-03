"""EA Visual Template v1: Stakeholder Map → TOGAF Stakeholder Catalog (Phase A)."""

from __future__ import annotations

from haip.togaf.templates._base import wrap_html

DEFAULT_DATA: dict = {
    "quadrants": {
        "keep_satisfied": {
            "label": "高权力 · 低兴趣 (Keep Satisfied)",
            "stakeholders": ["院领导", "医务处"],
            "color": "warning",
        },
        "key_players": {
            "label": "高权力 · 高兴趣 (Key Players)",
            "stakeholders": ["科室主任", "主治医生"],
            "color": "info",
        },
        "monitor": {
            "label": "低权力 · 低兴趣 (Monitor)",
            "stakeholders": ["信息科"],
            "color": "",
        },
        "keep_informed": {
            "label": "低权力 · 高兴趣 (Keep Informed)",
            "stakeholders": ["护士长", "药剂师"],
            "color": "success",
        },
    },
}


def render(
    data: dict | None = None,
    theme: dict[str, str] | None = None,
    *,
    full_page: bool = True,
    title: str = "干系人地图 — 权力·兴趣矩阵",
) -> str:
    """Render a stakeholder power/interest matrix as HTML.

    Args:
        data: Dict with key "quadrants" mapping quadrant names to
              {label, stakeholders: [str], color: str}.
        theme: CSS variable overrides.
        full_page: If True, wrap in full HTML page; if False, return fragment only.
        title: Page/element title.

    Returns:
        HTML string (full page or fragment).
    """
    q = (data or DEFAULT_DATA)["quadrants"]

    bg_map = {
        "keep_satisfied": "var(--warning-bg)",
        "key_players": "var(--info-bg)",
        "monitor": "var(--bg)",
        "keep_informed": "var(--success-bg)",
    }

    quadrants_html = ""
    for qid in ("keep_satisfied", "key_players", "monitor", "keep_informed"):
        info = q[qid]
        bg = bg_map[qid]
        border = ';border:1px solid var(--card-border)' if qid == "monitor" else ""
        badges = "".join(
            f'<span class="lx-badge {info["color"]}">{s}</span>'
            for s in info.get("stakeholders", [])
        )
        quadrants_html += (
            f'<div style="min-height:160px;padding:8px;background:{bg};'
            f'border-radius:var(--radius){border}">'
            f'<div style="font-size:var(--font-size-sm);color:var(--text-muted);'
            f'margin-bottom:8px">{info["label"]}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:4px">{badges}</div>'
            f"</div>"
        )

    body = f"""
<div class="lx-card">
  <div class="lx-card-title">{title}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;position:relative">
    {quadrants_html}
  </div>
</div>
<div class="lx-footer">TOGAF Phase A · 干系人管理 · v1</div>
"""
    if full_page:
        return wrap_html("干系人地图", body, theme)
    return body
