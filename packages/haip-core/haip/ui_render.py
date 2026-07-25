"""通用 Agent UI 渲染引擎 — Card-based layout."""

from __future__ import annotations

import json


def render_agent_ui(name: str, cn_name: str, agent_type: str, port: int,
                    tools: list[dict], depends_on: list[dict],
                    guard_triggers: list[str], sub_agents: list[str]) -> str:

    type_map = {"business": "业务智能体", "specialist": "专家智能体", "master_data": "主数据智能体"}

    # ── Sidebar tabs ──
    sb = ""
    for i, t in enumerate(tools):
        desc = t.get("description", "")
        label = desc.split("(")[0].split("（")[0].strip() if desc else t["name"]
        if len(label) > 12:
            label = label[:10] + "…"
        cls = ' active' if i == 0 else ''
        sb += f'        <div class="tab{cls}" onclick="showTab(\'{t["name"]}\')">{label}</div>\n'

    # ── Tool cards ──
    cards = ""
    for t in tools:
        inp = t.get("input", {})
        desc = t.get("description", "")
        label = desc.split("(")[0].split("（")[0].strip() if desc else t["name"]
        fields = ""
        if inp:
            for field, ftype in inp.items():
                fields += f'<div class="form-group"><label>{field}</label>'
                fields += f'<input class="inp-{t["name"]}" data-field="{field}" value="" placeholder="{ftype}"></div>\n'
        else:
            fields += '<div class="form-group"><label>参数 (JSON)</label>'
            fields += f'<textarea class="inp-{t["name"]}">{{}}</textarea></div>\n'

        cards += f'''    <div class="tool-card" id="card-{t["name"]}">
      <h3>{label}</h3>
      <div class="tool-desc">{desc}</div>
      {fields}
      <div class="btn-row">
        <button class="btn btn-primary" onclick="callTool('{t["name"]}')">执行</button>
        <button class="btn btn-secondary" onclick="runGuard('{t["name"]}')">安全校验</button>
      </div>
      <div class="result-box" id="result-{t["name"]}">点击执行...</div>
    </div>
'''

    # ── Guard banner ──
    guard_html = ""
    if guard_triggers:
        tags = " ".join(f'<span class="risk-tag">{t}</span>' for t in guard_triggers)
        guard_html = f'<div class="guard-banner"><span class="guard-label">安全触发规则</span>{tags}</div>'

    xhaip_data = json.dumps({"name": name, "tools": tools}, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip — {cn_name}</title>
<link rel="stylesheet" href="/static/agent.css">
</head>
<body>

<div class="header">
  <h1><span class="icon">🏥</span> {cn_name}</h1>
  <span class="header-meta">{name} | {type_map.get(agent_type, '')} | port {port} | {len(tools)} tools</span>
</div>

<div class="container">

  <div class="sidebar">
    <div class="sidebar-title">工具列表</div>
{sb}
    <div class="sidebar-foot">{len(tools)} 个工具</div>
  </div>

  <div class="main">
    {guard_html}
    <div class="tool-grid">
{cards}    </div>
  </div>

  <div class="history-panel">
    <h4>调用历史</h4>
    <div id="history-list">
      <div style="color:var(--text2);font-size:12px">暂无记录</div>
    </div>
  </div>

</div>

<script type="application/json" id="xhaip-data">
{xhaip_data}
</script>
<script src="/static/agent.js"></script>
</body>
</html>"""
