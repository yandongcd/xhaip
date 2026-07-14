"""测试 ClinicalWorkflow DSL + AgentTool 委派模式."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

import pytest  # noqa: E402
from haip.orchestrator.graph import (  # noqa: E402
    ClinicalWorkflow, Node, NodeType, WorkflowBuilder,
)
from haip.orchestrator.agent_tool import (  # noqa: E402
    AgentTool, build_agent_tools, get_agent_tool_schemas,
    create_agent_tool_executor,
)
from haip.session.store import Event  # noqa: E402


# ── Workflow DSL 基本测试 ──

class TestClinicalWorkflowDSL:
    def test_simple_sequential(self):
        """A → B → C 顺序链."""
        wf = ClinicalWorkflow("test_seq", edges=[
            ("START", "A", "B", "C", "END"),
        ])
        layers = wf.toposort_layers()
        assert len(layers) >= 1
        # START 在第一层，后续每层一个节点
        node_ids = [n for layer in layers for n in layer]
        assert "A" in node_ids
        assert "B" in node_ids
        assert "C" in node_ids

    def test_conditional_routing(self):
        """START → classify → router → {high: A, low: B}."""
        wf = ClinicalWorkflow("test_route", edges=[
            ("START", "classify", "router"),
            ("router", {"high": "risk_high", "low": "risk_low"}),
        ])
        assert "router" in wf._routes
        route = wf._routes["router"]
        assert route.targets["high"] == "risk_high"
        assert route.targets["low"] == "risk_low"

    def test_fan_out_fan_in(self):
        """并行评估 → 汇聚."""
        wf = ClinicalWorkflow("test_fan", edges=[
            ("START", "assess_a"),
            ("START", "assess_b"),
            ("assess_a", "join"),
            ("assess_b", "join"),
            ("join", "final", "END"),
        ])
        assert wf.is_join("join") is True
        assert wf.is_join("final") is False
        # join 有 2 个前驱
        successors = wf.get_successors("join")
        assert "final" in successors

    def test_mixed_sequential_conditional(self):
        """混合: START→A→router→{ok:B→END, err:C→D→END}."""
        wf = ClinicalWorkflow("test_mix", edges=[
            ("START", "A", "router"),
            ("router", {"ok": "B", "err": "C"}),
            ("B", "END"),
            ("C", "D", "END"),
        ])
        assert len(wf._adjacency) >= 5  # 包含 START/END

    def test_compiles_multiple_edges(self):
        """多次调用 compile() 不会重复添加."""
        wf = ClinicalWorkflow("test", edges=[("START", "A", "END")])
        count_1 = len(wf._adjacency)
        wf.compile()
        count_2 = len(wf._adjacency)
        assert count_1 == count_2

    def test_node_with_labels(self):
        """带 label 的节点."""
        node_a = Node("assess", NodeType.AGENT, "风险评估", agent_name="cardio")
        node_b = Node("plan", NodeType.FUNCTION, "方案生成")
        wf = ClinicalWorkflow("test", edges=[("START", node_a, node_b, "END")])
        assert "assess" in wf._node_registry
        assert wf._node_registry["assess"].label == "风险评估"


# ── WorkflowBuilder 测试 ──

class TestWorkflowBuilder:
    def test_builder_chain(self):
        wb = WorkflowBuilder("test", "测试流程")
        wb.add_function("step1", lambda d: {"ok": True}, "步骤1")
        wb.add_agent("step2", "cardiology", "会诊")
        wb.chain("START", "step1", "step2", "END")
        wf = wb.build()

        assert wf.name == "test"
        assert wf.label == "测试流程"
        assert "step1" in wf._node_registry
        assert "step2" in wf._node_registry

    def test_builder_route(self):
        wb = WorkflowBuilder("test", "路由测试")
        wb.add_function("classify", lambda d: d, "分类")
        wb.add_agent("high_handler", "cardiology")
        wb.add_agent("low_handler", "pharmacy")
        wb.route("classify", {"high": "high_handler", "low": "low_handler"})
        wf = wb.build()

        assert "classify_router" in wf._routes or any(
            "classify" in k for k in wf._routes
        )

    def test_builder_fan_out_in(self):
        wb = WorkflowBuilder("parallel", "并行测试")
        wb.add_function("source", lambda d: d)
        wb.add_function("worker_a", lambda d: d)
        wb.add_function("worker_b", lambda d: d)
        wb.add_join("result", "结果汇聚")
        wb.fan_out("source", "worker_a", "worker_b")
        wb.fan_in("result", "worker_a", "worker_b")
        wb.chain("result", "END")
        wf = wb.build()

        assert wf.is_join("result")


# ── AgentTool 测试 ──

class TestAgentTool:
    def test_basic_schema(self):
        """单个 AgentTool 生成正确的 schema."""
        # Mock 一个 agent 注册
        from haip.agent import DomainPlugin, register, list_all
        list_all().clear()

        plugin = DomainPlugin(
            name="cardiology", cn_name="心内科智能体",
            type="business", department="心血管内科",
            tools=[],
        )
        register(plugin)

        at = AgentTool("cardiology", mode="single")
        schema = at.get_schema()

        assert schema["name"] == "agent_cardiology"
        assert "心内科" in schema["description"]
        assert "query" in schema["parameters"]["properties"]

    def test_task_mode_schema(self):
        """task 模式的 schema 无 tool 参数."""
        at = AgentTool("cardiology", mode="task")
        schema = at.get_schema()
        assert "tool" not in schema["parameters"].get("required", [])

    def test_batch_build(self):
        tools = build_agent_tools(["cardiology", "pharmacy", "orthopedic"])
        assert len(tools) == 3
        assert tools[0].agent_name == "cardiology"
        assert tools[1].agent_name == "pharmacy"

    def test_schema_deduplication(self):
        tools = build_agent_tools(["cardiology", "cardiology", "pharmacy"])
        schemas = get_agent_tool_schemas(tools)
        assert len(schemas) == 2  # 去重

    def test_executor_creates_callable(self):
        tools = build_agent_tools(["cardiology"])
        executor = create_agent_tool_executor(tools)
        assert callable(executor)

    def test_executor_unknown_tool(self):
        tools = build_agent_tools(["cardiology"])
        executor = create_agent_tool_executor(tools)
        result = executor("unknown_tool", {})
        assert result["status"] == "error"


# ── 端到端: Workflow + AgentTool 集成 ──

class TestWorkflowAgentToolIntegration:
    def test_workflow_with_agent_nodes(self):
        """工作流包含 Agent 节点 (不实际执行 LLM)."""
        wb = WorkflowBuilder("clinical", "临床路径")
        wb.add_function("triage", lambda d: {"level": 3, "urgent": False})
        wb.add_agent("cardio", "cardiology")
        wb.chain("START", "triage", "cardio", "END")
        wf = wb.build()

        node = wf._node_registry.get("cardio")
        assert node is not None
        assert node.node_type == NodeType.AGENT
        assert node.agent_name == "cardiology"

    def test_complex_clinical_pathway(self):
        """模拟复杂临床路径:
        START → classify → {急救: cardio_consult, 常规: assess} → plan → END
        """
        wb = WorkflowBuilder("emergency", "急诊路径")

        def _classify(data: dict) -> dict:
            return {"output": "regular", "risk": "low"}

        wb.add_function("classify", _classify, "分诊")
        wb.add_agent("cardio", "cardiology", "心内科会诊")
        wb.add_agent("assess", "medical-record", "常规评估")
        wb.add_agent("plan", "pain-hub", "方案制定")
        wb.chain("START", "classify")
        wb.route("classify", {"emergency": "cardio", "regular": "assess"})
        wb.chain("assess", "plan", "END")
        wb.chain("cardio", "plan", "END")

        wf = wb.build()

        # 验证图结构
        assert "classify_router" in wf._routes or any(
            "classify" in k for k in wf._routes
        )
        assert len(wf._node_registry) >= 5  # START + class + router + 3 agents + END

    def test_workflow_toposort_deterministic(self):
        """拓扑排序结果稳定."""
        wf = ClinicalWorkflow("seq", edges=[("START", "A", "B", "C", "END")])
        layers1 = wf.toposort_layers()
        layers2 = wf.toposort_layers()
        assert layers1 == layers2


# ── Node 模型测试 ──

class TestNode:
    def test_function_node(self):
        def my_func(x):
            return x
        node = Node("f1", NodeType.FUNCTION, "计算", func=my_func)
        assert node.node_type == NodeType.FUNCTION
        assert node.func is my_func
        assert node.label == "计算"

    def test_agent_node(self):
        node = Node("a1", NodeType.AGENT, "AI诊断", agent_name="cardiology")
        assert node.node_type == NodeType.AGENT
        assert node.agent_name == "cardiology"
