"""创伤骨科诊疗门户 (/ortho-portal) 集成测试."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HAIP_TEST_MODE"] = "true"

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


class TestPortalRoute:
    def test_route_returns_200(self):
        r = client.get("/ortho-portal")
        assert r.status_code == 200

    def test_route_is_html(self):
        r = client.get("/ortho-portal")
        body = r.text.lower()
        for tag in ["<!doctype", "<html", "<head", "<body", "<title"]:
            assert tag in body, f"缺{tag}"


class TestPortalLayout:
    def _body(self):
        return client.get("/ortho-portal").text

    def test_has_layout_anchors(self):
        body = self._body()
        for anchor in ["kpi-bar", "patient-list", "capability-grid",
                       "result-panel", "stage-timeline", "theme-toggle"]:
            assert anchor in body, f"缺锚点 {anchor}"

    def test_has_title_and_tokens(self):
        body = self._body()
        assert "创伤骨科" in body
        assert "--accent" in body
        assert "body.light" in body


class TestPortalContent:
    def _body(self):
        return client.get("/ortho-portal").text

    def test_has_eight_capabilities(self):
        body = self._body()
        for api in ["classify", "assess", "mdt", "timing",
                    "complications", "plan", "rehab", "followup"]:
            assert api in body, f"缺能力API {api}"

    def test_has_eleven_stages_labels(self):
        body = self._body()
        for label in ["急诊分诊", "骨折分型", "术前评估", "MDT 会诊",
                      "手术时机", "并发症预测", "手术方案", "围术期护理",
                      "术后康复", "随访计划", "质控审计"]:
            assert label in body, f"缺阶段 {label}"

    def test_has_patient_ids_and_loader(self):
        body = self._body()
        assert "P001" in body and "P005" in body
        assert "/api/call" in body
        assert "his_patient" in body
