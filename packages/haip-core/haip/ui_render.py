"""通用 Agent UI 渲染引擎 — Card-based layout with patient dropdown."""
from __future__ import annotations

import json


def render_agent_ui(name: str, cn_name: str, agent_type: str, port: int,
                    tools: list[dict], depends_on: list[dict],
                    guard_triggers: list[str], sub_agents: list[str],
                    patients: list[dict] | None = None) -> str:

    type_map = {"business": "业务智能体", "specialist": "专家智能体", "master_data": "主数据智能体"}

    # ── Build patient options HTML ──
    patient_options = ""
    patients_json = "[]"
    if patients:
        patients_json = json.dumps(patients, ensure_ascii=False)
        patient_options = "".join(
            f'<option value="{p.get("patient_id","")}">{p.get("patient_id","")} — {p.get("name","")} ({p.get("age","")}岁)</option>\n'
            for p in patients[:100]
        )

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
                fid = f"inp-{t['name']}-{field}"
                fields += f'<div class="form-group"><label for="{fid}">{field}</label>'
                if field == "patient_id":
                    # Render as dropdown populated from patient list
                    fields += f'<select id="{fid}" class="inp-{t["name"]} sel-patient-id" data-field="{field}">'
                    fields += f'<option value="">-- 选择患者 --</option>{patient_options}</select></div>\n'
                else:
                    fields += f'<input id="{fid}" class="inp-{t["name"]}" data-field="{field}" placeholder="{ftype}"></div>\n'
        else:
            fid = f"inp-{t['name']}-params"
            fields += f'<div class="form-group"><label for="{fid}">参数 (JSON)</label>'
            fields += f'<textarea id="{fid}" class="inp-{t["name"]}">{{}}</textarea></div>\n'

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
    <div class="sidebar-title" style="margin-top:16px">患者列表</div>
    <div class="patient-mini-list" id="patient-mini-list"></div>
  </div>

  <div class="main">
    {guard_html}
    <div class="tool-grid" id="tool-grid">
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
<script type="application/json" id="xhaip-patients">
{patients_json}
</script>
<script src="/static/agent.js"></script>
<script>
// Populate patient list in sidebar
(function(){{var pl=document.getElementById('patient-mini-list');if(!pl)return;
var pts=JSON.parse(document.getElementById('xhaip-patients').textContent);
if(!pts.length){{pl.innerHTML='<div style="padding:6px;font-size:11px;color:var(--text2)">暂无患者</div>';return;}}
var h='';pts.forEach(function(p){{h+='<div class=\"pmini\" onclick=\"selectPatientMini(\\''+p.patient_id+'\\')\" title=\"'+p.diagnosis+'\">'+p.patient_id+' — '+p.name+' ('+p.age+'岁)</div>';}});
pl.innerHTML=h;}})();

function selectPatientMini(pid){{
  var sel=document.querySelectorAll('.sel-patient-id');
  for(var i=0;i<sel.length;i++){{sel[i].value=pid;}}
}}
</script>
</body>
</html>"""
