"""药剂科专业 UI HTML (radiology-cockpit gold standard)."""
PHARMACY_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip 药剂科 — 临床药学工作台</title>
<style>
/* ===== Gold Standard Design Tokens ===== */
:root{--bg:#1c1c1e;--card-bg:#2c2c2e;--text:#f5f5f7;--text-secondary:#a1a1a6;--accent:#0a84ff;--danger:#ff453a;--warning:#ff9f0a;--success:#30d158;--purple:#bf5af2;--green:#30d158;--yellow:#ff9f0a;--red:#ff453a;--border:#38383a;--glow:rgba(10,132,255,.08);--bg-gradient:radial-gradient(ellipse at 50% 0%,var(--card-bg) 0%,var(--bg) 60%)}
body.light{--bg:#f2f2f7;--card-bg:#ffffff;--text:#1c1c1e;--text-secondary:#6e6e73;--accent:#007aff;--danger:#ff3b30;--warning:#ff9500;--success:#34c759;--purple:#af52de;--green:#34c759;--yellow:#ff9500;--red:#ff3b30;--border:#e5e5ea;--bg-gradient:radial-gradient(ellipse at 50% 0%,#ffffff 0%,#f2f2f7 60%)}
body.light .sidebar{background:var(--card-bg);border-right:1px solid var(--border)}
body.light .sidebar h2{color:var(--text)}
body.light .tab-link{color:var(--text-secondary)}
body.light .tab-link.active{color:#fff}
body.light .tab-link:hover:not(.active){color:var(--text);background:rgba(0,122,255,.04)}
body.light .result-box{background:var(--bg);color:var(--text);border:1px solid var(--border)}
body.light .drug-table th{background:var(--bg)}
body.light .drug-table td{border-bottom:1px solid var(--border)}
body.light .tag-crit{background:rgba(255,59,48,.12)}body.light .tag-high{background:rgba(255,149,0,.12)}body.light .tag-mod{background:rgba(52,199,89,.12)}
*{margin:0;padding:0;box-sizing:border-box}
::selection{background:var(--accent);color:#fff}
body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text','PingFang SC','Microsoft YaHei','Helvetica Neue',sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;background:var(--bg-gradient);color:var(--text);line-height:1.47;display:flex;height:100vh;overflow:hidden;letter-spacing:-.01em;transition:background .3s ease,color .3s ease}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.sidebar{width:200px;background:linear-gradient(180deg,#1a1a1a,#2B2B2B);color:#fff;overflow-y:auto;flex-shrink:0;display:flex;flex-direction:column}
.sidebar h2{padding:14px;font-size:15px;border-bottom:1px solid rgba(255,255,255,.1);display:flex;align-items:center;gap:6px}
.tab-link{display:block;padding:8px 14px;color:rgba(255,255,255,.6);cursor:pointer;font-size:12px;border-left:2px solid transparent;transition:all .15s ease}
.tab-link:hover{color:#fff;background:rgba(255,255,255,.05)}
.tab-link.active{color:#fff;border-left-color:var(--accent);background:rgba(10,132,255,.15)}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.main-h{height:52px;padding:0 20px;background:var(--card-bg);border-bottom:1px solid var(--border);font-size:14px;font-weight:600;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px)}
.content{flex:1;display:flex;overflow:hidden}
.left{flex:1;padding:16px 20px;overflow-y:auto}
.right{width:420px;padding:16px;background:var(--card-bg);border-left:1px solid var(--border);overflow-y:auto;flex-shrink:0}
.panel{display:none}.panel.active{display:block;animation:fadeIn .2s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
.panel h3{font-size:14px;font-weight:600;color:var(--accent);margin-bottom:10px}
.form-group{margin:6px 0}.form-group label{font-size:11px;color:var(--text-secondary);display:block;margin-bottom:4px;font-weight:500;text-transform:uppercase;letter-spacing:.04em}
.form-group input,.form-group select,.form-group textarea{padding:7px 12px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:13px;width:100%;font-family:inherit;margin-top:2px;outline:none;transition:border-color .15s}
.form-group input:focus,.form-group textarea:focus,.form-group select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(10,132,255,.12)}
.form-group textarea{height:70px;resize:vertical;font-family:'SF Mono',SFMono-Regular,Consolas,monospace;line-height:1.5}
.btn{padding:7px 18px;border:none;border-radius:8px;font-size:12px;font-weight:590;cursor:pointer;font-family:inherit;transition:all .12s ease}
.btn:active{transform:scale(.96)}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{opacity:.9;box-shadow:0 4px 12px rgba(10,132,255,.3)}
.result-box{background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:12px;padding:12px 16px;font-family:'SF Mono',SFMono-Regular,Consolas,monospace;font-size:11px;line-height:1.5;white-space:pre-wrap;max-height:400px;overflow-y:auto;margin-top:8px}
.row{display:flex;gap:8px;margin:6px 0}
.tag{display:inline-block;padding:1px 6px;border-radius:6px;font-size:9px;font-weight:600;margin:1px}
.tag-crit{background:rgba(255,69,58,.12);color:var(--danger)}.tag-high{background:rgba(255,159,10,.12);color:var(--warning)}.tag-mod{background:rgba(48,209,88,.12);color:var(--success)}
.drug-table{width:100%;font-size:11px;border-collapse:collapse;margin:8px 0}
.drug-table th{text-align:left;padding:6px 8px;background:var(--bg);font-size:10px;text-transform:uppercase;color:var(--text-secondary);letter-spacing:.03em;border-bottom:2px solid var(--border)}
.drug-table td{padding:6px 8px;border-bottom:1px solid var(--border)}
.drug-table tbody tr:hover{background:var(--bg)}
.header-btn{padding:5px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card-bg);color:var(--text);cursor:pointer;font-size:11px;font-weight:500;font-family:inherit;transition:all .15s}
.header-btn:hover{background:var(--accent);color:#fff;border-color:var(--accent);transform:scale(1.02)}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#060d14}
.badge-green{background:var(--green)}.badge-yellow{background:var(--warning)}.badge-red{background:var(--red)}.badge-purple{background:var(--purple)}
</style>
</head>
<body>
<div class="sidebar">
  <h2>💊 药剂科</h2>
  <div class="tab-link active" onclick="showTab('nutrition')">🥗 NRS2002 营养评估</div>
  <div class="tab-link" onclick="showTab('tpn')">💉 TPN 配比</div>
  <div class="tab-link" onclick="showTab('review')">📋 处方审核 (17规则)</div>
  <div class="tab-link" onclick="showTab('drugs')">🔍 药品查询</div>
  <div class="tab-link" onclick="showTab('route')">🔄 营养途径</div>
  <div class="tab-link" onclick="showTab('guard')">🛡 Guard</div>
  <div style="padding:8px 14px;font-size:10px;color:rgba(255,255,255,.3);border-top:1px solid rgba(255,255,255,.1);margin-top:auto">💊 231 tests | 93%</div>
</div>
<div class="main">
  <div class="main-h"><span id="panel-title">🥗 NRS2002 营养风险评估</span><div style="display:flex;align-items:center;gap:8px"><span style="font-size:11px;color:var(--text-secondary)">药学部临床工作台</span><button class="header-btn" onclick="toggleTheme()" id="btn-theme">🌙 黑夜</button></div></div>
  <div class="content">
    <div class="left">
      <div class="panel active" id="panel-nutrition"><h3>患者基本信息</h3><div class="row"><div class="form-group" style="flex:1"><label>患者ID</label><input id="f-id" value="__PID__"></div><div class="form-group" style="flex:1"><label>年龄</label><input id="f-age" value="__AGE__" type="number"></div><div class="form-group" style="flex:1"><label>体重(kg)</label><input id="f-wt" value="__WT__" type="number"></div><div class="form-group" style="flex:1"><label>身高(cm)</label><input id="f-ht" value="__HT__" type="number"></div></div><div class="form-group"><label>实验室 (JSON)</label><textarea id="f-labs">__LABS__</textarea></div><button class="btn btn-primary" onclick="callTool('assess_nutrition')">评估营养风险</button><div class="result-box" id="result-nutrition"></div></div>
      <div class="panel" id="panel-tpn"><h3>TPN 配比计算</h3><div class="row"><div class="form-group" style="flex:1"><label>体重(kg)</label><input id="f-wt2" value="__WT__" type="number"></div><div class="form-group" style="flex:1"><label>能量(kcal)</label><input id="f-ene" value="1800" type="number"></div></div><button class="btn btn-primary" onclick="callTool('calculate_tpn')">计算 TPN</button><div class="result-box" id="result-tpn"></div></div>
      <div class="panel" id="panel-review"><h3>处方审核 — 17条药物交互规则</h3><div class="form-group"><label>处方项目 (JSON数组)</label><textarea id="f-rx" style="height:100px">[{"name":"华法林","dose":"2.5mg qd"},{"name":"低分子肝素","dose":"4000IU q12h"},{"name":"布洛芬","dose":"400mg tid"},{"name":"庆大霉素","dose":"80mg q8h"},{"name":"呋塞米","dose":"20mg qd"}]</textarea></div><button class="btn btn-primary" onclick="callTool('full_prescription_review')">完整审核 (17规则)</button><button class="btn" style="background:var(--warning);color:#000;margin-left:4px" onclick="callTool('review_prescription')">基础审核</button><div class="result-box" id="result-review"></div></div>
      <div class="panel" id="panel-drugs"><h3>药品查询</h3><div class="row"><div class="form-group" style="flex:1"><label>关键词</label><input id="f-drug" value="华法林"></div></div><button class="btn btn-primary" onclick="callTool('list_medications')">查询</button><div class="result-box" id="result-drugs"></div></div>
      <div class="panel" id="panel-route"><h3>营养途径推荐</h3><div class="form-group"><label>胃肠功能</label><select id="f-gi"><option>normal</option><option>impaired</option></select></div><button class="btn btn-primary" onclick="callTool('recommend_nutrition_route')">推荐</button><div class="result-box" id="result-route"></div></div>
      <div class="panel" id="panel-guard"><h3>Guard 验证</h3><div class="form-group"><label>处方审核输出</label><textarea id="f-guard" style="height:80px">华法林与低分子肝素联用，需监测INR。参考: ACCP 抗血栓治疗指南。</textarea></div><button class="btn btn-primary" onclick="runGuard()">Guard</button><div class="result-box" id="result-guard"></div></div>
    </div>
    <div class="right">
      <div id="drug-rules"><h3 style="font-size:12px;margin-bottom:8px;color:var(--text)">📋 内置药物交互规则 (17条)</h3>
        <table class="drug-table"><tr><th>规则</th><th>药物</th><th>交互药物</th><th>风险</th></tr>
          <tr><td>D01</td><td>华法林</td><td>肝素/LMWH</td><td><span class="tag tag-high">HIGH</span></td></tr>
          <tr><td>D02</td><td>华法林</td><td>阿司匹林/氯吡格雷</td><td><span class="tag tag-high">HIGH</span></td></tr>
          <tr><td>D05</td><td>氨基糖苷类</td><td>呋塞米</td><td><span class="tag tag-high">HIGH</span></td></tr>
          <tr><td>D06</td><td>头孢曲松</td><td>钙剂</td><td><span class="tag tag-crit">CRITICAL</span></td></tr>
          <tr><td>D08</td><td>钙</td><td>磷</td><td><span class="tag tag-crit">CRITICAL</span></td></tr>
          <tr><td>D11</td><td>阿片类</td><td>苯二氮䓬类</td><td><span class="tag tag-crit">CRITICAL</span></td></tr>
          <tr><td>D12</td><td>NSAIDs</td><td>华法林</td><td><span class="tag tag-high">HIGH</span></td></tr>
        </table>
        <div style="font-size:10px;color:var(--text-secondary);margin-top:8px">共17条规则: 抗凝4 / 抗生素3 / 电解质3 / 镇痛3 / 心血管4</div>
      </div>
      <div id="summary" style="margin-top:12px"></div>
    </div>
  </div>
</div>
<script>
(function(){var t=localStorage.getItem('xhaip_theme')||'dark';if(t==='light'){document.body.classList.add('light');document.getElementById('btn-theme').textContent='☀ 白天'}})();
function toggleTheme(){var isLight=document.body.classList.toggle('light');localStorage.setItem('xhaip_theme',isLight?'light':'dark');document.getElementById('btn-theme').textContent=isLight?'☀ 白天':'🌙 黑夜'}
const API='/api/call';let currentTab='nutrition',history=[];
function showTab(t){document.querySelectorAll('.tab-link').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.panel').forEach(e=>e.classList.remove('active'));document.querySelector(`.tab-link[onclick*="${t}"]`)?.classList.add('active');document.getElementById('panel-'+t)?.classList.add('active');currentTab=t;document.getElementById('panel-title').textContent=document.querySelector(`.tab-link[onclick*="${t}"]`)?.textContent?.trim()||t}
function g(id){return document.getElementById(id)?.value||''}
async function callTool(tool){
  let params={patient_id:g('f-id')};
  if(tool==='assess_nutrition')params={patient_id:g('f-id'),weight_kg:parseFloat(g('f-wt')),height_cm:parseFloat(g('f-ht')),lab_results:JSON.parse(g('f-labs')||'{}'),age:parseInt(g('f-age'))};
  else if(tool==='calculate_tpn')params={patient_id:g('f-id'),weight_kg:parseFloat(g('f-wt2')),energy_kcal:parseFloat(g('f-ene'))};
  else if(tool==='full_prescription_review')params={patient_id:g('f-id'),prescription_items:JSON.parse(g('f-rx')||'[]')};
  else if(tool==='review_prescription')params={patient_id:g('f-id'),prescription_items:JSON.parse(g('f-rx')||'[]')};
  else if(tool==='list_medications')params={keyword:g('f-drug')};
  else if(tool==='recommend_nutrition_route')params={patient_id:g('f-id'),gi_function:g('f-gi')};
  const el=document.getElementById('result-'+currentTab);el.textContent='执行中...';
  try{const r=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent:'pharmacy',tool,params})});const d=await r.json();el.textContent=JSON.stringify(d,null,2)}catch(e){el.textContent='Error: '+e.message}
}
async function runGuard(){const r=await fetch('/api/guard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({output:g('f-guard'),scenario:'药物交互',agent:'pharmacy'})});const d=await r.json();document.getElementById('result-guard').textContent=JSON.stringify(d,null,2)}
</script>
</body>
</html>"""


_DEFAULT_LABS = {"albumin": 28, "crp": 80, "na": 135, "k": 3.2, "ca": 2.0,
                 "mg": 0.7, "bun": 12, "glucose": 8.5}


def render_pharmacy_ui() -> str:
    """渲染药剂科 UI — 患者信息取自数字病人库首位兼容患者, 无则用演示默认值。"""
    import json

    from haip.patients import load_patients

    pts = load_patients("pharmacy", limit=1, only_compatible=True)
    p = pts[0] if pts else {}
    labs = p.get("lab_results") or _DEFAULT_LABS
    return (PHARMACY_TEMPLATE
            .replace("__PID__", str(p.get("patient_id", "P001")))
            .replace("__AGE__", str(p.get("age", 75)))
            .replace("__WT__", str(p.get("weight_kg", 55)))
            .replace("__HT__", str(p.get("height_cm", 170)))
            .replace("__LABS__", json.dumps(labs, ensure_ascii=False)))
