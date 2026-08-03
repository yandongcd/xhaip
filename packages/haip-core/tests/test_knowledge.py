"""测试知识库 SQLite 存储."""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.knowledge import KnowledgeStore


class TestKnowledgeStore:
    def test_create_tables(self):
        store = KnowledgeStore(":memory:")
        guidelines = store.search_guidelines("test")
        assert guidelines == []
        store.close()

    def test_upsert_guideline(self):
        store = KnowledgeStore(":memory:")
        store.upsert_guideline({
            "id": "nice-ng37",
            "name": "NICE NG37 Hip Fracture",
            "abbr": "NICE NG37",
            "publisher": "NICE",
            "version": "2023",
            "trust_level": "T1",
        })
        g = store.get_guideline("nice-ng37")
        assert g is not None
        assert g["trust_level"] == "T1"
        assert g["publisher"] == "NICE"
        store.close()

    def test_search_guidelines(self):
        store = KnowledgeStore(":memory:")
        store.upsert_guideline({"id": "nice-ng37", "name": "NICE NG37", "publisher": "NICE"})
        store.upsert_guideline({"id": "aaos-2022", "name": "AAOS 2022", "publisher": "AAOS"})
        results = store.search_guidelines("NICE")
        assert len(results) == 1
        results = store.search_guidelines("hip")
        assert len(results) == 0  # name is "NICE NG37", doesn't contain "hip"
        store.close()

    def test_count_by_trust_level(self):
        store = KnowledgeStore(":memory:")
        store.upsert_guideline({"id": "g1", "name": "T1 Guide", "trust_level": "T1"})
        store.upsert_guideline({"id": "g2", "name": "T1 Guide2", "trust_level": "T1"})
        store.upsert_guideline({"id": "g3", "name": "T2 Guide", "trust_level": "T2"})
        counts = store.count_by_trust_level()
        assert counts.get("T1") == 2
        assert counts.get("T2") == 1
        store.close()

    def test_upsert_rule(self):
        store = KnowledgeStore(":memory:")
        store.upsert_rule({
            "id": "cardiac-ctni-high",
            "rule_set_id": "hip_fracture_timing",
            "decision_point": "cardiac_delay",
            "condition_expr": "troponin_I > 0.04",
            "conclusion": "心脏延迟因素触发",
            "rule_type": "threshold",
            "certainty": "strong",
            "evidence_sources": ["umi-2018"],
        })
        rules = store.find_rules("cardiac_delay")
        assert len(rules) == 1
        assert rules[0]["conclusion"] == "心脏延迟因素触发"
        assert rules[0]["certainty"] == "strong"
        store.close()

    def test_find_rules_empty(self):
        store = KnowledgeStore(":memory:")
        assert store.find_rules("nonexistent") == []
        store.close()

    def test_count_rules(self):
        store = KnowledgeStore(":memory:")
        store.upsert_rule({"id": "r1", "rule_set_id": "set1", "decision_point": "d1",
                           "conclusion": "c1"})
        store.upsert_rule({"id": "r2", "rule_set_id": "set1", "decision_point": "d2",
                           "conclusion": "c2"})
        store.upsert_rule({"id": "r3", "rule_set_id": "set2", "decision_point": "d1",
                           "conclusion": "c3"})
        assert store.count_rules() == 3
        assert store.count_rules("set1") == 2
        store.close()

    def test_sync_from_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            gl_dir = Path(tmp) / "guidelines"
            gl_dir.mkdir()
            (gl_dir / "test.yaml").write_text(yaml.dump({
                "id": "test-guideline", "name": "Test Guide",
                "publisher": "Test Publisher", "trust_level": "T1",
            }), encoding="utf-8")

            rules_dir = Path(tmp) / "rules"
            rules_dir.mkdir()
            (rules_dir / "test_set.yaml").write_text(yaml.dump({
                "id": "test_rule_set",
                "name": "Test Rules",
                "rules": [
                    {"id": "R001", "decision_point": "test_point",
                     "conclusion": "test conclusion", "rule_type": "threshold"},
                ],
            }), encoding="utf-8")

            store = KnowledgeStore(":memory:")
            stats = store.sync_from_dir(guidelines_dir=gl_dir, rules_dir=rules_dir)
            assert stats["guidelines"] == 1
            assert stats["rules"] == 1
            assert store.get_guideline("test-guideline") is not None
            assert store.count_rules("test_rule_set") == 1
            store.close()


# ── Error Path Tests ─────────────────────────────────────────────────

class TestKnowledgeErrorPaths:
    def test_corrupted_yaml_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            gl_dir = Path(tmp) / "guidelines"
            gl_dir.mkdir()
            (gl_dir / "corrupt.yaml").write_text("::: bad yaml :::\n{{{unbalanced", encoding="utf-8")

            store = KnowledgeStore(":memory:")
            stats = store.sync_from_dir(guidelines_dir=gl_dir)
            assert stats["guidelines"] == 0

    def test_nonexistent_rule_search(self):
        store = KnowledgeStore(":memory:")
        results = store.find_rules("completely_nonexistent_decision_point_xyz")
        assert results == []

    def test_sync_with_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            gl_dir = Path(tmp) / "guidelines"
            gl_dir.mkdir()
            rules_dir = Path(tmp) / "rules"
            rules_dir.mkdir()

            store = KnowledgeStore(":memory:")
            stats = store.sync_from_dir(guidelines_dir=gl_dir, rules_dir=rules_dir)
            assert stats["guidelines"] == 0
            assert stats["rules"] == 0

    def test_upsert_none_guideline(self):
        store = KnowledgeStore(":memory:")
        with pytest.raises((TypeError, AttributeError)):
            store.upsert_guideline(None)
        store.close()


# ═════════════════════════════════════════════════════════════
# KnowledgeRuntime tests (runtime.py coverage)
# ═════════════════════════════════════════════════════════════

class TestKnowledgeRuntime:
    def test_sync_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            rules_dir = hospital / "knowledge" / "rules"
            gl_dir.mkdir(parents=True)
            rules_dir.mkdir(parents=True)

            (gl_dir / "test_gl.yaml").write_text(yaml.dump({
                "id": "g-test", "name": "Test Guide", "publisher": "WHO", "trust_level": "T1",
            }), encoding="utf-8")
            (rules_dir / "test_rules.yaml").write_text(yaml.dump({
                "id": "test_rs", "name": "Test Rules",
                "rules": [{"id": "R1", "decision_point": "test_dp", "conclusion": "ok", "rule_type": "threshold"}],
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            stats = kb.sync()
            assert stats["guidelines"] == 1
            assert stats["rules"] == 1
            kb.close()

    def test_search_and_find(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            rules_dir = hospital / "knowledge" / "rules"
            gl_dir.mkdir(parents=True)
            rules_dir.mkdir(parents=True)

            (gl_dir / "g.yaml").write_text(yaml.dump({
                "id": "g1", "name": "NICE Test", "publisher": "NICE", "trust_level": "T1",
            }), encoding="utf-8")
            (rules_dir / "r.yaml").write_text(yaml.dump({
                "id": "rs1", "rules": [
                    {"id": "R1", "decision_point": "cardiac_delay", "conclusion": "delay", "rule_type": "threshold"}
                ],
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            kb.sync()
            gl = kb.search_guidelines("NICE")
            assert len(gl) == 1
            rules = kb.find_rules("cardiac_delay")
            assert len(rules) == 1
            kb.close()

    def test_resync_with_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            gl_dir.mkdir(parents=True)

            (gl_dir / "g.yaml").write_text(yaml.dump({
                "id": "g1", "name": "Original", "publisher": "A", "trust_level": "T1",
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            stats = kb.sync()
            assert stats["guidelines"] == 1

            (gl_dir / "g.yaml").write_text(yaml.dump({
                "id": "g1", "name": "Updated", "publisher": "B", "trust_level": "T2",
            }), encoding="utf-8")

            kb.resync()
            gl = kb.get_guideline("g1")
            assert gl["name"] == "Updated"
            kb.close()

    def test_start_stop_hot_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            gl_dir.mkdir(parents=True)
            (gl_dir / "g.yaml").write_text(yaml.dump({
                "id": "g1", "name": "Test", "publisher": "A", "trust_level": "T1",
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            kb.sync()
            assert not kb.hot_reload_enabled
            kb.start_hot_reload(poll_interval=0.1)
            assert kb.hot_reload_enabled
            kb.stop_hot_reload()
            assert not kb.hot_reload_enabled
            kb.close()

    def test_singleton_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            from haip.knowledge.runtime import get_kb, reset_kb
            reset_kb()
            kb1 = get_kb(str(tmp))
            assert kb1 is not None
            assert kb1._synced
            kb2 = get_kb(str(tmp))
            assert kb1 is kb2
            reset_kb()
            kb3 = get_kb(str(tmp))
            assert kb3 is not kb1

    def test_force_resync(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            rules_dir = hospital / "knowledge" / "rules"
            gl_dir.mkdir(parents=True)
            rules_dir.mkdir(parents=True)
            (gl_dir / "g.yaml").write_text(yaml.dump({
                "id": "g1", "name": "G1", "publisher": "A", "trust_level": "T1",
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            stats = kb.force_resync()
            assert stats["guidelines"] == 1
            kb.close()

    def test_verify_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            citations = kb.verify_citations("test text", "test")
            assert isinstance(citations, list)
            kb.close()

    def test_stats_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(tmp))
            stats = kb.stats()
            assert "guidelines" in stats
            assert "total_rules" in stats
            assert stats["synced"]
            kb.close()

    def test_count_by_trust_level_via_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            gl_dir.mkdir(parents=True)
            (gl_dir / "g1.yaml").write_text(yaml.dump({
                "id": "g1", "name": "T1", "publisher": "A", "trust_level": "T1",
            }), encoding="utf-8")
            (gl_dir / "g2.yaml").write_text(yaml.dump({
                "id": "g2", "name": "T2", "publisher": "B", "trust_level": "T2",
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            kb.sync()
            counts = kb.count_by_trust_level()
            assert counts.get("T1") == 1
            assert counts.get("T2") == 1
            kb.close()

    def test_hot_reload_does_not_double_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(tmp))
            kb.start_hot_reload(poll_interval=0.1)
            assert kb.hot_reload_enabled
            kb.start_hot_reload(poll_interval=0.5)
            kb.stop_hot_reload()
            kb.close()

    def test_check_for_changes_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            gl_dir.mkdir(parents=True)
            (gl_dir / "g.yaml").write_text(yaml.dump({
                "id": "g1", "name": "Test", "publisher": "A", "trust_level": "T1",
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            kb.sync()
            kb._file_mtimes = kb._build_file_snapshot()
            changed = kb._check_for_changes()
            assert changed == []
            kb.close()

    def test_check_for_changes_detects_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            gl_dir.mkdir(parents=True)
            (gl_dir / "old.yaml").write_text(yaml.dump({
                "id": "g1", "name": "Old", "publisher": "A", "trust_level": "T1",
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            kb.sync()
            (gl_dir / "new.yaml").write_text(yaml.dump({
                "id": "g2", "name": "New", "publisher": "B", "trust_level": "T2",
            }), encoding="utf-8")
            changed = kb._check_for_changes()
            assert len(changed) >= 1
            kb.close()

    def test_check_for_changes_detects_deleted_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hospital = project_root / "packages" / "haip-hospital"
            gl_dir = hospital / "knowledge" / "guidelines"
            gl_dir.mkdir(parents=True)
            (gl_dir / "temp.yaml").write_text(yaml.dump({
                "id": "g1", "name": "Temp", "publisher": "A", "trust_level": "T1",
            }), encoding="utf-8")

            from haip.knowledge.runtime import KnowledgeRuntime
            kb = KnowledgeRuntime(str(project_root))
            kb.sync()
            kb._file_mtimes = kb._build_file_snapshot()
            (gl_dir / "temp.yaml").unlink()
            changed = kb._check_for_changes()
            assert len(changed) >= 1
            kb.close()


# ═════════════════════════════════════════════════════════════
# CaseManager tests (cases.py coverage)
# ═════════════════════════════════════════════════════════════

class TestCaseManager:
    def test_load_and_search_by_department(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            import json
            patients_data = {
                "patients": [
                    {"patient_id": "P001", "name": "Test1", "department": "呼吸内科", "diagnosis": "COPD", "age": 65},
                    {"patient_id": "P002", "name": "Test2", "department": "骨科", "diagnosis": "骨折", "age": 40},
                    {"patient_id": "P003", "name": "Test3", "department": "呼吸内科", "diagnosis": "哮喘", "age": 30},
                ]
            }
            (data_dir / "patients.json").write_text(json.dumps(patients_data, ensure_ascii=False), encoding="utf-8")

            from haip.knowledge.cases import CaseManager
            cm = CaseManager(str(data_dir))
            assert cm.stats()["total"] == 3

            resp_results = cm.search(department="呼吸内科")
            assert len(resp_results) == 2
            for p in resp_results:
                assert p["department"] == "呼吸内科"

    def test_search_by_diagnosis(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            import json
            patients_data = {
                "patients": [
                    {"patient_id": "P001", "name": "T1", "department": "内科", "diagnosis": "COPD急性加重", "age": 65},
                    {"patient_id": "P002", "name": "T2", "department": "内科", "diagnosis": "哮喘发作", "age": 30},
                    {"patient_id": "P003", "name": "T3", "department": "外科", "diagnosis": "骨折", "age": 25},
                ]
            }
            (data_dir / "patients.json").write_text(json.dumps(patients_data, ensure_ascii=False), encoding="utf-8")

            from haip.knowledge.cases import CaseManager
            cm = CaseManager(str(data_dir))
            asthma = cm.search(diagnosis="哮喘")
            assert len(asthma) >= 1
            assert asthma[0]["patient_id"] == "P002"

    def test_search_by_age_range(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            import json
            patients_data = {
                "patients": [
                    {"patient_id": "P001", "name": "T1", "department": "儿科", "diagnosis": "发热", "age": 5},
                    {"patient_id": "P002", "name": "T2", "department": "内科", "diagnosis": "高血压", "age": 45},
                    {"patient_id": "P003", "name": "T3", "department": "老年科", "diagnosis": "关节炎", "age": 75},
                ]
            }
            (data_dir / "patients.json").write_text(json.dumps(patients_data, ensure_ascii=False), encoding="utf-8")

            from haip.knowledge.cases import CaseManager
            cm = CaseManager(str(data_dir))
            kids = cm.search(age_min=0, age_max=17)
            assert len(kids) == 1
            assert kids[0]["patient_id"] == "P001"

            elderly = cm.search(age_min=65, age_max=120)
            assert len(elderly) == 1
            assert elderly[0]["patient_id"] == "P003"

    def test_get_patient_by_id(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            import json
            patients_data = {
                "patients": [
                    {"patient_id": "P001", "name": "Test1", "department": "内科", "diagnosis": "感冒", "age": 25},
                ]
            }
            (data_dir / "patients.json").write_text(json.dumps(patients_data, ensure_ascii=False), encoding="utf-8")

            from haip.knowledge.cases import CaseManager
            cm = CaseManager(str(data_dir))
            p = cm.get("P001")
            assert p is not None
            assert p["name"] == "Test1"
            assert cm.get("NONEXISTENT") is None

    def test_compatible_agents_lookup(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            import json
            patients_data = {
                "patients": [
                    {"patient_id": "P001", "name": "T1", "department": "内科",
                     "diagnosis": "感冒", "age": 25, "compatible_agents": ["respiratory", "medical-record"]},
                    {"patient_id": "P002", "name": "T2", "department": "外科",
                     "diagnosis": "骨折", "age": 40},
                ]
            }
            (data_dir / "patients.json").write_text(json.dumps(patients_data, ensure_ascii=False), encoding="utf-8")

            from haip.knowledge.cases import CaseManager
            cm = CaseManager(str(data_dir))
            agents = cm.compatible_agents("P001")
            assert "respiratory" in agents
            assert "medical-record" in agents

            agents2 = cm.compatible_agents("P002")
            assert agents2 == []

            agents3 = cm.compatible_agents("NONEXISTENT")
            assert agents3 == []

    def test_empty_directory_load(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.knowledge.cases import CaseManager
            cm = CaseManager(str(d))
            assert cm.cases == []
            assert cm.stats()["total"] == 0

    def test_load_list_format(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            import json
            patients_list = [
                {"patient_id": "P100", "name": "L1", "department": "内科", "diagnosis": "测试", "age": 30},
                {"patient_id": "P101", "name": "L2", "department": "外科", "diagnosis": "测试2", "age": 50},
            ]
            (data_dir / "patients.json").write_text(json.dumps(patients_list, ensure_ascii=False), encoding="utf-8")

            from haip.knowledge.cases import CaseManager
            cm = CaseManager(str(data_dir))
            assert cm.stats()["total"] == 2
