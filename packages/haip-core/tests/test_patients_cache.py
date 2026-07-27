"""患者加载缓存测试 — 命中缓存不重读 / mtime 变更后重载 / compatible_agents 过滤 / clear_cache."""

from __future__ import annotations

import json
import time

import haip.patients as patients_mod
from haip.patients import clear_cache, load_all_patients, load_patients

PTS = [
    {"patient_id": "P001", "name": "张三", "compatible_agents": ["orthopedic-surgery"]},
    {"patient_id": "P002", "name": "李四", "compatible_agents": ["pharmacy"]},
    {"patient_id": "P003", "name": "王五", "compatible_agents": ["orthopedic-surgery"]},
]


def _write(tmp_path, payload):
    f = tmp_path / "patients.json"
    f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return f


class TestPatientCache:

    def test_cache_hit_avoids_reread(self, tmp_path, monkeypatch):
        """命中缓存时不重复读文件: monkeypatch 计数 json.loads."""
        f = _write(tmp_path, {"patients": PTS})
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        clear_cache()

        loads_calls = []
        orig_loads = json.loads

        def _counting_loads(s, **kw):
            loads_calls.append(1)
            return orig_loads(s, **kw)

        monkeypatch.setattr(patients_mod.json, "loads", _counting_loads)

        result1 = load_patients("orthopedic-surgery")
        result2 = load_patients("orthopedic-surgery")

        assert len(result1) == 2
        assert len(result2) == 2
        assert len(loads_calls) == 1, f"预期 1 次 json.loads, 实际 {len(loads_calls)}"

    def test_mtime_change_reloads(self, tmp_path, monkeypatch):
        """mtime 变更后自动重载, 返回新数据."""
        f = _write(tmp_path, {"patients": PTS})
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        clear_cache()

        result1 = load_patients("orthopedic-surgery")
        assert [p["patient_id"] for p in result1] == ["P001", "P003"]

        new_pts = [{"patient_id": "P099", "name": "新患者", "compatible_agents": ["orthopedic-surgery"]}]
        time.sleep(0.05)
        f.write_text(json.dumps({"patients": new_pts}, ensure_ascii=False), encoding="utf-8")

        result2 = load_patients("orthopedic-surgery")
        assert [p["patient_id"] for p in result2] == ["P099"]

    def test_compatible_agents_filter_still_works(self, tmp_path, monkeypatch):
        """缓存后 compatible_agents 过滤仍正确."""
        f = _write(tmp_path, {"patients": PTS})
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        clear_cache()

        result = load_patients("pharmacy")
        assert [p["patient_id"] for p in result] == ["P002"]

    def test_clear_cache_forces_reload(self, tmp_path, monkeypatch):
        """clear_cache 后强制重载."""
        f = _write(tmp_path, {"patients": [PTS[0]]})
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        clear_cache()

        result1 = load_patients("orthopedic-surgery", limit=10)
        assert len(result1) == 1

        f.write_text(json.dumps({"patients": PTS}, ensure_ascii=False), encoding="utf-8")
        clear_cache()
        result2 = load_patients("orthopedic-surgery", limit=10)
        assert len(result2) == 2

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        """文件不存在时返回空列表."""
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", tmp_path / "nope.json")
        clear_cache()
        assert load_patients("orthopedic-surgery") == []

    def test_corrupt_json_after_cache(self, tmp_path, monkeypatch):
        """缓存后文件损坏: 应返回空但不清空缓存 (保留旧数据)."""
        f = _write(tmp_path, {"patients": PTS})
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        clear_cache()

        result1 = load_patients("orthopedic-surgery")
        assert len(result1) == 2

        f.write_text("{corrupt", encoding="utf-8")
        time.sleep(0.05)
        result2 = load_patients("orthopedic-surgery")
        assert result2 == []

        f.write_text(json.dumps({"patients": PTS}, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.05)
        clear_cache()
        result3 = load_patients("orthopedic-surgery")
        assert len(result3) == 2


class TestLoadAllPatients:
    def test_returns_all_patients(self, tmp_path, monkeypatch):
        f = _write(tmp_path, {"patients": PTS})
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        clear_cache()
        result = load_all_patients()
        assert len(result) == 3
        assert result[0]["patient_id"] == "P001"

    def test_respects_max_items(self, tmp_path, monkeypatch):
        f = _write(tmp_path, {"patients": PTS})
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        clear_cache()
        result = load_all_patients(max_items=2)
        assert len(result) == 2

    def test_uses_cache_on_second_call(self, tmp_path, monkeypatch):
        f = _write(tmp_path, {"patients": PTS})
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        clear_cache()
        load_all_patients()
        result = load_all_patients()
        assert len(result) == 3

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", tmp_path / "nonexistent.json")
        clear_cache()
        assert load_all_patients() == []
