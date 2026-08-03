"""测试 roles.py — 角色系统和 lab 值范围检查."""

from __future__ import annotations

import pytest

from haip.togaf.roles import (
    _LabContext,
    check_range,
    get_role,
    list_roles,
    view_patient_as_anesthesiologist,
    view_patient_as_attending,
    view_patient_as_clinical_pharmacist,
    view_patient_as_dietitian,
    view_patient_as_head_nurse,
    view_patient_as_iv_compounding_pharmacist,
    view_patient_as_pharmacist,
    view_patient_as_review_pharmacist,
    view_patient_as_role,
)


class TestCheckRange:
    def test_none_value_returns_normal(self):
        assert check_range("Hb", None) == {"abnormal": False, "direction": ""}

    def test_unknown_test_returns_normal(self):
        assert check_range("MADE_UP_TEST", 999) == {"abnormal": False, "direction": ""}

    def test_normal_value(self):
        # 血红蛋白测定正常范围 110-160
        result = check_range("血红蛋白测定", 140)
        assert result["abnormal"] is False
        assert result["direction"] == ""

    def test_low_value(self):
        result = check_range("血红蛋白测定", 80)
        assert result["abnormal"] is True
        assert result["direction"] == "偏低"

    def test_high_value(self):
        result = check_range("白细胞计数", 25.0)
        assert result["abnormal"] is True
        assert result["direction"] == "偏高"

    def test_non_numeric_value(self):
        assert check_range("血红蛋白测定", "N/A") == {"abnormal": False, "direction": ""}

    def test_boundary_low(self):
        result = check_range("血红蛋白测定", 110)
        assert result["abnormal"] is False


class TestLabContext:
    def test_construct_from_lab_results_dict(self):
        patient = {"lab_results": {"Hb": 140, "WBC": 8.0}}
        lc = _LabContext(patient)
        assert lc.get("Hb") is not None
        assert lc.get("WBC") is not None
        assert lc.get("NONEXISTENT") is None

    def test_construct_from_lab_tests_list(self):
        patient = {"lab_tests": [
            {"name": "Hb", "value": 140},
            {"name": "WBC", "value": 8.0},
        ]}
        lc = _LabContext(patient)
        assert lc.get("Hb") == {"name": "Hb", "value": 140}

    def test_prefers_lab_tests_over_lab_results(self):
        patient = {
            "lab_tests": [{"name": "Hb", "value": 100}],
            "lab_results": {"Hb": 140},
        }
        lc = _LabContext(patient)
        assert lc.get("Hb") == {"name": "Hb", "value": 100}

    def test_get_float(self):
        lc = _LabContext({"lab_results": {"Hb": 140}})
        assert lc.get_float("Hb") == 140.0

    def test_get_float_nonexistent(self):
        lc = _LabContext({})
        assert lc.get_float("X") is None

    def test_get_float_non_numeric(self):
        lc = _LabContext({"lab_results": {"Hb": "N/A"}})
        assert lc.get_float("Hb") is None

    def test_check_range_normal(self):
        lc = _LabContext({"lab_results": {"血红蛋白测定": 140}})
        result = lc.check_range("血红蛋白测定")
        assert result is not None
        assert result["abnormal"] is False

    def test_check_range_abnormal(self):
        lc = _LabContext({"lab_results": {"血红蛋白测定": 80}})
        result = lc.check_range("血红蛋白测定")
        assert result is not None
        assert result["abnormal"] is True

    def test_check_range_missing(self):
        lc = _LabContext({})
        assert lc.check_range("Hb") is None

    def test_check_electrolytes(self):
        lc = _LabContext({"lab_results": {"钾离子": 2.0, "钠离子": 140}})
        issues = lc.check_electrolytes(["钾离子", "钠离子"])
        assert len(issues) == 1
        assert issues[0]["name"] == "钾离子"
        assert "低" in issues[0]["direction"]


class TestListRoles:
    def test_returns_all_roles(self):
        roles = list_roles()
        assert "anesthesiologist" in roles
        assert "attending" in roles
        assert "pharmacist" in roles
        assert "head_nurse" in roles

    def test_returns_copy_not_reference(self):
        r1 = list_roles()
        r2 = list_roles()
        assert r1 is not r2
        assert r1 == r2


class TestGetRole:
    def test_existing_role(self):
        role = get_role("attending")
        assert role is not None
        assert role.name == "主治医生"

    def test_unknown_role(self):
        assert get_role("nonexistent") is None


class TestViewPatientAsRole:
    def test_dispatch_to_anesthesiologist(self):
        result = view_patient_as_role("anesthesiologist", {})
        assert result is not None
        assert "airway" in result

    def test_dispatch_to_attending(self):
        result = view_patient_as_role("attending", {})
        assert result is not None

    def test_dispatch_to_pharmacist(self):
        result = view_patient_as_role("pharmacist", {})
        assert result is not None

    def test_dispatch_to_clinical_pharmacist(self):
        result = view_patient_as_role("clinical_pharmacist", {})
        assert result is not None

    def test_dispatch_to_dietitian(self):
        result = view_patient_as_role("dietitian", {})
        assert result is not None

    def test_dispatch_to_head_nurse(self):
        result = view_patient_as_role("head_nurse", {})
        assert result is not None

    def test_unknown_role_returns_none(self):
        assert view_patient_as_role("captain", {}) is None


class TestViewPatientAsAnesthesiologist:
    def test_empty_patient(self):
        result = view_patient_as_anesthesiologist({})
        assert result is not None
        assert "airway" in result
        assert result["role_name"] is not None

    def test_detects_obesity_osa_risk(self):
        result = view_patient_as_anesthesiologist({"past_history": "肥胖"})
        assert result["airway"]["needs_eval"] is True


class TestViewPatientAsAttending:
    def test_empty_patient(self):
        result = view_patient_as_attending({})
        assert result is not None
        assert "role_name" in result


class TestAllViews:
    """Verify all 8 views return non-None with min valid structure."""

    _VIEWS = [
        view_patient_as_anesthesiologist,
        view_patient_as_attending,
        view_patient_as_pharmacist,
        view_patient_as_clinical_pharmacist,
        view_patient_as_review_pharmacist,
        view_patient_as_iv_compounding_pharmacist,
        view_patient_as_dietitian,
        view_patient_as_head_nurse,
    ]

    @pytest.mark.parametrize("view_fn", _VIEWS)
    def test_returns_dict(self, view_fn):
        result = view_fn({})
        assert isinstance(result, dict)
