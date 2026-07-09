"""药剂科全链路 E2E — YAML 定义 → 注册 → A2A 调用 → Guard 验证 → Orchestrator 编排.

参照疼痛科 test_pain_e2e.py 的测试模式:
  - 完整临床路径验证
  - 多 Agent 协作场景
  - 异常/高危场景检测
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.agent import load_from_dir, _registry, get as get_agent, DomainPlugin, ToolDef, register  # noqa: E402
from haip.a2a import call, clear_history, get_history  # noqa: E402
from haip.guard.verifier import GuardVerifier  # noqa: E402
from haip.orchestrator import (  # noqa: E402
    A2AOrchestrator, TaskNode, TaskDAG, MockTransport, OrchestrationMode,
)


YAML_DIR = project_root / "packages" / "haip-hospital" / "agents" / "definitions"


class TestPharmacyE2E:
    def setup_method(self):
        _registry.clear()
        clear_history()

    # ── 场景 1: YAML 完整加载 ──

    def test_yaml_load_all_tools(self):
        count = load_from_dir(str(YAML_DIR))
        assert count >= 1
        p = get_agent("pharmacy")
        assert len(p.tools) >= 5
        tool_names = {t.name for t in p.tools}
        assert "assess_nutrition" in tool_names
        assert "calculate_tpn" in tool_names
        assert "review_prescription" in tool_names
        assert "recommend_nutrition_route" in tool_names
        assert "list_medications" in tool_names

    def test_yaml_guard_config(self):
        load_from_dir(str(YAML_DIR))
        p = get_agent("pharmacy")
        assert len(p.guard.triggers) >= 2
        assert "药物交互" in p.guard.triggers
        assert len(p.guard.high_risk_scenarios) >= 3

    def test_yaml_ui_config(self):
        load_from_dir(str(YAML_DIR))
        p = get_agent("pharmacy")
        assert p.ui.template == "chat-with-role-switcher"
        assert len(p.ui.roles) >= 4
        role_ids = {r["id"] for r in p.ui.roles}
        assert "pharmacist" in role_ids
        assert "clinical_pharmacist" in role_ids

    # ── 场景 2: A2A 调用 + 业务逻辑 ──

    def test_assess_nutrition_high_risk_elderly(self):
        """高龄 + 营养不良 → 高风险。"""
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(name="assess_nutrition", description="",
                          handler="pharmacy.assessment.assess_nutrition_risk")],
        ))
        result = call("pharmacy", "assess_nutrition", {
            "patient_id": "P004", "weight_kg": 48.0, "height_cm": 170.0,
            "lab_results": {"albumin": 25.0, "crp": 80.0, "k": 3.2},
            "age": 82,
        })
        assert result["status"] == "ok"
        assert result["risk_level"] == "高"
        assert result["nrs_score"] >= 5
        assert not result["electrolytes_ok"]

    def test_assess_nutrition_low_risk_young(self):
        """年轻健康 → 低风险。"""
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(name="assess_nutrition", description="",
                          handler="pharmacy.assessment.assess_nutrition_risk")],
        ))
        result = call("pharmacy", "assess_nutrition", {
            "patient_id": "P005", "weight_kg": 72.0, "height_cm": 178.0,
            "lab_results": {"albumin": 45.0, "crp": 2.0},
            "age": 35,
        })
        assert result["status"] == "ok"
        assert result["risk_level"] == "低"
        assert result["nrs_score"] <= 2

    # ── 场景 3: Guard 高危场景检测 ──

    def test_guard_detects_drug_interaction(self):
        """处方审核触发药物交互高危场景。"""
        v = GuardVerifier()
        output = (
            "处方审核结果：华法林 2.5mg qd + 低分子肝素 4000IU q12h 联用，"
            "需每日监测 INR。参考：ACCP 抗血栓治疗指南。"
        )
        result = v.verify(output, scenario="抗凝管理", agent_name="pharmacy")
        # 应触发高危场景检测
        assert len(result.citations) >= 1 or len(result.flags) >= 1

    def test_guard_cross_validation_conflict_detected(self):
        """心脏评估和麻醉评估结论冲突。"""
        v = GuardVerifier()
        output = "ASA III级，华法林禁忌使用，建议低分子肝素桥接。"
        cross = ["ASA II级，华法林适用，无需桥接。"]

        result = v.verify(output, scenario="麻醉评估",
                         cross_agent_outputs=cross)
        assert result.cross_validation_conflict
    # ── 场景 4: Orchestrator 多 Agent 编排 ──

    def test_orchestrator_pharmacy_workflow(self):
        """编排: 药剂科营养评估 + 病历查询。"""
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(name="assess_nutrition", description="",
                          handler="pharmacy.assessment.assess_nutrition_risk")],
        ))
        register(DomainPlugin(
            name="medical-record", type="master_data",
            tools=[ToolDef(name="get_patient", description="",
                          handler="pharmacy.assessment.assess_nutrition_risk")],
        ))
        transport = MockTransport({
            "medical-record/get_patient": {
                "status": "ok",
                "result": {"patient_id": "P001", "weight_kg": 55.0, "height_cm": 170.0},
            },
        })
        orch = A2AOrchestrator(transport=transport, mode=OrchestrationMode.PIPELINE)
        result = orch.execute(pipeline_steps=[
            TaskNode(id="get_data", agent="medical-record", tool="get_patient"),
            TaskNode(id="assess", agent="pharmacy", tool="assess_nutrition",
                     params={"lab_results": {"albumin": 28.0}},
                     depends_on=["get_data"]),
        ])
        assert result.status == "completed"
        assert len(transport.call_log) == 2

    def test_orchestrator_parallel_independent_agents(self):
        """3 个独立 Agent 并行评估。"""
        for name in ("cardio", "anesthesia", "nutrition"):
            register(DomainPlugin(
                name=name, type="specialist",
                tools=[ToolDef(name="assess", description="",
                              handler="pharmacy.assessment.assess_nutrition_risk")],
            ))
        transport = MockTransport({
            "cardio/assess": {"status": "ok", "conclusion": "心脏低风险"},
            "anesthesia/assess": {"status": "ok", "conclusion": "ASA II"},
            "nutrition/assess": {"status": "ok", "conclusion": "营养低风险"},
        })
        orch = A2AOrchestrator(transport=transport)
        dag = TaskDAG(nodes=[
            TaskNode(id="c", agent="cardio", tool="assess"),
            TaskNode(id="a", agent="anesthesia", tool="assess"),
            TaskNode(id="n", agent="nutrition", tool="assess"),
        ])
        _ = orch.execute(dag=dag)
        layers = dag.toposort_layers()
        assert len(layers) == 1  # 3 节点同一层, 可并行
        assert len(transport.call_log) == 3

    # ── 场景 5: Guard 集成到 Orchestrator ──

    def test_orchestrator_with_guard_integration(self):
        """编排后对聚合结果进行 Guard 验证。"""
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(name="assess_nutrition", description="",
                          handler="pharmacy.assessment.assess_nutrition_risk")],
        ))
        transport = MockTransport({
            "pharmacy/assess_nutrition": {
                "status": "ok",
                "recommendations": ["立即手术", "使用THA方案"],
                "nrs_score": 5,
            },
        })
        orch = A2AOrchestrator(transport=transport)
        dag = TaskDAG(nodes=[
            TaskNode(id="n1", agent="pharmacy", tool="assess_nutrition",
                     params={"patient_id": "P001", "weight_kg": 50.0, "height_cm": 170.0,
                             "lab_results": {"albumin": 28.0}}),
        ])
        result = orch.execute(dag=dag)
        assert result.status == "completed"

        # Guard 验证编排结果
        v = GuardVerifier()
        guard_result = v.verify(
            result.answer, scenario="手术方案", agent_name="pharmacy",
        )
        assert isinstance(guard_result.citations, list)

    # ── 场景 6: 异常场景 ──

    def test_a2a_missing_patient_id(self):
        """缺少必填参数不 crash。"""
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(name="assess_nutrition", description="",
                          handler="pharmacy.assessment.assess_nutrition_risk")],
        ))
        result = call("pharmacy", "assess_nutrition", {})
        assert result["status"] == "ok"  # assess_nutrition 有默认值

    def test_a2a_type_error_in_params(self):
        """参数类型错误不 crash — A2A dispatcher 捕获异常返回 error。"""
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(name="assess_nutrition", description="",
                          handler="pharmacy.assessment.assess_nutrition_risk")],
        ))
        result = call("pharmacy", "assess_nutrition",
                      {"weight_kg": "not_a_number", "height_cm": None})
        # 类型错误导致函数异常，dispatcher 捕获并返回 error
        assert result["status"] == "error"

    def test_orchestrator_circular_dependency(self):
        """循环依赖不卡死。"""
        dag = TaskDAG(nodes=[
            TaskNode(id="a", agent="x", tool="t",
                     depends_on=["b"]),
            TaskNode(id="b", agent="x", tool="t",
                     depends_on=["a"]),
        ])
        _ = dag.toposort_layers()
        assert dag.nodes[0].status == "error"
        assert "circular" in dag.nodes[0].result["error"]

    def test_call_history_full_chain(self):
        """验证调用历史完整追踪。"""
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(name="assess_nutrition", description="",
                          handler="pharmacy.assessment.assess_nutrition_risk")],
        ))
        call("pharmacy", "assess_nutrition", {
            "patient_id": "P001", "weight_kg": 70.0, "height_cm": 165.0,
        })
        call("pharmacy", "assess_nutrition", {
            "patient_id": "P002", "weight_kg": 55.0, "height_cm": 170.0,
            "lab_results": {"albumin": 28.0}, "age": 75,
        })
        history = get_history()
        assert len(history) == 2
        assert all(h["agent"] == "pharmacy" for h in history)
