"""创伤骨科诊疗门户 (/ortho-portal) 集成测试."""

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
            assert pid in MOCK_PATIENT_DB, f"缺少患者 {pid}"

    def test_each_patient_has_structured_fields(self):
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        for pid in REQUIRED_PATIENTS:
            p = MOCK_PATIENT_DB[pid]
            assert p.get("labs"), f"{pid} 缺 labs"
            assert isinstance(p["labs"], dict) and len(p["labs"]) >= 5
            assert isinstance(p.get("conditions"), list)
            assert isinstance(p.get("meds"), list)
            assert p.get("fracture_type"), f"{pid} 缺 fracture_type"

    def test_query_patient_passes_structured_fields(self):
        from orthopedics.his_adapter import query_patient
        r = query_patient(patient_id="P003")
        assert r["patient_id"] == "P003"
        assert "labs" in r and "conditions" in r and "meds" in r
        assert r["_mock"] is True


class TestUrgencyDistribution:
    """校验患者数据能覆盖不同手术时机分级 (真实引擎计算)."""

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
        assert "high" in overalls  # P005 高龄+痴呆+CKD
