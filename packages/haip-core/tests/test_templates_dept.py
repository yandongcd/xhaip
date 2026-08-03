"""测试 templates_dept.py — 科室模板和指南匹配."""

from __future__ import annotations

from haip.togaf.templates_dept import (
    DeptTemplate,
    get_dept_template,
    get_guideline_info,
    get_template_by_type,
    list_template_types,
)


class TestDeptTemplate:
    def test_construction(self):
        t = DeptTemplate(
            type_id="test", name="Test", type_kr="测试",
            value_streams=[{"id": "vs-1", "name": "Stream 1"}],
            business_processes=[{"id": "bp-1", "name": "Process 1"}],
            common_data_entities=["患者信息"],
            typical_roles=["主治医师"],
        )
        assert t.type_id == "test"
        assert len(t.value_streams) == 1
        assert len(t.business_processes) == 1


class TestListTemplateTypes:
    def test_returns_all_types(self):
        types = list_template_types()
        assert "surgery" in types
        assert "internal_medicine" in types
        assert "other_clinical" in types

    def test_all_are_strings(self):
        for t in list_template_types():
            assert isinstance(t, str)


class TestGetTemplateByType:
    def test_surgery(self):
        t = get_template_by_type("surgery")
        assert t is not None
        assert t.type_id == "surgery"
        assert len(t.business_processes) == 8

    def test_internal_medicine(self):
        t = get_template_by_type("internal_medicine")
        assert t is not None
        assert t.type_id == "internal_medicine"

    def test_unknown_type(self):
        assert get_template_by_type("nonexistent") is None


class TestGetDeptTemplate:
    def test_direct_registry_match(self):
        t = get_dept_template("surgery", "")
        assert t is not None
        assert t.type_id == "surgery"

    def test_parent_fallback(self):
        # medical_technology is in _PARENT_TO_TEMPLATE
        t = get_dept_template("some_unknown_dept", "surgery")
        assert t is not None

    def test_fallback_to_other(self):
        t = get_dept_template("nonexistent", "nonexistent")
        assert t is not None  # falls back to _TEMPLATE_OTHER


class TestGetGuidelineInfo:
    def test_returns_list(self):
        result = get_guideline_info("breast_center")
        assert isinstance(result, list)

    def test_unknown_org_returns_empty(self):
        result = get_guideline_info("nonexistent_dept")
        assert result == []
