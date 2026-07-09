"""测试 UI 渲染输出正确性."""

import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent  # xhaip root
sys.path.insert(0, str(project_root / "packages" / "haip-core"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))

from haip.ui_render import render_agent_ui  # noqa: E402
from haip.agent import load_from_dir, get as get_agent, _registry  # noqa: E402


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
            assert len(html) > 5000, f"{name} render too short"
            assert "</html>" in html

    def test_labels_are_chinese(self):
        html = _render("orthopedic-surgery")
        labels = re.findall(r'class="tab[^"]*"[^>]*>([^<]+)', html)
        assert len(labels) >= 5
        for l in labels:
            assert any('\u4e00' <= c <= '\u9fff' for c in l), f"Label not Chinese: {l}"

    def test_contains_js_functions(self):
        html = _render("pharmacy")
        assert "callTool" in html
        assert "runGuard" in html
        assert "/api/call" in html
        assert "/api/guard" in html

    def test_renders_tools_as_tabs(self):
        html = _render("cardio-risk")
        count = html.count('class="tab')
        assert count >= 3  # 3 tools = 3 tabs

    def test_guard_triggers_rendered(self):
        html = _render("pharmacy")
        assert "高危触发" in html

    def test_agent_name_in_html(self):
        html = _render("pediatrics")
        assert "儿科智能体" in html

    def test_portal_render_no_errors(self):
        """所有 Agent 渲染不报错。"""
        for name in _registry:
            _render(name)

    def test_pain_hub_sub_agents(self):
        html = _render("pain-hub")
        assert "pain" in html.lower()

    def test_medical_record_no_error(self):
        html = _render("medical-record")
        assert len(html) > 5000
