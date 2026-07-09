"""Generated JS for ui_process ? extracted from ui_process.py."""

PROCESS_JS = """var PATIENTS = {patients_json};
var STAGES = {stages_json};
var GUARD_TRIGGERS = {json.dumps(guard_triggers, ensure_ascii=False)};
var DEPENDS_ON = {json.dumps(depends_on or [], ensure_ascii=False)};
var AGENT_NAME = "{name}";
var AGENT_CN = "{cn_name}";
var AGENT_TYPE = "{agent_type}";
var DEPT = "{department or '—'}";
var currentPatient = null;
var currentStage = 1;
var completedStages = {{}};
var currentRole = "{roles[0]['id'] if roles else 'attending'}";

function init(){{
  try {{
    var testEl = document.getElementById('patient-list');
    if (!testEl) {{ console.error('patient-list not found in DOM'); return; }}
    testEl.innerHTML = '<div style="padding:10px;text-align:center;font-size:12px;color:var(--text2)">加载中: '+PATIENTS.length+' 位患者...</div>';
    setTimeout(function(){{ renderPatientList(); }}, 100);
  }} catch(e) {{ document.getElementById('patient-list').innerHTML = '<div style="color:red;padding:10px">JS Error: '+e.message+'</div>'; }}
  clickStage(1);
  document.getElementById('home-stages').textContent = STAGES.length;
  document.getElementById('home-patients').textContent = PATIENTS.length;
  document.getElementById('home-roles').textContent = {len(roles)};
  document.getElementById('home-guards').textContent = GUARD_TRIGGERS.length;
  renderDepsPage();
  renderGuidelinesPage();
}}

function toggleMenu(){{
  document.getElementById('menu-overlay').classList.toggle('open');
  document.getElementById('menu-panel').classList.toggle('open');
}}
function closeMenu(){{
  document.getElementById('menu-overlay').classList.remove('open');
  document.getElementById('menu-panel').classList.remove('open');
}}
function switchToPage(name){{
  document.querySelectorAll('.page-panel').forEach(function(e){{ e.style.display = 'none' }});
  var p = document.getElementById('page-'+name);
  if (p) p.style.display = 'block';
  document.querySelectorAll('.menu-item').forEach(function(e){{ e.classList.remove('active') }});
  var items = document.querySelectorAll('.menu-item');
  items.forEach(function(e){{ if(e.textContent.indexOf(name)===-1) return; e.classList.add('active') }});
  document.querySelectorAll('.stage-content').forEach(function(e){{ e.classList.remove('active') }});
  document.getElementById('center-content').scrollTop = 0;
}}

function switchRole(rid){{
  currentRole = rid;
  document.querySelectorAll('.role-pill').forEach(function(e){{ e.classList.remove('active') }});
  var btn = document.querySelector('.role-pill[data-role="'+rid+'"]');
  if (btn) btn.classList.add('active');
  showToast('已切换至: '+(btn?btn.textContent.trim():rid));
  // 筛选右侧阶段列表
  document.querySelectorAll('.rb-item').forEach(function(el){{
    var order = parseInt(el.getAttribute('data-stage'));
    var stage = STAGES.find(function(s){{ return s.order === order }});
    if (!stage) return;
    var allowed = stage.role_ids || [];
    el.style.display = (allowed.length === 0 || allowed.indexOf(rid) >= 0) ? 'flex' : 'none';
  }});
  // 更新当前阶段计数
  var visibleItems = document.querySelectorAll('.rb-item:not([style*="display: none"])');
  document.getElementById('rb-done-count').textContent = visibleItems.length;
  if (currentPatient) renderStageContent(currentStage);
}}

function renderDepsPage(){{
  var html = '';
  DEPENDS_ON.forEach(function(d){{
    html += '<div class="dp"><span class="dpl">'+d.agent+'</span><span class="dpv">'+(d.reason||'协作')+'</span></div>';
  }});
  document.getElementById('deps-list').innerHTML = html || '<span style="color:var(--text3)">无依赖 Agent</span>';

  var groups = {{}};
  PATIENTS.forEach(function(p){{ var d=p.department||'其他'; groups[d]=(groups[d]||0)+1 }});
  var tbody = '';
  for (var k in groups) tbody += '<tr><td>'+k+'</td><td>'+groups[k]+'</td><td>'+AGENT_CN+'</td></tr>';
  document.getElementById('coverage-table').innerHTML = tbody;
}}

function renderGuidelinesPage(){{
  var tags = GUARD_TRIGGERS.map(function(t){{ return '<span class="tag red">'+t+'</span>' }}).join(' ');
  document.getElementById('guidelines-triggers').innerHTML = tags || '<span style="color:var(--text3)">无高危触发</span>';

  var html = '';
  STAGES.forEach(function(s){{
    html += '<div class="dp"><span class="dpl">阶段'+s.order+'</span><span class="dpv">'+s.label+' — '+s.desc+'</span></div>';
  }});
  document.getElementById('guidelines-stages').innerHTML = html;
}}

function renderPatientList(filter){{
  var list = PATIENTS;
  var q = (document.getElementById('patient-search').value||'').toLowerCase();
  if (q){{ list = list.filter(function(p){{ return (p.name+p.diagnosis+(p.patient_id||'')+(p.department||'')).toLowerCase().indexOf(q)>=0 }}) }}
  var html = '';
  list.forEach(function(p){{
    var active = currentPatient && currentPatient.patient_id===p.patient_id ? ' active' : '';
    var statusLabel = (p.urgency||'normal')==='high' ? '紧急' : '常规';
    var statusClass = (p.urgency||'normal')==='high' ? 'urgent' : 'normal';
    html += '<div class="p-item'+active+'" onclick="selectPatient(\\''+p.patient_id+'\\')">'+
      '<div class="p-name">'+p.name+' <span class="p-age">'+p.age+'岁</span></div>'+
      '<div class="p-diag">'+p.diagnosis+'</div>'+
      '<div class="p-meta">'+p.patient_id+' · <span class="p-stage '+statusClass+'">'+statusLabel+'</span></div></div>';
  }});
  document.getElementById('patient-list').innerHTML = html || '<div class="empty"><div class="e-icon">🔍</div><div class="e-text">未找到患者</div></div>';
  document.getElementById('lb-count').textContent = list.length;
}}

function selectPatient(pid){{
  currentPatient = PATIENTS.find(function(p){{ return p.patient_id===pid }});
  currentStage = 1; completedStages = {{}};
  document.getElementById('header-patient').classList.add('visible');
  document.getElementById('hp-name').textContent = currentPatient.name+' · '+currentPatient.age+'岁';
  document.getElementById('hp-stage').textContent = currentPatient.department||DEPT;
  clickStage(1); renderPatientList(); updateRightbar();
}}

function resetSelection(){{
  currentPatient = null; currentStage = 1; completedStages = {{}};
  document.getElementById('header-patient').classList.remove('visible');
  clickStage(1); renderPatientList(); updateRightbar();
}}

function searchPatients(){{ renderPatientList() }}

function clickStage(n){{
  if (!currentPatient && n>1){{ showToast('请先在左侧选择一个患者'); return }}
  currentStage = n;
  document.querySelectorAll('.stage-content').forEach(function(e){{ e.classList.remove('active') }});
  var el = document.getElementById('stage-'+n);
  if (el) el.classList.add('active');
  updateRightbar();
  if (currentPatient) renderStageContent(n);
}}

function advanceStage(){{
  if (!currentPatient) return;
  completedStages[currentStage] = true;
  if (currentStage < STAGES.length){{ clickStage(currentStage+1) }}
  else{{ showComplete() }}
}}

function showComplete(){{
  var done = Object.keys(completedStages).length;
  showToast('🎉 '+currentPatient.name+' 全部流程完成！已完成 '+done+'/'+STAGES.length+' 阶段');
  updateRightbar();
}}

function updateRightbar(){{
  document.querySelectorAll('.rb-item').forEach(function(item, i){{
    var s = i+1;
    var dot = item.querySelector('.rb-dot');
    var status = item.querySelector('.rb-status');
    dot.className = 'rb-dot'; status.className = 'rb-status'; status.textContent = '';
    item.classList.remove('active');
    if (s === currentStage){{ dot.classList.add('current'); status.textContent = '当前'; status.classList.add('active-s'); item.classList.add('active') }}
    else if (completedStages[s]){{ dot.classList.add('done'); status.textContent = '✓'; status.classList.add('done') }}
    else{{ dot.classList.add('locked') }}
  }});
  document.getElementById('rb-current-stage').textContent = currentStage+'/'+STAGES.length;
  document.getElementById('rb-done-count').textContent = Object.keys(completedStages).length;
}}

function renderStageContent(n){{
  if (!currentPatient) return;
  var p = currentPatient;
  var s = STAGES[n-1];
  var el = document.getElementById('stage-'+n);
  if (!el) return;
  var content = '';
  if (n===1) content = renderStage1(p,s);
  else if (n===STAGES.length) content = renderLastStage(p,s);
  else content = renderMidStage(p,s,n);
  el.innerHTML = '<div class="stage-bar s'+n+'" style="width:'+(completedStages[n]?'100':'30')+'%"></div>'+
    '<div class="stage-hdr"><span class="sh-num">'+n+'</span><h2>'+s.label+'</h2><span class="sh-role">'+s.role+'</span>'+
    (n<STAGES.length ? '<button class="btn btn-sm btn-outline" onclick="advanceStage()" style="margin-left:auto">下一步 →</button>' : '')+
    '</div><div class="sh-desc" style="margin-bottom:12px;font-size:var(--fs-sm)">'+s.desc+'</div>'+
    content+
    '<div class="fx-nav">'+
    (n>1 ? '<button class="btn btn-outline" onclick="clickStage('+(n-1)+')">← '+STAGES[n-2].label+'</button>' : '<span></span>')+
    (n<STAGES.length ? '<button class="btn" onclick="advanceStage()">确认 → '+STAGES[n].label+'</button>' : '<button class="btn btn-success" onclick="showComplete()">✅ 完成全部流程</button>')+
    '</div>';
}}

function renderStage1(p,s){{
  return '<div class="section"><div class="section-title">📋 患者概要</div>'+
    '<div class="summary-bar"><span>姓名: <strong>'+p.name+'</strong></span> · <span>'+p.age+'岁</span> · <span>'+p.patient_id+'</span> · <span>科室: <span class="tag blue">'+(p.department||DEPT)+'</span></span>'+
    '<br><span>诊断: <strong>'+p.diagnosis+'</strong></span></div></div>'+
    '<div class="card"><h3><span class="ch-icon">📖</span> 病史详情</h3>'+
    '<div class="tabs"><button class="tab-btn active" data-pane="basic" onclick="switchTab(\\'basic\\')">基本信息</button>'+
    '<button class="tab-btn" data-pane="present" onclick="switchTab(\\'present\\')">现病史</button>'+
    '<button class="tab-btn" data-pane="labs" onclick="switchTab(\\'labs\\')">检验指标</button></div>'+
    '<div class="tab-pane active" id="pane-basic"><div style="font-size:13px;line-height:1.8">'+formatDP(p)+'</div></div>'+
    '<div class="tab-pane" id="pane-present"><div style="font-size:13px;line-height:1.8">'+(p.present||p.scenario||'待录入')+'</div></div>'+
    '<div class="tab-pane" id="pane-labs"><div style="font-size:13px;line-height:1.8">'+formatLabs(p)+'</div></div>'+
    '</div>'+
    '<div class="section"><div class="section-title">🚨 分诊判定</div>'+
    '<div class="triage-card '+(p.urgency==='high'?'I':'III')+'">'+
    '<div class="triage-main '+(p.urgency==='high'?'tri-i':'tri-iii')+'">'+(p.urgency==='high'?'⚠ 紧急处理':'✓ 常规处理')+'</div>'+
    '<div class="triage-sub">'+(p.urgency==='high'?'需优先处理，触发高危流程':'按标准流程依次推进')+'</div></div></div>'+
    '<div class="alert '+(p.urgency==='high'?'red':'blue')+'">'+(p.urgency==='high'?'⚠ 该患者已触发紧急流程，请优先完成登记与分诊。':'ℹ 患者信息完整，可进入诊断与分型阶段。')+'</div>';
}}

function renderMidStage(p,s,n){{
  var items = [];
  if (p.assessments) items = p.assessments;
  else if (p.tools) items = p.tools;
  else items = ['检验结果复核','影像资料评估','风险评分计算','合并症管理','用药方案确认'];
  var done = completedStages[n] ? items.length : Math.floor(items.length*0.5);
  var pending = items.length - done;
  var html = '<div class="kpis">';
  html += '<div class="kpi"><span class="val blue">'+items.length+'</span><span class="lbl">评估项</span></div>';
  html += '<div class="kpi"><span class="val '+(done===items.length?'green':'blue')+'">'+done+'</span><span class="lbl">已完成</span></div>';
  html += '<div class="kpi"><span class="val '+(pending>0?'amber':'green')+'">'+pending+'</span><span class="lbl">待完成</span></div>';
  html += '<div class="kpi"><span class="val blue">'+(done===items.length?'100':Math.round(done/items.length*100))+'%</span><span class="lbl">完成率</span></div>';
  html += '</div>';
  html += '<div class="cl-section"><div class="cl-section-title">'+s.label+' — 检查列表</div>';
  items.forEach(function(item,i){{
    var isDone = completedStages[n] || i < Math.floor(items.length/2);
    html += '<div class="cl-item"><span class="ck '+(isDone?'done':'')+'">'+(isDone?'✓':'')+'</span>'+
      '<span class="cl-name">'+item+'</span><span class="cl-dept">'+(p.department||DEPT)+'</span>'+
      '<span class="cl-reason">'+(isDone?'已完成':'待执行')+'</span></div>';
  }});
  html += '</div>';
  if (p.plan && (n===4 || n===Math.floor(STAGES.length/2))) html += '<div class="card"><h3><span class="ch-icon">💡</span> 建议方案</h3><div style="font-size:13px;line-height:1.8">'+p.plan+'</div></div>';
  if (p.execution && (n===5 || n===Math.floor(STAGES.length*0.8))) html += '<div class="card"><h3><span class="ch-icon">🩺</span> 执行记录</h3><div style="font-size:13px;line-height:1.8">'+p.execution+'</div></div>';
  return html;
}}

function renderLastStage(p,s){{
  return '<div class="card"><h3><span class="ch-icon">📅</span> 随访计划</h3>'+
    '<div style="font-size:13px;line-height:1.8">'+(p.followup||'根据科室规范制定个性化随访方案，包括定期复查、功能评估、长期用药管理。')+'</div></div>'+
    '<div class="card"><h3><span class="ch-icon">📊</span> 随访节点</h3>'+
    '<div class="fu-timeline">'+
    '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">出院 1 周</span><span class="fu-sub">症状评估 / 伤口检查</span></div>'+
    '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">出院 1 月</span><span class="fu-sub">功能评估 / 复查检验</span></div>'+
    '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">出院 3 月</span><span class="fu-sub">全面评估 / 长期方案</span></div>'+
    '</div></div>'+
    '<div class="card"><h3><span class="ch-icon">📋</span> 随访记录表</h3>'+
    '<table><tr><th>时间</th><th>项目</th><th>执行科室</th><th>状态</th></tr>'+
    '<tr><td>出院后 1 周</td><td>症状评估 / 伤口检查</td><td>'+(p.department||DEPT)+'门诊</td><td><span class="tag green">待执行</span></td></tr>'+
    '<tr><td>出院后 1 月</td><td>功能评估 / 复查检验</td><td>'+(p.department||DEPT)+'门诊</td><td><span class="tag blue">待执行</span></td></tr>'+
    '<tr><td>出院后 3 月</td><td>全面评估 / 长期方案</td><td>'+(p.department||DEPT)+' · 康复科</td><td><span class="tag blue">待执行</span></td></tr></table></div>';
}}

function formatDP(p){{
  var html = '';
  var fields = {{patient_id:'患者ID',name:'姓名',age:'年龄',gender:'性别',diagnosis:'诊断',department:'科室',scenario:'临床场景'}};
  for (var k in fields){{ if (p[k]!==undefined && p[k]!==null) html += '<div class="dp"><span class="dpl">'+fields[k]+'</span><span class="dpv">'+p[k]+'</span></div>' }}
  return html;
}}

function formatLabs(p){{
  if (!p.lab_results || Object.keys(p.lab_results).length===0) return '<div class="empty"><div class="e-icon">🔬</div><div class="e-text">暂无检验数据</div></div>';
  var html = '';
  for (var k in p.lab_results){{ html += '<div class="dp"><span class="dpl">'+k+'</span><span class="dpv">'+p.lab_results[k]+'</span></div>' }}
  return html;
}}

function switchTab(pane){{
  document.querySelectorAll('.tab-btn').forEach(function(e){{ e.classList.remove('active') }});
  var btn = document.querySelector('.tab-btn[data-pane="'+pane+'"]');
  if (btn) btn.classList.add('active');
  document.querySelectorAll('.tab-pane').forEach(function(e){{ e.classList.remove('active') }});
  var p = document.getElementById('pane-'+pane);
  if (p) p.classList.add('active');
}}

function showToast(msg){{
  var t = document.getElementById('toast');
  t.textContent = msg; t.style.display = 'block';
  clearTimeout(t._timeout);
  t._timeout = setTimeout(function(){{ t.style.display = 'none' }}, 2500);
}}

init();"""
