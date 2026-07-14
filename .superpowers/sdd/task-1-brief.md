## Task 1: 鎵╁厖 his_adapter 鎮ｈ€呬富鏁版嵁鍒?5 浣?
**Files:**
- Modify: `packages/haip-hospital/modules/orthopedics/his_adapter.py:25-36` (MOCK_PATIENT_DB) 鍙?`:81-100` (query_patient)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: 鏃?(鍩虹鏁版嵁灞?
- Produces:
  - `MOCK_PATIENT_DB: dict[str, dict]` 鈥?閿?`P001..P005`锛屾瘡浣嶅惈 `name, age, gender, diagnosis, comorbidities, medications, allergies, labs(dict), conditions(list[str]), meds(list[str]), fracture_type(str), procedure(str)`銆?  - `query_patient(*, patient_id: str, **kwargs) -> dict` 鈥?杩斿洖涓婅堪鍏ㄩ儴瀛楁 + `patient_id, source:"HIS", _mock:True`銆?- 鎮ｈ€呴闄╁垎甯?(渚?KPI 鏂█)锛歅001=urgent(涓嵄)銆丳002=emergency(鏃犲洜绱?銆丳003=elective(楂樺嵄蹇冭剰)銆丳004=emergency銆丳005=urgent銆?
- [ ] **Step 1: 鏂板缓娴嬭瘯鏂囦欢骞跺啓鎮ｈ€呮暟鎹殑澶辫触娴嬭瘯**

Create `tests/integration/test_ortho_portal.py`:

```python
"""鍒涗激楠ㄧ璇婄枟闂ㄦ埛 (/ortho-portal) 闆嗘垚娴嬭瘯."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital" / "modules"))

from fastapi.testclient import TestClient  # noqa: E402
from haip.agent import load_from_dir  # noqa: E402

load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))
from haip.web_server import app  # noqa: E402

client = TestClient(app)

REQUIRED_PATIENTS = ["P001", "P002", "P003", "P004", "P005"]


class TestPatientData:
    def test_five_patients_exist(self):
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        for pid in REQUIRED_PATIENTS:
            assert pid in MOCK_PATIENT_DB, f"缂哄皯鎮ｈ€?{pid}"

    def test_each_patient_has_structured_fields(self):
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        for pid in REQUIRED_PATIENTS:
            p = MOCK_PATIENT_DB[pid]
            assert p.get("labs"), f"{pid} 缂?labs"
            assert isinstance(p["labs"], dict) and len(p["labs"]) >= 5
            assert isinstance(p.get("conditions"), list)
            assert isinstance(p.get("meds"), list)
            assert p.get("fracture_type"), f"{pid} 缂?fracture_type"

    def test_query_patient_passes_structured_fields(self):
        from orthopedics.his_adapter import query_patient
        r = query_patient(patient_id="P003")
        assert r["patient_id"] == "P003"
        assert "labs" in r and "conditions" in r and "meds" in r
        assert r["_mock"] is True
```

- [ ] **Step 2: 杩愯娴嬭瘯纭澶辫触**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPatientData -q`
Expected: FAIL锛圥003 缂哄け / labs 閿笉瀛樺湪锛夈€?
- [ ] **Step 3: 鏇挎崲 MOCK_PATIENT_DB 涓?5 浣嶅苟琛ラ綈瀛楁**

灏?`his_adapter.py` 涓?`MOCK_PATIENT_DB = { ... P001, P002 ... }` 鏁村潡鏇挎崲涓猴細

```python
MOCK_PATIENT_DB = {
    "P001": {
        "name": "寮?*", "age": 78, "gender": "濂?,
        "diagnosis": "鍙宠偂楠ㄩ楠ㄦ姌 Garden III",
        "comorbidities": ["楂樿鍘?, "2鍨嬬硸灏跨梾"],
        "medications": ["纭濊嫰鍦板钩 30mg qd", "浜岀敳鍙岃儘 500mg bid"],
        "allergies": ["闈掗湁绱?],
        "labs": {"cTnI": 0.02, "Hb": 95, "Cr": 110, "Glu": 9.5,
                 "WBC": 8.5, "CRP": 40, "INR": 1.1, "egfr": 65},
        "conditions": ["楂樿鍘?, "绯栧翱鐥?],
        "meds": ["nifedipine", "metformin"],
        "fracture_type": "鑲￠棰堥鎶?, "procedure": "THA (鍏ㄩ珛鍏宠妭缃崲)",
    },
    "P002": {
        "name": "鏉?*", "age": 82, "gender": "鐢?,
        "diagnosis": "宸﹁偂楠ㄨ浆瀛愰棿楠ㄦ姌 Evans ID",
        "comorbidities": ["鎴块ⅳ", "楂樿鍘?],
        "medications": ["鍗庢硶鏋?3mg qd", "姘ㄦ隘鍦板钩 5mg qd"],
        "allergies": [],
        "labs": {"cTnI": 0.01, "Hb": 138, "Cr": 90, "Glu": 5.4,
                 "WBC": 6.5, "CRP": 6, "INR": 1.1, "egfr": 82},
        "conditions": ["楂樿鍘?],
        "meds": ["amlodipine"],
        "fracture_type": "杞瓙闂撮鎶?, "procedure": "PFNA (鑲￠杩戠闃叉棆楂撳唴閽?",
    },
    "P003": {
        "name": "鐜?*", "age": 80, "gender": "鐢?,
        "diagnosis": "鍙宠偂楠ㄩ楠ㄦ姌 Garden IV",
        "comorbidities": ["鍐犲績鐥?, "闄堟棫蹇冩", "楂樿鍘?],
        "medications": ["闃垮徃鍖规灄 100mg qd", "缇庢墭娲涘皵 25mg bid"],
        "allergies": [],
        "labs": {"cTnI": 0.08, "Hb": 105, "Cr": 120, "Glu": 6.8,
                 "WBC": 9.0, "CRP": 30, "INR": 1.2, "egfr": 55},
        "conditions": ["鍐犲績鐥?, "蹇冩鍙?, "楂樿鍘?],
        "meds": ["aspirin", "metoprolol"],
        "fracture_type": "鑲￠棰堥鎶?, "procedure": "THA (鍏ㄩ珛鍏宠妭缃崲)",
    },
    "P004": {
        "name": "璧?*", "age": 68, "gender": "濂?,
        "diagnosis": "宸﹁偂楠ㄨ浆瀛愰棿楠ㄦ姌 Evans IIA",
        "comorbidities": ["楠ㄨ川鐤忔澗"],
        "medications": ["闃夸粦鑶﹂吀閽?70mg qw"],
        "allergies": [],
        "labs": {"cTnI": 0.01, "Hb": 128, "Cr": 78, "Glu": 5.1,
                 "WBC": 7.0, "CRP": 8, "INR": 1.0, "egfr": 90},
        "conditions": ["楠ㄨ川鐤忔澗"],
        "meds": ["alendronate"],
        "fracture_type": "杞瓙闂撮鎶?, "procedure": "PFNA (鑲￠杩戠闃叉棆楂撳唴閽?",
    },
    "P005": {
        "name": "闄?*", "age": 85, "gender": "濂?,
        "diagnosis": "鍙宠偂楠ㄩ楠ㄦ姌 Garden III 鍚堝苟璐",
        "comorbidities": ["鎱㈡€ц偩鐥?, "璐", "鐥村憜"],
        "medications": ["姘悺鏍奸浄 75mg qd"],
        "allergies": ["纾鸿兒"],
        "labs": {"cTnI": 0.03, "Hb": 88, "Cr": 150, "Glu": 6.2,
                 "WBC": 8.0, "CRP": 50, "INR": 1.3, "egfr": 45},
        "conditions": ["鎱㈡€ц偩鐥?, "璐", "鐥村憜", "鍐犲績鐥?],
        "meds": ["clopidogrel"],
        "fracture_type": "鑲￠棰堥鎶?, "procedure": "THA (鍏ㄩ珛鍏宠妭缃崲)",
    },
}
```

锛堣鏄庯細P002 鏃犻珮鍗便€佹棤 warfarin-with-INR>1.5 瑙﹀彂 鈫?emergency锛汸004 鏃犲洜绱?鈫?emergency锛汸001 hb<100+鏃犲績鑴忕梾 涓嶈Е鍙戙€乬lucose 9.5 涓嶈Е鍙戙€乪gfr 65 涓嶈Е鍙戔€﹀疄闄?P001 鏃犱腑鍗卞洜绱犱害涓?emergency鈥斺€旇 Step 6 淇銆傦級

- [ ] **Step 4: `query_patient` 閫忎紶鏂板瓧娈碉紙宸茶嚜鍔ㄩ€忎紶锛岀‘璁ゆ棤闇€鏀瑰姩锛?*

`query_patient` 鐜版湁瀹炵幇 `return {**patient, "patient_id": ..., "source": "HIS", "_mock": True, ...}` 宸茬粡閫忎紶 `**patient` 鍏ㄩ儴瀛楁锛屾棤闇€鏀逛唬鐮併€備粎纭杩斿洖鍚?`labs/conditions/meds`銆?
- [ ] **Step 5: 杩愯娴嬭瘯纭鏁版嵁缁撴瀯閫氳繃**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPatientData -q`
Expected: PASS锛? 椤癸級銆?
- [ ] **Step 6: 琛ュ厖 urgency 鍒嗗竷鏂█骞舵牎鍑嗘暟鎹?*

鍦?`test_ortho_portal.py` 杩藉姞锛?
```python
class TestUrgencyDistribution:
    """鏍￠獙鎮ｈ€呮暟鎹兘瑕嗙洊涓嶅悓鎵嬫湳鏃舵満鍒嗙骇 (鐪熷疄寮曟搸璁＄畻)."""

    def _timing(self, pid):
        from orthopedics import evaluate_timing
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        p = MOCK_PATIENT_DB[pid]
        return evaluate_timing(patient_id=pid, labs=p["labs"],
                               conditions=p["conditions"], meds=p["meds"],
                               ecg_findings="")["urgency"]

    def test_has_elective_high_risk(self):
        assert self._timing("P003") == "elective"  # cTnI 0.08 > 0.04

    def test_has_emergency_case(self):
        urgencies = {self._timing(p) for p in REQUIRED_PATIENTS}
        assert "emergency" in urgencies

    def test_complications_high_risk_exists(self):
        from orthopedics import predict_complications
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        overalls = []
        for pid in REQUIRED_PATIENTS:
            p = MOCK_PATIENT_DB[pid]
            r = predict_complications(patient_id=pid, age=p["age"],
                                      labs=p["labs"], conditions=p["conditions"])
            overalls.append(r["overall_risk"])
        assert "high" in overalls  # P005 楂橀緞+鐥村憜+CKD
```

Run: `python -m pytest tests/integration/test_ortho_portal.py -q`
Expected: PASS銆傝嫢鏌愭柇瑷€澶辫触锛屽井璋冨搴旀偅鑰?labs/conditions锛堝 P003 cTnI 鎻愬埌 0.08 宸?>0.04 瑙﹀彂 elective锛汸005 age 85 + 鐥村憜 鈫?fall high锛夈€?
- [ ] **Step 7: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-hospital/modules/orthopedics/his_adapter.py tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 鎵╁厖 his_adapter 鎮ｈ€呭埌 5 浣嶅苟琛ラ綈 labs/conditions/meds"
```

---

