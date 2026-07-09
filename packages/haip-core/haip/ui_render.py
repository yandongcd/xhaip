"""通用 Agent UI 渲染引擎 — YAML → 专业工作台 HTML (radiology-cockpit gold standard)."""

from __future__ import annotations

import json


def render_agent_ui(name: str, cn_name: str, agent_type: str, port: int,
                    tools: list[dict], depends_on: list[dict],
                    guard_triggers: list[str], sub_agents: list[str]) -> str:
    """渲染 Agent 专业 UI。"""

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

    tools_json = json.dumps(tools, ensure_ascii=False)

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

    first_tab_label = tabs[0]["label"] if tabs else "工具调用"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip — {cn_name}</title>
<style>
/* ===== Gold Standard Design Tokens (radiology-cockpit SKILL) ===== */
:root{{--bg:#1c1c1e;--card-bg:#2c2c2e;--text:#f5f5f7;--text-secondary:#a1a1a6;--accent:#0a84ff;--danger:#ff453a;--warning:#ff9f0a;--success:#30d158;--purple:#bf5af2;--green:#30d158;--yellow:#ff9f0a;--red:#ff453a;--border:#38383a;--glow:rgba(10,132,255,.08);--bg-gradient:radial-gradient(ellipse at 50% 0%,var(--card-bg) 0%,var(--bg) 60%)}}
body.light{{--bg:#f2f2f7;--card-bg:#ffffff;--text:#1c1c1e;--text-secondary:#6e6e73;--accent:#007aff;--danger:#ff3b30;--warning:#ff9500;--success:#34c759;--purple:#af52de;--green:#34c759;--yellow:#ff9500;--red:#ff3b30;--border:#e5e5ea;--bg-gradient:radial-gradient(ellipse at 50% 0%,#ffffff 0%,#f2f2f7 60%)}}
body.light .header button:hover,body.light .header button.active{{color:#fff!important}}
body.light .sidebar{{background:var(--card-bg);border-right:1px solid var(--border)}}
body.light .sidebar h2{{color:var(--text)}}
body.light .tab{{color:var(--text-secondary)}}
body.light .tab.active{{color:#fff}}
body.light .result-box{{background:var(--bg);color:var(--text)}}
body.light .header-btn:hover{{background:var(--accent);color:#fff}}
body.light .sidebar .meta,.body.light .sidebar .foot{{color:var(--text-secondary)}}
body.light .panel-label{{color:var(--accent)}}
*{{margin:0;padding:0;box-sizing:border-box}}
::selection{{background:var(--accent);color:#fff}}
body{{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text','PingFang SC','Microsoft YaHei','Helvetica Neue',sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;background:var(--bg-gradient);color:var(--text);line-height:1.47;display:flex;height:100vh;overflow:hidden;letter-spacing:-.01em;transition:background .3s ease,color .3s ease}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:transparent}}::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}

/* Header */
.header{{height:52px;background:var(--card-bg);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px;flex-shrink:0;-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px)}}
.header h1{{font-size:17px;font-weight:600;display:flex;align-items:center;gap:10px;letter-spacing:-.02em}}
.header-meta{{font-size:11px;color:var(--text-secondary)}}
.header-right{{display:flex;align-items:center;gap:8px}}
.header-btn{{padding:5px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card-bg);color:var(--text);cursor:pointer;font-size:11px;font-weight:500;font-family:inherit;transition:all .15s cubic-bezier(0.4,0,0.2,1)}}
.header-btn:hover{{background:var(--accent);color:#fff;border-color:var(--accent);transform:scale(1.02)}}
.header-btn.active{{background:var(--accent);color:#fff;border-color:var(--accent)}}

/* Layout */
.app{{flex:1;display:flex;overflow:hidden}}
.sidebar{{width:200px;background:linear-gradient(180deg,#1a1a1a,#2B2B2B);color:#fff;overflow-y:auto;flex-shrink:0;display:flex;flex-direction:column;transition:background .3s ease}}
.sidebar h2{{padding:14px;font-size:15px;border-bottom:1px solid rgba(255,255,255,.1);display:flex;align-items:center;gap:6px}}
.sidebar .meta{{padding:8px 14px;font-size:10px;color:rgba(255,255,255,.4)}}
.tab{{display:block;padding:8px 14px;color:rgba(255,255,255,.6);cursor:pointer;font-size:12px;border-left:2px solid transparent;transition:all .15s ease}}
.tab:hover{{color:#fff;background:rgba(255,255,255,.05)}}
.tab.active{{color:#fff;border-left-color:var(--accent);background:rgba(10,132,255,.15)}}
.sidebar .foot{{padding:8px 14px;font-size:10px;color:rgba(255,255,255,.3);margin-top:auto;border-top:1px solid rgba(255,255,255,.1)}}

.main{{flex:1;display:flex;flex-direction:column;overflow:hidden}}
.content{{flex:1;display:flex;overflow:hidden}}
.left{{flex:1;padding:20px 24px;overflow-y:auto}}
.right{{width:300px;padding:16px;background:var(--card-bg);border-left:1px solid var(--border);overflow-y:auto;flex-shrink:0}}

/* Panel */
.panel{{display:none;animation:fadeIn .2s ease}}
.panel.active{{display:block}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:translateY(0)}}}}
.panel-label{{font-size:15px;font-weight:600;color:var(--accent);margin-bottom:4px}}
.panel-desc{{font-size:11px;color:var(--text-secondary);margin-bottom:16px;line-height:1.5}}

/* Form */
.form-group{{margin:8px 0}}.form-group label{{font-size:11px;color:var(--text-secondary);display:block;margin-bottom:4px;font-weight:500;text-transform:uppercase;letter-spacing:.04em}}
.form-group input,.form-group select,.form-group textarea{{padding:7px 12px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:13px;width:100%;font-family:inherit;transition:border-color .15s ease;outline:none}}
.form-group input:focus,.form-group textarea:focus{{border-color:var(--accent);box-shadow:0 0 0 3px rgba(10,132,255,.12)}}
.form-group textarea{{height:70px;resize:vertical;font-family:'SF Mono',SFMono-Regular,Consolas,monospace;line-height:1.5}}

/* Buttons */
.btn-row{{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap}}
.btn{{padding:7px 18px;border:none;border-radius:8px;font-size:12px;font-weight:590;cursor:pointer;font-family:inherit;transition:all .12s ease}}
.btn:active{{transform:scale(.96)}}
.btn-primary{{background:var(--accent);color:#fff}}.btn-primary:hover{{opacity:.9;box-shadow:0 4px 12px rgba(10,132,255,.3)}}
.btn-secondary{{background:transparent;color:var(--text);border:1px solid var(--border)}}.btn-secondary:hover{{border-color:var(--accent);color:var(--accent);background:rgba(10,132,255,.04)}}

/* Result */
.result-box{{background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:12px;padding:14px 18px;font-family:'SF Mono',SFMono-Regular,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;max-height:450px;overflow-y:auto;margin-top:10px;transition:background .3s ease}}

/* Right panel */
.right h4{{font-size:10px;color:var(--text-secondary);margin-bottom:8px;text-transform:uppercase;letter-spacing:.04em;font-weight:590}}
.tag-list{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:16px}}
.risk-tag{{display:inline-block;padding:2px 8px;background:rgba(255,69,58,.12);color:var(--danger);border-radius:4px;font-size:10px;font-weight:500}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#060d14}}
.badge-green{{background:var(--green)}}.badge-yellow{{background:var(--warning)}}.badge-red{{background:var(--red)}}.badge-purple{{background:var(--purple)}}
#history-list{{font-size:11px}}.history-item{{padding:5px 0;border-bottom:1px solid var(--border);font-size:11px;display:flex;justify-content:space-between;align-items:center}}
.hist-tool{{color:var(--accent);font-weight:500}}.hist-status{{font-size:10px}}.hist-time{{color:var(--text-secondary);font-size:10px}}

/* Responsive */
@media(max-width:768px){{.sidebar{{width:160px}}.right{{width:240px}}}}
</style>
</head>
<body>
<div class="header">
  <h1>{icon_map.get(agent_type, '🤖')} {cn_name}</h1>
  <div class="header-right">
    <span class="header-meta">{name} | {type_map.get(agent_type, '')} | port:{port}</span>
    <button class="header-btn" id="btn-theme" onclick="toggleTheme()" title="切换主题">🌙 黑夜</button>
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
<script>
var AGENT='{name}';var TOOLS={tools_json};var HISTORY=[];
(function(){{var t=localStorage.getItem('xhaip_theme')||'dark';if(t==='light'){{document.body.classList.add('light');document.getElementById('btn-theme').innerHTML='☀️ 白天'}}}})();
function toggleTheme(){{var isLight=document.body.classList.toggle('light');localStorage.setItem('xhaip_theme',isLight?'light':'dark');document.getElementById('btn-theme').innerHTML=isLight?'☀️ 白天':'🌙 黑夜'}}
function showTab(t){{document.querySelectorAll('.tab').forEach(function(e){{e.classList.remove('active')}});document.querySelectorAll('.panel').forEach(function(e){{e.classList.remove('active')}});var el=document.querySelector('.tab[onclick*="'+t+'"]');if(el)el.classList.add('active');var p=document.getElementById('panel-'+t);if(p)p.classList.add('active')}}
async function callTool(tool){{
  var params={{}};var toolDef=TOOLS.find(function(t){{return t.name===tool}});
  if(toolDef&&Object.keys(toolDef.input||{{}}).length){{
    for(var k in toolDef.input){{params[k]=document.querySelector('.inp-'+tool+'[data-field="'+k+'"]')?.value||toolDef.input[k]}}
  }}else{{
    try{{var el=document.querySelector('.inp-'+tool);if(el)params=JSON.parse(el.value||'{{}}')}}catch(e){{}}
  }}
  var el=document.getElementById('result-'+tool);el.textContent='执行中...';
  try{{
    var r=await fetch('/api/call',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{agent:AGENT,tool:tool,params:params}})}});
    var d=await r.json();el.textContent=JSON.stringify(d,null,2);
    addHistory(tool,d.status||'ok');
  }}catch(e){{el.textContent='Error: '+e.message}}
}}
async function runGuard(tool){{
  var output=document.getElementById('result-'+tool)?.textContent||'';
  var r=await fetch('/api/guard',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{output:output,agent:AGENT}})}});
  var d=await r.json();document.getElementById('result-'+tool).textContent='安全校验结果:\\n'+JSON.stringify(d,null,2)
}}
function addHistory(tool,status){{
  HISTORY.unshift({{tool:tool,time:new Date().toLocaleTimeString('zh-CN'),status:status}});
  if(HISTORY.length>10)HISTORY.pop();
  var color=status==='ok'?'var(--success)':'var(--danger)';
  document.getElementById('history-list').innerHTML=HISTORY.map(function(e){{return '<div class="history-item"><span class="hist-tool">'+e.tool+'</span><span class="hist-status" style="color:'+color+'">'+e.status+'</span><span class="hist-time">'+e.time+'</span></div>'}}).join('')
}}
</script>
</body>
</html>"""
    return html
