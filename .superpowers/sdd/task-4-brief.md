## Task 4: 闂ㄦ埛 JS 鈥?鎮ｈ€呴槦鍒?+ 鑳藉姏鍗?+ 闃舵鏃堕棿杞存覆鏌?
**Files:**
- Modify: `packages/haip-core/haip/ui_ortho_portal.html` (`<script>` 娈?
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: 甯冨眬閿氱偣 (Task 3)锛沗POST /api/call` (his_patient) 鎷夋偅鑰呫€?- Produces: 鍓嶇鍏ㄥ眬瀵硅薄/甯搁噺锛堜緵 Task 5 浣跨敤锛夛細
  - `const PATIENT_IDS = ["P001","P002","P003","P004","P005"]`
  - `const CAPS = [...]`锛? 椤癸紝瀛楁 `{id,ico,title,desc,api}`锛宎pi 鈭?classify/assess/mdt/timing/complications/plan/rehab/followup锛?  - `const STAGES = [...]`锛?1 椤?`{order,label,desc}`锛屼笌 YAML 瀵瑰簲锛?  - `let selectedPid = null`
  - `function renderPatients(list)` / `function renderCaps()` / `function renderStages()` / `async function loadPatients()`

- [ ] **Step 1: 鍐欍€岃兘鍔涘崱涓庨樁娈甸潤鎬佸唴瀹广€嶆祴璇?*

鍦?`test_ortho_portal.py` 杩藉姞锛?
```python
class TestPortalContent:
    def _body(self):
        return client.get("/ortho-portal").text

    def test_has_eight_capabilities(self):
        body = self._body()
        for api in ["classify", "assess", "mdt", "timing",
                    "complications", "plan", "rehab", "followup"]:
            assert api in body, f"缂鸿兘鍔?API {api}"

    def test_has_eleven_stages_labels(self):
        body = self._body()
        for label in ["鎬ヨ瘖鍒嗚瘖", "楠ㄦ姌鍒嗗瀷", "鏈墠璇勪及", "MDT 浼氳瘖",
                      "鎵嬫湳鏃舵満", "骞跺彂鐥囬娴?, "鎵嬫湳鏂规", "鍥存湳鏈熸姢鐞?,
                      "鏈悗搴峰", "闅忚璁″垝", "璐ㄦ帶瀹¤"]:
            assert label in body, f"缂洪樁娈?{label}"

    def test_has_patient_ids_and_loader(self):
        body = self._body()
        assert "P001" in body and "P005" in body
        assert "/api/call" in body
        assert "his_patient" in body
```

- [ ] **Step 2: 杩愯纭澶辫触**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalContent -q`
Expected: FAIL锛坰cript 涓虹┖锛夈€?
- [ ] **Step 3: 濉厖 JS锛堝父閲?+ 娓叉煋 + 鎮ｈ€呭姞杞斤級**

灏?`ui_ortho_portal.html` 涓?`<script>/* Task 4/5 濉厖 JS */</script>` 鏇挎崲涓猴細

```html
<script>
const PATIENT_IDS = ["P001","P002","P003","P004","P005"];
const CAPS = [
  {id:"classify", ico:"馃Υ", title:"楠ㄦ姌鍒嗗瀷", desc:"Garden/Evans/AO", api:"classify"},
  {id:"assess", ico:"馃搵", title:"鏈墠璇勪及", desc:"鍚堝苟鐥?鑽墿/钀ュ吇", api:"assess"},
  {id:"mdt", ico:"馃攧", title:"MDT 浼氳瘖", desc:"澶氬绉戣仛鍚堢邯瑕?, api:"mdt"},
  {id:"timing", ico:"鈴憋笍", title:"T2 鎵嬫湳鏃舵満", desc:"8 鍥犵礌鍒嗙骇鍐崇瓥", api:"timing"},
  {id:"complications", ico:"馃┖", title:"骞跺彂鐥囬娴?, desc:"DVT/鎰熸煋/蹇冭剰/璺屽€?, api:"complications"},
  {id:"plan", ico:"馃敧", title:"鎵嬫湳鏂规", desc:"THA/HA/PFNA/DHS", api:"plan"},
  {id:"rehab", ico:"馃弮", title:"鏈悗搴峰", desc:"4 闃舵 + Harris", api:"rehab"},
  {id:"followup", ico:"馃搮", title:"闅忚璁″垝", desc:"1/3/6/12 鏈?, api:"followup"},
];
const STAGES = [
  {order:1, label:"鎬ヨ瘖鍒嗚瘖", desc:"11 椤规鏌ユ竻鍗? 缁胯壊閫氶亾鍒ゅ畾"},
  {order:2, label:"楠ㄦ姌鍒嗗瀷", desc:"Garden/Evans/AO 鍒嗗瀷璇勪及"},
  {order:3, label:"鏈墠璇勪及", desc:"鍚堝苟鐥?鑽墿/钀ュ吇/璁ょ煡 + 14 椤瑰畬澶囨€?},
  {order:4, label:"MDT 浼氳瘖", desc:"鑱氬悎蹇冨唴+楹婚唹+楠ㄧ+鐤肩棝 鈫?绾"},
  {order:5, label:"鎵嬫湳鏃舵満", desc:"T2 8 鍥犵礌灞傛鍐崇瓥"},
  {order:6, label:"骞跺彂鐥囬娴?, desc:"DVT/鎰熸煋/蹇冭剰/璺屽€?璋靛 4 缁?},
  {order:7, label:"鎵嬫湳鏂规", desc:"THA/HA/PFNA/DHS 鎺ㄨ崘"},
  {order:8, label:"鍥存湳鏈熸姢鐞?, desc:"4 闃舵 25 椤规姢鐞嗚鍒?},
  {order:9, label:"鏈悗搴峰", desc:"4 闃舵搴峰 + Harris 璇勫垎"},
  {order:10, label:"闅忚璁″垝", desc:"1/3/6/12 鏈?+ 绾㈡棗鐥囩姸 + 楠ㄨ川鐤忔澗"},
  {order:11, label:"璐ㄦ帶瀹¤", desc:"6 闃舵 18 妫€鏌ョ偣鍚堣璇勫垎"},
];
let selectedPid = null;
let patients = {};

function renderStages(){
  document.getElementById("stage-rows").innerHTML = STAGES.map(s =>
    `<div class="stage-row"><div class="num">${s.order}</div><div><div>${s.label}</div><div class="st-desc">${s.desc}</div></div></div>`
  ).join("");
}

function renderCaps(){
  document.getElementById("capability-grid").innerHTML = CAPS.map(c =>
    `<div class="cap" data-api="${c.api}" onclick="runCapability('${c.api}')"><div class="cap-ico">${c.ico}</div><div class="cap-title">${c.title}</div><div class="cap-desc">${c.desc}</div></div>`
  ).join("");
}

function renderPatients(){
  const el = document.getElementById("patient-list");
  const ids = Object.keys(patients);
  if(!ids.length){ el.innerHTML = '<div class="muted" style="padding:8px">鍚庣鏈繛鎺?/ 鏃犳偅鑰?/div>'; return; }
  el.innerHTML = ids.map(pid => {
    const p = patients[pid];
    const active = pid === selectedPid ? "active" : "";
    return `<div class="p-card ${active}" onclick="selectPatient('${pid}')"><div class="p-name">${p.name||pid}</div><div class="p-meta">${p.age||"?"}宀?路 ${p.gender||""} 路 ${pid}</div><div class="p-meta">${p.diagnosis||""}</div></div>`;
  }).join("");
}

function selectPatient(pid){
  selectedPid = pid;
  renderPatients();
  document.getElementById("result-empty").style.display = "none";
  document.getElementById("result-content").innerHTML = `<div class="muted">宸查€夋嫨 ${patients[pid].name||pid}锛岀偣鍑昏兘鍔涘崱鎵ц AI 璇婄枟</div>`;
}

async function apiCall(path, body){
  const r = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  if(!r.ok) throw new Error("HTTP "+r.status);
  return r.json();
}

async function loadPatients(){
  for(const pid of PATIENT_IDS){
    try{
      const d = await apiCall("/api/call", {agent:"orthopedic-surgery", tool:"his_patient", params:{patient_id:pid}});
      if(!d.error) patients[pid] = d;
    }catch(e){ /* 璺宠繃澶辫触椤?*/ }
  }
  renderPatients();
  computeKpi();  // Task 5 瀹氫箟
}

// 涓婚鍒囨崲
document.getElementById("theme-toggle").addEventListener("click", () => {
  document.body.classList.toggle("light");
  document.getElementById("theme-toggle").textContent = document.body.classList.contains("light") ? "馃寵 娣辫壊" : "鈽€ 娴呰壊";
});

// 鍒濆鍖?renderStages();
renderCaps();
function computeKpi(){}      // Task 5 瑕嗙洊瀹炵幇
function runCapability(){}   // Task 5 瑕嗙洊瀹炵幇
loadPatients();
</script>
```

- [ ] **Step 4: 杩愯纭鍐呭娴嬭瘯閫氳繃**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalContent -q`
Expected: PASS锛? 椤癸級銆?
- [ ] **Step 5: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-core/haip/ui_ortho_portal.html tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 闂ㄦ埛 JS 鎮ｈ€呴槦鍒?鑳藉姏鍗?闃舵娓叉煋"
```

---

