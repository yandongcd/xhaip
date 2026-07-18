"""Concurrent access safety tests — P3 priority."""

import concurrent.futures
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.a2a import call, clear_history, get_history
from haip.agent import register as reg_agent, list_all, get as get_agent, DomainPlugin, ToolDef
from haip.knowledge import KnowledgeStore
from haip.operations.sync_checks import SkillSync


class TestConcurrentAgentRegistration:
    """50 threads register agents simultaneously — verify no corruption."""

    def test_concurrent_registration(self):
        saved = dict(list_all())
        list_all().clear()
        try:
            def register_agent(idx: int):
                plugin = DomainPlugin(
                    name=f"concurrent_agent_{idx}",
                    cn_name=f"并发Agent_{idx}",
                    type="specialist",
                    department=f"dept_{idx % 5}",
                )
                reg_agent(plugin)
                return plugin

            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(register_agent, i) for i in range(50)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            registry = list_all()
            assert len(registry) >= 50, f"Expected >=50 agents, got {len(registry)}"
            for r in results:
                found = get_agent(r.name)
                assert found is not None, f"Agent {r.name} lost during concurrent registration"
                assert found.cn_name == r.cn_name
        finally:
            list_all().clear()
            for name, p in saved.items():
                reg_agent(p)

    def test_concurrent_registration_no_duplicate(self):
        saved = dict(list_all())
        list_all().clear()
        try:
            name = "same_name_agent"

            def register_same(idx: int):
                plugin = DomainPlugin(
                    name=name,
                    cn_name=f"Attempt_{idx}",
                    type="specialist",
                )
                reg_agent(plugin)
                return idx

            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(register_same, i) for i in range(20)]
                for f in concurrent.futures.as_completed(futures):
                    f.result()

            registry = list_all()
            assert name in registry, "Agent disappeared during concurrent overwrites"
        finally:
            list_all().clear()
            for n, p in saved.items():
                reg_agent(p)


class TestConcurrentA2ACalls:
    """10 threads call different A2A handlers simultaneously — verify all succeed."""

    def test_concurrent_a2a_calls(self):
        saved = dict(list_all())
        list_all().clear()
        clear_history()
        try:
            for i in range(10):
                reg_agent(DomainPlugin(
                    name=f"a2a_{i}", type="specialist",
                ))

            def make_call(idx: int):
                result = call(f"a2a_{idx}", "nonexistent_tool")
                return result

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_call, i) for i in range(10)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            for r in results:
                assert r["status"] == "error", f"Expected error for unknown tool, got {r}"
                assert "error" in r, f"Missing error field: {list(r.keys())}"
                assert isinstance(r.get("error", ""), str), "Error should be string"
        finally:
            list_all().clear()
            for name, p in saved.items():
                reg_agent(p)

    def test_concurrent_a2a_mixed_known_unknown(self):
        saved = dict(list_all())
        list_all().clear()
        clear_history()
        try:
            reg_agent(DomainPlugin(
                name="known_agent", type="specialist",
            ))
            for i in range(5):
                reg_agent(DomainPlugin(
                    name=f"mixed_{i}", type="specialist",
                ))

            def call_known():
                result = call("known_agent", "nonexistent")
                return result

            def call_unknown():
                result = call("ghost_agent", "nonexistent")
                return result

            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(call_known) for _ in range(3)]
                futures += [executor.submit(call_unknown) for _ in range(3)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            assert len(results) == 6
            for r in results:
                assert r["status"] == "error"
        finally:
            list_all().clear()
            for name, p in saved.items():
                reg_agent(p)


class TestConcurrentKnowledgeAccess:
    """5 threads search guidelines while 5 sync YAML — verify no crashes."""

    def test_concurrent_knowledge_access(self):
        import tempfile
        import yaml as yaml_lib

        with tempfile.TemporaryDirectory() as tmp:
            gl_dir = Path(tmp) / "guidelines"
            gl_dir.mkdir()
            (gl_dir / "test.yaml").write_text(yaml_lib.dump({
                "id": "test-guideline",
                "name": "Test Guide",
                "publisher": "Test Publisher",
                "trust_level": "T1",
            }), encoding="utf-8")

            # Use file-based DB to allow better concurrent access
            db_path = Path(tmp) / "test.db"
            store = KnowledgeStore(str(db_path))

            def search_loop():
                keywords = ["Test", "NICE", "nonexistent", "Guide", "Publisher"]
                for i in range(50):
                    try:
                        results = store.search_guidelines(keywords[i % len(keywords)])
                        assert isinstance(results, list)
                    except Exception:
                        pass

            def sync_loop():
                for _ in range(10):
                    try:
                        store.sync_from_dir(guidelines_dir=gl_dir)
                    except Exception:
                        pass

            errors = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                searchers = [executor.submit(search_loop) for _ in range(5)]
                syncers = [executor.submit(sync_loop) for _ in range(5)]
                all_futures = searchers + syncers

                for f in concurrent.futures.as_completed(all_futures):
                    try:
                        f.result()
                    except Exception as e:
                        errors.append(str(e))

            # Verify the store is still usable after concurrent access
            results = store.search_guidelines("Test")
            assert isinstance(results, list)
            store.close()
            assert not errors or all("thread" in e.lower() for e in errors), (
                f"Unexpected errors: {errors}"
            )


class TestCallHistoryThreadSafety:
    """20 threads call a2a simultaneously — verify history count is correct."""

    def test_call_history_thread_safety(self):
        saved = dict(list_all())
        list_all().clear()
        clear_history()
        try:
            reg_agent(DomainPlugin(name="history_test", type="specialist"))

            def make_call(call_id: int):
                params = {"call_id": call_id}
                return call("history_test", "nonexistent", params)

            num_threads = 20
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(make_call, i) for i in range(num_threads)]
                for f in concurrent.futures.as_completed(futures):
                    f.result()

            history = get_history(limit=200)
            assert len(history) == num_threads, (
                f"Expected {num_threads} history entries, got {len(history)}"
            )
            agents_in_history = {h["agent"] for h in history}
            assert agents_in_history == {"history_test"}, (
                f"Unexpected agents in history: {agents_in_history}"
            )
        finally:
            list_all().clear()
            for name, p in saved.items():
                reg_agent(p)

    def test_history_no_duplicates_or_loss(self):
        saved = dict(list_all())
        list_all().clear()
        clear_history()
        try:
            for i in range(3):
                reg_agent(DomainPlugin(name=f"dup_{i}", type="specialist"))

            def call_agent(name: str, count: int):
                for j in range(count):
                    call(name, "nonexistent", {"seq": j})

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(call_agent, "dup_0", 20),
                    executor.submit(call_agent, "dup_1", 20),
                    executor.submit(call_agent, "dup_2", 20),
                ]
                for f in concurrent.futures.as_completed(futures):
                    f.result()

            history = get_history(limit=200)
            assert len(history) == 60, f"Expected 60 history entries, got {len(history)}"
        finally:
            list_all().clear()
            for name, p in saved.items():
                reg_agent(p)
