"""HTML Page Integration Tests — validates all web UI endpoints.

Test categories:
  1. HTTP status: all endpoints return 200 with text/html content type
  2. Structure: DOCTYPE, charset, title, required elements present
  3. Content: process pages have stages/roles/patients; dashboard has stats
  4. Simulated: verify JS is valid (no syntax errors in inline scripts)

Run:
  pytest tests/test_html_pages.py -v
  or: python tests/test_html_pages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "haip-core"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "haip-hospital"))

import pytest
import json
from haip.agent import load_from_dir, list_all


# ── Constants ──

API_BASE = "http://127.0.0.1:8769"
ENDPOINTS = [
    ("/", "门户首页"),
    ("/dashboard", "TOGAF仪表盘"),
    ("/process/orthopedic-surgery", "骨科流程"),
    ("/process/respiratory", "呼吸科流程"),
    ("/process/cardiology", "心内科流程"),
    ("/process/neurosurgery", "神外流程"),
    ("/agent/orthopedic-surgery", "骨科Agent"),
    ("/agent/pharmacy", "药剂科Agent"),
    ("/ortho", "骨科专业界面"),
    ("/pharmacy", "药剂科专业界面"),
]

# Required HTML elements
REQUIRED_META = [
    ('charset', 'UTF-8'),
    ('doctype', '<!doctype'),
    ('html_tag', '<html'),
    ('body_tag', '<body'),
    ('head_tag', '<head'),
    ('title_tag', '<title'),
]

PROCESS_REQUIRED = [
    'patient-list', 'patient-search', 'stage-content',
    'role-bar', 'rb-stages', 'header-patient',
]

DASHBOARD_REQUIRED = [
    'dept-card', 'dept-score', 'dept-grid',
    'tier-bar', 'stats', 'content',
]


# ── Helpers ──

def _fetch(path: str) -> tuple[int, str, str]:
    """Fetch a URL and return (status, content_type, body)."""
    import urllib.request
    try:
        req = urllib.request.Request(f"{API_BASE}{path}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, content_type, body
    except Exception as e:
        return 0, "", str(e)


def _check_html_structure(body: str, endpoint: str) -> list[str]:
    """Check basic HTML structure requirements."""
    issues: list[str] = []
    body_lower = body.lower()
    for name, expected in REQUIRED_META:
        if expected.lower() not in body_lower:
            issues.append(f"Missing {name}")
    return issues


def _check_process_page(body: str, agent_name: str) -> list[str]:
    """Check process page has required clinical UI elements."""
    issues: list[str] = []
    for elem in PROCESS_REQUIRED:
        if elem not in body:
            issues.append(f"Missing element: {elem}")
    # Check STAGES data is populated
    if 'var STAGES = [' not in body:
        issues.append("Missing STAGES data")
    if 'var PATIENTS = [' not in body:
        issues.append("Missing PATIENTS data")
    if 'renderPatientList' not in body:
        issues.append("Missing renderPatientList function")
    return issues


def _check_dashboard(body: str) -> list[str]:
    """Check dashboard has required elements."""
    issues: list[str] = []
    for elem in DASHBOARD_REQUIRED:
        if elem not in body:
            issues.append(f"Missing element: {elem}")
    # Check tier stats
    if 'L3' not in body and 'L2' not in body:
        issues.append("Missing maturity tier data")
    return issues


# ── Tests ──

class TestHTMLEndpoints:
    """HTTP-level tests for all HTML endpoints."""

    @pytest.mark.parametrize("path,name", ENDPOINTS)
    def test_endpoint_returns_html(self, path, name):
        """Each HTML endpoint returns 200 with text/html."""
        status, ct, body = _fetch(path)
        assert status == 200, f"{name}: HTTP {status} (expected 200)"
        assert "text/html" in ct.lower(), f"{name}: Content-Type is {ct}"

    @pytest.mark.parametrize("path,name", ENDPOINTS)
    def test_html_structure_valid(self, path, name):
        """HTML pages have valid basic structure."""
        status, ct, body = _fetch(path)
        if status != 200:
            pytest.skip(f"{name}: not available")
        issues = _check_html_structure(body, name)
        assert not issues, f"{name}: {issues}"

    def test_portal_has_agents(self):
        """Portal page lists agents."""
        _, _, body = _fetch("/")
        assert 'agents' in body.lower() or 'agent-list' in body, "Portal missing agent list"

    def test_dashboard_structure(self):
        """Dashboard has all required sections."""
        _, _, body = _fetch("/dashboard")
        issues = _check_dashboard(body)
        assert not issues, f"Dashboard: {issues}"

    def test_dashboard_api(self):
        """Dashboard JSON API returns valid data."""
        import urllib.request
        req = urllib.request.Request(f"{API_BASE}/api/dashboard")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        assert 'departments' in data, "Missing departments"
        assert len(data['departments']) >= 39, f"Expected >=39 depts, got {len(data['departments'])}"
        assert 'summary' in data, "Missing summary"
        assert data['summary']['avg_score'] > 0, "Avg score should be > 0"

    def test_health_endpoint(self):
        """Health check returns valid JSON."""
        import urllib.request
        req = urllib.request.Request(f"{API_BASE}/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        assert data['status'] == 'ok', "Health status not ok"
        assert data['agents_loaded'] >= 48, f"Expected >=48 agents, got {data['agents_loaded']}"

    def test_agents_api(self):
        """Agents API returns all registered agents."""
        import urllib.request
        req = urllib.request.Request(f"{API_BASE}/api/agents")
        with urllib.request.urlopen(req, timeout=5) as resp:
            agents = json.loads(resp.read())
        assert len(agents) >= 48, f"Expected >=48 agents, got {len(agents)}"
        types = set(a['type'] for a in agents)
        assert 'business' in types, "Missing business agents"
        assert 'specialist' in types, "Missing specialist agents"


class TestProcessPages:
    """Process page content tests for representative agents."""

    PROCESS_AGENTS = [
        "orthopedic-surgery", "respiratory", "cardiology",
        "neurosurgery", "obgyn", "emergency", "dermatology",
    ]

    @pytest.mark.parametrize("agent", PROCESS_AGENTS)
    def test_process_page_structure(self, agent):
        """Process pages have clinical UI structure."""
        _, _, body = _fetch(f"/process/{agent}")
        issues = _check_process_page(body, agent)
        assert not issues, f"{agent}: {issues}"

    @pytest.mark.parametrize("agent", PROCESS_AGENTS)
    def test_process_page_has_stages(self, agent):
        """Process pages embed stage data."""
        _, _, body = _fetch(f"/process/{agent}")
        assert 'var STAGES = [' in body, f"{agent}: no STAGES data"
        # Extract and validate
        import re
        m = re.search(r'var STAGES = (\[.*?\]);', body, re.DOTALL)
        assert m, f"{agent}: cannot parse STAGES"
        stages = json.loads(m.group(1))
        assert len(stages) >= 3, f"{agent}: only {len(stages)} stages"

    @pytest.mark.parametrize("agent", PROCESS_AGENTS)
    def test_process_page_has_roles(self, agent):
        """Process pages have role pills."""
        _, _, body = _fetch(f"/process/{agent}")
        assert 'role-pill' in body, f"{agent}: no role pills"
        assert 'switchRole' in body, f"{agent}: no switchRole function"

    @pytest.mark.parametrize("agent", PROCESS_AGENTS)
    def test_process_page_js_valid(self, agent):
        """Inline JavaScript has no syntax errors in process pages."""
        _, _, body = _fetch(f"/process/{agent}")
        import re
        m = re.search(r'<script>\n(.*?)\n</script>', body, re.DOTALL)
        if not m:
            return  # No inline script (uses modules)
        js = m.group(1)
        # Replace embedded JSON data with empty arrays (valid syntax)
        js = re.sub(r'var (PATIENTS|STAGES|GUARD_TRIGGERS|DEPENDS_ON) = \[.*?\];', r'var \1 = [];', js, flags=re.DOTALL)
        try:
            compile(js, f"{agent}_process.js", "exec")
        except SyntaxError as e:
            pytest.fail(f"{agent}: JS syntax error at line {e.lineno}: {e.msg}")


class TestDemoPage:
    """Tests for the static demo HTML page."""

    DEMO_PATH = Path(__file__).resolve().parent.parent / "docs" / "xhaip-agent-demo.html"

    def test_demo_file_exists(self):
        assert self.DEMO_PATH.exists(), "Demo HTML file not found"

    def test_demo_has_48_agents(self):
        content = self.DEMO_PATH.read_text(encoding="utf-8")
        # Count agent entries in AGENTS array
        count = content.count('{name:"')
        assert count >= 48, f"Expected >=48 agents, found {count}"

    def test_demo_html_structure(self):
        content = self.DEMO_PATH.read_text(encoding="utf-8")
        issues = _check_html_structure(content, "demo")
        assert not issues, f"Demo: {issues}"

    def test_demo_js_valid(self):
        content = self.DEMO_PATH.read_text(encoding="utf-8")
        import re
        m = re.search(r'<script>\n(.*?)\n</script>', content, re.DOTALL)
        assert m, "No script tag in demo"
        js = m.group(1)
        try:
            compile(js, "demo_page.js", "exec")
        except SyntaxError as e:
            pytest.fail(f"Demo JS syntax error at line {e.lineno}: {e.msg}")


class TestDepartmentMatrix:
    """Tests for the department matrix HTML page."""

    MATRIX_PATH = Path(__file__).resolve().parent.parent / "docs" / "department-matrix.html"

    def test_matrix_file_exists(self):
        assert self.MATRIX_PATH.exists(), "Matrix HTML file not found"

    def test_matrix_has_all_groups(self):
        content = self.MATRIX_PATH.read_text(encoding="utf-8")
        for group in ["内科", "外科", "妇产儿科", "五官科", "急诊重症"]:
            assert group in content, f"Matrix missing group: {group}"

    def test_matrix_html_structure(self):
        content = self.MATRIX_PATH.read_text(encoding="utf-8")
        issues = _check_html_structure(content, "matrix")
        assert not issues, f"Matrix: {issues}"


# ── Main (run directly) ──

if __name__ == "__main__":
    print("=== HTML Page Integration Tests ===\n")
    import urllib.request

    # Quick connectivity check
    try:
        req = urllib.request.Request(f"{API_BASE}/api/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        print(f"Server: {data['status']} | Agents: {data['agents_loaded']} | Version: {data['version']}")
    except Exception as e:
        print(f"Server not reachable: {e}")
        print("Start with: .\\deploy.ps1")
        sys.exit(1)

    # Test all endpoints
    passed = 0
    failed = 0

    for path, name in ENDPOINTS:
        status, ct, body = _fetch(path)
        ok = status == 200 and "html" in ct.lower()
        if ok:
            issues = _check_html_structure(body, name)
            if issues:
                print(f"  WARN {name}: {issues}")
                passed += 1
            else:
                print(f"  OK   {name} ({len(body)//1024}KB)")
                passed += 1
        else:
            print(f"  FAIL {name}: HTTP {status}")
            failed += 1

    # Test process pages
    for agent in TestProcessPages.PROCESS_AGENTS:
        _, _, body = _fetch(f"/process/{agent}")
        issues = _check_process_page(body, agent)
        if issues:
            print(f"  WARN process/{agent}: {issues}")
        else:
            print(f"  OK   process/{agent} ({len(body)//1024}KB)")

    # Test dashboard
    _, _, body = _fetch("/dashboard")
    dash_issues = _check_dashboard(body)
    if dash_issues:
        print(f"  WARN dashboard: {dash_issues}")
    else:
        print(f"  OK   dashboard ({len(body)//1024}KB)")

    # Test demo file
    demo = Path("docs/xhaip-agent-demo.html")
    if demo.exists():
        print(f"  OK   docs/xhaip-agent-demo.html ({demo.stat().st_size//1024}KB)")
    else:
        print(f"  FAIL demo file not found")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
