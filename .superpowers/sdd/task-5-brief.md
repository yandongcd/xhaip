## Task 5: 闂ㄦ埛 JS 鈥?KPI 鑱氬悎 + 鑳藉姏鍗℃墽琛屾覆鏌?
**Files:**
- Modify: `packages/haip-core/haip/ui_ortho_portal.html` (`<script>` 娈电殑 `computeKpi` / `runCapability` 鍗犱綅瀹炵幇)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: Task 4 鐨?`patients`銆乣selectedPid`銆乣apiCall`銆乣CAPS`锛涘悗绔?`POST /api/v1/orthopedic/{timing,complications,classify,assess,plan,mdt,rehab,followup}`銆?- Produces: 瀹為檯瀹炵幇 `async function computeKpi()`锛堝啓鍏?5 涓?`#kpi-*`锛変笌 `async function runCapability(api)`锛堟妸缁撴灉娓叉煋杩?`#result-content`锛屽惈 urgency/overall_risk 寰界珷锛夈€?- 鍏ュ弬缁勭粐瑙勫垯锛?  - timing: `{patient_id, labs, conditions, meds, ecg_findings:""}`
  - complications: `{patient_id, age, labs, conditions}`
  - classify: `{patient_id, xray_findings:{location:fracture_type, type:""}}`
  - assess: `{patient_id}`
  - plan: `{patient_id, fracture_type, age}`
  - mdt: `{patient_id, chief_complaint:diagnosis}`
  - rehab: `{patient_id, procedure}`
  - followup: `{patient_id, procedure}`

- [ ] **Step 1: 鍐?KPI/鑳藉姏鎵ц鐨勯敋鐐逛笌鍑芥暟瀛樺湪鎬ф祴璇?*

鍦?`test_ortho_portal.py` 杩藉姞锛?
```python
class TestPortalKpiAndRun:
    def _body(self):
        return client.get("/ortho-portal").text

    def test_kpi_uses_v1_api(self):
        body = self._body()
        assert "/api/v1/orthopedic/timing" in body
        assert "/api/v1/orthopedic/complications" in body

    def test_run_capability_dispatch(self):
        body = self._body()
        for api in ["classify","assess","mdt","timing",
                    "complications","plan","rehab","followup"]:
            assert "/api/v1/orthopedic/" + api in body

    def test_kpi_targets_present(self):
        body = self._body()
        for kid in ["kpi-total","kpi-pending","kpi-48h",
                    "kpi-highrisk","kpi-avgfactor"]:
            assert kid in body
```

锛堝悓鏃堕獙璇佸悗绔兘鍔涚湡瀹炲彲绠椻€斺€旈泦鎴愬啋鐑燂級

```python
class TestV1ApiSmoke:
    def _p(self, pid):
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        return MOCK_PATIENT_DB[pid]

    def test_timing_api(self):
        p = self._p("P003")
        r = client.post("/api/v1/orthopedic/timing",
                        json={"patient_id":"P003","labs":p["labs"],
                              "conditions":p["conditions"],"meds":p["meds"],
                              "ecg_findings":""})
        assert r.status_code == 200
        assert r.json()["urgency"] == "elective"

    def test_complications_api(self):
        p = self._p("P005")
        r = client.post("/api/v1/orthopedic/complications",
                        json={"patient_id":"P005","age":p["age"],
                              "labs":p["labs"],"conditions":p["conditions"]})
        assert r.status_code == 200
        assert r.json()["overall_risk"] in ("low","moderate","high")

    def test_plan_api(self):
        r = client.post("/api/v1/orthopedic/plan",
                        json={"patient_id":"P001","fracture_type":"鑲￠棰堥鎶?,"age":78})
        assert r.status_code == 200
        assert "procedure" in r.json()
```

- [ ] **Step 2: 杩愯纭澶辫触**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalKpiAndRun tests/integration/test_ortho_portal.py::TestV1ApiSmoke -q`
Expected: `TestPortalKpiAndRun` FAIL锛堝崰浣嶇┖鍑芥暟涓嶅惈 v1 璺緞锛夛紱`TestV1ApiSmoke` 搴斿凡 PASS锛堝悗绔氨缁級銆?
- [ ] **Step 3: 鐢ㄧ湡瀹炲疄鐜版浛鎹?`computeKpi` / `runCapability` 鍗犱綅**

灏?Task 4 涓殑杩欎袱琛屽崰浣嶏細

```javascript
function computeKpi(){}      // Task 5 瑕嗙洊瀹炵幇
function runCapability(){}   // Task 5 瑕嗙洊瀹炵幇
```

鏇挎崲涓猴細

```javascript
async function computeKpi(){
  const ids = Object.keys(patients);
  if(!ids.length){ return; }
  let pending=0, emergency=0, highrisk=0, factorSum=0, n=0;
  for(const pid of ids){
    const p = patients[pid];
    try{
      const t = await apiCall("/api/v1/orthopedic/timing",
        {patient_id:pid, labs:p.labs||{}, conditions:p.conditions||[], meds:p.meds||[], ecg_findings:""});
      if(t.urgency==="emergency") emergency++;
      if(t.urgency==="emergency"||t.urgency==="urgent") pending++;
      factorSum += (t.total_factors||0);
      const c = await apiCall("/api/v1/orthopedic/complications",
        {patient_id:pid, age:p.age||0, labs:p.labs||{}, conditions:p.conditions||[]});
      if(c.overall_risk==="high") highrisk++;
      n++;
    }catch(e){ /* 璺宠繃 */ }
  }
  document.getElementById("kpi-total").textContent = ids.length;
  document.getElementById("kpi-pending").textContent = pending;
  document.getElementById("kpi-48h").textContent = n ? Math.round(emergency/n*100)+"%" : "鈥?;
  document.getElementById("kpi-highrisk").textContent = highrisk;
  document.getElementById("kpi-avgfactor").textContent = n ? (factorSum/n).toFixed(1) : "鈥?;
}

function badge(v){
  const cls = {high:"high",moderate:"moderate",low:"low",emergency:"emergency",urgent:"urgent",elective:"high"}[v] || "moderate";
  return `<span class="badge ${cls}">${v}</span>`;
}

function buildParams(api, p){
  const pid = selectedPid;
  switch(api){
    case "timing": return {patient_id:pid, labs:p.labs||{}, conditions:p.conditions||[], meds:p.meds||[], ecg_findings:""};
    case "complications": return {patient_id:pid, age:p.age||0, labs:p.labs||{}, conditions:p.conditions||[]};
    case "classify": return {patient_id:pid, xray_findings:{location:p.fracture_type||"", type:""}};
    case "assess": return {patient_id:pid};
    case "plan": return {patient_id:pid, fracture_type:p.fracture_type||"", age:p.age||0};
    case "mdt": return {patient_id:pid, chief_complaint:p.diagnosis||""};
    case "rehab": return {patient_id:pid, procedure:p.procedure||""};
    case "followup": return {patient_id:pid, procedure:p.procedure||""};
    default: return {patient_id:pid};
  }
}

async function runCapability(api){
  const content = document.getElementById("result-content");
  document.getElementById("result-empty").style.display = "none";
  if(!selectedPid){ content.innerHTML = '<div class="muted">璇峰厛鍦ㄥ乏渚ч€夋嫨鎮ｈ€?/div>'; return; }
  const p = patients[selectedPid];
  content.innerHTML = '<div class="muted">璋冪敤涓€?/div>';
  try{
    const d = await apiCall("/api/v1/orthopedic/"+api, buildParams(api, p));
    let head = "";
    if(d.urgency) head += "鎵嬫湳鏃舵満: " + badge(d.urgency) + " 路 SLA " + (d.sla||"") + "<br>";
    if(d.overall_risk) head += "缁煎悎椋庨櫓: " + badge(d.overall_risk) + "<br>";
    if(d.error) head += '<span class="badge high">閿欒</span> ' + d.error + "<br>";
    content.innerHTML = `<div style="margin-bottom:8px">${head}</div><div class="result-box">${JSON.stringify(d,null,2)}</div>`;
  }catch(e){
    content.innerHTML = '<div class="result-box"><span class="badge high">鍚庣鏈繛鎺?/span> ' + e.message + '</div>';
  }
}
```

- [ ] **Step 4: 杩愯纭鍏ㄩ儴閫氳繃**

Run: `python -m pytest tests/integration/test_ortho_portal.py -q`
Expected: PASS锛堝叏閮ㄧ被锛夈€?
- [ ] **Step 5: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-core/haip/ui_ortho_portal.html tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 闂ㄦ埛 KPI 鑱氬悎 + 鑳藉姏鍗＄湡瀹?API 鎵ц"
```

---

