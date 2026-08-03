"""Check all agent handler imports — find broken ones."""
import importlib
import pathlib
import sys

import yaml

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "packages" / "haip-core"))
sys.path.insert(0, str(root / "packages" / "haip-hospital"))
sys.path.insert(0, str(root / "packages" / "haip-hospital" / "modules"))

agents_dir = root / "packages/haip-hospital/agents/definitions"
results = []
total_handlers = 0
ok_count = 0

for yf in sorted(agents_dir.glob("*.yaml")):
    data = yaml.safe_load(yf.read_text(encoding="utf-8"))
    if not data:
        continue
    agent_name = data.get("name", yf.stem)
    for tool in data.get("tools", []):
        handler = tool.get("handler", "")
        if not handler or "." not in handler:
            continue
        total_handlers += 1
        try:
            mod, fn = handler.rsplit(".", 1)
            module = importlib.import_module(mod)
            getattr(module, fn)
            ok_count += 1
        except ModuleNotFoundError:
            results.append({"agent": agent_name, "tool": tool.get("name", ""), "handler": handler, "error": "module not found"})
        except AttributeError:
            results.append({"agent": agent_name, "tool": tool.get("name", ""), "handler": handler, "error": "function not found"})
        except Exception as e:
            results.append({"agent": agent_name, "tool": tool.get("name", ""), "handler": handler, "error": str(e)[:120]})

print(f"Total handlers: {total_handlers}")
print(f"OK: {ok_count}")
print(f"Broken: {len(results)}")
print()
if results:
    print("=== BROKEN HANDLERS ===")
    for r in results:
        print(f"  [{r['agent']}] {r['tool']} => {r['handler']} | {r['error']}")
else:
    print("  All handlers OK")
