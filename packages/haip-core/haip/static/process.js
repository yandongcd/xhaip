var XHAIP_DATA = JSON.parse(document.getElementById('xhaip-data').textContent);
var PATIENTS = [];
var STAGES = XHAIP_DATA.stages;
var GUARD_TRIGGERS = XHAIP_DATA.guard_triggers;
var DEPENDS_ON = XHAIP_DATA.depends_on;
var AGENT_NAME = XHAIP_DATA.name;
var AGENT_CN = XHAIP_DATA.cn_name;
var AGENT_TYPE = XHAIP_DATA.agent_type;
var DEPT = XHAIP_DATA.department;
var currentPatient = null;
var currentStage = 1;
var completedStages = {};
var currentRole = XHAIP_DATA.default_role_id;

function init(){
  try {
    var testEl = document.getElementById('patient-list');
    if (!testEl) { console.error('patient-list not found in DOM'); return; }
    testEl.innerHTML = '<div style="padding:10px;text-align:center;font-size:12px;color:var(--text2)">加载患者数据...</div>';
    loadPatientsAsync();
  } catch(e) { document.getElementById('patient-list').innerHTML = '<div style="color:red;padding:10px">JS Error: '+e.message+'</div>'; }
  switchRole(currentRole);
  document.getElementById('home-stages').textContent = STAGES.length;
  document.getElementById('home-roles').textContent = 7;
  document.getElementById('home-guards').textContent = GUARD_TRIGGERS.length;
  renderDepsPage();
  renderGuidelinesPage();
}

async function loadPatientsAsync() {
  try {
    var resp = await fetch('/api/patients/' + AGENT_NAME + '?limit=100');
    var data = await resp.json();
    PATIENTS = data.patients || [];
    document.getElementById('home-patients').textContent = data.total || PATIENTS.length;
    renderPatientList();
  } catch(e) {
    document.getElementById('patient-list').innerHTML = '<div style="color:red;padding:10px">加载失败: '+e.message+'</div>';
  }
}

function toggleMenu(){
  document.getElementById('menu-overlay').classList.toggle('open');
  document.getElementById('menu-panel').classList.toggle('open');
}
function closeMenu(){
  document.getElementById('menu-overlay').classList.remove('open');
  document.getElementById('menu-panel').classList.remove('open');
}
function switchToPage(name){
  document.querySelectorAll('.page-panel').forEach(function(e){ e.style.display = 'none' });
  var p = document.getElementById('page-'+name);
  if (p) p.style.display = 'block';
  document.querySelectorAll('.menu-item').forEach(function(e){ e.classList.remove('active') });
  var items = document.querySelectorAll('.menu-item');
  items.forEach(function(e){ if(e.textContent.indexOf(name)===-1) return; e.classList.add('active') });
  document.querySelectorAll('.stage-content').forEach(function(e){ e.classList.remove('active') });
  document.getElementById('center-content').scrollTop = 0;
}

function switchRole(rid){
  currentRole = rid;
  document.querySelectorAll('.role-pill').forEach(function(e){ e.classList.remove('active') });
  var btn = document.querySelector('.role-pill[data-role="'+rid+'"]');
  if (btn) btn.classList.add('active');
  showToast('已切换至: '+(btn?btn.textContent.trim():rid));
  // 筛选右侧阶段列表 — 仅隐藏不可见的，不强制显示
  document.querySelectorAll('.rb-item').forEach(function(el){
    var order = parseInt(el.getAttribute('data-stage'));
    var stage = STAGES.find(function(s){ return s.order === order });
    if (!stage) return;
    var allowed = stage.role_ids || [];
    if (allowed.length === 0 || allowed.indexOf(rid) >= 0) {
      el.style.display = '';
    } else {
      el.style.display = 'none';
    }
  });
  // 筛选中间栏 stage-content — 仅隐藏不可见的
  document.querySelectorAll('.stage-content').forEach(function(el){
    var order = parseInt(el.id.replace('stage-',''));
    var stage = STAGES.find(function(s){ return s.order === order });
    if (!stage) return;
    var allowed = stage.role_ids || [];
    if (allowed.length > 0 && allowed.indexOf(rid) < 0) {
      el.classList.remove('active');
      el.style.display = 'none';
    }
  });
  // 查找当前角色可访问的第一个阶段
  var firstAccessible = 1;
  for (var i = 0; i < STAGES.length; i++) {
    var allowed = STAGES[i].role_ids || [];
    if (allowed.length === 0 || allowed.indexOf(rid) >= 0) {
      firstAccessible = STAGES[i].order;
      break;
    }
  }
  // 如果当前阶段不可访问，跳转到第一个可访问阶段
  var currStage = STAGES.find(function(s){ return s.order === currentStage });
  if (currStage) {
    var currAllowed = currStage.role_ids || [];
    if (currAllowed.length > 0 && currAllowed.indexOf(rid) < 0) {
      clickStage(firstAccessible);
      return;
    }
  }
  var visibleItems = document.querySelectorAll('.rb-item[style*="display:"]');
  visibleItems = Array.from(document.querySelectorAll('.rb-item')).filter(function(el){ return el.style.display !== 'none' });
  document.getElementById('rb-done-count').textContent = visibleItems.length;
  if (currentPatient) renderStageContent(currentStage);
}

function renderDepsPage(){
  var html = '';
  DEPENDS_ON.forEach(function(d){
    html += '<div class="dp"><span class="dpl">'+d.agent+'</span><span class="dpv">'+(d.reason||'协作')+'</span></div>';
  });
  document.getElementById('deps-list').innerHTML = html || '<span style="color:var(--text3)">无依赖 Agent</span>';

  var groups = {};
  PATIENTS.forEach(function(p){ var d=p.department||'其他'; groups[d]=(groups[d]||0)+1 });
  var tbody = '';
  for (var k in groups) tbody += '<tr><td>'+k+'</td><td>'+groups[k]+'</td><td>'+AGENT_CN+'</td></tr>';
  document.getElementById('coverage-table').innerHTML = tbody;
}

function renderGuidelinesPage(){
  var tags = GUARD_TRIGGERS.map(function(t){ return '<span class="tag red">'+t+'</span>' }).join(' ');
  document.getElementById('guidelines-triggers').innerHTML = tags || '<span style="color:var(--text3)">无高危触发</span>';

  var html = '';
  STAGES.forEach(function(s){
    html += '<div class="dp"><span class="dpl">阶段'+s.order+'</span><span class="dpv">'+s.label+' — '+s.desc+'</span></div>';
  });
  document.getElementById('guidelines-stages').innerHTML = html;
}

function renderPatientList(filter){
  var list = PATIENTS;
  var q = (document.getElementById('patient-search').value||'').toLowerCase();
  if (q){ list = list.filter(function(p){ return (p.name+p.diagnosis+(p.patient_id||'')+(p.department||'')).toLowerCase().indexOf(q)>=0 }) }
  var html = '';
  list.forEach(function(p){
    var active = currentPatient && currentPatient.patient_id===p.patient_id ? ' active' : '';
    var statusLabel = (p.urgency||'normal')==='high' ? '紧急' : '常规';
    var statusClass = (p.urgency||'normal')==='high' ? 'urgent' : 'normal';
    html += '<div class="p-item'+active+'" onclick="selectPatient(\''+p.patient_id+'\')">'+
      '<div class="p-name">'+p.name+' <span class="p-age">'+p.age+'岁</span></div>'+
      '<div class="p-diag">'+p.diagnosis+'</div>'+
      '<div class="p-meta">'+p.patient_id+' · <span class="p-stage '+statusClass+'">'+statusLabel+'</span></div></div>';
  });
  document.getElementById('patient-list').innerHTML = html || '<div class="empty"><div class="e-icon">🔍</div><div class="e-text">未找到患者</div></div>';
  document.getElementById('lb-count').textContent = list.length;
}

function selectPatient(pid){
  currentPatient = PATIENTS.find(function(p){ return p.patient_id===pid });
  currentStage = 1; completedStages = {};
  document.getElementById('header-patient').classList.add('visible');
  document.getElementById('hp-name').textContent = currentPatient.name+' · '+currentPatient.age+'岁';
  document.getElementById('hp-badge').textContent = currentPatient.department||DEPT;
  clickStage(1); renderPatientList(); updateRightbar();
}

function resetSelection(){
  currentPatient = null; currentStage = 1; completedStages = {};
  document.getElementById('header-patient').classList.remove('visible');
  clickStage(1); renderPatientList(); updateRightbar();
}

function searchPatients(){ renderPatientList() }

function clickStage(n){
  if (!currentPatient && n>1){ showToast('请先在左侧选择一个患者'); return }
  currentStage = n;
  document.querySelectorAll('.stage-content').forEach(function(e){ e.classList.remove('active') });
  var el = document.getElementById('stage-'+n);
  if (el) el.classList.add('active');
  updateRightbar();
  if (currentPatient) renderStageContent(n);
}

function advanceStage(){
  if (!currentPatient) return;
  completedStages[currentStage] = true;
  if (currentStage < STAGES.length){ clickStage(currentStage+1) }
  else{ showComplete() }
}

function showComplete(){
  var done = Object.keys(completedStages).length;
  showToast('🎉 '+currentPatient.name+' 全部流程完成！已完成 '+done+'/'+STAGES.length+' 阶段');
  updateRightbar();
}

function updateRightbar(){
  document.querySelectorAll('.rb-item').forEach(function(item, i){
    var s = i+1;
    var dot = item.querySelector('.rb-dot');
    var status = item.querySelector('.rb-status');
    dot.className = 'rb-dot'; status.className = 'rb-status'; status.textContent = '';
    item.classList.remove('active');
    if (s === currentStage){ dot.classList.add('current'); status.textContent = '当前'; status.classList.add('active-s'); item.classList.add('active') }
    else if (completedStages[s]){ dot.classList.add('done'); status.textContent = '✓'; status.classList.add('done') }
    else{ dot.classList.add('locked') }
  });
  document.getElementById('rb-current-stage').textContent = currentStage+'/'+STAGES.length;
  document.getElementById('rb-done-count').textContent = Object.keys(completedStages).length;
}

function renderStageContent(n){
  if (!currentPatient) return;
  var p = currentPatient;
  var s = STAGES[n-1];
  var el = document.getElementById('stage-'+n);
  if (!el) return;
  var content = '';
  if (n===1) content = renderStage1(p,s);
  else if (n===STAGES.length) content = renderLastStage(p,s);
  else content = renderMidStage(p,s,n);
  el.innerHTML = '<div class="stage-bar s'+n+'" style="height:3px;background:var(--accent);border-radius:2px;margin-bottom:20px;width:'+(completedStages[n]?'100':'30')+'%;transition:all .3s"></div>'+
    '<div class="stage-hdr" style="display:flex;align-items:center;gap:16px;margin-bottom:24px;padding-bottom:16px;border-bottom:2px solid var(--border)">'+
    '<span class="sh-num" style="width:36px;height:36px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700">'+n+'</span>'+
    '<h2 style="font-size:20px;font-weight:700;color:var(--text);margin:0">'+s.label+'</h2>'+
    '<span class="sh-role" style="font-size:12px;color:var(--text3);background:var(--bg-subtle);padding:4px 14px;border-radius:var(--radius-full)">'+s.role+'</span>'+
    (n<STAGES.length ? '<button class="btn btn-sm btn-outline" onclick="advanceStage()" style="margin-left:auto;padding:6px 16px;border:1px solid var(--border);border-radius:var(--radius-full);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-family:inherit">下一步 →</button>' : '')+
    '</div><div class="sh-desc" style="font-size:12px;color:var(--text2);margin-bottom:16px">'+s.desc+'</div>'+
    content+
    '<div class="fx-nav" style="display:flex;justify-content:space-between;margin-top:20px;padding-top:16px;border-top:1px solid var(--border-muted)">'+
    (n>1 ? '<button class="btn btn-outline" onclick="clickStage('+(n-1)+')" style="padding:8px 20px;border:1px solid var(--border);border-radius:var(--radius-full);background:transparent;color:var(--text);cursor:pointer;font-size:13px;font-family:inherit">← '+STAGES[n-2].label+'</button>' : '<span></span>')+
    (n<STAGES.length ? '<button class="btn" onclick="advanceStage()" style="padding:8px 20px;border:none;border-radius:var(--radius-full);background:var(--accent);color:#fff;font-weight:600;font-size:13px;cursor:pointer;font-family:inherit">确认 → '+STAGES[n].label+'</button>' : '<button class="btn btn-success" onclick="showComplete()" style="padding:8px 20px;border:none;border-radius:var(--radius-full);background:var(--green);color:#fff;font-weight:600;font-size:13px;cursor:pointer;font-family:inherit">✅ 完成全部流程</button>')+
    '</div>';
}

function renderStage1(p,s){
  if (AGENT_TYPE === 'master_data') {
    return renderMasterDataStage1(p,s);
  } else if (AGENT_TYPE === 'specialist') {
    return renderSpecialistStage1(p,s);
  }
  return '<div class="section" style="margin-bottom:20px"><div class="section-title" style="font-size:13px;font-weight:700;color:var(--accent);margin-bottom:10px">📋 患者概要</div>'+
    '<div class="summary-bar" style="background:var(--bg-overlay);border-radius:8px;padding:16px 20px;font-size:14px;line-height:2;color:var(--text)"><span>姓名: <strong style="color:var(--accent)">'+p.name+'</strong></span> · <span>'+p.age+'岁</span> · <span>'+p.patient_id+'</span> · <span>科室: <span class="tag blue" style="display:inline-block;padding:2px 8px;border-radius:var(--radius-full);font-size:12px;font-weight:500;background:var(--blue-bg);color:var(--blue)">'+(p.department||DEPT)+'</span></span>'+
    '<br><span>诊断: <strong style="color:var(--accent)">'+p.diagnosis+'</strong></span></div></div>'+
    '<div class="card" style="background:var(--bg-elevated);border:1px solid var(--border);border-radius:10px;padding:24px;margin-bottom:16px"><h3 style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:14px;display:flex;align-items:center;gap:8px"><span class="ch-icon">📖</span> 病史详情</h3>'+
    '<div class="tabs" style="display:flex;gap:0;margin-bottom:0;border-bottom:2px solid var(--border)">'+
    '<button class="tab-btn active" data-pane="basic" onclick="switchTab(\'basic\')" style="padding:8px 20px;border:none;border-bottom:3px solid var(--accent);background:transparent;color:var(--accent);font-weight:700;font-size:14px;cursor:pointer;font-family:inherit">基本信息</button>'+
    '<button class="tab-btn" data-pane="present" onclick="switchTab(\'present\')" style="padding:8px 20px;border:none;border-bottom:3px solid transparent;background:transparent;color:var(--text3);font-weight:500;font-size:14px;cursor:pointer;font-family:inherit">现病史</button>'+
    '<button class="tab-btn" data-pane="labs" onclick="switchTab(\'labs\')" style="padding:8px 20px;border:none;border-bottom:3px solid transparent;background:transparent;color:var(--text3);font-weight:500;font-size:14px;cursor:pointer;font-family:inherit">检验指标</button></div>'+
    '<div class="tab-pane active" id="pane-basic" style="display:block;padding:20px 0 0 0"><div style="font-size:13px;line-height:1.8">'+formatDP(p)+'</div></div>'+
    '<div class="tab-pane" id="pane-present" style="display:none;padding:20px 0 0 0"><div style="font-size:13px;line-height:1.8">'+(p.present||p.scenario||'待录入')+'</div></div>'+
    '<div class="tab-pane" id="pane-labs" style="display:none;padding:20px 0 0 0"><div style="font-size:13px;line-height:1.8">'+formatLabs(p)+'</div></div>'+
    '</div>'+
    '<div class="section" style="margin-bottom:20px"><div class="section-title" style="font-size:13px;font-weight:700;color:var(--accent);margin-bottom:10px">🚨 分诊判定</div>'+
    '<div class="triage-card '+(p.urgency==='high'?'I':'III')+'" style="border-radius:10px;padding:16px 20px;margin-top:12px;border-left:4px solid '+(p.urgency==='high'?'var(--red)':'var(--green)')+';background:var(--bg-elevated)">'+
    '<div class="triage-main '+(p.urgency==='high'?'tri-i':'tri-iii')+'" style="font-size:18px;font-weight:700;color:'+(p.urgency==='high'?'var(--red)':'var(--green)')+'">'+(p.urgency==='high'?'⚠ 紧急处理':'✓ 常规处理')+'</div>'+
    '<div class="triage-sub" style="font-size:13px;color:var(--text2);margin-top:4px">'+(p.urgency==='high'?'需优先处理，触发高危流程':'按标准流程依次推进')+'</div></div></div>'+
    '<div class="alert '+(p.urgency==='high'?'red':'blue')+'" style="border-radius:8px;padding:12px 16px;font-size:13px;line-height:1.6;margin-top:12px;background:'+(p.urgency==='high'?'var(--red-bg)':'var(--blue-bg)')+';border:1px solid '+(p.urgency==='high'?'rgba(220,38,38,.2)':'rgba(8,145,178,.2)')+';color:'+(p.urgency==='high'?'var(--red)':'var(--accent)')+'">'+'ℹ 患者信息完整，可进入诊断与分型阶段。'+'</div>';
}

function renderMasterDataStage1(p,s) {
  return '<div class="section" style="margin-bottom:20px"><div class="section-title" style="font-size:13px;font-weight:700;color:var(--accent);margin-bottom:10px">📊 数据概览</div>'+
    '<div class="summary-bar" style="background:var(--bg-overlay);border-radius:8px;padding:16px 20px;font-size:14px;line-height:2;color:var(--text)"><span>数据源: <strong style="color:var(--accent)">'+(p.patient_id||'ALL')+'</strong></span> · <span>机构: <span class="tag blue" style="display:inline-block;padding:2px 8px;border-radius:var(--radius-full);font-size:12px;font-weight:500;background:var(--blue-bg);color:var(--blue)">'+(p.department||DEPT)+'</span></span>'+
    '<br><span>描述: <strong style="color:var(--accent)">'+(p.diagnosis||'主数据资产')+'</strong></span></div></div>'+
    '<div class="card" style="background:var(--bg-elevated);border:1px solid var(--border);border-radius:10px;padding:24px;margin-bottom:16px"><h3 style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:14px;display:flex;align-items:center;gap:8px"><span class="ch-icon">🗂️</span> 数据资产详情</h3>'+
    '<div class="tabs" style="display:flex;gap:0;margin-bottom:0;border-bottom:2px solid var(--border)">'+
    '<button class="tab-btn active" data-pane="basic" onclick="switchTab(\'basic\')" style="padding:8px 20px;border:none;border-bottom:3px solid var(--accent);background:transparent;color:var(--accent);font-weight:700;font-size:14px;cursor:pointer;font-family:inherit">基本信息</button>'+
    '<button class="tab-btn" data-pane="labs" onclick="switchTab(\'labs\')" style="padding:8px 20px;border:none;border-bottom:3px solid transparent;background:transparent;color:var(--text3);font-weight:500;font-size:14px;cursor:pointer;font-family:inherit">数据字段</button></div>'+
    '<div class="tab-pane active" id="pane-basic" style="display:block;padding:20px 0 0 0"><div style="font-size:13px;line-height:1.8">'+formatDP(p)+'</div></div>'+
    '<div class="tab-pane" id="pane-labs" style="display:none;padding:20px 0 0 0"><div style="font-size:13px;line-height:1.8">'+formatLabs(p)+'</div></div>'+
    '</div>'+
    '<div class="section" style="margin-bottom:20px"><div class="section-title" style="font-size:13px;font-weight:700;color:var(--accent);margin-bottom:10px">💡 数据状态</div>'+
    '<div class="triage-card III" style="border-radius:10px;padding:16px 20px;margin-top:12px;border-left:4px solid var(--green);background:var(--bg-elevated)">'+
    '<div class="triage-main" style="font-size:18px;font-weight:700;color:var(--green)">✓ 数据就绪</div>'+
    '<div class="triage-sub" style="font-size:13px;color:var(--text2);margin-top:4px">数据源已接入，可按标准流程进入分析阶段</div></div></div>'+
    '<div class="alert blue" style="border-radius:8px;padding:12px 16px;font-size:13px;line-height:1.6;margin-top:12px;background:var(--blue-bg);border:1px solid rgba(8,145,178,.2);color:var(--accent)">ℹ 数据资产信息完整，可进入数据分析阶段。</div>';
}

function renderSpecialistStage1(p,s) {
  return '<div class="section" style="margin-bottom:20px"><div class="section-title" style="font-size:13px;font-weight:700;color:var(--accent);margin-bottom:10px">🔬 专业评估概要</div>'+
    '<div class="summary-bar" style="background:var(--bg-overlay);border-radius:8px;padding:16px 20px;font-size:14px;line-height:2;color:var(--text)"><span>对象: <strong style="color:var(--accent)">'+p.name+'</strong></span> · <span>'+p.patient_id+'</span> · <span>领域: <span class="tag blue" style="display:inline-block;padding:2px 8px;border-radius:var(--radius-full);font-size:12px;font-weight:500;background:var(--blue-bg);color:var(--blue)">'+(p.department||DEPT)+'</span></span>'+
    '<br><span>场景: <strong style="color:var(--accent)">'+(p.diagnosis||'专业评估')+'</strong></span></div></div>'+
    '<div class="card" style="background:var(--bg-elevated);border:1px solid var(--border);border-radius:10px;padding:24px;margin-bottom:16px"><h3 style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:14px;display:flex;align-items:center;gap:8px"><span class="ch-icon">📋</span> 评估详情</h3>'+
    '<div class="tabs" style="display:flex;gap:0;margin-bottom:0;border-bottom:2px solid var(--border)">'+
    '<button class="tab-btn active" data-pane="basic" onclick="switchTab(\'basic\')" style="padding:8px 20px;border:none;border-bottom:3px solid var(--accent);background:transparent;color:var(--accent);font-weight:700;font-size:14px;cursor:pointer;font-family:inherit">基本信息</button>'+
    '<button class="tab-btn" data-pane="present" onclick="switchTab(\'present\')" style="padding:8px 20px;border:none;border-bottom:3px solid transparent;background:transparent;color:var(--text3);font-weight:500;font-size:14px;cursor:pointer;font-family:inherit">评估说明</button>'+
    '<button class="tab-btn" data-pane="labs" onclick="switchTab(\'labs\')" style="padding:8px 20px;border:none;border-bottom:3px solid transparent;background:transparent;color:var(--text3);font-weight:500;font-size:14px;cursor:pointer;font-family:inherit">参考指标</button></div>'+
    '<div class="tab-pane active" id="pane-basic" style="display:block;padding:20px 0 0 0"><div style="font-size:13px;line-height:1.8">'+formatDP(p)+'</div></div>'+
    '<div class="tab-pane" id="pane-present" style="display:none;padding:20px 0 0 0"><div style="font-size:13px;line-height:1.8">'+(p.present||p.scenario||'待填写')+'</div></div>'+
    '<div class="tab-pane" id="pane-labs" style="display:none;padding:20px 0 0 0"><div style="font-size:13px;line-height:1.8">'+formatLabs(p)+'</div></div>'+
    '</div>'+
    '<div class="section" style="margin-bottom:20px"><div class="section-title" style="font-size:13px;font-weight:700;color:var(--accent);margin-bottom:10px">🎯 评估判定</div>'+
    '<div class="triage-card III" style="border-radius:10px;padding:16px 20px;margin-top:12px;border-left:4px solid var(--green);background:var(--bg-elevated)">'+
    '<div class="triage-main" style="font-size:18px;font-weight:700;color:var(--green)">✓ 可进入评估</div>'+
    '<div class="triage-sub" style="font-size:13px;color:var(--text2);margin-top:4px">按专业评估标准流程依次推进</div></div></div>'+
    '<div class="alert blue" style="border-radius:8px;padding:12px 16px;font-size:13px;line-height:1.6;margin-top:12px;background:var(--blue-bg);border:1px solid rgba(8,145,178,.2);color:var(--accent)">ℹ 评估信息完整，可进入专业分析阶段。</div>';
}

function renderMidStage(p,s,n){
  var midIndex = n - 2; // 0-based among middle stages (skip first and last)
  var midCount = STAGES.length - 2;
  var stageFraction = midCount > 0 ? midIndex / midCount : 0.5; // 0~1, position in middle stages

  var items = [];
  if (p.assessments && p.assessments.length) items = p.assessments;
  else if (p.tools && p.tools.length) items = p.tools;
  else if (AGENT_TYPE === 'master_data') {
    var masterStages = [
      ['数据源接入','数据格式校验','字段映射配置'],
      ['数据清洗与标准化','缺失值处理','异常值标记'],
      ['统计指标计算','趋势对比分析','异常模式检测']
    ];
    items = masterStages[Math.floor(stageFraction * masterStages.length)] || masterStages[masterStages.length-1];
  } else if (AGENT_TYPE === 'specialist') {
    var specStages = [
      ['专业指标采集','数据质量评估','参考范围比对'],
      ['风险评估计算','风险分层','干预阈值判定'],
      ['干预方案生成','方案优先级排序','效果预估']
    ];
    items = specStages[Math.floor(stageFraction * specStages.length)] || specStages[specStages.length-1];
  } else {
    var businessStages = [
      ['检验结果复核','影像资料调阅','生命体征评估'],
      ['风险评分计算','合并症影响评估','多学科会诊协调'],
      ['治疗方案制定','用药方案确认','手术风险评估'],
      ['治疗执行监控','并发症预防','疗效初步评估']
    ];
    items = businessStages[Math.floor(stageFraction * businessStages.length)] || businessStages[businessStages.length-1];
  }

  var done = completedStages[n] ? items.length : Math.floor(items.length*0.5);
  var pending = items.length - done;
  var html = '<div class="kpis">';
  html += '<div class="kpi"><span class="val blue">'+items.length+'</span><span class="lbl">检查项</span></div>';
  html += '<div class="kpi"><span class="val '+(done===items.length?'green':'blue')+'">'+done+'</span><span class="lbl">已完成</span></div>';
  html += '<div class="kpi"><span class="val '+(pending>0?'amber':'green')+'">'+pending+'</span><span class="lbl">待完成</span></div>';
  html += '<div class="kpi"><span class="val blue">'+(items.length>0?Math.round(done/items.length*100):0)+'%</span><span class="lbl">完成率</span></div>';
  html += '</div>';
  html += '<div class="cl-section"><div class="cl-section-title">'+s.label+' — 检查列表</div>';
  items.forEach(function(item,i){
    var isDone = completedStages[n] || i < Math.floor(items.length/2);
    html += '<div class="cl-item"><span class="ck '+(isDone?'done':'')+'">'+(isDone?'✓':'')+'</span>'+
      '<span class="cl-name">'+item+'</span><span class="cl-dept">'+(p.department||DEPT)+'</span>'+
      '<span class="cl-reason">'+(isDone?'已完成':'待执行')+'</span></div>';
  });
  html += '</div>';
  if (p.plan && (n===4 || n===Math.floor(STAGES.length/2))) html += '<div class="card"><h3><span class="ch-icon">💡</span> 建议方案</h3><div style="font-size:13px;line-height:1.8">'+p.plan+'</div></div>';
  if (p.execution && (n===5 || n===Math.floor(STAGES.length*0.8))) html += '<div class="card"><h3><span class="ch-icon">🩺</span> 执行记录</h3><div style="font-size:13px;line-height:1.8">'+p.execution+'</div></div>';
  return html;
}

function renderLastStage(p,s){
  if (AGENT_TYPE === 'master_data') {
    return '<div class="card"><h3><span class="ch-icon">📤</span> 报告输出计划</h3>'+
      '<div style="font-size:13px;line-height:1.8">'+(p.followup||'根据数据规范生成标准化报告，包括指标看板、趋势图表、异常标注和分发配置。')+'</div></div>'+
      '<div class="card"><h3><span class="ch-icon">📊</span> 报告节点</h3>'+
      '<div class="fu-timeline">'+
      '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">日报</span><span class="fu-sub">核心指标 / 异常摘要</span></div>'+
      '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">周报</span><span class="fu-sub">趋势对比 / 环比分析</span></div>'+
      '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">月报</span><span class="fu-sub">综合分析 / 建议报告</span></div>'+
      '</div></div>'+
      '<div class="card"><h3><span class="ch-icon">📋</span> 分发计划</h3>'+
      '<table><tr><th>频率</th><th>报告内容</th><th>接收方</th><th>状态</th></tr>'+
      '<tr><td>每日</td><td>核心指标看板</td><td>数据管理员</td><td><span class="tag green">已配置</span></td></tr>'+
      '<tr><td>每周</td><td>趋势分析报告</td><td>科主任</td><td><span class="tag blue">已配置</span></td></tr>'+
      '<tr><td>每月</td><td>综合分析报告</td><td>全院管理层</td><td><span class="tag blue">已配置</span></td></tr></table></div>';
  }
  if (AGENT_TYPE === 'specialist') {
    return '<div class="card"><h3><span class="ch-icon">📅</span> 评估输出计划</h3>'+
      '<div style="font-size:13px;line-height:1.8">'+(p.followup||'根据专业评估规范生成评估报告，包括核心建议、风险预警和后续监测节点。')+'</div></div>'+
      '<div class="card"><h3><span class="ch-icon">📊</span> 跟踪节点</h3>'+
      '<div class="fu-timeline">'+
      '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">评估完成</span><span class="fu-sub">报告生成 / 建议输出</span></div>'+
      '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">1 月后</span><span class="fu-sub">效果初评 / 调整</span></div>'+
      '<div class="fu-node"><span class="fu-dot"></span><span class="fu-label">3 月后</span><span class="fu-sub">全面复核 / 长期方案</span></div>'+
      '</div></div>'+
      '<div class="card"><h3><span class="ch-icon">📋</span> 交付清单</h3>'+
      '<table><tr><th>时间</th><th>交付物</th><th>接收方</th><th>状态</th></tr>'+
      '<tr><td>即时</td><td>评估报告</td><td>申请科室</td><td><span class="tag green">待生成</span></td></tr>'+
      '<tr><td>1月后</td><td>效果评估</td><td>申请科室</td><td><span class="tag blue">计划中</span></td></tr>'+
      '<tr><td>3月后</td><td>长期管理方案</td><td>申请科室 · 专科</td><td><span class="tag blue">计划中</span></td></tr></table></div>';
  }
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
}

function formatDP(p){
  var html = '';
  var fields = {patient_id:'患者ID',name:'姓名',age:'年龄',gender:'性别',diagnosis:'诊断',department:'科室',scenario:'临床场景'};
  for (var k in fields){ if (p[k]!==undefined && p[k]!==null) html += '<div style="display:flex;padding:5px 0;border-bottom:1px solid var(--border-muted);line-height:1.8"><span style="width:90px;flex-shrink:0;color:var(--text3);font-size:12px;font-weight:500">'+fields[k]+'</span><span style="color:var(--text);font-size:13px;font-weight:500">'+p[k]+'</span></div>' }
  return html;
}

function formatLabs(p){
  if (!p.lab_results || Object.keys(p.lab_results).length===0) return '<div class="empty" style="text-align:center;padding:60px 20px;color:var(--text3)"><div class="e-icon">🔬</div><div class="e-text" style="font-size:14px">暂无检验数据</div></div>';
  var html = '';
  for (var k in p.lab_results){ html += '<div style="display:flex;padding:5px 0;border-bottom:1px solid var(--border-muted);line-height:1.8"><span style="width:90px;flex-shrink:0;color:var(--text3);font-size:12px;font-weight:500">'+k+'</span><span style="color:var(--text);font-size:13px;font-weight:500">'+p.lab_results[k]+'</span></div>' }
  return html;
}

function switchTab(pane){
  document.querySelectorAll('.tab-btn').forEach(function(e){
    e.classList.remove('active');
    e.style.borderBottomColor = 'transparent';
    e.style.color = 'var(--text3)';
    e.style.fontWeight = '500';
  });
  var btn = document.querySelector('.tab-btn[data-pane="'+pane+'"]');
  if (btn) {
    btn.classList.add('active');
    btn.style.borderBottomColor = 'var(--accent)';
    btn.style.color = 'var(--accent)';
    btn.style.fontWeight = '700';
  }
  document.querySelectorAll('.tab-pane').forEach(function(e){ e.style.display = 'none' });
  var p = document.getElementById('pane-'+pane);
  if (p) p.style.display = 'block';
}

function showToast(msg){
  var t = document.getElementById('toast');
  t.textContent = msg; t.style.display = 'block';
  clearTimeout(t._timeout);
  t._timeout = setTimeout(function(){ t.style.display = 'none' }, 2500);
}

init();

