"""共享患者加载器测试 — dict/list 格式、兼容过滤、异常回退."""

from __future__ import annotations

import json

import haip.patients as patients_mod
from haip.patients import load_patients


def _write(tmp_path, payload) -> None:
    f = tmp_path / "patients.json"
    f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return f


PTS = [
    {"patient_id": "P001", "name": "张三", "compatible_agents": ["orthopedic-surgery"]},
    {"patient_id": "P002", "name": "李四", "compatible_agents": ["pharmacy"]},
    {"patient_id": "P003", "name": "王五", "compatible_agents": ["orthopedic-surgery"]},
]


class TestLoadPatients:
    def test_dict_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, {"total": 3, "patients": PTS}))
        result = load_patients("orthopedic-surgery")
        assert [p["patient_id"] for p in result] == ["P001", "P003"]

    def test_list_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, PTS))
        result = load_patients("pharmacy")
        assert [p["patient_id"] for p in result] == ["P002"]

    def test_no_match_falls_back_to_all(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, {"patients": PTS}))
        result = load_patients("no-such-agent", limit=2)
        assert len(result) == 2

    def test_only_compatible_no_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, {"patients": PTS}))
        assert load_patients("no-such-agent", only_compatible=True) == []

    def test_limit(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, {"patients": PTS}))
        assert len(load_patients("orthopedic-surgery", limit=1)) == 1

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", tmp_path / "nope.json")
        assert load_patients("orthopedic-surgery") == []

    def test_corrupt_json_warns(self, tmp_path, monkeypatch, caplog):
        f = tmp_path / "patients.json"
        f.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        with caplog.at_level("WARNING"):
            assert load_patients("orthopedic-surgery") == []
        assert "patients.json" in caplog.text

    def test_unexpected_structure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, "just a string"))
        assert load_patients("orthopedic-surgery") == []
