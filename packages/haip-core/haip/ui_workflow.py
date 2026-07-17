"""工作流 UI — process 同款三栏布局 + 角色 stage 筛选 + 工具执行."""

from __future__ import annotations

import json

from haip.patients import load_patients


def _build_role_pills(roles: dict) -> tuple[str, str]:
    """角色 Pill HTML + 首个角色 id."""
    pills = ""
    first_role = ""
    for rid, rcfg in roles.items():
        if not first_role:
            first_role = rid
        icon = rcfg.get("icon", "")
        role_label = rcfg.get("name", rid)
        pills += (
            f'<button class="role-pill" data-role="{rid}" '
            f'onclick="switchRole(\'{rid}\')">{icon} {role_label}</button>\n'
        )
    return pills, first_role


def _build_stage_nav(stages: list[dict]) -> str:
    """右侧阶段导航 HTML."""
    items = ""
    for s in stages:
        items += (
            f'<div class="rb-item" data-stage="{s["order"]}" onclick="clickStage({s["order"]})">'
            f'<span class="rb-dot current"></span>'
            f'<div class="rb-info"><div class="rb-name">{s["order"]}. {s["label"]}</div></div>'
            f'<span class="rb-status active-s">当前</span></div>\n'
        )
    return items


def _build_stage_panels(stages: list[dict]) -> str:
    """阶段面板 HTML (带执行按钮)."""
    panels = ""
    for i, s in enumerate(stages):
        act = " active" if i == 0 else ""
        tool_name = s["tool"]
        panels += (
            f'<div class="stage-content{act}" id="stage-{s["order"]}">'
            f'<div class="stage-header"><span class="stage-badge">{s["order"]}</span>'
            f'<div><h3>{s["label"]}</h3><p>{s["description"]}</p>'
            f'<span class="guide-ref">{s.get("guideline_ref", "")}</span></div></div>'
            f'<div class="form-group"><label>参数</label>'
            f'<textarea id="params-{s["id"]}" '
            f'placeholder="请先在左侧选择数字病人, 参数将自动填充"></textarea></div>'
            f'<div class="btn-row">'
            f'<button class="btn-exec" onclick="callStage(\'{s["id"]}\',\'{tool_name}\')">'
            f'▶ 执行 {s["label"]}</button>'
            f'<button class="btn-guard" onclick="showGuard(\'{s["id"]}\')">🛡 安全校验</button>'
        )
        if i < len(stages) - 1:
            panels += (
                f'<button class="btn-next" '
                f'onclick="autoNext(\'{s["id"]}\',\'{stages[i + 1]["id"]}\')">→ 下一步</button>'
            )
        panels += (
            f'</div>'
            f'<div class="result-box" id="result-{s["id"]}">'
            f'<span class="result-placeholder">点击「执行」开始...</span></div>'
            f'</div>\n'
        )
    return panels


def render_workflow_ui(
    name: str,
    cn_name: str,
    agent_type: str,
    port: int,
    tools: list[dict],
    workflow_stages: list[dict],
    roles: dict,
    guard_triggers: list[str],
) -> str:
    icon_map = {"business": "🏥", "specialist": "🔬", "master_data": "🗄️"}
    patients = load_patients(name)

    wf_json = json.dumps(workflow_stages, ensure_ascii=False)
    roles_json = json.dumps(roles, ensure_ascii=False)
    patients_json = json.dumps(patients, ensure_ascii=False)

    # ── 角色 Pill ──
    role_pills, first_role = _build_role_pills(roles)

    # ── 右侧阶段导航 ──
    sb_items = _build_stage_nav(workflow_stages)

    # ── 阶段面板 (带执行按钮) ──
    panels = _build_stage_panels(workflow_stages)

    # ── Guard ──
    guard_html = ""
    if guard_triggers:
        tags = " ".join(f'<span class="tag red">{t}</span>' for t in guard_triggers)
        guard_html = (
            '<div class="rb-stats"><div class="rb-stat"><span>⚠ 高危触发</span></div>'
            f'<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:3px">{tags}</div></div>'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{cn_name} · 诊疗流程 — HAIP</title>
<style>
:root{{
  --bg-default:#ffffff;--bg-overlay:#f6f8fa;--bg-inset:#f0f3f6;
  --bg-subtle:#e8ecf0;--bg-elevated:#ffffff;--border:#d0d7de;
  --border-muted:#e1e5ea;--text:#1f2328;--text2:#656d76;
  --text3:#8b949e;--accent:#0969da;--accent-hover:#0550ae;
  --red:#cf222e;--red-bg:rgba(207,34,46,0.10);
  --blue:#0969da;--blue-bg:rgba(9,105,218,0.10);
  --green:#1a7f37;--green-bg:rgba(26,127,55,0.10);
  --amber:#8b6914;--amber-bg:rgba(139,105,20,0.10);
  --purple:#6e5494;--purple-bg:rgba(110,84,148,0.10);
  --radius:8px;--radius-sm:6px;--radius-full:999px;
  --shadow-sm:0 1px 3px rgba(0,0,0,0.06);
  --shadow-md:0 4px 12px rgba(0,0,0,0.08);
  --fs-sm:12px;--fs-base:14px;--fs-lg:16px;--fs-xl:20px;
  --h:52px;
}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
html{{font-size:16px;-webkit-font-smoothing:antialiased}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif;background:var(--bg-default);color:var(--text);min-height:100vh;font-size:14px;line-height:1.47;display:flex;flex-direction:column}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:transparent}}::-webkit-scrollbar-thumb{{background:var(--border-muted);border-radius:3px}}

/* Header */
.header{{flex-shrink:0;z-index:100;background:var(--bg-elevated);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;height:var(--h);gap:12px}}
.header h1{{font-size:16px;font-weight:700;color:var(--accent);display:flex;align-items:center;gap:6px;white-space:nowrap}}
.header-role{{display:flex;gap:4px;margin-left:12px;flex-wrap:wrap}}
.role-pill{{background:transparent;border:1px solid var(--border);border-radius:var(--radius-full);padding:3px 12px;font-size:12px;cursor:pointer;transition:all .2s;color:var(--text2);font-family:inherit;white-space:nowrap}}
.role-pill:hover{{border-color:var(--accent);color:var(--text)}}
.role-pill.active{{background:var(--accent);border-color:var(--accent);color:#fff}}
.header-patient{{margin-left:auto;font-size:13px;color:var(--text2);display:flex;align-items:center;gap:8px}}
.header-patient .hp-name{{font-weight:600;color:var(--text)}}
.header-patient .hp-badge{{font-size:10px;padding:1px 8px;border-radius:var(--radius-full);background:var(--blue-bg);color:var(--blue)}}

/* 3-Column Layout */
.app{{flex:1;display:flex;overflow:hidden}}
.leftbar{{width:240px;background:var(--bg-overlay);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto;flex-shrink:0}}
.lb-search{{padding:10px 12px}}.lb-search input{{width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:12px;background:var(--bg-default);color:var(--text);font-family:inherit;outline:none}}
.lb-search input:focus{{border-color:var(--accent);box-shadow:0 0 0 3px var(--blue-bg)}}
.lb-header{{padding:4px 12px 8px;font-size:11px;color:var(--text3);font-weight:500}}
.patient-list{{flex:1;overflow-y:auto;padding:0 8px}}
.p-item{{padding:10px 12px;cursor:pointer;border-radius:var(--radius-sm);transition:all .15s;margin:2px 0;border:1px solid transparent}}
.p-item:hover{{background:var(--bg-subtle)}}
.p-item.active{{background:var(--blue-bg);border-color:var(--accent)}}
.p-name{{font-size:13px;font-weight:600;color:var(--text)}}
.p-age{{font-size:11px;color:var(--text3);font-weight:400;margin-left:4px}}
.p-diag{{font-size:11px;color:var(--text2);margin-top:2px}}
.p-meta{{font-size:10px;color:var(--text3);margin-top:2px}}.p-stage{{padding:1px 6px;border-radius:var(--radius-full);font-size:9px;font-weight:500}}.p-stage.normal{{background:var(--green-bg);color:var(--green)}}.p-stage.urgent{{background:var(--red-bg);color:var(--red)}}
.lb-footer{{padding:10px 12px;font-size:11px;color:var(--text3);border-top:1px solid var(--border-muted)}}

.center{{flex:1;overflow-y:auto;padding:20px 24px}}
.stage-content{{display:none}}.stage-content.active{{display:block;animation:fadeIn .2s ease}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:translateY(0)}}}}
.stage-header{{display:flex;align-items:flex-start;gap:14px;margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid var(--border-muted)}}
.stage-badge{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:600;background:var(--accent);color:#fff;flex-shrink:0;box-shadow:0 4px 12px rgba(9,105,218,.25)}}
.stage-header h3{{font-size:16px;font-weight:600;color:var(--text);margin-bottom:2px}}
.stage-header p{{font-size:12px;color:var(--text2);line-height:1.5}}
.guide-ref{{font-size:10px;color:var(--purple);margin-top:4px;display:inline-block;font-weight:500}}
.form-group{{margin:8px 0}}.form-group label{{font-size:11px;color:var(--text3);display:block;margin-bottom:4px;font-weight:500;text-transform:uppercase;letter-spacing:.04em}}
.form-group textarea{{width:100%;height:80px;padding:10px 14px;background:var(--bg-inset);color:var(--text);border:1px solid var(--border);border-radius:var(--radius);font-size:13px;font-family:Consolas,monospace;resize:vertical;line-height:1.5;transition:border .15s ease;outline:none}}
.form-group textarea:focus{{border-color:var(--accent);box-shadow:0 0 0 3px var(--blue-bg)}}
.btn-row{{display:flex;gap:8px;margin:14px 0;flex-wrap:wrap;align-items:center}}
.btn-exec{{padding:9px 20px;background:var(--accent);color:#fff;border:none;border-radius:var(--radius);font-size:13px;font-weight:600;cursor:pointer;transition:all .15s ease;min-height:36px;font-family:inherit}}
.btn-exec:hover{{opacity:.92;box-shadow:0 4px 12px rgba(9,105,218,.3);transform:scale(1.02)}}
.btn-exec:active{{transform:scale(.96)}}
.btn-guard{{padding:9px 16px;background:transparent;color:var(--text2);border:1px solid var(--border);border-radius:var(--radius);font-size:12px;cursor:pointer;transition:all .15s ease;font-weight:500;min-height:36px;font-family:inherit}}
.btn-guard:hover{{border-color:var(--accent);color:var(--accent);background:var(--blue-bg)}}
.btn-next{{padding:9px 16px;background:transparent;color:var(--green);border:1px solid var(--green);border-radius:var(--radius);font-size:12px;cursor:pointer;transition:all .15s ease;font-weight:500;min-height:36px;font-family:inherit}}
.btn-next:hover{{background:var(--green);color:#fff}}
.result-box{{background:var(--bg-elevated);border:1px solid var(--border);border-radius:12px;padding:16px 20px;font-family:Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;max-height:420px;overflow-y:auto;box-shadow:var(--shadow-sm);margin-top:4px}}
.result-placeholder{{color:var(--text3);font-style:italic}}

.rightbar{{width:240px;background:var(--bg-overlay);border-left:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto;flex-shrink:0}}
.rb-title{{padding:14px 12px 8px;font-size:13px;font-weight:700;color:var(--text)}}
.rb-list{{padding:0 8px;flex:1;overflow-y:auto}}
.rb-item{{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:var(--radius-sm);transition:all .15s;font-size:12px;cursor:pointer}}
.rb-item:hover{{background:var(--bg-subtle)}}
.rb-item.active{{background:var(--blue-bg)}}
.rb-item.rb-hidden{{display:none!important}}
.rb-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;border:2px solid var(--border-muted);transition:all .2s}}
.rb-item.done .rb-dot{{background:var(--green);border-color:var(--green);box-shadow:0 0 0 3px var(--green-bg)}}
.rb-dot.current{{background:var(--accent);border-color:var(--accent);box-shadow:0 0 0 3px var(--blue-bg)}}
.rb-info{{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}}
.rb-name{{font-weight:500;font-size:11px}}
.rb-status{{font-size:9px;padding:1px 6px;border-radius:var(--radius-full);margin-left:auto}}
.rb-status.done{{background:var(--green-bg);color:var(--green)}}
.rb-status.active-s{{background:var(--blue-bg);color:var(--blue)}}
.rb-stats{{padding:10px 12px;border-top:1px solid var(--border-muted)}}
.rb-stat{{display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:11px;color:var(--text2)}}
.rb-stat .val{{font-weight:600;color:var(--text)}}
.tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:500;margin:1px}}
.tag.red{{background:var(--red-bg);color:var(--red)}}
.tag.blue{{background:var(--blue-bg);color:var(--blue)}}
</style>
</head>
<body>

<div class="header">
  <h1>{icon_map.get(agent_type, '🏥')} {cn_name} 工作台</h1>
  <div class="header-role">
    <span style="font-size:11px;color:var(--text3);padding:3px 4px 3px 0">角色:</span>
{role_pills}
  </div>
  <div class="header-patient" id="header-patient">
    <span class="hp-name" id="hp-name"></span>
    <span class="hp-badge" id="hp-badge"></span>
  </div>
</div>

<div class="app">
  <div class="leftbar">
    <div class="lb-search"><input type="text" id="patient-search" placeholder="搜索患者..." oninput="searchPatients()"></div>
    <div class="lb-header">数字病人 · {cn_name}</div>
    <div class="patient-list" id="patient-list"></div>
    <div class="lb-footer">共 <strong id="lb-count">0</strong> 位患者</div>
  </div>

  <div class="center" id="center-content">
{panels}
  </div>

  <div class="rightbar">
    <div class="rb-title">诊疗阶段</div>
    <div class="rb-list" id="rb-stages">
{sb_items}
    </div>
    <div class="rb-stats">
      <div class="rb-stat"><span>当前阶段</span><span class="val" id="rb-current-stage" style="font-weight:600">1/{len(workflow_stages)}</span></div>
      <div class="rb-stat"><span>可用阶段</span><span class="val" id="rb-visible-count" style="font-weight:600">{len(workflow_stages)}/{len(workflow_stages)}</span></div>
      <div class="rb-stat"><span>已完成</span><span class="val" id="rb-done-count" style="font-weight:600">0</span></div>
    </div>
{guard_html}
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
var AGENT='{name}';var STAGES={wf_json};var ROLES={roles_json};
var PATIENTS={patients_json};
var CURRENT_ROLE='{first_role or "attending"}';
var WORKFLOW_DATA={{}};
var COMPLETED_STAGES=new Set();var STAGE_RESULTS={{}};
var currentPatient=null;var currentStage=1;

function init(){{
  renderPatientList();
  clickStage(1);
  switchRole(CURRENT_ROLE);
  if(PATIENTS.length)selectPatient(PATIENTS[0].patient_id);
}}

function switchRole(rid){{
  CURRENT_ROLE=rid;
  document.querySelectorAll('.role-pill').forEach(function(e){{e.classList.remove('active')}});
  var btn=document.querySelector('.role-pill[data-role="'+rid+'"]');
  if(btn)btn.classList.add('active');
  // 筛选右侧阶段列表
  var rc=ROLES[rid];var allowed=rc?rc.stages:null;var visCount=0;
  document.querySelectorAll('.rb-item').forEach(function(el){{
    var order=parseInt(el.getAttribute('data-stage'));
    var stage=STAGES.find(function(s){{return s.order===order}});
    if(!stage)return;
    var show=!allowed||allowed==='all'||allowed.indexOf(order)>=0;
    if(show){{el.classList.remove('rb-hidden');visCount++}}
    else{{el.classList.add('rb-hidden')}}
  }});
  document.getElementById('rb-visible-count').textContent=visCount+'/'+STAGES.length;
  // 自动跳到首个可见阶段
  var curItem=document.querySelector('.rb-item.active');
  if(!curItem||curItem.classList.contains('rb-hidden')){{
    var firstVis=document.querySelector('.rb-item:not(.rb-hidden)');
    if(firstVis)clickStage(parseInt(firstVis.getAttribute('data-stage')));
  }}
  if(currentPatient)fillCurrentParams();
}}

function clickStage(n){{
  currentStage=n;
  document.querySelectorAll('.rb-item').forEach(function(e){{e.classList.remove('active');e.querySelector('.rb-status').textContent='';e.querySelector('.rb-status').classList.remove('active-s','done')}});
  var el=document.querySelector('.rb-item[data-stage="'+n+'"]');
  if(el){{el.classList.add('active');el.querySelector('.rb-status').textContent='当前';el.querySelector('.rb-status').classList.add('active-s')}}
  document.querySelectorAll('.stage-content').forEach(function(e){{e.classList.remove('active')}});
  var p=document.getElementById('stage-'+n);if(p)p.classList.add('active');
  document.getElementById('rb-current-stage').textContent=n+'/'+STAGES.length;
  fillCurrentParams();
}}

async function callStage(sid,tool){{
  var el=document.getElementById('result-'+sid);
  var pe=document.getElementById('params-'+sid),params=WORKFLOW_DATA;
  if(!currentPatient&&(!pe||!pe.value.trim())){{el.textContent='⚠ 请先在左侧选择数字病人';return}}
  el.textContent='⏳ 执行中...';
  if(pe){{try{{Object.assign(params,JSON.parse(pe.value))}}catch(e){{}}}}
  try{{
    var r=await fetch('/api/call',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{agent:AGENT,tool:tool,params:params}})}});
    var d=await r.json();el.textContent=JSON.stringify(d,null,2);
    if(d.status==='ok'){{
      COMPLETED_STAGES.add(sid);STAGE_RESULTS[sid]=d;
      var s=STAGES.find(function(x){{return x.id===sid}});
      if(s)WORKFLOW_DATA[s.key_output]=d[s.key_output]||d;
      updateProgress();
    }}
  }}catch(e){{el.textContent='❌ '+e.message}}
}}

function autoNext(fromId,toId){{
  var stage=STAGES.find(function(s){{return s.id===toId}});
  if(stage)clickStage(stage.order);
  if(STAGE_RESULTS[fromId]){{
    var el=document.getElementById('params-'+toId);
    if(el)el.value=JSON.stringify(STAGE_RESULTS[fromId],null,2);
  }}
}}

function updateProgress(){{
  var done=COMPLETED_STAGES.size;
  document.getElementById('rb-done-count').textContent=done;
  document.querySelectorAll('.rb-item').forEach(function(e){{
    var order=parseInt(e.getAttribute('data-stage'));
    var stage=STAGES.find(function(s){{return s.order===order}});
    if(stage&&COMPLETED_STAGES.has(stage.id)){{e.classList.add('done');e.querySelector('.rb-dot').classList.add('done')}}
  }});
}}

function showGuard(sid){{
  var out=document.getElementById('result-'+sid)?.textContent||'';
  fetch('/api/guard',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{output:out,agent:AGENT}})}})
  .then(function(r){{return r.json()}}).then(function(d){{document.getElementById('result-'+sid).textContent='🛡 安全校验:\\n'+JSON.stringify(d,null,2)}});
}}

function renderPatientList(){{
  var list=PATIENTS;
  var q=(document.getElementById('patient-search').value||'').toLowerCase();
  if(q){{list=list.filter(function(p){{return(p.name+(p.diagnosis||'')+(p.patient_id||'')).toLowerCase().indexOf(q)>=0}})}}
  var html='';
  list.forEach(function(p){{
    var active=currentPatient&&currentPatient.patient_id===p.patient_id?' active':'';
    var statusLabel=(p.urgency||'normal')==='high'?'紧急':'常规';
    var statusClass=(p.urgency||'normal')==='high'?'urgent':'normal';
    html+='<div class="p-item'+active+'" onclick="selectPatient(\\''+p.patient_id+'\\')">'+
      '<div class="p-name">'+p.name+'<span class="p-age">'+p.age+'岁</span></div>'+
      '<div class="p-diag">'+(p.diagnosis||'')+'</div>'+
      '<div class="p-meta">'+p.patient_id+' · <span class="p-stage '+statusClass+'">'+statusLabel+'</span></div></div>';
  }});
  document.getElementById('patient-list').innerHTML=html||'<div style="padding:12px;text-align:center;color:var(--text3);font-size:12px">未找到患者</div>';
  document.getElementById('lb-count').textContent=list.length;
}}

function selectPatient(pid){{
  currentPatient=PATIENTS.find(function(p){{return p.patient_id===pid}});
  currentStage=1;COMPLETED_STAGES=new Set();STAGE_RESULTS={{}};
  document.getElementById('header-patient').style.display='flex';
  document.getElementById('hp-name').textContent=currentPatient.name+' · '+currentPatient.age+'岁';
  document.getElementById('hp-badge').textContent=currentPatient.department||'';
  WORKFLOW_DATA={{patient_id:currentPatient.patient_id,age:currentPatient.age||0,weight_kg:currentPatient.weight_kg||0,height_cm:currentPatient.height_cm||0,lab_results:currentPatient.lab_results||{{}},conditions:currentPatient.conditions||[]}};
  clickStage(1);renderPatientList();updateProgress();
}}

function searchPatients(){{renderPatientList()}}

function fillCurrentParams(){{
  if(!currentPatient)return;
  var ap=document.querySelector('.stage-content.active');
  if(!ap)return;var ta=ap.querySelector('textarea');
  if(ta)ta.value=JSON.stringify(WORKFLOW_DATA,null,2);
}}

function showToast(msg){{
  var t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');
  setTimeout(function(){{t.classList.remove('show')}},2000);
}}

init();
</script>
<style>
.toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--text);color:#fff;padding:8px 20px;border-radius:var(--radius-full);font-size:12px;z-index:9999;opacity:0;transition:opacity .3s;pointer-events:none}}
.toast.show{{opacity:1}}
</style>
</body>
</html>"""
