"""测试 Orchestrator — 并行 DAG 执行."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.orchestrator import (
    A2AOrchestrator,
    AgentTransport,
    MockTransport,
    OrchestrationMode,
    OrchestrationResult,
    TaskDAG,
    TaskNode,
)


def _make_node(agent: str, tool: str, nid: str = "1",
               deps: list[str] | None = None, params: dict | None = None) -> TaskNode:
    return TaskNode(id=nid, agent=agent, tool=tool,
                    depends_on=deps or [], params=params or {})


class TestTaskDAG:
    def test_single_node(self):
        dag = TaskDAG(nodes=[_make_node("a", "t1")])
        layers = dag.toposort_layers()
        assert len(layers) == 1
        assert len(layers[0]) == 1

    def test_linear_chain(self):
        dag = TaskDAG(nodes=[
            _make_node("a", "t1", "1"),
            _make_node("a", "t2", "2", ["1"]),
            _make_node("a", "t3", "3", ["2"]),
        ])
        layers = dag.toposort_layers()
        assert len(layers) == 3
        assert all(len(ly) == 1 for ly in layers)

    def test_parallel_independent(self):
        """无依赖节点应放在同一层。"""
        dag = TaskDAG(nodes=[
            _make_node("a", "t1", "1"),
            _make_node("b", "t1", "2"),
            _make_node("c", "t1", "3"),
        ])
        layers = dag.toposort_layers()
        assert len(layers) == 1
        assert len(layers[0]) == 3

    def test_diamond_dependency(self):
        """A → (B, C) → D — B/C 同层并行。"""
        dag = TaskDAG(nodes=[
            _make_node("a", "t1", "A"),
            _make_node("b", "t1", "B", ["A"]),
            _make_node("c", "t1", "C", ["A"]),
            _make_node("d", "t1", "D", ["B", "C"]),
        ])
        layers = dag.toposort_layers()
        assert len(layers) == 3
        assert len(layers[0]) == 1  # A
        assert len(layers[1]) == 2  # B, C parallel
        assert len(layers[2]) == 1  # D

    def test_external_dag_input(self):
        """外部预定义 DAG 可传入执行。"""
        dag = TaskDAG(nodes=[
            _make_node("a", "t1", "1"),
            _make_node("a", "t2", "2"),
        ])
        assert len(dag.nodes) == 2
        assert dag.nodes[0].status == "pending"


class TestOrchestratorPipeline:
    def test_pipeline_mode(self):
        transport = MockTransport({
            "a/step1": {"status": "ok", "output": "done1"},
            "a/step2": {"status": "ok", "output": "done2"},
        })
        orch = A2AOrchestrator(transport=transport, mode=OrchestrationMode.PIPELINE)
        result = orch.execute(pipeline_steps=[
            _make_node("a", "step1", "s1"),
            _make_node("a", "step2", "s2", ["s1"]),
        ])
        assert result.status == "completed"
        assert len(result.errors) == 0
        assert len(transport.call_log) == 2

    def test_direct_mode(self):
        transport = MockTransport({"a/t1": {"status": "ok", "output": "ok"}})
        orch = A2AOrchestrator(transport=transport, mode=OrchestrationMode.DIRECT)
        result = orch.execute(pipeline_steps=[_make_node("a", "t1", "1")])
        assert result.status == "completed"
        assert len(transport.call_log) == 1

    def test_error_propagation(self):
        """上游节点失败时，下游节点 skip。"""
        transport = MockTransport({
            "a/bad": {"status": "error", "error": "fail"},
            "a/ok": {"status": "ok", "output": "after"},
        })
        orch = A2AOrchestrator(transport=transport)
        result = orch.execute(dag=TaskDAG(nodes=[
            _make_node("a", "bad", "n1"),
            _make_node("a", "ok", "n2", ["n1"]),
        ]))
        assert result.nodes[0].status == "error"
        assert result.nodes[1].status == "skipped"

    def test_dependency_data_injection(self):
        """依赖节点的结果应注入下游 params。"""
        responses = {
            "a/t1": {"status": "ok", "result": {"x": 42}},
            "b/t2": {"status": "ok", "output": "got 42"},
        }
        transport = MockTransport(responses)
        orch = A2AOrchestrator(transport=transport)
        dag = TaskDAG(nodes=[
            _make_node("a", "t1", "n1"),
            _make_node("b", "t2", "n2", ["n1"]),
        ])
        result = orch.execute(dag=dag)
        assert result.nodes[1].status == "completed"
        # Transport received the merged params
        call2 = transport.call_log[1]
        assert "_dep_n1" in call2["params"]

    def test_parallel_independent_execution(self):
        """独立节点都应被调用。"""
        transport = MockTransport({
            "a/t": {"status": "ok"},
            "b/t": {"status": "ok"},
            "c/t": {"status": "ok"},
        })
        orch = A2AOrchestrator(transport=transport)
        dag = TaskDAG(nodes=[
            _make_node("a", "t", "1"),
            _make_node("b", "t", "2"),
            _make_node("c", "t", "3"),
        ])
        result = orch.execute(dag=dag)
        assert len(transport.call_log) == 3
        assert all(n.status == "completed" for n in result.nodes)

    def test_answer_aggregation(self):
        transport = MockTransport({
            "a/t1": {"status": "ok", "recommendations": ["R1", "R2"]},
            "b/t2": {"status": "ok", "conclusion": "治疗完成"},
        })
        orch = A2AOrchestrator(transport=transport)
        dag = TaskDAG(nodes=[
            _make_node("a", "t1", "1"),
            _make_node("b", "t2", "2"),
        ])
        result = orch.execute(dag=dag)
        assert "R1" in result.answer
        assert "治疗完成" in result.answer

    def test_no_llm_no_task_returns_error(self):
        orch = A2AOrchestrator(mode=OrchestrationMode.AUTO)
        result = orch.execute(task="test")
        assert result.status == "error"

    def test_plan_with_mock_llm(self):
        import json

        from haip.llm.mock import MockProvider
        dag_json = json.dumps([
            {"id": "n1", "agent": "pharmacy", "tool": "assess"},
            {"id": "n2", "agent": "pharmacy", "tool": "review", "depends_on": ["n1"]},
        ])
        llm = MockProvider({"task": {"content": dag_json}})
        transport = MockTransport({"pharmacy/assess": {"status": "ok"},
                                  "pharmacy/review": {"status": "ok"}})
        orch = A2AOrchestrator(transport=transport, llm=llm)
        result = orch.execute(task="评估患者营养风险并审核处方")
        assert result.status == "completed"
