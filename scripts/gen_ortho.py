"""生成 ortho UI + 验证 HTML 输出。"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital" / "modules"))

from haip.agent import get as get_agent
from haip.agent import load_from_dir
from haip.ui_render import render_agent_ui

load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))
p = get_agent("orthopedic-surgery")
tools = [{"name": t.name, "description": t.description, "input": t.input} for t in p.tools]
h = render_agent_ui(p.name, p.cn_name, p.type, p.port, tools, p.depends_on, p.guard.triggers, p.sub_agents)

# Save
with open(ROOT / "packages" / "haip-core" / "haip" / "ui_ortho.html", "w", encoding="utf-8") as f:
    f.write(h)

# Validate
labels = re.findall(r'class="tab[^"]*"[^>]*>([^<]+)', h)
print(f"Generated: {len(h)} chars")
print(f"Labels ({len(labels)}): {', '.join(labels[:15])}")
_lo, _hi = chr(0x4E00), chr(0x9FFF)
print(f"All Chinese: {all(any(_lo <= c <= _hi for c in lbl) for lbl in labels)}")
print(f"Has callTool JS: {'callTool' in h}")
print(f"Has Guard JS: {'runGuard' in h}")
print(f"Has API path: {'/api/call' in h}")
print(f"Has orthopedic-surgery: {'orthopedic-surgery' in h}")
