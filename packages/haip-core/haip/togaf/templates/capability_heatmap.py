"""EA Visual Template v1: Capability Heatmap → TOGAF Business Capability Map (Phase B)."""

from __future__ import annotations

from haip.togaf.templates._base import wrap_html


DEFAULT_DATA: list[dict] = [
    {"capability": "临床诊疗", "maturity": 4, "criticality": 5, "coverage": 0.85},
    {"capability": "影像诊断", "maturity": 4, "criticality": 5, "coverage": 0.90},
    {"capability": "检验服务", "maturity": 3, "criticality": 5, "coverage": 0.80},
    {"capability": "药事管理", "maturity": 4, "criticality": 4, "coverage": 0.75},
    {"capability": "手术管理", "maturity": 3, "criticality": 5, "coverage": 0.70},
    {"capability": "护理服务", "maturity": 3, "criticality": 4, "coverage": 0.78},
    {"capability": "康复管理", "maturity": 2, "criticality": 3, "coverage": 0.50},
    {"capability": "远程医疗", "maturity": 2, "criticality": 3, "coverage": 0.40},
]

MATURITY_LABELS: dict[int, str] = {
    1: "初始",
    2: "已管理",
    3: "已定义",
    4: "量化管理",
    5: "优化",
}


def render(
    data: list[dict] | None = None,
    theme: dict[str, str] | None = None,
    *,
    full_page: bool = True,
    title: str = "业务能力热力图",
) -> str:
    """Render a capability heatmap as HTML.

    Args:
        data: List of dicts with keys: capability, maturity (1-5), criticality (1-5),
              coverage (0.0-1.0).
        theme: CSS variable overrides.
        full_page: If True, wrap in full HTML page; if False, return fragment only.
        title: Page/element title.

    Returns:
        HTML string (full page or fragment).
    """
    items = data or DEFAULT_DATA

    rows = ""
    for d in items:
        if d["maturity"] >= 4:
            color = "success"
        elif d["maturity"] >= 3:
            color = "warning"
        else:
            color = "danger"
        maturity_label = MATURITY_LABELS.get(d["maturity"], f"L{d['maturity']}")
        rows += (
            f"<tr>"
            f"<td><strong>{d['capability']}</strong></td>"
            f"<td><span class=\"lx-badge {color}\">{maturity_label}</span></td>"
            f"<td><span class=\"lx-badge primary\">{chr(9733) * d['criticality']}</span></td>"
            f"<td style=\"text-align:right\">{int(d['coverage'] * 100)}%</td>"
            f"</tr>"
        )

    body = f"""
<div class="lx-card">
  <div class="lx-card-title">{title}</div>
  <table class="lx-table">
    <thead><tr><th>能力域</th><th>成熟度</th><th>关键性</th><th style="text-align:right">覆盖率</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<div class="lx-footer">TOGAF Phase B · 业务架构 · v1</div>
"""
    if full_page:
        return wrap_html(title, body, theme)
    return body
