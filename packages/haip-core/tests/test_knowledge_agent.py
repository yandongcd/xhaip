"""测试 KnowledgeAgent 基类 — 纯逻辑部分 (无需 LLM/DB 隔离)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from haip.togaf.knowledge_agent import KnowledgeAgent, _load_patients


def _clear_patient_cache():
    """Reset the global patient cache so tests see fresh data."""
    import haip.togaf.knowledge_agent as km
    km._patient_cache = None


class TestMakeClinicalError:
    def test_returns_error_dict(self):
        agent = KnowledgeAgent(agent_name="test-agent")
        result = agent.make_clinical_error("Something went wrong")
        assert result["status"] == "error"
        assert result["agent"] == "test-agent"
        assert result["error"] == "Something went wrong"

    def test_empty_message(self):
        agent = KnowledgeAgent(agent_name="test-agent")
        result = agent.make_clinical_error("")
        assert result["error"] == ""


class TestGetPatientFromKwargs:
    def test_returns_patient_when_found(self, monkeypatch, tmp_path):
        patient = {"patient_id": "P001", "name": "Test", "compatible_agents": []}
        data = {"patients": [patient]}
        f = tmp_path / "patients.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr("haip.togaf.knowledge_agent.PATIENTS_FILE", f)
        _clear_patient_cache()

        agent = KnowledgeAgent(agent_name="test-agent")
        result = agent.get_patient_from_kwargs({"patient_id": "P001"})
        p, err = result
        assert p is not None
        assert p["name"] == "Test"
        assert err is None

    def test_returns_error_when_not_found(self, monkeypatch, tmp_path):
        f = tmp_path / "patients.json"
        f.write_text(json.dumps({"patients": []}), encoding="utf-8")
        monkeypatch.setattr("haip.togaf.knowledge_agent.PATIENTS_FILE", f)
        _clear_patient_cache()

        agent = KnowledgeAgent(agent_name="test-agent")
        result = agent.get_patient_from_kwargs({"patient_id": "NONEXISTENT"})
        p, err = result
        assert p is None
        assert err is not None
        assert err["status"] == "error"
        assert "NONEXISTENT" in err["error"]

    def test_missing_patient_id_returns_error(self, monkeypatch, tmp_path):
        f = tmp_path / "patients.json"
        f.write_text(json.dumps({"patients": []}), encoding="utf-8")
        monkeypatch.setattr("haip.togaf.knowledge_agent.PATIENTS_FILE", f)
        _clear_patient_cache()

        agent = KnowledgeAgent(agent_name="test-agent")
        result = agent.get_patient_from_kwargs({})
        p, err = result
        assert p is None
        assert err is not None
        assert "Patient" in err["error"]


class TestGetPatient:
    def test_returns_dict_for_known_id(self, monkeypatch, tmp_path):
        patient = {"patient_id": "P001", "name": "Alice"}
        f = tmp_path / "patients.json"
        f.write_text(json.dumps({"patients": [patient]}), encoding="utf-8")
        monkeypatch.setattr("haip.togaf.knowledge_agent.PATIENTS_FILE", f)
        _clear_patient_cache()

        agent = KnowledgeAgent()
        result = agent.get_patient("P001")
        assert result == patient

    def test_returns_none_for_unknown_id(self, monkeypatch, tmp_path):
        f = tmp_path / "patients.json"
        f.write_text(json.dumps({"patients": []}), encoding="utf-8")
        monkeypatch.setattr("haip.togaf.knowledge_agent.PATIENTS_FILE", f)
        _clear_patient_cache()

        agent = KnowledgeAgent()
        assert agent.get_patient("BOGUS") is None


class TestGetPatientsByDept:
    def test_filters_by_department(self, monkeypatch, tmp_path):
        patients = [
            {"patient_id": "P001", "name": "Alice", "department": "骨外科"},
            {"patient_id": "P002", "name": "Bob", "department": "呼吸科"},
            {"patient_id": "P003", "name": "Cathy", "department": "骨外科"},
        ]
        f = tmp_path / "patients.json"
        f.write_text(json.dumps({"patients": patients}), encoding="utf-8")
        monkeypatch.setattr("haip.togaf.knowledge_agent.PATIENTS_FILE", f)
        _clear_patient_cache()

        agent = KnowledgeAgent(department="骨外科")
        result = agent.get_patients_by_dept()
        assert len(result) == 2
        assert all(p["department"] == "骨外科" for p in result)

    def test_empty_when_no_match(self, monkeypatch, tmp_path):
        patients = [{"patient_id": "P001", "department": "呼吸科"}]
        f = tmp_path / "patients.json"
        f.write_text(json.dumps({"patients": patients}), encoding="utf-8")
        monkeypatch.setattr("haip.togaf.knowledge_agent.PATIENTS_FILE", f)
        _clear_patient_cache()

        agent = KnowledgeAgent(department="骨外科")
        result = agent.get_patients_by_dept()
        assert result == []


class TestAssessVitals:
    def test_all_normal(self):
        agent = KnowledgeAgent()
        patient = {"lab_results": {"WBC": 7.0, "Hb": 140, "PLT": 250}}
        result = agent.assess_vitals(patient)
        assert result["all_normal"] is True
        assert result["alerts"] == []

    def test_low_value_alert(self):
        agent = KnowledgeAgent()
        patient = {"lab_results": {"Hb": 80}}  # below normal range
        result = agent.assess_vitals(patient)
        assert result["all_normal"] is False
        assert any("Hb" in a for a in result["alerts"])

    def test_high_value_alert(self):
        agent = KnowledgeAgent()
        patient = {"lab_results": {"WBC": 25.0}}  # above normal range
        result = agent.assess_vitals(patient)
        assert result["all_normal"] is False
        assert any("WBC" in a for a in result["alerts"])

    def test_non_numeric_value_skipped(self):
        agent = KnowledgeAgent()
        patient = {"lab_results": {"WBC": "N/A"}}
        result = agent.assess_vitals(patient)
        assert result["all_normal"] is True  # non-numeric skipped silently

    def test_missing_lab_results(self):
        agent = KnowledgeAgent()
        result = agent.assess_vitals({})
        assert result["all_normal"] is True


class TestSearchGuidelines:
    def test_finds_matching_guideline(self, monkeypatch):
        agent = KnowledgeAgent()
        with tempfile.TemporaryDirectory() as td:
            gd = Path(td) / "guidelines"
            gd.mkdir()
            (gd / "test-guide.yaml").write_text("COPD 诊疗指南 2024", encoding="utf-8")
            monkeypatch.setenv("HAIP_KNOWLEDGE_DIR", td)
            results = agent.search_guidelines("COPD")
            assert len(results) > 0

    def test_returns_empty_when_no_match(self, monkeypatch):
        agent = KnowledgeAgent()
        with tempfile.TemporaryDirectory() as td:
            gd = Path(td) / "guidelines"
            gd.mkdir()
            (gd / "test-guide.yaml").write_text("COPD 诊疗指南 2024", encoding="utf-8")
            monkeypatch.setenv("HAIP_KNOWLEDGE_DIR", td)
            results = agent.search_guidelines("NONEXISTENT")
            assert results == []

    def test_handles_missing_directory(self, monkeypatch):
        agent = KnowledgeAgent()
        with tempfile.TemporaryDirectory() as td:
            monkeypatch.setenv("HAIP_KNOWLEDGE_DIR", td)
            results = agent.search_guidelines("anything")
            assert results == []


class TestClinicalResult:
    def test_basic_summary(self):
        agent = KnowledgeAgent(agent_name="test-agent")
        result = agent.clinical_result("评估完成")
        assert result["status"] == "ok"
        assert result["agent"] == "test-agent"
        assert result["summary"] == "评估完成"

    def test_with_patient_info(self):
        agent = KnowledgeAgent(agent_name="test-agent")
        patient = {"patient_id": "P001", "name": "张三", "diagnosis": "股骨颈骨折"}
        result = agent.clinical_result("手术建议", patient=patient)
        assert result["patient"]["id"] == "P001"
        assert result["patient"]["name"] == "张三"

    def test_with_alerts_and_rules(self):
        agent = KnowledgeAgent(agent_name="test-agent")
        result = agent.clinical_result(
            summary="需注意",
            patient={"patient_id": "P001"},
            alerts=["Hb 偏低", "PLT 偏高"],
            guidelines=["KDIGO 2024"],
            rules=["抗凝管理"],
            stage="术前评估",
            findings={"Hb": 80},
            recommendations="建议输血",
        )
        assert result["alerts"] == ["Hb 偏低", "PLT 偏高"]
        assert result["guideline_refs"] == ["KDIGO 2024"]
        assert result["rule_refs"] == ["抗凝管理"]
        assert result["stage"] == "术前评估"

    def test_backward_compat_tuple_input(self):
        """Test old-style call: clinical_result(summary_str, patient=dict)."""
        agent = KnowledgeAgent(agent_name="test-agent")
        result = agent.clinical_result("评估通过", patient={"patient_id": "P001"})
        assert result["status"] == "ok"
        assert result["patient"]["id"] == "P001"
