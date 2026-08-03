"""Verify v2.0 Phase 0 deliverables."""
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "packages" / "haip-core"))
sys.path.insert(0, str(PROJECT / "packages" / "haip-hospital"))

from haip.agent import list_all, load_from_dir

defs_dir = PROJECT / "packages" / "haip-hospital" / "agents" / "definitions"
count = load_from_dir(str(defs_dir))
registry = list_all()

total = len(registry)
deep = sum(1 for a in registry.values() if getattr(a, 'trust_tier', 'standard') == 'deep')
standard = sum(1 for a in registry.values() if getattr(a, 'trust_tier', 'standard') == 'standard')
light = sum(1 for a in registry.values() if getattr(a, 'trust_tier', 'standard') == 'light')

print("=== v2.0 Phase 0 Verification ===")
print(f"Agents: {total} total = {deep} deep + {standard} standard + {light} light")
print(f"New: anesthesia={registry.get('anesthesia') is not None}, infection-control={registry.get('infection-control') is not None}")

# Show tier distribution
print(f"\nDeep ({deep}): {sorted([k for k,v in registry.items() if v.trust_tier == 'deep'])}")
print(f"\nStandard ({standard}): {sorted([k for k,v in registry.items() if v.trust_tier == 'standard'])}")
print(f"\nLight ({light}): {sorted([k for k,v in registry.items() if v.trust_tier == 'light'])}")

# Verify new agents
for name in ['anesthesia', 'infection-control']:
    a = registry.get(name)
    if a:
        print(f"\n[{name}] tier={a.trust_tier}, dept={a.department}, tools={len(a.tools)}")
        for t in a.tools:
            print(f"  - {t.name}: {t.handler}")
    else:
        print(f"\n[{name}] NOT LOADED")
