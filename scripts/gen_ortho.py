"""生成 ortho UI + 验证 HTML 输出。"""
import re, sys
sys.path.insert(0, r"D:\FC\xhaip\packages\haip-core")
sys.path.insert(0, r"D:\FC\xhaip\packages\haip-hospital")
sys.path.insert(0, r"D:\FC\xhaip\packages\haip-hospital\modules")

from haip.agent import load_from_dir, get as get_agent
from haip.ui_render import render_agent_ui

load_from_dir(r"D:\FC\xhaip\packages\haip-hospital\agents\definitions")
p = get_agent("orthopedic-surgery")
tools = [{"name": t.name, "description": t.description, "input": t.input} for t in p.tools]
h = render_agent_ui(p.name, p.cn_name, p.type, p.port, tools, p.depends_on, p.guard.triggers, p.sub_agents)

# Save
with open(r"D:\FC\xhaip\packages\haip-core\haip\ui_ortho.html", "w", encoding="utf-8") as f:
    f.write(h)

# Validate
labels = re.findall(r'class="tab[^"]*"[^>]*>([^<]+)', h)
print(f"Generated: {len(h)} chars")
print(f"Labels ({len(labels)}): {', '.join(labels[:15])}")
print(f"All Chinese: {all(any('\u4e00' <= c <= '\u9fff' for c in l) for l in labels)}")
print(f"Has callTool JS: {'callTool' in h}")
print(f"Has Guard JS: {'runGuard' in h}")
print(f"Has API path: {'/api/call' in h}")
print(f"Has orthopedic-surgery: {'orthopedic-surgery' in h}")
