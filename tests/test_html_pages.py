"""HTML Page Tests (FastAPI TestClient — no live server needed).

Covers: portal, dashboard, process pages, demo page, department matrix.
"""

from __future__ import annotations

import sys
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))

import pytest
from fastapi.testclient import TestClient
from haip.agent import load_from_dir

# Load agents once
load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))
from haip.web_server import app

client = TestClient(app)


# ── Helpers ──

def _check_html(resp, endpoint: str) -> list[str]:
    issues: list[str] = []
    body = resp.text.lower()
    for tag in ['<!doctype', '<html', '<body', '<head', '<title']:
        if tag not in body:
            issues.append(f"Missing {tag}")
    return issues


def _check_process_body(body: str) -> list[str]:
    issues: list[str] = []
    for elem in ['patient-list', 'stage-content', 'role-pill', 'rb-stages']:
        if elem not in body:
            issues.append(f"Missing {elem}")
    if 'renderPatientList' not in body:
        issues.append("Missing renderPatientList")
    return issues


# ── Basic Endpoints ──

class TestBasicEndpoints:
    endpoints = [
        ("/", "portal"),
        ("/dashboard", "dashboard"),
        ("/process/orthopedic-surgery", "ortho-process"),
        ("/process/respiratory", "resp-process"),
        ("/agent/orthopedic-surgery", "ortho-agent"),
        ("/agent/pharmacy", "pharm-agent"),
        ("/ortho", "ortho-ui"),
        ("/pharmacy", "pharm-ui"),
    ]

    @pytest.mark.parametrize("path,name", endpoints)
    def test_200_html(self, path, name):
        resp = client.get(path)
        assert resp.status_code == 200, f"{name}: {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")

    @pytest.mark.parametrize("path,name", endpoints)
    def test_html_structure(self, path, name):
        resp = client.get(path)
        issues = _check_html(resp, name)
        assert not issues, f"{name}: {issues}"


# ── Process Pages ──

class TestProcessPages:
    agents = ["orthopedic-surgery", "respiratory", "cardiology", "neurosurgery",
              "obgyn", "emergency", "dermatology"]

    @pytest.mark.parametrize("agent", agents)
    def test_structure(self, agent):
        resp = client.get(f"/process/{agent}")
        assert resp.status_code == 200
        issues = _check_process_body(resp.text)
        assert not issues, f"{agent}: {issues}"

    @pytest.mark.parametrize("agent", agents)
    def test_has_stages_data(self, agent):
        resp = client.get(f"/process/{agent}")
        # STAGES data embedded as JS variable
        assert 'STAGES' in resp.text, f"{agent}: no STAGES var"

    @pytest.mark.parametrize("agent", agents)
    def test_has_role_pills(self, agent):
        resp = client.get(f"/process/{agent}")
        assert 'switchRole' in resp.text, f"{agent}: no role switching"


# ── Workflow Pages ──

class TestWorkflowPages:
    def test_workflow_page_200(self):
        resp = client.get("/workflow/orthopedic-surgery")
        assert resp.status_code == 200

    def test_workflow_has_patients(self):
        """数字病人数据必须嵌入页面 (patients.json dict 格式)."""
        resp = client.get("/workflow/orthopedic-surgery")
        m = re.search(r"var PATIENTS=(\[.*?\]);\n", resp.text, re.DOTALL)
        assert m, "no PATIENTS var"
        patients = json.loads(m.group(1))
        assert len(patients) > 0, "PATIENTS is empty"
        assert all("patient_id" in p for p in patients)

    def test_workflow_patients_compatible(self):
        """嵌入的患者应与 agent 兼容."""
        resp = client.get("/workflow/orthopedic-surgery")
        m = re.search(r"var PATIENTS=(\[.*?\]);\n", resp.text, re.DOTALL)
        assert m
        patients = json.loads(m.group(1))
        assert patients, "PATIENTS is empty"
        for p in patients:
            assert "orthopedic-surgery" in p.get("compatible_agents", []), (
                f"{p.get('patient_id')} 与 orthopedic-surgery 不兼容"
            )


    # JS id 契约已由 test_ui_contracts.py C1 全站覆盖


    def test_workflow_agent_var_is_agent_name(self):
        """JS AGENT 变量必须是 agent 技术名, 不能被角色名遮蔽."""
        resp = client.get("/workflow/orthopedic-surgery")
        m = re.search(r"var AGENT='([^']+)'", resp.text)
        assert m, "no AGENT var"
        assert m.group(1) == "orthopedic-surgery", f"AGENT 被污染为: {m.group(1)}"


# ── Dashboard ──

class TestDashboard:
    def test_dashboard_html(self):
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert 'dept-card' in resp.text
        assert 'tier-bar' in resp.text

    def test_dashboard_api(self):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert 'depts' in data
        assert len(data['depts']) >= 39
        assert data['avg_score'] > 0


# ── API ──

class TestAPI:
    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'ok'
        expected = len(_load_yaml_agents())
        assert data['agents_loaded'] >= expected, f"Expected >= {expected}, got {data['agents_loaded']}"

    def test_agents_list(self):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        expected = len(_load_yaml_agents())
        assert len(agents) >= expected, f"Expected >= {expected}, got {len(agents)}"
        types = {a['type'] for a in agents}
        assert 'business' in types
        assert 'specialist' in types


# ── Demo HTML (static file) ──

def _load_yaml_agents() -> dict[str, dict]:
    """从 YAML definitions 加载 source-of-truth agent 列表."""
    import yaml
    agents = {}
    def_dir = ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
    for f in sorted(def_dir.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        agents[data["name"]] = {
            "type": data.get("type", "unknown"),
            "cn_name": data.get("cn_name", ""),
            "port": data.get("port", 0),
        }
    return agents


def _parse_html_agents() -> dict[str, dict]:
    """从 demo.html 的 const AGENTS = [...] 中解析 agent 列表."""
    import ast
    p = ROOT / "docs" / "xhaip-agent-demo.html"
    content = p.read_text(encoding="utf-8")

    # 提取 AGENTS 数组文本
    m = re.search(r"const AGENTS = \[(.*?)\];", content, re.DOTALL)
    assert m, "未找到 const AGENTS = [...] 定义"
    array_text = m.group(1)

    # 逐对象正则提取 (name, cn, type, port)
    entries = re.findall(
        r'\{name:"([^"]+)",cn:"([^"]*)",type:"([^"]+)",port:(\d+)[^}]*\}',
        array_text,
    )
    agents = {}
    for name, cn, atype, port_str in entries:
        agents[name] = {
            "type": atype,
            "cn_name": cn,
            "port": int(port_str),
        }
    return agents


class TestDemoPage:
    def test_file_exists(self):
        assert (ROOT / "docs" / "xhaip-agent-demo.html").exists()

    def test_agent_count_matches_yaml(self):
        """HTML 与 YAML 的 agent 数量一致."""
        yaml_agents = _load_yaml_agents()
        html_agents = _parse_html_agents()
        assert len(html_agents) == len(yaml_agents), (
            f"HTML 有 {len(html_agents)} 个 agent，YAML 有 {len(yaml_agents)} 个"
        )

    def test_all_yaml_agents_in_html(self):
        """YAML 中定义的每个 agent 都出现在 HTML 中."""
        yaml_agents = _load_yaml_agents()
        html_agents = _parse_html_agents()
        yaml_names = set(yaml_agents)
        html_names = set(html_agents)
        missing = yaml_names - html_names
        assert not missing, f"HTML 中缺少: {missing}"

    def test_all_html_agents_in_yaml(self):
        """HTML 中的每个 agent 都有对应的 YAML 定义."""
        yaml_agents = _load_yaml_agents()
        html_agents = _parse_html_agents()
        yaml_names = set(yaml_agents)
        html_names = set(html_agents)
        extra = html_names - yaml_names
        assert not extra, f"HTML 中存在未定义的 agent: {extra}"

    def test_agent_types_consistent(self):
        """HTML 中每 agent 的 type 与 YAML 一致."""
        yaml_agents = _load_yaml_agents()
        html_agents = _parse_html_agents()
        mismatches = []
        for name in set(yaml_agents) & set(html_agents):
            yt = yaml_agents[name]["type"]
            ht = html_agents[name]["type"]
            if yt != ht:
                mismatches.append(f"{name}: YAML={yt} HTML={ht}")
        assert not mismatches, f"type 不一致:\n  " + "\n  ".join(mismatches)

    def test_agent_ports_consistent(self):
        """HTML 中每 agent 的 port 与 YAML 一致 (port=0 视为可选)."""
        yaml_agents = _load_yaml_agents()
        html_agents = _parse_html_agents()
        mismatches = []
        for name in set(yaml_agents) & set(html_agents):
            yp = yaml_agents[name]["port"]
            hp = html_agents[name]["port"]
            if yp != 0 and hp != 0 and yp != hp:
                mismatches.append(f"{name}: YAML={yp} HTML={hp}")
        assert not mismatches, f"port 不一致:\n  " + "\n  ".join(mismatches)

    def test_html_structure(self):
        p = ROOT / "docs" / "xhaip-agent-demo.html"
        content = p.read_text(encoding="utf-8")
        for tag in ['<!DOCTYPE', '<html', '<body', '<script>']:
            assert tag in content, f"Missing {tag}"

    def test_js_structure(self):
        p = ROOT / "docs" / "xhaip-agent-demo.html"
        content = p.read_text(encoding="utf-8")
        m = re.search(r'<script>\n(.*?)\n</script>', content, re.DOTALL)
        assert m, "No script tag"
        js = m.group(1)
        assert 'const AGENTS = [' in js
        assert 'function selectAgent' in js
        assert 'function callTool' in js
        assert len(js) > 1000


# ── Department Matrix ──

class TestDepartmentMatrix:
    def test_file_exists(self):
        assert (ROOT / "docs" / "department-matrix.html").exists()

    def test_has_all_groups(self):
        content = (ROOT / "docs" / "department-matrix.html").read_text(encoding="utf-8")
        for group in ["内科", "外科", "妇产儿科", "五官科", "急诊重症"]:
            assert group in content, f"Missing group: {group}"
