"""Performance benchmark tests — P3 priority."""

import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.a2a import call, clear_history
from haip.agent import DomainPlugin, list_all
from haip.agent import get as get_agent
from haip.agent import register as reg_agent
from haip.knowledge import KnowledgeStore
from haip.orchestrator import A2AOrchestrator, MockTransport, TaskDAG, TaskNode


def test_call_batch_throughput():
    """Time 100 sequential A2A calls, assert < 2 seconds."""
    list_all().clear()
    clear_history()

    reg_agent(DomainPlugin(name="perf_test", type="specialist"))

    t0 = time.perf_counter()
    for _ in range(100):
        call("perf_test", "nonexistent_tool")
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, f"100 A2A calls took {elapsed:.2f}s (expected < 2s)"


def test_orchestrator_parallel_speedup():
    """Compare parallel vs sequential execution times, assert parallel is faster."""
    transport = MockTransport({
        "a/t1": {"status": "ok"}, "b/t2": {"status": "ok"},
        "c/t3": {"status": "ok"}, "d/t4": {"status": "ok"},
        "e/t5": {"status": "ok"},
    })

    parallel_dag = TaskDAG(nodes=[
        TaskNode(id="1", agent="a", tool="t1"),
        TaskNode(id="2", agent="b", tool="t2"),
        TaskNode(id="3", agent="c", tool="t3"),
        TaskNode(id="4", agent="d", tool="t4"),
        TaskNode(id="5", agent="e", tool="t5"),
    ])

    sequential_dag = TaskDAG(nodes=[
        TaskNode(id="1", agent="a", tool="t1"),
        TaskNode(id="2", agent="b", tool="t2", depends_on=["1"]),
        TaskNode(id="3", agent="c", tool="t3", depends_on=["2"]),
        TaskNode(id="4", agent="d", tool="t4", depends_on=["3"]),
        TaskNode(id="5", agent="e", tool="t5", depends_on=["4"]),
    ])

    orch = A2AOrchestrator(transport=transport)

    result_par = orch.execute(dag=parallel_dag)
    result_seq = orch.execute(dag=sequential_dag)

    assert result_par.status == "completed"
    assert result_seq.status == "completed"
    assert result_par.total_elapsed_ms <= result_seq.total_elapsed_ms * 1.5, (
        f"Parallel {result_par.total_elapsed_ms:.1f}ms vs Sequential "
        f"{result_seq.total_elapsed_ms:.1f}ms"
    )


def test_knowledge_search_performance():
    """Time 1000 guideline searches, assert < 1 second."""
    store = KnowledgeStore(":memory:")
    for i in range(100):
        store.upsert_guideline({
            "id": f"g{i}",
            "name": f"Guideline {i}",
            "publisher": f"Publisher {i % 10}",
            "trust_level": "T1",
        })

    keywords = ["Guideline", "Publisher", "T1", "nonexistent", "0", "50", "99"]
    t0 = time.perf_counter()
    for i in range(1000):
        store.search_guidelines(keywords[i % len(keywords)])
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"1000 guideline searches took {elapsed:.2f}s (expected < 1s)"
    store.close()


def test_registry_lookup_speed():
    """Time 10000 agent lookups, assert < 0.5 seconds."""
    from haip.agent import _registry, get

    saved = dict(_registry)
    _registry.clear()

    try:
        for i in range(100):
            _registry[f"agent_{i}"] = DomainPlugin(
                name=f"agent_{i}", type="specialist",
            )

        t0 = time.perf_counter()
        for _ in range(10000):
            get("agent_50")
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.5, f"10000 registry lookups took {elapsed:.2f}s (expected < 0.5s)"
    finally:
        _registry.clear()
        _registry.update(saved)
