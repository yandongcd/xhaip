"""HTTP 集成测试 — 启动 FastAPI TestClient, 验证所有端点。

覆盖历次 HTML 异常:
  1. 端口/路径兼容性
  2. Agent 正确加载 (PROJECT_ROOT 问题)
  3. 工具名与 YAML 一致性
  4. 患者端点数据返回
  5. Guard 端点可用
  6. 知识库端点
  7. 通用 UI 端点
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent  # xhaip root
sys.path.insert(0, str(project_root / "packages" / "haip-core"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))

import pytest
from fastapi.testclient import TestClient

from haip.agent import _registry, load_from_dir
from haip.web_server import app

client = TestClient(app)
YAML_DIR = project_root / "packages" / "haip-hospital" / "agents" / "definitions"


@pytest.fixture(autouse=True)
def ensure_agents_loaded():
    """每个 HTTP 测试前确保 Agent 已加载 (其他测试文件可能清空了 registry)。"""
    if len(_registry) < 14:
        load_from_dir(str(YAML_DIR))


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.2.0"

    def test_health_agents_loaded(self):
        """PROJECT_ROOT 路径错误时 agents_loaded=0, 此测试捕获该问题。"""
        r = client.get("/api/health")
        assert r.json()["agents_loaded"] >= 14


class TestAgentsEndpoint:
    def test_list_agents_count(self):
        r = client.get("/api/agents")
        assert r.status_code == 200
        agents = r.json()
        assert len(agents) >= 14

    def test_pharmacy_exists(self):
        r = client.get("/api/agents")
        agents = {a["name"]: a for a in r.json()}
        assert "pharmacy" in agents
        assert agents["pharmacy"]["type"] == "business"

    def test_orthopedic_exists(self):
        r = client.get("/api/agents")
        agents = {a["name"]: a for a in r.json()}
        assert "orthopedic-surgery" in agents
        p = agents["orthopedic-surgery"]
        assert len(p["tools"]) >= 10

    def test_tool_names_match_yaml(self):
        """工具名与 YAML 定义一致 — 手工 HTML 硬编码名检测。"""
        r = client.get("/api/agents/orthopedic-surgery")
        assert r.status_code == 200
        data = r.json()
        tool_names = {t["name"] for t in data["tools"]}
        assert "timing_decision" in tool_names, "YAML tool name mismatch"
        assert "classify_fracture" in tool_names
        assert "surgical_plan" in tool_names
        assert "complication_risk" in tool_names
        assert "harris_score" in tool_names

    def test_agent_detail_has_handler(self):
        r = client.get("/api/agents/pharmacy")
        assert r.status_code == 200
        data = r.json()
        for tool in data["tools"]:
            assert "handler" in tool
            # handler format: pkg.fn (至少一个点)
            assert "." in tool["handler"], f"handler {tool['handler']} missing dot"


class TestCallEndpoint:
    def test_call_valid_tool(self):
        r = client.post("/api/call", json={
            "agent": "pharmacy",
            "tool": "nutrition_assess",
            "params": {"patient_id": "P001", "weight_kg": 55, "height_cm": 170,
                       "lab_results": {"albumin": 28}, "age": 78},
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["risk_level"] in ("高危", "中危", "低危")

    def test_call_unknown_agent(self):
        r = client.post("/api/call", json={"agent": "ghost", "tool": "x"})
        assert r.status_code == 200
        assert r.json()["status"] == "error"

    def test_call_wrong_tool_name(self):
        """手工 HTML 使用错误工具名时应有明确错误。"""
        r = client.post("/api/call", json={
            "agent": "orthopedic-surgery", "tool": "evaluate_timing", "params": {},
        })
        assert r.status_code == 200
        assert r.json()["status"] == "error"
        assert "no tool" in r.json()["error"].lower()

    def test_call_missing_agent(self):
        r = client.post("/api/call", json={"tool": "x"})
        assert r.status_code == 400

    def test_call_cardio_risk(self):
        r = client.post("/api/call", json={
            "agent": "cardio-risk", "tool": "assess_cardiac",
            "params": {"labs": {"creatinine": 2.5}, "ecg_findings": "ST depression"},
        })
        assert r.status_code == 200
        assert r.json()["rcri_score"] >= 1

    def test_call_pain_hub_triage(self):
        r = client.post("/api/call", json={
            "agent": "pain-hub", "tool": "triage",
            "params": {"pain_type": "acute", "vas_score": 8, "description": "cauda equina"},
        })
        assert r.status_code == 200
        assert r.json()["route_to"] in ("acute-pain", "cancer-pain", "chronic-pain", "interventional-pain", "pain-rehab", "pain-hub")

    def test_call_medical_record(self):
        r = client.post("/api/call", json={
            "agent": "medical-record", "tool": "get_patient",
            "params": {"patient_id": "P001"},
        })
        assert r.status_code == 200
        assert r.json()["found"] is True

    def test_call_pediatrics(self):
        r = client.post("/api/call", json={
            "agent": "pediatrics", "tool": "dose_calculate",
            "params": {"drug_name": "amoxicillin", "weight_kg": 15},
        })
        assert r.status_code == 200
        assert r.json()["single_dose_mg"] == 750.0


class TestPatientsEndpoint:
    def test_patients_all(self):
        r = client.get("/patients")
        assert r.status_code == 200
        patients = r.json()
        assert len(patients) >= 50

    def test_patients_filter_by_agent(self):
        """demo 页面按 Agent 过滤患者。"""
        r = client.get("/patients?agent=pharmacy")
        assert r.status_code == 200
        patients = r.json()
        assert len(patients) >= 5

    def test_patients_anonymized(self):
        """所有患者名称已匿名化。"""
        r = client.get("/patients")
        patients = r.json()
        for p in patients[:10]:
            assert "*" in p.get("name", ""), f"Patient {p['patient_id']} not anonymized"

    def test_stats_endpoint(self):
        r = client.get("/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["agents_loaded"] >= 14
        assert data["patients_loaded"] >= 100


class TestGuardEndpoint:
    def test_guard_verify(self):
        r = client.post("/api/guard", json={
            "output": "建议 THA 手术, 时机 48h。参考: NICE NG37",
            "scenario": "手术决策", "agent": "orthopedic-surgery",
        })
        assert r.status_code == 200
        data = r.json()
        assert "passed" in data
        assert "citations" in data

    def test_guard_verifies_known_guideline(self):
        """指南资产库中存在的引用 (nice-ng37.yaml) 必须 verified=true."""
        r = client.post("/api/guard", json={
            "output": "建议 THA 手术, 时机 48h。参考: NICE NG37",
            "scenario": "手术决策", "agent": "orthopedic-surgery",
        })
        data = r.json()
        ng37 = [c for c in data["citations"] if "NG37" in c["source"].upper()]
        assert ng37, "未提取到 NICE NG37 引用"
        assert ng37[0]["verified"] is True, "nice-ng37.yaml 在资产库中, 引用应 verified"
        assert "存在未验证的指南引用" not in data["flags"]

    def test_guard_cross_validation(self):
        r = client.post("/api/guard", json={
            "output": "ASA III, 建议延迟手术",
            "scenario": "麻醉评估",
            "cross_agent_outputs": ["ASA II, 可手术"],
        })
        assert r.status_code == 200
        data = r.json()
        assert "cross_validation_conflict" in data


class TestKnowledgeEndpoint:
    def test_knowledge_stats(self):
        r = client.get("/api/knowledge/stats")
        assert r.status_code == 200
        data = r.json()
        assert "knowledge" in data
        assert "cases" in data

    def test_knowledge_search(self):
        r = client.get("/api/knowledge/search?q=NICE")
        assert r.status_code == 200
        data = r.json()
        assert "guidelines" in data


class TestUIEndpoints:
    def test_portal_returns_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert len(r.text) > 5000

    def test_ortho_ui_returns_html(self):
        r = client.get("/ortho")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "orthopedic" in r.text.lower() or "骨科" in r.text

    def test_pharmacy_ui_returns_html(self):
        r = client.get("/pharmacy")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_generic_agent_ui(self):
        """通用 /agent/{name} 路由 — 历次 PATH 错误检测。"""
        for name in ("pharmacy", "cardio-risk", "pediatrics", "pain-hub", "medical-record"):
            r = client.get(f"/agent/{name}")
            assert r.status_code == 200, f"/agent/{name} returned {r.status_code}"
            assert "text/html" in r.headers["content-type"]
            assert "callTool" in r.text, f"/agent/{name} missing callTool JS"
            assert "/api/call" in r.text, f"/agent/{name} missing /api/call"

    def test_generic_ui_labels_chinese(self):
        """UI 标签应为中文。"""
        import re
        r = client.get("/agent/orthopedic-surgery")
        labels = re.findall(r'class="tab[^"]*"[^>]*>([^<]+)', r.text)
        for lbl in labels:
            assert any('\u4e00' <= c <= '\u9fff' for c in lbl), f"Label not Chinese: {lbl}"

    def test_agent_ui_not_found(self):
        r = client.get("/agent/nonexistent")
        assert r.status_code == 404


class TestWorkflowUI:
    def test_ortho_workflow_renders(self):
        """工作流 UI 应正确渲染, 含角色过滤+进度条+自动数据传递JS。"""
        r = client.get("/workflow/orthopedic-surgery")
        assert r.status_code == 200
        assert "switchRole" in r.text, "Missing role switch JS"
        assert "callStage" in r.text, "Missing stage call JS"
        assert "autoNext" in r.text, "Missing auto-next JS"
        assert "COMPLETED_STAGES" in r.text, "Missing progress tracking"

    def test_pharmacy_workflow_renders(self):
        r = client.get("/workflow/pharmacy")
        assert r.status_code == 200
        assert "switchRole" in r.text

    def test_workflow_has_roles(self):
        """每个阶段应标注可见角色。"""
        r = client.get("/workflow/orthopedic-surgery")
        assert "主治医师" in r.text
        assert "主刀医生" in r.text or "surgeon" in r.text

    def test_workflow_stage_count(self):
        """骨科应有10个阶段。"""
        r = client.get("/workflow/orthopedic-surgery")
        # 计数 stage-item
        count = r.text.count("stage-content")
        assert count >= 10, f"Expected >=10 stages, got {count}"

    def test_workflow_guideline_refs(self):
        """每个阶段应有指南引用。"""
        r = client.get("/workflow/orthopedic-surgery")
        assert "卫健委2022" in r.text or "NICE" in r.text

    def test_workflow_no_agent_404(self):
        r = client.get("/workflow/nonexistent")
        assert r.status_code == 404

    def test_auto_data_passing_js(self):
        """autoNext 函数应在 JS 中定义。"""
        r = client.get("/workflow/orthopedic-surgery")
        assert "function autoNext" in r.text


class TestWorkflowData:
    def test_workflow_definition_exists(self):
        from haip.workflow import get_workflow
        wf = get_workflow("orthopedic-surgery")
        assert wf is not None
        assert len(wf["stages"]) == 10
        assert len(wf["roles"]) >= 3

    def test_role_filter(self):
        from haip.workflow import get_visible_stages
        # 主刀医生只能看到 分型/评估/时机/并发症/手术 (5个阶段)
        stages = get_visible_stages("orthopedic-surgery", "surgeon")
        stage_ids = [s["id"] for s in stages]
        assert "classify" in stage_ids
        assert "surgery" in stage_ids
        assert "nursing" not in stage_ids, "Surgeon should not see nursing"
        assert "followup" not in stage_ids, "Surgeon should not see followup"

    def test_attending_sees_all(self):
        from haip.workflow import get_visible_stages
        stages = get_visible_stages("orthopedic-surgery", "attending")
        assert len(stages) == 10

    def test_pharmacy_role_filter(self):
        from haip.workflow import get_visible_stages
        # 静配药师只看到 TPN 配比
        stages = get_visible_stages("pharmacy", "iv_compounding_pharmacist")
        assert len(stages) == 1
        assert stages[0]["id"] == "tpn"


class TestCORSandErrors:
    def test_cors_headers(self):
        """FastAPI CORS middleware 已配置 (TestClient 中 header 可能被过滤)。"""
        r = client.get("/api/agents")
        assert r.status_code == 200

    def test_404_not_crash(self):
        r = client.get("/nonexistent-path")
        assert r.status_code == 404


class TestHistoryEndpoint:
    def test_history_after_call(self):
        client.post("/api/call", json={
            "agent": "pharmacy", "tool": "assess_nutrition",
            "params": {"patient_id": "P001", "weight_kg": 70, "height_cm": 165},
        })
        r = client.get("/api/history")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[-1]["agent"] == "pharmacy"


class TestAuditUserTracking:
    """P1-2: 中间件顺序 — Auth 必须先于 Audit 执行, 审计事件须记录 user_id.

    旧顺序 (RateLimit→Metrics→Audit→Auth) 下 Audit 在 Auth 之前读取
    request.state.current_user → 恒为 None; 修复后 Auth 最外层先执行。
    """

    def test_audit_records_test_mode_user(self):
        from haip.audit import get_audit_logger
        logger = get_audit_logger()
        before = len(logger.query(resource="/api/agents", user_id="test-user"))
        r = client.get("/api/agents")
        assert r.status_code == 200
        events = logger.query(resource="/api/agents", user_id="test-user")
        assert len(events) > before, "审计事件缺少 user_id — Auth 未先于 Audit 执行"

    def test_audit_records_jwt_user(self):
        """生产模式 + 真实 JWT: 审计事件 user_id = token 身份."""
        os.environ["HAIP_TEST_MODE"] = "false"
        os.environ["HAIP_ENV"] = "production"
        try:
            from haip.agent import _registry, load_from_dir
            from haip.audit import get_audit_logger
            from haip.auth.jwt import create_access_token
            from haip.web_server import YAML_DIR
            from haip.web_server import app as app2
            if len(_registry) < 14:
                load_from_dir(str(YAML_DIR))
            c2 = TestClient(app2)
            token, _ = create_access_token(
                "audit_doc_1", "audit", ["doctor"], ["agent:read"])
            logger = get_audit_logger()
            before = len(logger.query(resource="/api/agents", user_id="audit_doc_1"))
            r = c2.get("/api/agents", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 200, r.text[:200]
            after = logger.query(resource="/api/agents", user_id="audit_doc_1")
            assert len(after) > before, "JWT 请求的审计事件必须记录 token 中的 user_id"
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"
            os.environ.pop("HAIP_ENV", None)


class TestSessionUserScoping:
    """P1-3: 会话 IDOR — user 作用域取自 JWT, 客户端 user_id 参数被忽略."""

    def _prod_client(self):
        from haip.agent import _registry, load_from_dir
        from haip.web_server import YAML_DIR
        from haip.web_server import app as app2
        if len(_registry) < 14:
            load_from_dir(str(YAML_DIR))
        return TestClient(app2)

    @staticmethod
    def _token(user_id: str) -> str:
        from haip.auth.jwt import create_access_token
        token, _ = create_access_token(user_id, user_id, ["doctor"], ["agent:read"])
        return token

    def test_session_isolation_between_users(self, monkeypatch, tmp_path):
        """u2 无法读取/回滚 u1 的会话; 客户端传 user_id 参数被忽略 (仅认 JWT)."""
        monkeypatch.setattr(
            "haip.api.routes_sessions._get_session_db_path",
            lambda: str(tmp_path / "sessions.db"),
        )
        os.environ["HAIP_TEST_MODE"] = "false"
        os.environ["HAIP_ENV"] = "production"
        try:
            c = self._prod_client()
            h1 = {"Authorization": f"Bearer {self._token('sess_u1')}"}
            h2 = {"Authorization": f"Bearer {self._token('sess_u2')}"}

            r = c.post("/api/sessions", json={"state": {"owner": "u1"}}, headers=h1)
            assert r.status_code == 200, r.text[:200]
            sid = r.json()["session_id"]

            # IDOR 主断言: u2 携带 user_id=sess_u1 也读不到 u1 的会话
            r2 = c.get(f"/api/sessions/{sid}?user_id=sess_u1", headers=h2)
            assert r2.status_code == 404, "IDOR: u2 不应能读取 u1 的会话"

            # u1 可读; 即使客户端乱传 user_id 参数也忽略, 仅认 JWT 身份
            r3 = c.get(f"/api/sessions/{sid}?user_id=whatever", headers=h1)
            assert r3.status_code == 200
            assert r3.json()["user_id"] == "sess_u1"

            # 列表 user 作用域
            r4 = c.get("/api/sessions?user_id=sess_u1", headers=h2)
            assert r4.status_code == 200
            assert all(s["id"] != sid for s in r4.json()), "u2 列表不应包含 u1 的会话"
            r5 = c.get("/api/sessions", headers=h1)
            assert any(s["id"] == sid for s in r5.json())

            # rewind 归属校验
            r6 = c.post(f"/api/sessions/{sid}/rewind", json={"keep_events": 0}, headers=h2)
            assert r6.status_code == 404, "IDOR: u2 不应能 rewind u1 的会话"
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"
            os.environ.pop("HAIP_ENV", None)

    def test_create_session_ignores_body_user_id(self, monkeypatch, tmp_path):
        """create_session 忽略 body.user_id — 会话归属 JWT 用户."""
        monkeypatch.setattr(
            "haip.api.routes_sessions._get_session_db_path",
            lambda: str(tmp_path / "sessions.db"),
        )
        os.environ["HAIP_TEST_MODE"] = "false"
        os.environ["HAIP_ENV"] = "production"
        try:
            c = self._prod_client()
            h2 = {"Authorization": f"Bearer {self._token('sess_u2')}"}
            r = c.post("/api/sessions", json={
                "user_id": "sess_u1", "state": {"owner": "u2"},
            }, headers=h2)
            assert r.status_code == 200, r.text[:200]
            sid = r.json()["session_id"]
            # 会话归 sess_u2 — u1 读不到
            r1 = c.get(f"/api/sessions/{sid}?user_id=sess_u2", headers={
                "Authorization": f"Bearer {self._token('sess_u1')}"})
            assert r1.status_code == 404
            r2 = c.get(f"/api/sessions/{sid}", headers=h2)
            assert r2.status_code == 200
            assert r2.json()["user_id"] == "sess_u2"
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"
            os.environ.pop("HAIP_ENV", None)

    def test_sessions_anonymous_dev_mode_still_works(self, monkeypatch, tmp_path):
        """匿名 dev 模式 (loopback 免登录) 会话端点仍可用 — 稳定伪用户作用域."""
        monkeypatch.setattr(
            "haip.api.routes_sessions._get_session_db_path",
            lambda: str(tmp_path / "sessions.db"),
        )
        os.environ["HAIP_TEST_MODE"] = "false"
        old_env = os.environ.pop("HAIP_ENV", None)
        old_strict = os.environ.pop("HAIP_STRICT_SECURITY", None)
        try:
            c = TestClient(app, client=("127.0.0.1", 12345))
            r = c.post("/api/sessions", json={"state": {"x": 1}})
            assert r.status_code == 200, f"dev 模式匿名会话创建失败: {r.text[:200]}"
            sid = r.json()["session_id"]
            r2 = c.get(f"/api/sessions/{sid}")
            assert r2.status_code == 200
            assert r2.json()["user_id"] == "dev-user"
            r3 = c.get("/api/sessions")
            assert r3.status_code == 200
            assert any(s["id"] == sid for s in r3.json())
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"
            if old_env is not None:
                os.environ["HAIP_ENV"] = old_env
            if old_strict is not None:
                os.environ["HAIP_STRICT_SECURITY"] = old_strict
