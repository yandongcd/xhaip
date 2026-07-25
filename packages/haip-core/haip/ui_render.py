"""通用 Agent UI 渲染引擎 — YAML → 专业工作台 HTML."""

from __future__ import annotations

import json


def render_agent_ui(name: str, cn_name: str, agent_type: str, port: int,
                    tools: list[dict], depends_on: list[dict],
                    guard_triggers: list[str], sub_agents: list[str]) -> str:

    icon_map = {"business": "🏥", "specialist": "🔬", "master_data": "🗄️"}
    type_map = {"business": "业务智能体", "specialist": "专家智能体", "master_data": "主数据智能体"}

    tabs = []
    for t in tools:
        inp = t.get("input", {})
        desc = t.get("description", "")
        label = desc.split("(")[0].split("（")[0].strip() if desc else t["name"]
        if len(label) > 12:
            label = label[:10] + "…"
        tabs.append({"id": t["name"], "label": label,
                     "desc": desc,
                     "inputs": {k: str(v) for k, v in inp.items()} if inp else {},
                     "default_params": json.dumps(inp, indent=2) if inp else "{}"})

    sb = ""
    for i, t in enumerate(tabs):
        cls = ' active' if i == 0 else ''
        sb += f'          <div class="tab{cls}" onclick="showTab(\'{t["id"]}\')">{t["label"]}</div>\n'

    pn = ""
    for i, t in enumerate(tabs):
        cls = ' active' if i == 0 else ''
        pn += f'        <div class="panel{cls}" id="panel-{t["id"]}">\n'
        pn += f'          <div class="panel-label">{t["label"]}</div>\n'
        pn += f'          <p class="panel-desc">{t["desc"]}</p>\n'
        if t["inputs"]:
            for field, placeholder in t["inputs"].items():
                pn += f'          <div class="form-group"><label>{field}</label>'
                pn += f'<input class="inp-{t["id"]}" data-field="{field}" value="{placeholder}"></div>\n'
        else:
            pn += '          <div class="form-group"><label>参数 (JSON)</label>'
            pn += f'<textarea class="inp-{t["id"]}" style="height:80px">{t["default_params"]}</textarea></div>\n'
        pn += f'          <div class="btn-row"><button class="btn btn-primary" onclick="callTool(\'{t["id"]}\')">执行 {t["label"]}</button>'
        pn += f'<button class="btn btn-secondary" onclick="runGuard(\'{t["id"]}\')">安全校验</button></div>\n'
        pn += f'          <div class="result-box" id="result-{t["id"]}">点击执行...</div>\n        </div>\n'

    guard_rp = ""
    if guard_triggers:
        gtags = " ".join(f'<span class="risk-tag">{t}</span>' for t in guard_triggers)
        guard_rp = '<h4>高危触发</h4>'
        guard_rp += f'<div class="tag-list">{gtags}</div>'

    xhaip_data = json.dumps({
        "name": name,
        "tools": tools,
    }, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip — {cn_name}</title>
<link rel="stylesheet" href="/static/agent.css">
</head>
<body>
<div class="header">
  <h1>{icon_map.get(agent_type, '🤖')} {cn_name}</h1>
  <div class="header-right">
    <span class="header-meta">{name} | {type_map.get(agent_type, '')} | port:{port}</span>
  </div>
</div>
<div class="app">
<div class="sidebar">
  <h2>{icon_map.get(agent_type, '🤖')} {cn_name}</h2>
  <div class="meta">{name} | {agent_type}</div>
{sb}
  <div class="foot">{len(tools)} tools | {type_map.get(agent_type, '')}</div>
</div>
<div class="main">
  <div class="content">
    <div class="left">
{pn}    </div>
    <div class="right">
      <div class="card">{guard_rp}</div>
      <h4 style="margin-top:14px">调用历史</h4>
      <div id="history-list"></div>
    </div>
  </div>
</div>
</div>

<script type="application/json" id="xhaip-data">
{xhaip_data}
</script>
<script src="/static/agent.js"></script>
</body>
</html>"""
