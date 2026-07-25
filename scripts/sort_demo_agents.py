"""Sort AGENTS in demo HTML by maturity score."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))
from haip.agent import load_from_dir

load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))
from haip.togaf.analysis import analyze_all_v2

results = analyze_all_v2()
scores = {}
for r in results:
    if r.has_agent:
        scores[r.agent_name] = r.score.total

with open(ROOT / "docs" / "xhaip-agent-demo.html", encoding='utf-8') as f:
    lines = f.readlines()

# Find AGENTS array boundaries
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'const AGENTS = [' in line:
        start_idx = i
    if start_idx is not None and line.strip() == '];':
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print('ERROR: Could not find AGENTS array')
    sys.exit(1)

# Extract lines between [ and ]
content_lines = lines[start_idx+1:end_idx]

# Parse each agent entry (one per line, format: {name:"x",cn:"y",...},)
entries = []
current = ''
for line in content_lines:
    stripped = line.strip()
    if not stripped or stripped == '];':
        continue
    current += stripped
    if current.endswith('},') or current.endswith('}'):
        # Convert JS object to Python dict
        # Replace unquoted keys with quoted ones
        js_obj = current.rstrip(',')
        try:
            # Simple parse: extract name and type
            m_name = re.search(r'name:"([^"]+)"', js_obj)
            m_type = re.search(r'type:"([^"]+)"', js_obj)
            if m_name:
                entries.append({
                    'name': m_name.group(1),
                    'type': m_type.group(1) if m_type else 'business',
                    'raw': current.rstrip(',')
                })
        except Exception:
            pass
        current = ''

print(f'Parsed {len(entries)} agent entries')

# Sort by type group then score descending
type_order = {'business': 0, 'specialist': 1, 'master_data': 2, 'architecture': 3}
entries.sort(key=lambda a: (
    type_order.get(a['type'], 99),
    -scores.get(a['name'], 0)
))

# Rebuild the lines
new_lines = lines[:start_idx+1]
for e in entries:
    new_lines.append('  ' + e['raw'] + ',\n')
new_lines.append('];\n')
new_lines.extend(lines[end_idx+1:])

with open(ROOT / "docs" / "xhaip-agent-demo.html", 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'Sorted {len(entries)} agents by maturity')
for e in entries[:5]:
    s = scores.get(e['name'], '?')
    print(f'  {s:3d} {e["name"]}')
print('  ...')
for e in entries[-3:]:
    s = scores.get(e['name'], '?')
    print(f'  {s:3d} {e["name"]}')
