"""测试 leanix.py — FactSheet 和 LeanIXExporter 核心."""

from __future__ import annotations

from haip.togaf.leanix import FactSheet, LeanIXExporter


class TestFactSheet:
    def test_construction(self):
        f = FactSheet(id="app-1", type="Application", name="Test App")
        assert f.id == "app-1"
        assert f.type == "Application"
        assert f.name == "Test App"
        assert f.status == "active"

    def test_with_relations(self):
        f = FactSheet(id="if-1", type="Interface", name="A2A Link",
                      relations=[{"target": "app-2", "type": "communicates_via"}])
        assert len(f.relations) == 1
        assert f.relations[0]["target"] == "app-2"

    def test_to_dict(self):
        f = FactSheet(id="app-1", type="Application", name="Test")
        d = f.__dict__
        assert d["id"] == "app-1"


class TestLeanIXExporter:
    def test_add_application(self):
        ex = LeanIXExporter()
        ex.add_application("app-1", "Bone Surgery", owner="ortho")
        assert len(ex._facts) == 1
        f = ex._facts["app-1"]
        assert f.name == "Bone Surgery"
        # fields contain the owner
        assert f.fields.get("owner") == "ortho"

    def test_add_interface(self):
        ex = LeanIXExporter()
        ex.add_application("app-1", "Bone Surgery")
        ex.add_application("app-2", "Anesthesia")
        ex.add_interface("if-1", "A2A", "app-1", "app-2")
        assert "if-1" in ex._facts
        iface = ex._facts["if-1"]
        assert iface.fields.get("source") == "app-1"
        assert iface.fields.get("target") == "app-2"

    def test_to_json_empty(self):
        ex = LeanIXExporter()
        result = ex.to_json()
        assert isinstance(result, str)
        assert "[]" in result

    def test_to_json_with_data(self):
        ex = LeanIXExporter()
        ex.add_application("app-1", "Test")
        result = ex.to_json()
        assert "app-1" in result
