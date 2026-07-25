
var XHAIP_DATA = JSON.parse(document.getElementById('xhaip-data').textContent);
var AGENT = XHAIP_DATA.name;
var TOOLS = XHAIP_DATA.tools;
var HISTORY = [];

function showTab(t) {
  document.querySelectorAll('.tab').forEach(function(e) { e.classList.remove('active'); });
  document.querySelectorAll('.tool-card').forEach(function(e) { e.classList.remove('active'); });
  var el = document.querySelector('.tab[onclick*="'+t+'"]');
  if (el) el.classList.add('active');
  var card = document.getElementById('card-'+t);
  if (card) card.classList.add('active');
}

// Init: show first tool
(function() {
  if (TOOLS.length > 0) showTab(TOOLS[0].name);
})();

async function callTool(tool) {
  var params = {};
  var toolDef = TOOLS.find(function(t) { return t.name === tool; });
  if (toolDef && Object.keys(toolDef.input||{}).length) {
    for (var k in toolDef.input) {
      params[k] = document.querySelector('.inp-'+tool+'[data-field="'+k+'"]')?.value||toolDef.input[k];
    }
  } else {
    try { var el = document.querySelector('.inp-'+tool); if (el) params = JSON.parse(el.value||'{}'); } catch(e) {}
  }
  var el = document.getElementById('result-'+tool);
  el.textContent = '执行中...';
  try {
    var r = await fetch('/api/call', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({agent:AGENT, tool:tool, params:params})
    });
    var d = await r.json();
    el.textContent = JSON.stringify(d, null, 2);
    addHistory(tool, d.status || 'ok');
  } catch(e) { el.textContent = 'Error: '+e.message; }
}

async function runGuard(tool) {
  var output = document.getElementById('result-'+tool)?.textContent || '';
  var r = await fetch('/api/guard', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({output:output, agent:AGENT})
  });
  var d = await r.json();
  document.getElementById('result-'+tool).textContent = '安全校验结果:\n'+JSON.stringify(d, null, 2);
}

function addHistory(tool, status) {
  HISTORY.unshift({tool:tool, time:new Date().toLocaleTimeString('zh-CN'), status:status});
  if (HISTORY.length > 10) HISTORY.pop();
  var color = status === 'ok' ? 'var(--green)' : 'var(--danger)';
  document.getElementById('history-list').innerHTML = HISTORY.map(function(e) {
    return '<div class="history-item"><span class="hist-tool">'+e.tool+'</span><span class="hist-status" style="color:'+color+'">'+e.status+'</span><span class="hist-time">'+e.time+'</span></div>';
  }).join('');
}
