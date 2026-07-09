"""测试知识库 SQLite 存储."""

import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.knowledge import KnowledgeStore  # noqa: E402


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
        import yaml
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
