"""HTML Page Tests (FastAPI TestClient — no live server needed).

Covers: portal, dashboard, process pages, demo page, department matrix.
"""

from __future__ import annotations

import sys, json, re
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
        assert data['agents_loaded'] >= 48

    def test_agents_list(self):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert len(agents) >= 48
        types = {a['type'] for a in agents}
        assert 'business' in types
        assert 'specialist' in types


# ── Demo HTML (static file) ──

class TestDemoPage:
    def test_file_exists(self):
        p = ROOT / "docs" / "xhaip-agent-demo.html"
        assert p.exists()

    def test_has_48_agents(self):
        p = ROOT / "docs" / "xhaip-agent-demo.html"
        content = p.read_text(encoding="utf-8")
        assert 'const AGENTS = [' in content
        # Count agent entries
        count = content.count('{name:"')
        assert count >= 48, f"Expected >=48 agents, found {count}"

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
        # Basic JS structure checks (not ES6 syntax validation)
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
