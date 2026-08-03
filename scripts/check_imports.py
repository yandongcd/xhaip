"""Check all handler references against actual importable Python modules."""
import importlib
import pathlib
import sys

import yaml

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "packages" / "haip-core"))
sys.path.insert(0, str(root / "packages" / "haip-hospital"))
sys.path.insert(0, str(root / "packages" / "haip-hospital" / "modules"))

agents_dir = root / "packages/haip-hospital/agents/definitions"
total = 0
ok = 0
missing_module = 0
missing_func = 0
other_err = 0
missing_list = []

for yf in sorted(agents_dir.glob("*.yaml")):
    data = yaml.safe_load(yf.read_text(encoding="utf-8"))
    if not data:
        continue
    agent = data["name"]
    for tool in data.get("tools", []):
        handler = tool.get("handler", "")
        if not handler or "." not in handler:
            continue
        total += 1
        try:
            mod, fn = handler.rsplit(".", 1)
            module = importlib.import_module(mod)
            if hasattr(module, fn):
                ok += 1
            else:
                missing_func += 1
                missing_list.append(f"[{agent}] {handler} -> module '{mod}' has no '{fn}'")
        except ModuleNotFoundError:
            missing_module += 1
            missing_list.append(f"[{agent}] {handler} -> module '{mod}' NOT FOUND")
        except Exception as e:
            other_err += 1
            missing_list.append(f"[{agent}] {handler} -> {e}")

print(f"Total handlers: {total}")
print(f"OK: {ok}")
print(f"Module not found: {missing_module}")
print(f"Function not found: {missing_func}")
print(f"Other errors: {other_err}")
print()
if missing_list:
    print("=== ISSUES ===")
    for m in missing_list:
        print(f"  {m}")
