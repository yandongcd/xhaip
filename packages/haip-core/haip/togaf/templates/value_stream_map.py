"""EA Visual Template v1: Value Stream Map → TOGAF Value Stream (Phase B)."""

from __future__ import annotations

from haip.togaf.templates._base import wrap_html


DEFAULT_DATA: list[dict] = [
    {"name": "分诊登记", "desc": "患者到达→预检分诊→建档", "kpi": "分诊时间 < 5min"},
    {"name": "评估诊断", "desc": "病史采集→体格检查→辅助检查→确认", "kpi": "评估时间 < 30min"},
    {"name": "治疗决策", "desc": "制定方案→知情同意→MDT 协调", "kpi": "MDT 比例 > 80%"},
    {"name": "治疗执行", "desc": "手术/药物/康复→过程监护", "kpi": "并发症率 < 5%"},
    {"name": "康复随访", "desc": "功能评估→康复计划→定期随访", "kpi": "随访率 > 90%"},
]

STAGE_BGS: list[str] = [
    "var(--primary-bg)",
    "var(--info-bg)",
    "var(--warning-bg)",
    "var(--success-bg)",
    "var(--secondary-bg)",
]


def render(
    data: list[dict] | None = None,
    theme: dict[str, str] | None = None,
    *,
    full_page: bool = True,
    title: str = "价值流：临床诊疗路径",
) -> str:
    """Render a value stream map as HTML.

    Args:
        data: List of stage dicts with keys: name, desc, kpi (optional).
        theme: CSS variable overrides.
        full_page: If True, wrap in full HTML page; if False, return fragment only.
        title: Page/element title.

    Returns:
        HTML string (full page or fragment).
    """
    stages = data or DEFAULT_DATA

    steps = ""
    for i, s in enumerate(stages):
        bg = STAGE_BGS[i % len(STAGE_BGS)]
        steps += (
            f'<div style="flex:1;min-width:140px;padding:14px;background:{bg};'
            f'border-radius:var(--radius);text-align:center">'
            f'<div style="font-weight:700;margin-bottom:4px;color:var(--text)">{s["name"]}</div>'
            f'<div style="font-size:var(--font-size-sm);color:var(--text-secondary);'
            f'margin-bottom:6px">{s["desc"]}</div>'
        )
        if s.get("kpi"):
            steps += f'<span class="lx-badge info">{s["kpi"]}</span>'
        steps += "</div>"
        if i < len(stages) - 1:
            steps += (
                '<div style="display:flex;align-items:center;color:var(--text-muted);'
                'font-size:18px">→</div>'
            )

    body = f"""
<div class="lx-card">
  <div class="lx-card-title">{title}</div>
  <div style="display:flex;align-items:stretch;gap:8px;overflow-x:auto;padding:8px 0">
    {steps}
  </div>
</div>
<div class="lx-footer">TOGAF Phase B · 价值流 · v1</div>
"""
    if full_page:
        return wrap_html("价值流图", body, theme)
    return body
