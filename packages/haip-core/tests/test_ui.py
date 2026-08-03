"""测试 UI 渲染输出正确性."""

import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent  # xhaip root
sys.path.insert(0, str(project_root / "packages" / "haip-core"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))

from haip.agent import _registry, load_from_dir
from haip.agent import get as get_agent
from haip.ui_render import render_agent_ui


def _render(name):
    p = get_agent(name)
    return render_agent_ui(
        p.name, p.cn_name, p.type, p.port,
        [{"name": t.name, "description": t.description, "input": t.input} for t in p.tools],
        p.depends_on, p.guard.triggers, p.sub_agents,
    )


class TestUIRender:
    def setup_method(self):
        load_from_dir(str(project_root / "packages" / "haip-hospital" / "agents" / "definitions"))

    def test_all_agents_render(self):
        for name, p in _registry.items():
            html = _render(name)
            assert len(html) > 3000, f"{name} render too short: {len(html)}"
            assert "</html>" in html

    def test_labels_are_chinese(self):
        html = _render("orthopedic-surgery")
        labels = re.findall(r'class="tab[^"]*"[^>]*>([^<]+)', html)
        assert len(labels) >= 5
        for lbl in labels:
            assert any('\u4e00' <= c <= '\u9fff' for c in lbl), f"Label not Chinese: {lbl}"

    def test_contains_js_functions(self):
        html = _render("pharmacy")
        assert "callTool" in html
        assert "runGuard" in html
        assert "agent.js" in html or "/api/call" in html

    def test_renders_tools_as_tabs(self):
        html = _render("cardio-risk")
        count = html.count('class="tab')
        assert count >= 3  # 3 tools = 3 tabs

    def test_guard_triggers_rendered(self):
        html = _render("pharmacy")
        assert "安全触发规则" in html or "Guard" in html

    def test_agent_name_in_html(self):
        html = _render("pediatrics")
        assert "儿科智能体" in html

    def test_portal_render_no_errors(self):
        """所有 Agent 渲染不报错。"""
        assert len(_registry) > 0, "No agents loaded for render test"
        for name in _registry:
            html = _render(name)
            assert len(html) > 1000, f"{name} render too short"
            assert "</html>" in html, f"{name} render missing </html>"

    def test_pain_hub_sub_agents(self):
        html = _render("pain-hub")
        assert "pain" in html.lower()

    def test_medical_record_no_error(self):
        html = _render("medical-record")
        assert len(html) > 4000, f"medical-record render too short: {len(html)}"
