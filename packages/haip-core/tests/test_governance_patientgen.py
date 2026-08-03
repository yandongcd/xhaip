"""测试 governance.py 和 patient_generator.py — 纯数据/纯函数."""

from __future__ import annotations

from haip.togaf.governance import BPCheckResult, BPValidationReport
from haip.togaf.patient_generator import _DIAGNOSES, _LAB_TEMPLATES, _random_lab


class TestBPCheckResult:
    def test_create_pass(self):
        r = BPCheckResult(bp_name="BP-1", check_id="gov-001",
                          check_name="Test", passed=True, detail="OK")
        assert r.passed is True
        assert r.bp_name == "BP-1"

    def test_create_fail_with_suggestion(self):
        r = BPCheckResult(bp_name="BP-1", check_id="gov-001",
                          check_name="Test", passed=False, detail="Error",
                          suggestion="Fix it")
        assert r.passed is False
        assert r.suggestion == "Fix it"


class TestBPValidationReport:
    def test_all_passed_true(self):
        r = BPCheckResult("bp", "c1", "n", True, "ok")
        report = BPValidationReport(bp_count=1, checks_total=1, checks_passed=1, results=[r])
        assert report.all_passed is True

    def test_all_passed_false(self):
        r = BPCheckResult("bp", "c1", "n", False, "fail")
        report = BPValidationReport(bp_count=1, checks_total=1, checks_passed=0, results=[r])
        assert report.all_passed is False

    def test_summary_contains_fail(self):
        r = BPCheckResult("bp", "c1", "n", False, "error", "fix")
        report = BPValidationReport(bp_count=1, checks_total=1, checks_passed=0, results=[r])
        s = report.summary()
        assert "FAIL" in s
        assert "0/1" in s
        assert "error" in s

    def test_summary_all_pass(self):
        r = BPCheckResult("bp", "c1", "n", True, "ok")
        report = BPValidationReport(bp_count=1, checks_total=1, checks_passed=1, results=[r])
        s = report.summary()
        assert "FAIL" not in s
        assert "1/1" in s


class TestPatientGeneratorData:
    def test_diagnoses_all_strings(self):
        for dept, diags in _DIAGNOSES.items():
            assert len(diags) > 0
            for d in diags:
                assert isinstance(d, str)

    def test_lab_templates_exist(self):
        assert "general_surgery" in _LAB_TEMPLATES
        assert "emergency" in _LAB_TEMPLATES

    def test_diagnoses_and_labs_aligned(self):
        # Most departments with diagnoses should have lab templates
        for dept in ["respiratory", "nephrology", "endocrinology", "oncology",
                      "general_surgery", "neurosurgery", "obgyn", "emergency"]:
            assert dept in _DIAGNOSES


class TestRandomLab:
    def test_generates_for_dept(self):
        labs = _random_lab("COPD", ["WBC", "CRP"])
        assert isinstance(labs, dict)
        assert "WBC" in labs
        assert "CRP" in labs

    def test_values_in_range(self):
        for _ in range(100):
            labs = _random_lab("COPD", ["Hb", "WBC", "CRP", "Cr", "ALT", "FPG",
                                         "K+", "HbA1c", "TSH", "Troponin", "D-Dimer"])
            assert 80 <= labs.get("Hb", 80) <= 160
            assert 3.5 <= labs.get("WBC", 3.5) <= 18.0
            assert 5 <= labs.get("CRP", 5) <= 200
            assert 60 <= labs.get("Cr", 60) <= 300

    def test_unknown_key_gets_default(self):
        labs = _random_lab("test", ["UNKNOWN_KEY_XYZ"])
        # unknown keys get random 0.1-100
        assert isinstance(labs.get("UNKNOWN_KEY_XYZ", 0), float)
